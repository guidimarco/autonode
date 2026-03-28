# Autonode - Architecture (current state)

## Principio centrale: core puro e framework-agnostic

Il package `core/` contiene solo logica di dominio, dataclass `*Model` e port astratte.
Le integrazioni concrete stanno in `infrastructure/`.
`application/` orchestra il workflow (LangGraph) usando esclusivamente contratti del core.
`presentation/` espone gli entrypoint CLI e HTTP.

---

## Layout reale

```text
autonode/
├── config_examples/                # Config Templates
│   ├── agents.example.yaml
│   └── workflow.example.yaml
├── src/autonode/
│   │
│   ├── core/                       # Core: app core logic
│   │   ├── agents/                 # Agents: models, parser and ports
│   │   ├── sandbox/                # Sandbox: models, ports and exception
│   │   ├── logging.py              # AutonodeLogger + LoggerFactory (contract + registry)
│   │   ├── tools/                  # Tools: ports and registry
│   │   └── workflow/               # Workflow: models, parser and ports
│   │
│   ├── application/                # Use Cases
│   │   ├── use_cases/              # RunWorkflow, CleanupSessions
│   │   └── workflow/               # RunWorkflow utils: builder, post processing and state
│   │
│   ├── infrastructure/             # Adapters
│   │   ├── config/                 # Config Validation Schemas (YAML) and loaders
│   │   ├── logging/                # StandardErrorAutonodeLogger
│   │   ├── factory/                # LangChain factory and verdict schema
│   │   ├── sandbox/                # Docker adapter
│   │   ├── tools/                  # Tool registry and tools: aider, search codebase, ...
│   │   ├── vcs/                    # Git adapter
│   │   └── tracing.py              # configure_tracing(), get_run_metadata()
│   │
│   └── presentation/               # Entrypoints, handlers and validations (pydantic)
│       ├── cli.py                  # CLI entrypoint
│       ├── api.py                  # FastAPI gateway (`POST /execute`)
│       ├── cleanup/                # Cleanup handlers and models
│       ├── mcp/                    # MCP entrypoint
│       └── workflow/               # Workflow handlers and models
└── tests/
  ├── testdata/
  │   ├── agents.yaml
  │   └── workflow.yaml
  ├── stubs/
  │   ├── agent_factory.py         # StubAgentFactory
  │   └── vcs_provider.py          # StubVcsProviderForCompileTests
  └── test_*.py
```

---

## Direzione delle dipendenze

| Layer            | Dipende da                                          | Non deve dipendere da                                               |
| ---------------- | --------------------------------------------------- | ------------------------------------------------------------------- |
| `core`           | stdlib + librerie algoritmiche (es. `networkx`)     | `pydantic`, `autonode.infrastructure`, LangChain/LangGraph concreti |
| `application`    | `core` + LangGraph orchestration + stdlib dataclass | adapter concreti infrastructure, Pydantic                           |
| `infrastructure` | `core` + stack runtime (Pydantic, LangChain, tools) | `presentation`                                                      |
| `presentation`   | `application` + `infrastructure`                    | -                                                                   |

---

## Contratti principali

- `core/agents/ports.py`:
  - `AgentFactoryPort`
- `core/tools/ports.py`:
  - `ToolPort`
  - `ToolRegistryPort`
- `core/workflow/ports.py`:
  - `VCSProviderPort`
- `core/sandbox/ports.py`:
  - `SandboxProviderPort`

Questi contratti disaccoppiano il dominio da adapter concreti.

Per il logging, il core espone `AutonodeLogger` e `LoggerFactory`:

- i layer interni dipendono solo da questa astrazione;
- `install_autonode_process_logging()` in `infrastructure/logging/stderr_adapter.py` configura il root logger su `sys.stderr` e chiama `LoggerFactory.set_logger(create_stderr_autonode_logger())`;
- all'avvio, `presentation/cli.py` e `presentation/mcp/stdio_safe.py` (via `run_mcp_server`) invocano tale bootstrap.

### Double stream logging (MCP e mirroring su stderr)

Su trasporto **stdio**, stdout è riservato al protocollo JSON-RPC MCP: qualsiasi byte su fd 1 corromperebbe il canale.

Il sistema combina due meccanismi:

1. **Logging applicativo su stderr** — il bootstrap (`install_autonode_process_logging`) invia i record del logging Python su `sys.stderr`, così log e protocollo restano separati.
2. **Mirroring temporaneo di fd 1 su stderr** — durante l’esecuzione del tool `run_workflow`, il context manager `isolate_process_stdout_to_stderr()` in `presentation/mcp/stdio_safe.py` esegue `dup2` così che anche codice nativo o sottoprocessi che scrivono su stdout (fd 1) finiscano sullo stesso sink di stderr; alla fine del tool il fd 1 viene ripristinato per consentire al runtime MCP di rispondere al client.

In sintesi: **double stream** = canale protocollo intatto su stdout tra le invocazioni, **tutto il rumore diagnostico e le scritture “sbagliate” su stdout durante il tool** deviati verso stderr.

---

## Modelli e validazione

- Core:
  - dataclass con suffisso `Model`
  - esempio: `AgentWorkflowNodeModel` (`structured_review` per reviewer strutturato), `RoutingToolCallsOrNextModel`, `WorkflowModel`
- Infrastructure:
  - Pydantic schema con suffisso `Schema` (qui `*YamlSchema`)
  - mapping esplicito con `to_core()`

Flusso:

1. `infrastructure/config/*_schema.py`: valida forma e tipi dell'input YAML.
2. `to_core()`: converte in dataclass del core.
3. `core/workflow/parser.py`: valida semantica/topologia del grafo.

---

## Stato corrente degli entrypoint

- `presentation/cli.py`: entrypoint operativo. Sottocomando `cleanup` per sessioni sotto `{REPOS_ROOT}/autonode_docker/<session_id>/` e container `autonode-sandbox-*`. Sottocomando `mcp` per avviare il server MCP su stdio. Sottocomando default per eseguire un workflow.
- `presentation/api.py`: gateway HTTP (FastAPI) con `POST /execute` protetto da `X-API-Key` (`AUTONODE_API_KEY`). Risponde **202 Accepted** con `session_id` e avvia `RunWorkflowUseCase` in `BackgroundTasks` dopo aver creato le directory e scritto `status.json` (`accepted`). Lo stato macchina (`running` / `completed` / `failed`) è in `{DATA_ROOT}/<session_id>/status.json`; i log di sessione e lo stream stdout/stderr della sandbox sono in `{DATA_ROOT}/<session_id>/logs/session.log` (nessun mount di `DATA_ROOT` verso il container sandbox).
- Dopo ogni run workflow, `RunWorkflowUseCase` in `finally` rilascia il container sandbox, chiude i file handler del logger di sessione (`detach_session_logging`), e rimuove l’intera cartella operativa `{REPOS_ROOT}/autonode_docker/<session_id>/` (worktree + outputs). Restano sotto `{DATA_ROOT}/<session_id>/` log e `status.json`. Log globale errori di sistema: `{REPOS_ROOT}/autonode/autonode.log` (WARNING+), configurato in `install_autonode_process_logging`. Il **branch locale** `autonode/session-*` resta nel repo (nessun `git push` nel flusso standard).
- `RunWorkflowUseCase` usa checkpoint persistente SQLite (`autonode.db` in root progetto) come default quando non viene iniettato un checkpointer esterno; la continuità di stato è legata al `thread_id`.
- Hardening security:
  - `thread_id` / `session_id`: UUID v4; l’API HTTP fissa `thread_id = session_id` per correlare LangGraph e file di stato. CLI/MCP possono generare un UUID nuovo lato handler.
  - Layout: `REPOS_ROOT` è `/src` nel container; dati operativi in `{REPOS_ROOT}/autonode_docker/<session_id>/{workspace,outputs}`; persistenza log/stato in `{DATA_ROOT}/<session_id>/` (default `/data` in container, volume host dedicato). Il repository Git target è sotto `REPOS_ROOT` (validato con `ensure_git_repo_under_root`). In `setup_session_worktree` si salva il path relativo in `.source_repo` sotto la cartella Docker della sessione. Per i bind mount dei container sandbox, `HOST_PROJECTS_ROOT` mappa il prefisso host equivalente a `/src`; opzionale `HOST_DATA_ROOT` per path host equivalenti a `/data` se servissero tool che risolvono path dati (la sandbox **non** monta `DATA_ROOT`).
  - Validazione path delle config: `presentation/workflow/models.py` permette `workflow_path`/`agents_path` solo sotto cartelle `config/` (project o repo target).
  - Sandbox shell: `container_tool.docker_exec` usa `docker-py` `exec_run` con `/bin/bash -lc` e `workdir` `/workspace`; `path_guard` limita i path host al worktree e agli output sessione.
  - Error handling API: errori di validazione `repo_path` → 422; esecuzione workflow in background (errori runtime nel `status.json` e nei log).
- `infrastructure/vcs/git_worktree_provider.py`: provisioning worktree sotto `{REPOS_ROOT}/autonode_docker/<session_id>/workspace`, metadati `.source_repo`, commit locale (`commit_changes`), rimozione worktree + cartella Docker sessione, branch `autonode/session-*`, e `cleanup_orphaned_worktrees` (TTL) usato dal `cleanup --prune` della CLI.
- MCP (stdio): presente in `presentation/mcp/`; tool `run_workflow` invoca `presentation/workflow/handlers.run_workflow` con logging su stderr e isolamento temporaneo di fd stdout durante l’esecuzione. Path YAML di default: `config/workflow.yaml` e `config/agents.yaml` relativi alla root del repository (risolti da `Path(__file__)` in `server.py`). API HTTP remote: non presenti nel codice corrente.

---

## Nota su VCS

Il contratto `VCSProviderPort` è obbligatorio in `build_graph`.
Il CLI usa `GitWorktreeProvider` in `infrastructure/vcs/git_worktree_provider.py`; nei test di compilazione si usa uno stub dedicato sotto `tests/stubs/`.

Il provisioning del worktree avviene **prima** dell'invocazione del grafo (nel CLI bootstrap).
Il nodo `vcs_provision` non è più supportato nel grafo: se presente in un YAML, la compilazione fallisce con errore esplicito.
I nodi `vcs_sync` effettuano **commit locali** nel worktree tramite `VCSProviderPort.commit_changes` (nessun push verso remote).
