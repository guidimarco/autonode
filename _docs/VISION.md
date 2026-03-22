# Progetto Multi-Agent AI per Codebase Locale

## 1. Core Architetturale

- **Scelta principale:** LangChain come framework principale.
- **Obiettivo:** Core agnostico rispetto al framework (LangChain o Semantic Kernel), tramite interfacce/adapter.
- **Motivazione:** Ecosistema LangChain vasto e maturo, numerosi tool e integrazioni, buona documentazione e supporto community.
- **Alternativa:** Semantic Kernel
  - Pro: buone capacità di orchestrazione interna.
  - Contro: ecosistema più limitato, meno esempi pratici per agenti multi-task e RAG.

---

## 2. Orchestrazione Multi-Agent

- **Scelta principale:** LangGraph sopra LangChain come **motore centrale** per orchestrazione e **cicli iterativi** (stato del task, transizioni condizionali, feedback tra nodi).
- **Esempio di ciclo:** Coder → Reviewer → (in caso di errore o richiesta modifiche) ritorno al Coder fino a criteri di uscita definiti nel grafo.
- **Motivazione:** Permette flussi gerarchici, sequenziali e liberi tra agenti, miglior controllo e debug rispetto a catene lineari fisse.
- **Alternativa:** Crew AI
  - Pro: semplice per task out-of-the-box.
  - Contro: problemi di debugging con modelli economici e gestione contesto.
- **Architettura suggerita:**
  - Core agnostico → Adapter LangChain → LangGraph per gestione flussi e stato.

---

## 3. Gestione degli Agenti e Tool

- **Agenti:** Generalisti e specializzati per task diversi (analisi, sviluppo, review, test, brainstorming).
- **Motore di editing (grafo):** **Aider** è il motore di scrittura codice **primario** integrato nel grafo (tool/registry lato infrastructure), orchestrato dagli agenti LangGraph senza accoppiare il dominio `core/` ad Aider o a LangChain.
- **Tool:** Lettura/scrittura file, esecuzione script, chiamate API, integrazione con LLM provider.
- **Debug:** LangSmith (SaaS) o alternative open source (Langfuse, Helicone) per tracciare input/output agenti, tool call, prompt e output raw.
- **Motivazione:** Ecosistema LangChain già ampio e rodato, facilita testing e sviluppo iniziale anche con modelli economici.

---

## 4. Interfacce e input (hub ibrido)

Il runtime multi-agente è **centralizzato** e raggiungibile da più canali, con la stessa logica di orchestrazione sottostante.

| Canale                 | Ruolo                                                                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Ingressi primari (remote)** | **n8n** e **Telegram** (bot / automazioni) come canali operativi principali: payload testuali e metadati arrivano al layer **Presentation** tramite **FastAPI** (`presentation/api_server.py`), tipicamente via webhook (`POST /webhook/n8n` o equivalente). |
| **Local Dev (Cursor)** | Integrazione nativa tramite **MCP** (`presentation/mcp_server.py`), dove presente: sessioni interattive, tool e stato allineati al grafo. |
| **Remote Automation**  | Stesso backend FastAPI: avvio/ripresa task, correlazione `thread_id` / sessione per allineamento a checkpoint e notifiche. |

**Memoria condivisa:** lo stato del task persistito (checkpoint) deve essere lo **stesso store** leggibile sia dal server MCP sia dall’API remota, così una sessione locale e una pipeline n8n/Telegram operano sullo stesso task quando serve.

**Sicurezza (tool di scrittura):** tutti i tool che modificano filesystem o eseguono codice devono operare in **sandbox** o in una **directory controllata** (workspace del task / worktree di sessione), senza escape verso path arbitrari non autorizzati.

---

## 5. RAG e Ricerca Semantica

- **Scelta futura:** Integrazione con LlamaIndex (ex MyIndex) per retrieval avanzato e RAG su repository.
- **Motivazione:** Più flessibile e potente rispetto alle soluzioni built-in LangChain, permette indicizzazione semantica di codice e documenti.
- **Alternativa iniziale:** LangChain + Vector DB (Chroma, Qdrant, Weaviate) con tool loader nativo per prototipi rapidi.

---

## 6. Sandbox, strategia di sicurezza (Shadow Strategy) e gestione versione

- **Obiettivo:** Isolare ogni sessione di lavoro per sicurezza, audit e ripristino, senza modificare direttamente il branch principale dell’utente.

### Shadow Strategy (obbligatoria per sessione)

- Per ogni sessione (`session_id` / `thread_id`) il sistema deve usare un **Git Worktree** dedicato: working tree separato dal repository principale, così agenti e tool di editing operano su una copia isolata.
- I commit **non** avvengono sul branch di default (es. `main`/`master`): si lavora su **branch effimeri** con naming stabile, es. `autonode/session-<id>`, creati e aggiornati tramite il port `VCSProviderPort` (vedi architettura).

### Gestione versione e osservabilità remota

| Approccio | Pro | Contro |
| --------- | --- | ------ |
| **GitPython** (adapter in infrastructure) | API tipizzata, meno shell injection, testabile, integrabile con logica applicativa (commit message, branch, worktree). | Dipendenza aggiuntiva; edge case Git da gestire esplicitamente. |
| **Comandi `git` via shell** | Flessibile, scriptabile ovunque. | Più fragile (quoting, error handling), più difficile da testare in modo deterministico. |

- Il sistema utilizza **GitPython** per: creare worktree e branch di sessione, registrare **commit automatici** dopo round di editing riusciti, ed eseguire **push** del branch di sessione verso il remoto quando configurato — utile per **monitoraggio remoto** (es. notifiche o riassunti su **Telegram** tramite n8n dopo `git push`).
- **Python virtualenv** (o equivalente) resta consigliato per task/tool per dipendenze isolate.
- **Soluzione futura:** Container Docker o Podman per isolamento totale (filesystem, processi, rete), integrabile con tool wrapper LangChain.
- **Motivazione:** Test sicuri su repository locali, tracciamento delle modifiche per sessione, possibilità di rollback lato adapter senza contaminare il branch principale.
- **Alternative:** Firecracker o Kata Containers (microVM) → overkill per test locali, più adatti a setup industriali.

---

## 7. Flussi di Task

- **Tipi di flussi supportati:**
  - Sequenziali: planner → task agents → review → report.
  - Gerarchici/liberi: brainstorming, task splitting, agent collaboration.
- **Motivazione:** LangGraph consente flussi dinamici e controllati, simili a Crew AI ma più robusti e debug-friendly.
- **Memory/Context Passing:** possibile passaggio del contesto tra agenti dello stesso task o tra task correlati, senza collegamento diretto tra fasi principali.

---

## 8. Strategie di Test e Avvio

- Primo test rapido: 1 agente + tool base (read/write file) + worktree locale.
- Log dettagliato di input/output e tool call tramite LangSmith o logging locale.
- Scalare a multi-agent e orchestrazione dopo validazione.

---

## 9. Conclusioni e Motivazioni Scelte

- **LangChain:** ecosistema, librerie, agenti già pronti.
- **LangGraph:** orchestrazione flussi complessi e debug migliore.
- **LlamaIndex:** futura integrazione RAG avanzata.
- **Ingressi enterprise:** n8n e Telegram come canali primari verso FastAPI; stesso grafo e checkpoint degli altri entrypoint.
- **Shadow Strategy + GitPython:** worktree e branch effimeri per sessione; commit/push per visibilità e integrazione con automazioni remote.
- **Aider:** editing codice principale nel grafo, dietro port e infrastructure.
- **Sandbox:** sicurezza e testing isolato, modulare; obbligo operativo per tool di scrittura/esecuzione (worktree/directory controllata).
- **Agnosticismo core:** flessibilità futura per cambiare framework o provider VCS senza riscrivere logica core; hub MCP + API sulla stessa orchestrazione e stessa memoria di task dove richiesto.
- **Alternativa principale:** Semantic Kernel → più stabile in orchestrazione interna, ecosistema più piccolo, meno flessibile per test locali e agenti economici.

---

## 10. Link e Riferimenti

- [LangChain GitHub](https://github.com/hwchase17/langchain)
- [LangGraph GitHub](https://github.com/hwchase17/langgraph)
- [LlamaIndex GitHub](https://github.com/jerryjliu/llama_index)
- [LangSmith (SaaS)](https://www.langchain.com/langsmith)
