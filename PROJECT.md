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
- **Scelta principale:** LangGraph sopra LangChain per orchestrazione agenti.
- **Motivazione:** Permette flussi gerarchici, sequenziali e liberi tra agenti, miglior controllo e debug.
- **Alternativa:** Crew AI
  - Pro: semplice per task out-of-the-box.
  - Contro: problemi di debugging con modelli economici e gestione contesto.
- **Architettura suggerita:** 
  - Core agnostico → Adapter LangChain → LangGraph per gestione flussi.
  - Possibilità futura di sostituire LangChain con Semantic Kernel senza rifare core.

---

## 3. Gestione degli Agenti e Tool
- **Agenti:** Generalisti e specializzati per task diversi (analisi, sviluppo, review, test, brainstorming).
- **Tool:** Lettura/scrittura file, esecuzione script, chiamate API, integrazione con LLM provider.
- **Debug:** LangSmith (SaaS) o alternative open source (Langfuse, Helicone) per tracciare input/output agenti, tool call, prompt e output raw.
- **Motivazione:** Ecosistema LangChain già ampio e rodato, facilita testing e sviluppo iniziale anche con modelli economici.

---

## 4. RAG e Ricerca Semantica
- **Scelta futura:** Integrazione con LlamaIndex (ex MyIndex) per retrieval avanzato e RAG su repository.
- **Motivazione:** Più flessibile e potente rispetto alle soluzioni built-in LangChain, permette indicizzazione semantica di codice e documenti.
- **Alternativa iniziale:** LangChain + Vector DB (Chroma, Qdrant, Weaviate) con tool loader nativo per prototipi rapidi.

---

## 5. Sandbox e Sicurezza
- **Obiettivo:** Isolare ogni task/agent per sicurezza e testing.
- **Soluzione iniziale:** Git worktree + Python virtualenv per ogni task.
- **Soluzione futura:** Container Docker o Podman per isolamento totale (filesystem, processi, rete), integrabile con tool wrapper LangChain.
- **Motivazione:** Test sicuri su repository locali, possibilità di eseguire script e modifiche senza rischi.
- **Alternative:** Firecracker o Kata Containers (microVM) → overkill per test locali, più adatti a setup industriali.

---

## 6. Flussi di Task
- **Tipi di flussi supportati:**
  - Sequenziali: planner → task agents → review → report.
  - Gerarchici/liberi: brainstorming, task splitting, agent collaboration.
- **Motivazione:** LangGraph consente flussi dinamici e controllati, simili a Crew AI ma più robusti e debug-friendly.
- **Memory/Context Passing:** possibile passaggio del contesto tra agenti dello stesso task o tra task correlati, senza collegamento diretto tra fasi principali.

---

## 7. Strategie di Test e Avvio
- Primo test rapido: 1 agente + tool base (read/write file) + worktree locale.
- Log dettagliato di input/output e tool call tramite LangSmith o logging locale.
- Scalare a multi-agent e orchestrazione dopo validazione.

---

## 8. Conclusioni e Motivazioni Scelte
- **LangChain:** ecosistema, librerie, agenti già pronti.
- **LangGraph:** orchestrazione flussi complessi e debug migliore.
- **LlamaIndex:** futura integrazione RAG avanzata.
- **Sandbox:** sicurezza e testing isolato, modulare.
- **Agnosticismo core:** flessibilità futura per cambiare framework senza riscrivere logica core.
- **Alternativa principale:** Semantic Kernel → più stabile in orchestrazione interna, ecosistema più piccolo, meno flessibile per test locali e agenti economici.

---

## 9. Link e Riferimenti
- [LangChain GitHub](https://github.com/hwchase17/langchain)
- [LangGraph GitHub](https://github.com/hwchase17/langgraph)
- [LlamaIndex GitHub](https://github.com/jerryjliu/llama_index)
- [LangSmith (SaaS)](https://www.langchain.com/langsmith)
