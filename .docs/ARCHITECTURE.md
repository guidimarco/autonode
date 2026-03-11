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
│       ├── application/   # Use cases
│       │   └── workflow.py  # run_workflow, execute_tool_calls
│       ├── infrastructure/  # LangChain adapters
│       │   ├── config_loader.py
│       │   ├── tools/     # aider, registry
│       │   └── agents/    # CrewFactory
│       └── presentation/  # Entry points
│           ├── cli.py
│           └── api.py     # Placeholder (future HTTP API)
├── tests/                 # Unit & integration (placeholder)
└── playground/            # Sandbox for agent edits (unchanged)
```

## Dependency direction

- **core** → no internal deps (models + abstract ports).
- **application** → core only; orchestration receives factories/registries via callables.
- **infrastructure** → core + LangChain; implements tools, registry, agent factory.
- **presentation** → application + infrastructure; composes and runs.

No circular dependencies; domain and use cases stay framework-agnostic.

## Design choices

- **Ports in core**: `ToolRegistryPort`, `AgentFactoryPort` allow swapping LangChain for another runtime (e.g. Semantic Kernel) without changing application.
- **Workflow in application**: `run_workflow` and `execute_tool_calls` receive `create_agent_fn`, `get_tool_list_fn`, and `message_types` so the application layer does not import LangChain.
- **Config**: Agent config lives in YAML; loading is in infrastructure (`config_loader`); DTO is in core (`AgentConfig`).
- **Single package**: All code under `src/autonode/`; `main.py` and `config/` at repo root for clarity.
