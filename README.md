# Autonode

Autonode e un progetto Python che esegue workflow multi-agent su una codebase locale con una forte attenzione a isolamento, tracciabilita e qualita architetturale. Il runtime combina configurazione dichiarativa, orchestrazione a grafo e una sandbox per lavorare su repository Git senza toccare direttamente il branch principale.

Questo repository nasce con un obiettivo preciso: dimostrare capacita di progettazione software su una codebase reale, non solo di prototipazione AI. Il focus non e "far parlare un LLM", ma costruire un sistema estensibile, testabile e sicuro per orchestrare agenti, tool e modifiche al codice.

## Why This Project Matters

Autonode mette insieme alcuni problemi interessanti dal punto di vista ingegneristico:

- orchestrazione multi-agent con workflow dichiarativi;
- separazione rigorosa tra dominio, application logic e adapter concreti;
- isolamento operativo tramite Git worktree e Docker sandbox;
- integrazione con tool di sviluppo reali, incluso Aider;
- esposizione del runtime sia via CLI sia via MCP.

## Current State

Autonode oggi e gia in grado di:

- caricare un catalogo agenti e un workflow da file YAML;
- validare la forma dei config in infrastructure e la semantica/topologia nel core;
- compilare il workflow in un grafo LangGraph;
- creare un worktree Git per sessione su branch `autonode/session-*`;
- avviare una sandbox Docker isolata per tool ed esecuzione;
- esporre il run sia da CLI sia tramite server MCP su stdio;
- eseguire tool di repository exploration, file I/O, shell e Aider dentro l'ambiente isolato;
- fare commit locali nel worktree di sessione.

## Architecture At A Glance

Il progetto segue una struttura a layer:

- `src/autonode/core/`
  Dominio puro: dataclass `*Model`, parser e port astratte. Nessuna dipendenza da Pydantic o da adapter concreti.
- `src/autonode/application/`
  Orchestrazione del workflow e use case. Qui vive la compilazione del grafo LangGraph e il coordinamento del runtime.
- `src/autonode/infrastructure/`
  Adapter concreti: schema Pydantic, factory LangChain, tool registry, Docker sandbox, Git worktree provider, tracing.
- `src/autonode/presentation/`
  Entry point esterni: CLI, handler applicativi e server MCP.

Scelte architetturali principali:

- validazione di forma in infrastructure, validazione semantica nel core;
- porte e adapter per mantenere il dominio framework-agnostic;
- sandbox obbligatoria per evitare esecuzione diretta sull'host;
- VCS locale per sessione invece di modifiche sul branch principale;
- workflow configurabile via YAML invece di flussi hardcoded.

## Tech Stack

- Python 3.12
- LangChain
- LangGraph
- Pydantic
- Docker
- Git worktree
- Aider
- PyYAML
- Ruff
- Black
- Mypy
- Pytest
- MCP

## Repository Structure

```text
autonode/
├── _docs/                  # vision, architettura e stato progetto
├── config/                 # workflow e catalogo agenti di esempio
├── docker/                 # immagine sandbox
├── scripts/                # comandi di sviluppo
├── src/autonode/
│   ├── application/
│   ├── core/
│   ├── infrastructure/
│   └── presentation/
└── tests/                  # test unitari e fixture YAML
```

## Getting Started

### Prerequisites

- Python 3.12
- Docker (Docker Desktop o daemon attivo sul sistema: i workflow avviano la sandbox containerizzata)
- Git

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Environment

Crea un file `.env` nella root del repository (copia da `.env.example`). Le chiavi usate dal runtime includono almeno:

- `OPEN_ROUTER_API_KEY` — API key OpenRouter per LangChain / agenti
- `AUTONODE_MCP_LOG_LEVEL` — livello di log del processo MCP (es. `INFO`, `DEBUG`)

Opzionali: `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`, `AIDER_MODEL`.

### Build Sandbox Image

```bash
docker build -t autonode-sandbox:latest -f docker/sandbox.Dockerfile .
```

## Development & Testing

### Alias consigliato (MCP Inspector)

Per collegare [MCP Inspector](https://github.com/modelcontextprotocol/inspector) al server senza errori `ENOENT`, usa **path assoluti** (qui con `$(pwd)` dalla root del clone):

```bash
alias mcp-autonode='DANGEROUSLY_OMIT_AUTH=true npx @modelcontextprotocol/inspector "$(pwd)/.venv/bin/python" "$(pwd)/src/autonode/presentation/mcp/server.py"'
```

Esegui `mcp-autonode` dalla root del repository dopo aver attivato il venv se preferisci usare `python` da shell; l’alias sopra punta esplicitamente a `.venv/bin/python`.

### Check rapido MCP

Dopo aver copiato `.env` e installato le dipendenze:

```bash
bash scripts/test_mcp.sh
```

Lo script verifica presenza di `.venv`, presenza di `OPEN_ROUTER_API_KEY` in `.env` e stampa il comando Inspector.

## Usage

### Run A Workflow

```bash
autonode \
  --workflow config/workflow.yaml \
  --agents config/agents.yaml \
  --prompt "Analyze this repository and propose improvements" \
  --repo .
```

Cosa succede durante una run:

1. viene creato un worktree Git dedicato alla sessione;
2. viene avviata una sandbox Docker collegata a quel worktree;
3. il workflow YAML viene compilato in un grafo LangGraph;
4. agenti e tool lavorano nel worktree isolato;
5. eventuali modifiche vengono committate sul branch locale di sessione;
6. a fine run sandbox e worktree vengono rimossi, ma il branch locale resta disponibile.

### Start The MCP Server

```bash
autonode mcp
```

Il server MCP espone il tool `run_workflow` su stdio e riusa il runtime reale del progetto.

### Cleanup Session Artifacts

```bash
autonode cleanup --repo-path .
```

Per rimuovere anche il branch locale della sessione:

```bash
autonode cleanup --repo-path . --session-id <session-id> --delete-branch
```

## Quality And Testing

Esegui i controlli di qualita:

```bash
python -m scripts.dev lint
```

Correggi automaticamente il formattamento dove possibile:

```bash
python -m scripts.dev fix
```

Esegui i test:

```bash
pytest
```

Il repository include test su:

- parsing e validazione workflow;
- builder LangGraph e routing;
- tool registry e path guard;
- adapter Git worktree e Docker sandbox;
- entrypoint CLI e mapping MCP;
- use case principali.

## Design Highlights

### 1. Core purity

Il package `core/` contiene logica di dominio e contratti, non dettagli infrastrutturali. Questo rende il progetto piu facile da testare e piu semplice da evolvere se cambiano framework o provider.

### 2. Safer local automation

Invece di operare direttamente sul repository utente, Autonode crea un worktree di sessione e usa una sandbox Docker. E una scelta importante sia per sicurezza sia per auditabilita.

### 3. Declarative workflows

I workflow non sono hardcoded nella business logic: vengono definiti via YAML e tradotti in un grafo eseguibile. Questo approccio favorisce estensibilita e sperimentazione controllata.

### 4. Structured review path

Il motore supporta reviewer con output strutturato e decisioni di routing basate sullo stato del workflow, non solo su parsing fragile di testo libero.

## What Is Implemented Vs Planned

Implementato oggi:

- CLI operativa;
- server MCP;
- provisioning worktree di sessione;
- sandbox Docker;
- registry tool con file tools, shell, repository map, code search e Aider;
- compilazione workflow con LangGraph;
- test suite e controlli statici.

Previsto ma non ancora presente nel codice corrente:

- memoria persistente condivisa tra canali;
- componente RAG/semantic retrieval dedicata;
- workflow demo pubblici piu ricchi del file di esempio attuale.

## Documentation

La documentazione tecnica di supporto si trova in `/_docs`:

- `VISION.md`
- `ARCHITECTURE.md`
- `STATUS.md`

La documentazione distingue la direzione del progetto dallo stato realmente implementato, utile sia per contributor sia per chi valuta il repository.

## Roadmap

- introdurre persistenza/checkpoint condivisi;
- espandere i workflow demo con loop coder-reviewer realmente pronti per showcase;
- migliorare l'osservabilita del runtime e dei tool execution path.

## License

This project is licensed under the MIT License.
