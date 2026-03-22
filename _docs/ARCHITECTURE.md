# Autonode – Architecture (enterprise & vision)

## Principio centrale: **Core agnostic**

Il package **`core/`** non dipende da LangChain, LangGraph, GitPython o FastAPI. Le integrazioni (LLM, tool, VCS, HTTP) sono **iniettate** tramite **port** (`core/ports.py`) e modelli/DTO; **`application/`** orchestra il grafo e lo stato; **`infrastructure/`** fornisce implementazioni concrete; **`presentation/`** espone CLI/API/MCP.

---

## Layout (indicativo)

```
autonode/
├── config/
│   ├── agents.yaml
│   └── workflow.yaml
├── src/autonode/
│   ├── core/                    # Dominio e port (nessuna dipendenza framework)
│   │   ├── models.py            # SessionState, DTO cross-cutting (Pydantic)
│   │   ├── ports.py             # ToolRegistryPort, AgentFactoryPort, VCSProviderPort, …
│   │   ├── agents/              # Modelli e parser config agenti
│   │   └── workflow/            # WorkflowConfig, parser YAML
│   ├── application/             # Casi d’uso e LangGraph
│   │   ├── graph.py             # build_graph, stato iniziale
│   │   ├── graph_factory.py     # Compilazione grafo da WorkflowConfig
│   │   └── workflow_state.py    # GraphWorkflowState (TypedDict)
│   ├── infrastructure/          # Adapter concreti
│   │   ├── agents/              # Factory agenti (LangChain)
│   │   ├── tools/               # Registry, Aider, …
│   │   ├── git_adapter.py       # Implementazione GitPython di VCSProviderPort (shadow worktree)
│   │   ├── config_loader.py
│   │   └── workflow_loader.py
│   └── presentation/            # Entry points
│       ├── cli.py
│       ├── api_server.py        # FastAPI: webhook n8n / integrazione Telegram (bridge HTTP)
│       └── mcp_server.py        # MCP per Cursor (ove presente)
├── tests/
│   ├── testdata/              # YAML di workflow/agenti usati solo dai test (vivi solo sotto tests/)
│   ├── stubs/                 # Doppi di port (es. AgentFactory) senza LLM
│   └── conftest.py            # Carica testdata con core + PyYAML; fixture stub
└── playground/                  # Workspace sandbox locale (sviluppo)
```

---

## Direzione delle dipendenze

| Layer            | Dipende da                         | Non deve |
| ---------------- | ---------------------------------- | -------- |
| **core**         | Solo stdlib / Pydantic / tipi      | LangChain, LangGraph, GitPython, FastAPI |
| **application**  | **core** (+ LangGraph nel layer orchestrazione) | infrastructure concreta |
| **infrastructure** | **core** + stack scelto (LangChain, GitPython, …) | presentation |
| **presentation** | **application** + **infrastructure** | — |

Nessun ciclo tra layer; il dominio resta sostituibile (**Semantic Kernel**, altro VCS, altro server HTTP) cambiando solo infrastructure e wiring in presentation.

---

## Core layer

- **Port obbligatori per disaccoppiamento**
  - **`ToolRegistryPort` / `AgentFactoryPort`**: tool e agenti senza legare il core a LangChain.
  - **`VCSProviderPort`**: interfaccia per **controllo versione** (worktree di sessione, commit, push, rollback) senza che `core/` conosca GitPython o la CLI `git`.
- **Modelli**: `SessionState` e DTO workflow (`WorkflowConfig`, nodi del grafo) restano serializzabili e privi di import da runtime agente.

---

## Application layer (grafo LangGraph)

- **`graph_factory`**: compila un `StateGraph` da configurazione dichiarativa (`workflow.yaml`), iniettando factory tool e, dove previsto, un **`VCSProviderPort`** per i nodi di provisioning/sync.
- **Flusso logico enterprise** (mappatura concettuale; i nomi dei nodi nel YAML possono differire):

| Fase            | Ruolo |
| --------------- | ----- |
| **PROVISIONING** | Creazione ambiente isolato: branch effimero + **Git Worktree** per `session_id` (mai commit sul branch principale dell’utente). |
| **REFINING**     | Affinamento richiesta / **checklist di confidenza** / attesa utente orchestrabile via **n8n** (human-in-the-loop, poll, approvazioni Telegram). Può essere modellato come nodi dedicati o come cicli esterni che riprendono lo stesso `thread_id`. |
| **EXECUTION**    | Editing e tool: agenti LangGraph con **Aider** come motore di scrittura codice primario (registrato lato infrastructure, invocato tramite tool). |
| **SYNC**         | **Commit** (e **push** opzionale) sul branch di sessione per visibilità remota, audit e integrazione con notifiche (es. pipeline post-push verso Telegram). |

- Il **core** non importa LangGraph: il motore di grafo resta in `application/`; le implementazioni concrete sono iniettate.

---

## Infrastructure layer

| Componente | Ruolo |
| ---------- | ----- |
| **GitPython adapter** (`git_adapter.py`, es. `GitShadowVcsProvider`) | Implementa **`VCSProviderPort`**: worktree in directory dedicata, branch `autonode/session-*`, commit/push sul branch di sessione, rollback best-effort. |
| **Tool / Aider** | Integrazione **Aider** come tool di editing nel registry; path di lavoro allineato al worktree quando il grafo ha eseguito il provisioning. |
| **Agent factory, registry, config loader** | Wiring LangChain, caricamento YAML, tracing. |

**GitPython vs comandi shell**

| Criterio        | GitPython (adapter) | Shell `git` |
| --------------- | -------------------- | ----------- |
| Testabilità     | Alta (mock del port) | Media/bassa |
| Sicurezza       | Meno concatenazione stringhe | Rischio quoting/error handling |
| Manutenibilità  | Tipizzazione e flussi espliciti | Script ad hoc |

---

## Presentation layer

| Entry        | Ruolo |
| ------------ | ----- |
| **FastAPI** (`api_server.py`) | Bridge HTTP per **webhook n8n** e integrazioni bot (**Telegram**): validazione payload (Pydantic), avvio/ripresa grafo con `thread_id` per checkpoint condiviso con altri entrypoint. |
| **CLI** (`cli.py`) | Esecuzione locale, stessa composizione application + infrastructure. |
| **MCP** (`mcp_server.py`) | Sessioni interattive da IDE (ove presente). |

Tutti gli entrypoint devono poter riusare lo **stesso** checkpointer e gli stessi identificativi di sessione dove richiesto dall’integrazione.

---

## Riepilogo design

- **Ports in core**: tool, factory agenti, **VCS** — sostituibilità del runtime e del backend Git senza toccare le regole di dominio.
- **Workflow / grafo in application**: LangGraph con nodi configurabili; provisioning e sync collegati al port VCS.
- **GitPython in infrastructure**: un solo posto che parla con il repository Git; nessun accesso diretto da core.
- **FastAPI in presentation**: orchestratori esterni (n8n, Telegram) senza accoppiare il dominio a HTTP.
