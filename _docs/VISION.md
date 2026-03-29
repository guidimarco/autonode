# 📑 Visione di Progetto: AutoNode Evolution 2026

## 1. Visione Complessiva (L'Aspettativa Utente)

L'obiettivo è trasformare AutoNode da un semplice esecutore di script a un **Collaboratore Artificiale Autonomo** capace di operare sulla codebase con un approccio professionale e proattivo. L'applicativo deve essere in grado di:

- **Comprendere il Progetto:** Non limitarsi a leggere file isolati, ma mappare le dipendenze e la logica globale della codebase.
- **Ragionare per Obiettivi:** Ricevere input ad alto livello ("Migliora la gestione errori nel modulo X") e generare autonomamente un piano d'azione coerente.
- **Garantire Affidabilità:** Validare ogni modifica in un ambiente sicuro (**Sandbox**) tramite test automatici, riducendo al minimo l'intervento umano di correzione.
- **Collaborare Attivamente:** Sapere quando è necessario fermarsi per chiedere chiarimenti o approvazioni, rendendo l'utente il supervisore strategico del processo.

## 2. Architettura Ibrida e Flessibile

Il sistema deve superare la rigidità dei grafi sequenziali per abbracciare un modello di orchestrazione dinamica:

- **Workflow Strutturati:** Per task routinari e prevedibili, dove la sequenza di passi (es. Analisi -> Codice -> Test) garantisce stabilità.
- **Orchestrazione Dinamica (Agents-as-Tools):** Per task complessi, dove un "Agente Manager" può invocare specialisti (Coder, Reviewer) come se fossero strumenti, gestendo loop di correzione interni in modo invisibile all'utente.
- **Modalità Collaborativa (Crew):** Capacità di far interagire più agenti in una sessione di brainstorming o critica incrociata per la risoluzione di problemi architettonici.

## 3. Pilastri dello Sviluppo (Requisiti Non Tecnici)

Per garantire una transizione fluida verso il futuro dell'applicativo, ogni sviluppo deve rispettare:

- **Trasparenza e Controllo:** Monitoraggio in tempo reale dei costi (token) e dello stato di avanzamento, con checkpoint umani obbligatori per i passaggi critici.
- **Efficienza Cognitiva:** Gestione intelligente della memoria tramite sommari dinamici, per evitare il degradamento delle prestazioni nei task a lungo termine.
- **Isolamento Operativo:** Utilizzo rigoroso di Docker per l'esecuzione del codice e di strategie Git (branching di sessione) per mantenere il repository principale sempre pulito e sicuro.
- **Accessibilità Universale:** Un unico "cervello" agentico raggiungibile da client diversi (API HTTP, CLI, integrazioni esterne).

## 4. Roadmap Evolutiva e Priorità

### Fase 1: Consolidamento Infrastrutturale (Immediata)

- **Monitoraggio Token:** Tracciamento dei consumi integrato direttamente nel flusso di esecuzione e salvato nel database di sessione.
- **Sommario Dinamico:** Implementazione della logica di "compressione della memoria" per mantenere il contesto LLM pulito ed economico.
- **Semplificazione del Grafo:** Eliminazione dei nodi procedurali ridondanti (es. aggiornamento stato manuale) a favore di una logica di sistema automatica.

### Fase 2: Human-in-the-Loop (Interazione)

- **Tool di Interruzione:** Capacità dell'agente di sospendere l'esecuzione e inviare una notifica all'utente per richiedere input o conferme.
- **Validazione del Piano:** Interfaccia per permettere all'utente di visionare, modificare o approvare il piano d'azione generato dall'agente prima dell'inizio delle modifiche ai file.

### Fase 3: Modularità e Deleghe (Agenti come Strumenti)

- **Agent Registry:** Creazione di un catalogo di agenti specializzati caricabili on-demand.
- **Recursive Execution:** Abilitazione degli agenti a "chiamarsi tra loro", permettendo la gestione di task complessi tramite deleghe interne e loop di feedback autonomi.

### Fase 4: Intelligence Avanzata (Futuro)

- **RAG su Codebase:** Integrazione di sistemi di ricerca semantica per permettere agli agenti di navigare in repository di grandi dimensioni.
- **Multi-Workflow Engine:** Supporto a diversi modelli di interazione (Brainstorming vs Sviluppo) selezionabili in base alla natura del task.
