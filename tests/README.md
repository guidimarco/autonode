# Tests

- **`testdata/`** — Unica fonte di YAML per i test (`workflow_default.yaml`, `agents.yaml`, ecc.). **Non** usare `config/` del progetto nei test: così restano stabili anche se le configurazioni applicative cambiano.
- I test che validano il caricamento workflow leggono solo `testdata/workflow_default.yaml` (vedi `test_workflow_yaml_load.py` e `conftest.py`).
- **`stubs/`** — Doppi delle port (es. `StubAgentFactory`) senza LLM.
- **`conftest.py`** — Legge `testdata/workflow_default.yaml` con **PyYAML + `WorkflowYamlSchema`** (infrastructure boundary), poi converte in DTO core con `to_core()`.

Validazione: task VS Code **Autonode: Validate All**.
