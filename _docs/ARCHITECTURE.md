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
│   │   ├── constants.py            # Default paths, checkpoint DB path, token budget default
│   │   ├── logging.py              # AutonodeLogger + LoggerFactory (contract + registry)
│   │   ├── tools/                  # Tools: ports and registry
│   │   └── workflow/               # Workflow: models, parser and ports
│   │
│   ├── application/                # Use Cases
│   │   ├── use_cases/              # RunWorkflow, CleanupSessions
│   │   ├── agents/                 # LangGraph agent/tool node injectors (shared helpers)
│   │   └── workflow/               # post processing, state, factories (registry)
│   │
│   ├── infrastructure/             # Adapters
│   │   ├── config/                 # Config Validation Schemas (YAML) and loaders
│   │   ├── logging/                # StandardErrorAutonodeLogger
│   │   ├── factory/                # LangChain factory and verdict schema
│   │   ├── sandbox/                # Docker adapter
│   │   ├── tools/                  # Tool registry and tools: aider, search codebase, ...
│   │   ├── vcs/                    # Git adapter
│   │   ├── telemetry/              # TokenBudgetCallback (session token cap)
│   │   └── tracing.py              # configure_tracing(), get_run_metadata()
│   │
│   └── presentation/               # Entrypoints, handlers and validations (pydantic)
│       ├── cli.py                  # CLI entrypoint
│       ├── api.py                  # FastAPI gateway (`POST /execute`)
│       ├── cleanup/                # Cleanup handlers and models
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
- all'avvio, `presentation/cli.py` e `autonode.__main__` (server) invocano tale bootstrap.

---

## Modelli e validazione

- Core:
  - dataclass con suffisso `Model`
  - esempio: `WorkflowModel` (factory selector + runtime params), `PostProcessStepModel`
- Infrastructure:
  - Pydantic schema con suffisso `Schema` (qui `*YamlSchema`)
  - mapping esplicito con `to_core()`

Flusso:

1. `infrastructure/config/*_schema.py`: valida forma e tipi dell'input YAML.
2. `to_core()`: converte in dataclass del core.
3. `core/workflow/parser.py`: pass-through del modello già validato al confine.

### Workflow YAML (factory selector)

Il file YAML (`version: 2`) non descrive più nodi e archi: dichiara solo **quale factory Python** usare e i **parametri** (`params`) passati alla factory.

- Schema Pydantic: `WorkflowYamlSchema` in `infrastructure/config/workflow_schema.py` → `WorkflowModel` nel core (unico scudo di validazione strutturale dell’input YAML).
- Caricamento: `load_workflow_config()` in `infrastructure/config/loader.py`.

Le funzioni che compilano il grafo LangGraph si registrano in `application/workflow/factories/registry.py` (`register_factory`, `FACTORY_REGISTRY`, `FactoryContext`). `RunWorkflowUseCase` risolve `WorkflowModel.factory` con `get_registered_factory` e invoca la factory con un `FactoryContext` (include `session_python_logger` per tracciare `[AGENT_THOUGHT]` da `inject_agent_node` e dal nodo reviewer in `dev_review_loop`); la topologia del grafo resta interamente nella factory. Gli helper riusabili per nodi agente/tool LangGraph vivono in `application/agents/nodes.py` (`inject_agent_node`, `inject_tool_node`).

**Telemetria token (hard limit):** `infrastructure/telemetry/token_callback.py` espone `TokenBudgetCallback` (LangChain `BaseCallbackHandler`) e `TokenBudgetExceeded`. Con `token_budget > 0`, il callback somma i `total_tokens` riportati in `LLMResult.llm_output` e interrompe l'esecuzione al superamento del budget; con budget `0` (default in `core.constants`) non si applica alcun limite finché non viene fissato un valore positivo dalla config o dal runtime.

---

## Stato corrente degli entrypoint

- `presentation/cli.py`: entrypoint operativo. Sottocomando `cleanup` per sessioni sotto `{REPOS_ROOT}/autonode_docker/<session_id>/` e container `autonode-sandbox-*`. Sottocomando default per eseguire un workflow.
- `presentation/api.py`: gateway HTTP (FastAPI) con `POST /execute` protetto da `X-API-Key` (`AUTONODE_API_KEY`). Risponde **202 Accepted** con `session_id` e avvia `RunWorkflowUseCase` in `BackgroundTasks` dopo aver creato le directory e scritto `status.json` (`accepted`). Lo stato macchina (`running` / `completed` / `failed`) è in `{DATA_ROOT}/<session_id>/status.json`; il log di sessione è `{DATA_ROOT}/<session_id>/session.log` (radice sessione, senza sottocartella `logs/`): ragionamento assistente (`[AGENT_THOUGHT]`), output tool/Docker dopo ogni comando, stream stdout/stderr del container sandbox `[sandbox]` (nessun mount di `DATA_ROOT` verso il container sandbox).
- Dopo ogni run workflow, `RunWorkflowUseCase` in `finally` rilascia il container sandbox, chiude i file handler del logger di sessione (`detach_session_logging`), e rimuove l’intera cartella operativa `{REPOS_ROOT}/autonode_docker/<session_id>/` (worktree + outputs). Restano sotto `{DATA_ROOT}/<session_id>/` log e `status.json`. Log globale errori di sistema: `{REPOS_ROOT}/autonode/autonode.log` (WARNING+), configurato in `install_autonode_process_logging`. Il **branch locale** `autonode/session-*` resta nel repo (nessun `git push` nel flusso standard).
- `RunWorkflowUseCase` usa checkpoint persistente SQLite (`autonode.db` in root progetto) come default quando non viene iniettato un checkpointer esterno; la continuità di stato è legata al `thread_id`.
- Hardening security:
  - `thread_id` / `session_id`: UUID v4; l’API HTTP fissa `thread_id = session_id` per correlare LangGraph e file di stato. La CLI può generare un UUID nuovo lato handler.
  - Layout: `REPOS_ROOT` è `/src` nel container; dati operativi in `{REPOS_ROOT}/autonode_docker/<session_id>/{workspace,outputs}`; persistenza log/stato in `{DATA_ROOT}/<session_id>/` (default `/data` in container, volume host dedicato). Il repository Git target è sotto `REPOS_ROOT` (validato con `ensure_git_repo_under_root`). In `setup_session_worktree` si salva il path relativo in `.source_repo` sotto la cartella Docker della sessione. Per i bind mount dei container sandbox, `HOST_PROJECTS_ROOT` mappa il prefisso host equivalente a `/src`; opzionale `HOST_DATA_ROOT` per path host equivalenti a `/data` se servissero tool che risolvono path dati (la sandbox **non** monta `DATA_ROOT`).
  - Validazione path delle config: `presentation/workflow/models.py` permette `workflow_path`/`agents_path` solo sotto cartelle `config/` (project o repo target).
  - Sandbox shell: `container_tool.docker_exec` usa `docker-py` `exec_run` con `/bin/bash -lc` e `workdir` `/workspace`; `path_guard` limita i path host al worktree e agli output sessione.
  - Error handling API: errori di validazione `repo_path` → 422; esecuzione workflow in background (errori runtime nel `status.json` e nei log).
- `infrastructure/vcs/git_worktree_provider.py`: provisioning worktree sotto `{REPOS_ROOT}/autonode_docker/<session_id>/workspace`, metadati `.source_repo`, commit locale (`commit_changes`), rimozione worktree + cartella Docker sessione, branch `autonode/session-*`, e `cleanup_orphaned_worktrees` (TTL) usato dal `cleanup --prune` della CLI.
- Path YAML di default: `core.constants.DEFAULT_WORKFLOW_CONFIG_PATH` / `DEFAULT_AGENTS_CONFIG_PATH` (`config/workflow.yaml`, `config/agents.yaml` relativi alla root del repository).

---

## Nota su VCS

Il contratto `VCSProviderPort` è obbligatorio nel `FactoryContext` passato alle graph factory.
Il CLI usa `GitWorktreeProvider` in `infrastructure/vcs/git_worktree_provider.py`; nei test di compilazione si usa uno stub dedicato sotto `tests/stubs/`.

Il provisioning del worktree avviene **prima** dell'invocazione del grafo (nel CLI bootstrap).
Il nodo `vcs_provision` non è più supportato nel grafo: se presente in un YAML, la compilazione fallisce con errore esplicito.
I nodi `vcs_sync` effettuano **commit locali** nel worktree tramite `VCSProviderPort.commit_changes` (nessun push verso remote).
