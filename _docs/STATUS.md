# Project Status & Roadmap

## Visione

Autonode esegue workflow multi-agent su una codebase locale usando **grafi dichiarativi**.  
LLM, tool, VCS e integrazioni HTTP/MCP sono previsti via **adapter/ports**.  
Nel runtime, **LangGraph** itera nodi agent/tool e ferma la run su verdict o condizioni di fine.

## Stack Tecnologico

- **Python 3.12**: vincoli in `pyproject.toml` (`tool.ruff.target-version`, `tool.mypy.python_version`).
- **LangChain >= 0.3.0**: agenti creati con `langchain_openai.ChatOpenAI` (factory).
- **LangGraph >= 0.2**: orchestration del workflow in `application/graph_factory.py`.
- **LangSmith >= 0.1**: logging/tracing dichiarato (tracing configurabile).
- **LLM su OpenRouter**: `OPEN_ROUTER_API_KEY` + `base_url="https://openrouter.ai/api/v1"` in `infrastructure/agents/factory.py`.
- **Aider**: tool `aider` via package `aider-chat` (processo esterno) in `infrastructure/tools/aider.py`.
- **YAML >= 6.0**: workflow e agent catalog via `pyyaml`.

## Stato dell'Architettura

- **`core/`**: **solido**. Ports + DTO Pydantic (es. workflow/config) sono separati da framework e concrezioni. Domini implementati:
  - Agenti;
  - Tools;
  - Workflow.
- **`application/`**: **quasi completo**. `graph_factory` compila un `StateGraph` da `config/workflow.yaml` e gestisce routing/iterazioni.
- **`infrastructure/`**: **parzialmente solido**.
  - Tool: “Map/Search/PathGuard/Aider”
  - Factory agenti ci sono;
  - VCS provider reale no.
- **`presentation/`**: **placeholder** per ingressi remoti.
  - `cli.py` funziona;
  - `api.py` è solo descrittivo (nessun server FastAPI).

## Feature Implementate

- **Map (`get_repository_map`)**: produce una “repository map” Markdown usando euristiche su dichiarazioni (file estensioni Py/PHP/JS/TS), sempre sotto **sandbox root**.
- **Search (`search_codebase`)**: cerca stringhe testuali sotto una root; prova `rg` (se presente) e fallback Python; limita query length e numero risultati.
- **PathGuard (`resolve_under_root` / `resolved_root`)**: blocca **path assoluti** e traversal (`..`) per impedire escape dalla root consentita.
- **Aider (`aider` tool)**: avvia Aider come processo esterno. Ha un **Git guardrail**: non parte se il repository è **dirty**.

- **Workflow (LangGraph + YAML)**:
  - `WorkflowConfig` descrive nodi (`agent`, `tool_node`, `state_update`, `vcs_provision`, `vcs_sync`) e routing condizionale.
  - `tool_calls_or_next` manda al nodo tools solo se l’ultimo `AIMessage` contiene `tool_calls`.
  - `reviewer_finish_or_tools_or_revision` termina su **`verdict == approved`** oppure su **`iteration >= max_iterations`**.
  - Nel workflow corrente (`config/workflow.yaml`) l’loop “Coder/Reviewer” è modellato come **agent + reviewer**, non come un nodo di coding che usa realmente `aider`.

## Debito Tecnico e “Punti Oscuri”

- **Shadow worktree/VCS non operativo**: esiste `VCSProviderPort`, ma l’unica implementazione è `NoOpVcsProvider` ⇒ i nodi `vcs_provision`/`vcs_sync` non creano davvero worktree/branch.
- **Coding end-to-end non dimostrato**: il tool `aider` è registrato, ma il workflow di esempio non lo usa come motore di editing + commit/push.
- **Ingressi remoti assenti**: manca un’implementazione reale di FastAPI/MCP (nel repo non emerge un server in `presentation/api.py`).
- **Sandbox “fisica” non presente**: c’è enforcement logico su path, ma l’esecuzione (es. `shell`/`aider`) non è isolata a livello container/VM.
- **Verdetti euristici**: il routing si basa su **substring** dentro `response.content` (`approved_marker`), con rischio di routing non deterministico.
- **Testing: strumenti sì, integrazione VCS/shadow e coding no**: i test coprono tool/parsing, ma non vedo test end-to-end sul loop coding + VCS.

## Next Steps Proposti (3 priorità)

1. **Rendere operativa la sandbox fisica/shadow** (worktree, branch per sessione, path enforcement e ciclo di vita setup/sync/cleanup).  
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
