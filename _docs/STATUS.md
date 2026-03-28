# Project Status & Roadmap

## Visione

Autonode esegue workflow multi-agent su una codebase locale usando **grafi dichiarativi**.  
LLM, tool, VCS e integrazioni HTTP/MCP sono previsti via **adapter/ports**.  
Nel runtime, **LangGraph** itera nodi agent/tool e ferma la run su `review_verdict` (reviewer strutturato) o condizioni di fine.

## Stack Tecnologico

- **Python 3.12**: vincoli in `pyproject.toml` (`tool.ruff.target-version`, `tool.mypy.python_version`).
- **LangChain >= 0.3.0**: agenti creati con `langchain_openai.ChatOpenAI` (factory).
- **LangGraph >= 0.2**: orchestration del workflow in `application/workflow/builder.py` (`build_graph`).
- **LangSmith >= 0.1**: logging/tracing dichiarato (tracing configurabile).
- **LLM su OpenRouter**: `OPEN_ROUTER_API_KEY` + `base_url="https://openrouter.ai/api/v1"` in `infrastructure/factory/agent_factory.py`.
- **Aider**: tool `aider` via `aider-chat` (CLI nel container), registrato in `infrastructure/tools/registry.py`; modello `--model` da env `AIDER_MODEL` (default `openrouter/mistralai/devstral-2512`).
- **YAML >= 6.0**: workflow e agent catalog via `pyyaml`.

## Stato dell'Architettura

- **`core/`**: **solido**. Ports + dataclass `*Model` sono separati da framework e concrezioni. Domini implementati:
  - Agenti;
  - Tools;
  - Workflow.
- **`application/`**: **quasi completo**. `graph_factory` compila un `StateGraph` da `config/workflow.yaml` e gestisce routing/iterazioni.
- **`infrastructure/`**: **parzialmente solido**.
  - Tool: “Map/Search/PathGuard/Aider” (shell/aider in container quando `ToolRegistry` è costruito con `execution_env` Docker).
  - Factory agenti ci sono;
  - VCS: `GitWorktreeProvider` (layout `{REPOS_ROOT}/autonode_docker/<id>/workspace|outputs`; log/stato sotto `DATA_ROOT`) + cleanup; usato dal CLI insieme a `DockerAdapter`.
  - Sandbox Docker: immagine `autonode-sandbox:latest` costruita da `docker/sandbox.Dockerfile` con contesto `.` (cwd = root repo); `DockerAdapter` inietta nel container le API key note (`OPENAI_*`, `ANTHROPIC_*`, `OPEN_ROUTER_*`) per Aider/provider.
- **`presentation/`**: entrypoint CLI operativo; server MCP stdio (`autonode mcp`) in `presentation/mcp/`.
  - `cli.py` esegue il **bootstrap** (Git worktree + container Docker) **prima** di `graph.invoke()`; il grafo non avvia mai tool senza `execution_env` valido nello stato.

## Feature Implementate

- **Map (`get_repository_map`)**: produce una “repository map” Markdown usando euristiche su dichiarazioni (file estensioni Py/PHP/JS/TS), sempre sotto **sandbox root**.
- **Search (`search_codebase`)**: cerca stringhe testuali sotto una root; prova `rg` (se presente) e fallback Python; limita query length e numero risultati.
- **PathGuard (`resolve_under_root` / `resolved_root`)**: blocca **path assoluti** e traversal (`..`) per impedire escape dalla root consentita.
- **Aider (`aider` tool)**: eseguito nel container Docker della sessione (`docker exec`), non sull’host.

- **Workflow (LangGraph + YAML)**:
  - `WorkflowConfig` descrive nodi (`agent`, `tool_node`, `state_update`, `vcs_sync`) e routing condizionale. Il nodo YAML `vcs_provision` non è più supportato in compilazione: provisioning solo dal CLI bootstrap.
  - `tool_calls_or_next` manda al nodo tools solo se l’ultimo `AIMessage` contiene `tool_calls`.
  - `reviewer_finish_or_tools_or_revision` termina su **`review_verdict.is_approved`** oppure su **`iteration >= max_iterations`** (precedenza: `tool_calls` → tools node).
  - Nodi agent con **`structured_review: true`** usano output strutturato (`ReviewVerdictModel`) via factory; niente più parsing testuale con marker.
  - Nel workflow corrente (`config/workflow.yaml`) l’loop “Coder/Reviewer” è modellato come **agent + reviewer**, non come un nodo di coding che usa realmente `aider`.

## Debito Tecnico e “Punti Oscuri”

- **`compile_workflow` richiede sempre `vcs_provider`**: il CLI passa `GitWorktreeProvider`; in test si usa uno stub che non simula worktree reali.
- **Coding end-to-end non dimostrato**: il tool `aider` è registrato, ma il workflow di esempio non lo usa come motore di editing con commit locale end-to-end.
- **Ingressi remoti parziali**: MCP stdio in `presentation/mcp/` con tool `run_workflow` collegato al use case reale; manca FastAPI e altri ingressi HTTP.
- **Checkpoint / serializzazione stato**: `execution_env` nello stato del grafo potrebbe non essere serializzabile con checkpointer persistenti (da valutare se si introduce persistenza).
- ~~**Verdetti euristici**~~: sostituiti da **review strutturato** (`review_verdict` nello stato) per il reviewer; fallback sicuro a non approvato se l’output LLM non valida.
- **Testing: strumenti sì, integrazione VCS/worktree e coding no**: i test coprono tool/parsing; manca un end-to-end sul loop coding + Git reale.

## Next Steps Proposti (3 priorità)

1. **Rendere operativa la sandbox fisica** (worktree, branch per sessione, path enforcement e ciclo di vita setup/commit locale/cleanup container+worktree).  
   Riferimento: `_meta/todos.yaml` → `ambiente di sandbox per l'esecuzione`.
2. **Aggiungere memoria a breve/lungo termine e una base RAG** (persistenza per session/thread + retrieval controllato dalla sandbox).  
   Riferimento: `_meta/todos.yaml` → nuovo todo “memoria a breve/lungo termine + RAG”.
3. **Implementare gli ingressi remoti API (punto 3)** (FastAPI endpoint per avvio/ripresa workflow con `thread_id` e checkout dello stato).  
   Riferimento: `_meta/todos.yaml` → nuovo todo “api - punto 3”.

## Documentazione: regole operative (cosa aggiornare e come)

- Se modifichi **layer boundaries o ports**, aggiorna `_docs/ARCHITECTURE.md` (layout, dipendenze tra layer, contratti).
- Se cambi **flusso/terminologia di workflow e nodi**, aggiorna `_docs/PROJECT.md` e/o `_docs/STATUS.md` (solo ciò che cambia davvero).
- Se introduci nuovi **TODO/roadmap**, aggiorna `_meta/todos.yaml` (nome + description + eventuali `files:`). Se risolvi un todo rimuovilo dalla lista.
- Mantieni invariata la separazione test/dev: i file YAML di test restano in `tests/testdata/` (non in `config/`).
