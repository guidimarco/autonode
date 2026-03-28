# 🚀 Autonode Project: Setup & Configurazione

Sistema di automazione AI basato su **FastAPI**, **Docker** e **LangGraph**, con interfaccia remota via **Appsmith**.

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
- `CURRENT_UID` e `CURRENT_GID`: Il tuo ID utente (es. `1000`) per i permessi corretti.
- `DOCKER_GID`: Il gruppo docker della tua macchina (es. `999`).
- `HOST_PROJECTS_ROOT`: Percorso assoluto alle tue repo.
- `HOST_DATA_ROOT`: Percorso assoluto ai dati.

### Avvio dei Container

Lancia l'intero stack in modalità "detached":

```bash
docker compose up -d --build
```

Questo comando avvierà:

1. **Autonode Server:** Il cuore FastAPI che gestisce le richieste.
2. **Appsmith:** L'interfaccia UI locale con persistenza in `autonode_data/appsmith`.
3. **ngrok:** Per l'esposizione sicura del tunnel verso l'esterno.

---

## 📂 2. Gestione File e Sessioni (Nuova Architettura)

Abbiamo separato il codice dai dati persistenti per garantire isolamento e sicurezza:

- **Progetto (`~/repos/autonode`)**: Contiene solo i sorgenti e la logica. Non ospita più DB o log.
- **Dati (`~/repos/autonode_data`)**: La "cassaforte" esterna che ospita lo stato:
  - `autonode.db`: Database SQLite centrale (spostato qui per persistenza).
  - `appsmith/`: Tutti i file di configurazione e widget di Appsmith.
  - `{session_id}/`: Cartella dinamica per ogni esecuzione con:
    - `logs/session.log`: Log dell'agente e streaming Docker in tempo reale.
    - `status.json`: Stato del processo per il polling della UI.
- **WorkTree e Sandbox**: Ogni task inizializza un container dedicato che opera su un WorkTree temporaneo isolato, scrivendo i risultati nella cartella di sessione dedicata.

---

## 🌐 3. Esposizione con ngrok

Per permettere ad Appsmith (cloud) di parlare con il tuo server locale, esponi la porta del server (default `8000`):

```bash
ngrok http 8000
```

**Nota:** Copia l'URL `https://...` generato da ngrok. Ti servirà per configurare l'interfaccia.

---

## 📱 4. Configurazione Interfaccia (Appsmith)

I parametri fondamentali per far funzionare l'app:

- **Datasource URL**: L'URL fornito da ngrok + `/execute`.
- **Headers**: Aggiungi `X-API-Key` con il valore impostato nel tuo `.env`.
- **Metodo**: `POST`.
- **Body (JSON)**: Deve contenere i campi `prompt` e `repo_path` (percorso assoluto della repo target).

---

## 🧹 5. Manutenzione e Pulizia

In caso di problemi di permessi o file "fantasma":

1. Ripristina permessi: `sudo chown -R $USER:$USER ~/repos/autonode_data && chmod -R 777 ~/repos/autonode_data`
2. Pulisci Docker: `docker system prune`
3. Rimuovi sandbox appese: `docker rm -f $(docker ps -a -q --filter "name=autonode-sandbox-")`

---

## 📌 Note su Git e Persistenza

Il database SQLite (`autonode.db`) e le cartelle temporanee di sessione sono ora salvati in `HOST_DATA_ROOT`. Il repository `autonode` è ora **stateless**: puoi aggiornare il codice o cambiare branch senza perdere dati di sessione o configurazioni Appsmith.
