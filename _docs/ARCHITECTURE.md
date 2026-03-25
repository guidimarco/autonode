# Autonode - Architecture (current state)

## Principio centrale: core puro e framework-agnostic

Il package `core/` contiene solo logica di dominio, dataclass `*Model` e port astratte.
Le integrazioni concrete stanno in `infrastructure/`.
`application/` orchestra il workflow (LangGraph) usando esclusivamente contratti del core.
`presentation/` espone l'entrypoint CLI.

---

## Layout reale

```text
autonode/
├── config_examples/              # Templates
│   ├── agents.example.yaml
│   └── workflow.example.yaml
├── src/autonode/
│   ├── core/
│   │   ├── agents/
│   │   │   ├── models.py          # AgentModel
│   │   │   ├── parser.py          # parse_agents()
│   │   │   └── ports.py           # AgentFactoryPort
│   │   ├── sandbox/
│   │   │   ├── exceptions.py      # SandboxImageNotFoundError
│   │   │   ├── models.py          # WorkspaceBindingModel, ExecutionEnvironmentModel
│   │   │   └── ports.py           # SandboxProviderPort
│   │   ├── logging.py             # AutonodeLogger + LoggerFactory (contract + registry)
│   │   ├── tools/
│   │   │   └── ports.py           # ToolPort, ToolRegistryPort
│   │   └── workflow/
│   │       ├── models.py          # WorkflowModel, WorkflowNodeModel, RoutingRule, …
│   │       ├── parser.py          # parse_workflow() — validazione topologia (NetworkX)
│   │       └── ports.py           # VCSProviderPort
│   ├── application/
│   │   ├── use_cases/
│   │   │   ├── run_workflow_uc.py # RunWorkflowUseCase
│   │   │   └── cleanup_uc.py      # CleanupSessionsUseCase
│   │   └── workflow/
│   │       ├── builder.py         # build_graph() — compila StateGraph LangGraph
│   │       ├── post_processing.py # run_post_processing()
│   │       └── state.py           # GraphWorkflowState (`review_verdict`), make_initial_graph_state()
│   ├── infrastructure/
│   │   ├── config/
│   │   │   ├── agents_schema.py   # AgentsYamlSchema (Pydantic) + to_core()
│   │   │   ├── workflow_schema.py # WorkflowYamlSchema (Pydantic) + to_core()
│   │   │   └── loader.py          # load_workflow_config(), load_agents_config()
│   │   ├── logging/
│   │   │   └── stderr_adapter.py  # StandardErrorAutonodeLogger su sys.stderr
│   │   ├── factory/
│   │   │   ├── agent_factory.py # LangChainAgentFactory (AgentFactoryPort)
│   │   │   └── review_verdict_schema.py # ReviewVerdictSchema (Pydantic) → ReviewVerdictModel
│   │   ├── sandbox/
│   │   │   └── docker_adapter.py  # DockerAdapter (SandboxProviderPort)
│   │   ├── tools/
│   │   │   ├── registry.py        # ToolRegistry (ToolRegistryPort)
│   │   │   ├── path_guard.py      # PathGuard, resolve_under_root()
│   │   │   ├── ignore_rules.py    # should_skip(), SKIP_DIR_NAMES
│   │   │   ├── repository_map.py  # make_get_repository_map_tool()
│   │   │   └── codebase_search.py # make_search_codebase_tool()
│   │   ├── vcs/
│   │   │   └── git_worktree_provider.py  # GitWorktreeProvider (VCSProviderPort)
│   │   └── tracing.py             # configure_tracing(), get_run_metadata()
│   └── presentation/
│       ├── cli.py                 # main() — entrypoint CLI
│       ├── cleanup/
│       │   ├── handlers.py        # run_cleanup()
│       │   └── models.py          # CleanupRequest (Pydantic)
│       ├── mcp/
│       │   ├── server.py          # FastMCP stdio + tool ``run_workflow`` → handler workflow
│       │   ├── models.py          # mapping risposta MCP (success/error)
│       │   └── stdio_safe.py      # logging su stderr + isolamento fd stdout durante run
│       └── workflow/
│           ├── handlers.py        # run_workflow()
│           └── models.py          # WorkflowRunRequest (Pydantic)
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

- `presentation/cli.py`: entrypoint operativo. Sottocomando `cleanup` per worktree sotto `.autonode/worktrees/` e container `autonode-sandbox-*`. Sottocomando `mcp` per avviare il server MCP su stdio. Sottocomando default per eseguire un workflow.
- Dopo ogni run workflow, `RunWorkflowUseCase` rimuove in `finally` il container sandbox e il worktree di sessione; il **branch locale** `autonode/session-*` resta nel repo (nessun `git push` nel flusso standard).
- `infrastructure/vcs/git_worktree_provider.py`: provisioning worktree, commit locale (`commit_changes`), rimozione worktree per sessione / globale, branch `autonode/session-*`, e `cleanup_orphaned_worktrees` (TTL) usato dal `cleanup --prune` della CLI.
- MCP (stdio): presente in `presentation/mcp/`; tool `run_workflow` invoca `presentation/workflow/handlers.run_workflow` con logging su stderr e isolamento temporaneo di fd stdout durante l’esecuzione. Path YAML di default: `config/workflow.yaml` e `config/agents.yaml` relativi alla root del repository (risolti da `Path(__file__)` in `server.py`). API HTTP remote: non presenti nel codice corrente.

---

## Nota su VCS

Il contratto `VCSProviderPort` è obbligatorio in `build_graph`.
Il CLI usa `GitWorktreeProvider` in `infrastructure/vcs/git_worktree_provider.py`; nei test di compilazione si usa uno stub dedicato sotto `tests/stubs/`.

Il provisioning del worktree avviene **prima** dell'invocazione del grafo (nel CLI bootstrap).
Il nodo `vcs_provision` non è più supportato nel grafo: se presente in un YAML, la compilazione fallisce con errore esplicito.
I nodi `vcs_sync` effettuano **commit locali** nel worktree tramite `VCSProviderPort.commit_changes` (nessun push verso remote).
