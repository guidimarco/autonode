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
├── config/
│   ├── agents.yaml
│   └── workflow.yaml
├── src/autonode/
│   ├── core/
│   │   ├── agents/
│   │   │   ├── models.py
│   │   │   ├── parser.py
│   │   │   └── ports.py
│   │   ├── tools/
│   │   │   └── ports.py
│   │   └── workflow/
│   │       ├── models.py
│   │       ├── parser.py
│   │       └── ports.py
│   ├── application/
│   │   ├── graph.py
│   │   ├── graph_factory.py
│   │   ├── post_processing.py
│   │   └── workflow_state.py
│   ├── infrastructure/
│   │   ├── config/
│   │   │   ├── agents_schema.py
│   │   │   ├── workflow_schema.py
│   │   │   └── loader.py
│   │   ├── factory/
│   │   │   └── crew.py
│   │   ├── tools/
│   │   │   ├── registry.py
│   │   │   ├── path_guard.py
│   │   │   ├── ignore_rules.py
│   │   │   ├── repository_map.py
│   │   │   └── codebase_search.py
│   │   └── tracing.py
│   └── presentation/
│       ├── cli.py
│       └── models.py
└── tests/
  ├── testdata/
  ├── stubs/
  └── test_*.py
```

---

## Direzione delle dipendenze

| Layer            | Dipende da                                          | Non deve dipendere da                                               |
| ---------------- | --------------------------------------------------- | ------------------------------------------------------------------- |
| `core`           | stdlib + librerie algoritmiche (es. `networkx`)     | `pydantic`, `autonode.infrastructure`, LangChain/LangGraph concreti |
| `application`    | `core` + LangGraph orchestration                    | adapter concreti infrastructure                                     |
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

Questi contratti disaccoppiano il dominio da adapter concreti.

---

## Modelli e validazione

- Core:
  - dataclass con suffisso `Model`
  - esempio: `AgentWorkflowNodeModel`, `RoutingToolCallsOrNextModel`, `WorkflowModel`
- Infrastructure:
  - Pydantic schema con suffisso `Schema` (qui `*YamlSchema`)
  - mapping esplicito con `to_core()`

Flusso:

1. `infrastructure/config/*_schema.py`: valida forma e tipi dell'input YAML.
2. `to_core()`: converte in dataclass del core.
3. `core/workflow/parser.py`: valida semantica/topologia del grafo.

---

## Stato corrente degli entrypoint

- `presentation/cli.py`: entrypoint operativo (workflow con gli stessi flag di prima; sottocomando `cleanup` per worktree sotto `.autonode/worktrees/` e container `autonode-sandbox-*`).
- `infrastructure/vcs/workspace_cleanup.py`: pulizia worktree di sessione per età o in blocco.
- API/MCP remoti: non presenti nel codice corrente.

---

## Nota su VCS

Il contratto `VCSProviderPort` è obbligatorio in `compile_workflow` / `build_graph`.
Il CLI usa `GitWorktreeProvider` in `infrastructure/vcs/git_worktree_provider.py`; nei test di compilazione si usa uno stub dedicato sotto `tests/stubs/`.
