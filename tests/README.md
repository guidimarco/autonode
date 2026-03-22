# Tests

- **`testdata/`** — Unica fonte di YAML per i test (`workflow.yaml`, `agents.yaml`, ecc.). **Non** usare `config/` del progetto nei test: così restano stabili anche se le configurazioni applicative cambiano.
- I test che validano il caricamento workflow leggono solo `testdata/workflow.yaml` (vedi `test_workflow_yaml_load.py` e `conftest.py`).
- **`stubs/`** — Doppi delle port (es. `StubAgentFactory`) senza LLM.
- **`conftest.py`** — Legge `testdata/workflow.yaml` con **PyYAML + `parse_workflow_config`** (core), senza passare da `workflow_loader` dell’infrastructure.

Validazione: task VS Code **Autonode: Validate All**.
