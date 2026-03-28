# 🚀 Autonode Project: Setup & Configurazione

Sistema di automazione AI basato su **FastAPI**, **Docker** e **MCP (Model Context Protocol)**, con interfaccia remota via **Appsmith**.

## 🛠 Prerequisiti

- Docker & Docker Compose installati.
- Un account [ngrok](https://ngrok.com/) per l'esposizione del server.
- Un account GitHub per il tracking dei commit dell'agente.
- Un account OpenRouter per l'utilizzo dei modelli.

---

## 🏗 1. Inizializzazione del Progetto

### Configurazione Ambiente

Crea un file `.env` nella root del progetto partendo dall'esempio:

```bash
cp .env.example .env
```

Assicurati di impostare le seguenti variabili:

- `OPEN_ROUTER_API_KEY`: La tua chiave per il modello AI di OpenRouter.
- `AUTONODE_API_KEY`: Una stringa segreta per proteggere la tua API (X-API-Key).
- `CURRENT_UID` e `CURRENT_GID`: Il tuo ID utente (es. `1000`) per evitare problemi di permessi Git.
- `DOCKER_GID`: Il gruppo docker della tua macchina.

### Avvio dei Container

Lancia l'intero stack in modalità "detached":

```bash
docker compose up -d --build
```

Questo comando avvierà:

1. **Autonode Server:** Il cuore FastAPI che gestisce le richieste.
2. **MCP Server:** L'interfaccia Model Context Protocol per l'interazione con gli strumenti.
3. **Appsmith:** Se incluso nel compose per la gestione UI locale.

---

## 🌐 2. Esposizione con ngrok

Per permettere ad Appsmith (cloud) di parlare con il tuo server locale, esponi la porta del server (default `8000`):

```bash
ngrok http 8000
```

**Nota:** Copia l'URL `https://...` generato da ngrok. Ti servirà per configurare l'interfaccia.

---

## 📱 3. Configurazione Interfaccia (Appsmith)

Senza entrare nel dettaglio della creazione dei widget, ecco i parametri fondamentali per far funzionare l'app:

- **Datasource URL:** L'URL fornito da ngrok + `/execute`.
- **Headers:** Aggiungi `X-API-Key` con il valore impostato nel tuo `.env`.
- **Metodo:** `POST`.
- **Body (JSON):** Deve contenere i campi `prompt` e `repo_path` inviato dal tuo widget di input.

---

## 🤖 4. Funzionalità MCP (Model Context Protocol)

Il progetto integra un server MCP che estende le capacità dell'agente. Attraverso questo protocollo, l'AI può:

- Leggere/Scrivere file nel repository in modo sicuro.
- Gestire operazioni Git (branch, commit) con la tua identità GitHub.
- Eseguire tool di analisi del codice direttamente nel container.

---

## 🧹 5. Manutenzione e Pulizia

In caso di problemi di permessi o file "fantasma":

```bash
sudo chown -R $USER:$USER .
docker system prune
git branch | grep "autonode/session" | xargs git branch -D
```

---

## 📌 Note su Git

Il database SQLite (`autonode.db`) e le cartelle temporanee `.autonode/` sono volutamente esclusi dal tracking di Git tramite `.gitignore` per mantenere il repository leggero e pulito.
