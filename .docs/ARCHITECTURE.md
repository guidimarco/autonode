# Autonode – Architecture (post-refactor)

## Layout

```
autonode/
├── main.py                 # CLI entry (wires and runs)
├── config/
│   └── agents.yaml        # Agent definitions
├── src/
│   └── autonode/          # Main package
│       ├── core/          # Domain & ports
│       │   ├── models.py  # AgentConfig, DTOs
│       │   └── ports.py   # ToolRegistryPort, AgentFactoryPort (abstract)
│       ├── application/   # Use cases & orchestration
│       │   ├── workflow.py   # Attuale: run_workflow, execute_tool_calls
│       │   └── graph.py      # Evoluzione: grafo LangGraph (stato, cicli di feedback)
│       ├── infrastructure/  # LangChain adapters
│       │   ├── config_loader.py
│       │   ├── tools/     # aider, registry
│       │   └── agents/    # CrewFactory
│       └── presentation/  # Entry points (CLI, MCP, HTTP API)
│           ├── cli.py
│           ├── mcp_server.py   # Server MCP per integrazione Cursor (uso interattivo)
│           └── api_server.py   # FastAPI: trigger remoto (es. n8n)
├── tests/                 # Unit & integration (placeholder)
└── playground/            # Sandbox for agent edits (unchanged)
```

## Dependency direction

- **core** → no internal deps (models + abstract ports).
- **application** → core; workflow e `graph.py` usano solo le astrazioni esposte da `core/` per **tool**, **factory agenti** e (ove definito) **persistenza/checkpoint**. Il package **`core/`** non importa LangChain/LangGraph; **`graph.py`** può usare LangGraph come motore di grafo nel layer application, con implementazioni concrete iniettate via port dall’infrastructure.
- **infrastructure** → core + LangChain/LangGraph; implementa registry, factory, adapter e persistenza condivisa (checkpoint) dietro i port.
- **presentation** → application + infrastructure; composes and runs (CLI, MCP, API).

No circular dependencies; domain and use cases stay framework-agnostic (**Core agnostic**): il grafo LangGraph vive in `application/graph.py` ma le dipendenze concrete (tool, modelli, checkpoint store) sono iniettate via `core/ports.py`.

## Design choices

- **Ports in core**: `ToolRegistryPort`, `AgentFactoryPort` allow swapping LangChain for another runtime (e.g. Semantic Kernel) without changing application.
- **Workflow / graph in application**: `workflow.py` evolve in `graph.py` con LangGraph per stato e cicli (es. ripetizione nodo dopo feedback). Come oggi, le funzioni di orchestrazione ricevono factory/registry tramite callables definiti sui port, senza legare il package `core` al runtime LLM.
- **Config**: Agent config lives in YAML; loading is in infrastructure (`config_loader`); DTO is in core (`AgentConfig`).
- **Single package**: All code under `src/autonode/`; `main.py` and `config/` at repo root for clarity.
