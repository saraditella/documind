# DocuMind REST API

API REST per l'estrazione automatica di informazioni strutturate da documenti burocratici (bandi, contratti) in formato PDF, tramite una pipeline RAG (Retrieval-Augmented Generation) e validazione rigorosa dell'output con Pydantic.
Il sistema adotta un'architettura mista: calcolo locale degli embeddings vettoriali per eliminare costi fissi di vettorizzazione e inferenza cloud ultra-rapida tramite **Groq** (`openai/gpt-oss-120b`). Offre sia uno script per l'ingestion batch da riga di comando sia endpoint HTTP per caricamento dinamico, indicizzazione e query.

Progetto realizzato a scopo di studio per approfondire concretamente come si costruisce una pipeline RAG end-to-end con output strutturato.

---

## Cosa fa

1. **Ingestion dei documenti**:
    * **Via API (`POST /upload`)**: riceve un file PDF via form-data, assegna un UUID univoco, lo memorizza nella cartella `docs/`, segmenta il testo in chunk e indicizza i vettori nel database vettoriale locale.
    * **Via Script (`ingest.py`)**: consente di processare direttamente un documento locale predefinito (`docs/document.pdf`) popolando il database persistente.
2. **Retrieval semantico**: riceve una richiesta in linguaggio naturale (`GET /extract-data`) e recupera da **ChromaDB** i 4 chunk semanticamente più rilevanti per similarità vettoriale ($k=4$).
3. **Structured Extraction**: inietta contesto e query in un prompt vincolato e forza l'LLM a compilare lo schema Pydantic `DocumentInfo`, garantendo campi tipizzati e assenza di allucinazioni fuori formato.

Esempio di output:

```json
{
  "document_title": "Bando Ricerca & Innovazione 2026",
  "expiration": "31/12/2026",
  "allocated_budget": "€ 250.000,00",
  "key_requirements": [
    "Sede operativa attiva sul territorio regionale",
    "Iscrizione al Registro delle Imprese da almeno 12 mesi",
    "Durata del piano progettuale non superiore a 24 mesi"
  ]
}
```

---

## Stack Tecnologico

| Ambito / Livello | Tecnologia | Libreria / Modello | Ruolo e Motivazione Tecnica |
|---|---|---|---|
| **Web Framework** | **FastAPI** | `fastapi` | Gestione del routing HTTP asincrono, dependency injection e serializzazione automatica. |
| **ASGI Server** | **Uvicorn** | `uvicorn` | Server di esecuzione asincrono ad alte prestazioni per FastAPI. |
| **Data Validation** | **Pydantic v2** | `pydantic` (`BaseModel`, `Field`) | Definizione dello schema dati (`DocumentInfo`), tipizzazione statica e validazione del JSON estratto dall'LLM. |
| **RAG Orchestration** | **LangChain** | `langchain-core`, `langchain-text-splitters` | Composizione dichiarativa della pipeline tramite **LCEL** (LangChain Expression Language) con operatore pipe (`|`). |
| **PDF Parsing** | **PyMuPDF** | `langchain-community.document_loaders.PyMuPDFLoader` | Estrazione ad alta velocità del testo nativo dai documenti PDF caricati. |
| **Local Embeddings** | **HuggingFace** | `sentence-transformers/all-MiniLM-L6-v2` | Vettorizzazione semantica eseguita localmente (vettori a 384 dimensioni, zero costi API e zero latenza di rete). |
| **Vector Database** | **ChromaDB** | `langchain-chroma` | Database vettoriale per il salvataggio persistente su disco (`chroma_db/`) e similarity search sui chunk ($k=4$). |
| **LLM Inference** | **Groq Cloud** | `langchain-groq.ChatGroq` (`openai/gpt-oss-120b`) | Motore di inferenza LPU a bassissima latenza, configurato a `temperature=0` e vincolato con `.with_structured_output()`. |
| **Text Chunking** | **Recursive Character Text Splitter** | `RecursiveCharacterTextSplitter` | Segmentazione intelligente del testo in chunk da 1000 caratteri con sovrapposizione di 150 caratteri. |
| **Environment Config** | **Python-dotenv** | `python-dotenv` | Caricamento sicuro delle credenziali e chiavi API dal file `.env`. |
---

## 📁 Struttura del progetto

```
documind/
│
├── chroma_db/             # Vector database persistente ChromaDB (generato automaticamente)
├── docs/                  # Directory di storage locale per i PDF caricati
│   └── document.pdf       # File sorgente per l'ingestion manuale da script
│
├── main.py                # Applicazione FastAPI (endpoint /test, /upload, /extract-data)
├── ingest.py              # Script standalone per chunking e creazione database ChromaDB
├── models.py              # Schema Pydantic DocumentInfo
│
├── .env                   # Variabili d'ambiente (GROQ_API_KEY, HF_TOKEN)
├── .gitignore             # Ignora venv/, chroma_db/, docs/*.pdf, .env
├── requirements.txt       # Dipendenze del progetto
└── README.md              # Documentazione del progetto
```

---

## ⚙️ Setup e installazione

### 1. Clona il repository

```bash
git clone https://github.com/tuo-username/documind.git
cd documind
```

### 2. Crea e attiva l'ambiente virtuale

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Installa le dipendenze

```bash
pip install -r requirements.txt
```

### 4. Configura le variabili d'ambiente

Crea un file `.env` nella root del progetto:

```env
GROQ_API_KEY=gsk_tua_chiave_groq_qui
HF_TOKEN=hf_tuo_token_qui  # Opzionale: rimuove limiti di rate su Hugging Face Hub
```

### 5. Esegui l'ingestion di un documento

Metti un PDF di prova nella cartella `docs/`, poi:

```bash
python ingest.py
```

Questo script legge il PDF, lo divide in chunk semanticamente coerenti e salva i relativi embeddings in `chroma_db/`.

### 6. Avvia il server

```bash
uvicorn main:app --reload
```

L'API sarà disponibile su `http://127.0.0.1:8000`.

---

## 📡 Endpoint disponibili

### `GET /test`

Verifica che il server sia attivo.

```bash
curl http://127.0.0.1:8000/test
```

```json
{ "status": "ok", "message": "Il server è attivo" }
```

### `POST /upload`

Carica un documento PDF, ne divide il testo in chunk e ne salva i vettori (embeddings) all'interno del database ChromaDB.

**Body (multipart/form-data):**

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|---|---|---|
| `file` | file (binary) | sì | Il file burocratico in formato PDF da caricare e indicizzare |

```bash
curl -X POST "[http://127.0.0.1:8000/upload](http://127.0.0.1:8000/upload)" \
     -H "accept: application/json" \
     -F "file=@/percorso/al/tuo/documento.pdf;type=application/pdf"
```

### `GET /extract-data`

Esegue la pipeline RAG completa e restituisce i dati estratti in formato JSON validato.

**Query parameter:**

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|---|---|---|
| `request` | string | sì | La domanda in linguaggio naturale da porre al documento indicizzato |

```bash
curl "http://127.0.0.1:8000/extract-data?request=qual+è+la+scadenza+e+il+budget+del+bando"
```

In caso di errore lato servizio (es. OpenAI non raggiungibile), l'API restituisce uno status `503` con un messaggio pulito, senza esporre dettagli interni.

---

## 🧪 Testing manuale

- **Swagger UI** (consigliato): `http://127.0.0.1:8000/docs` — documentazione interattiva generata automaticamente da FastAPI, permette di testare gli endpoint direttamente da browser
- **ReDoc**: `http://127.0.0.1:8000/redoc`
- **Postman**: importa manualmente le richieste sopra, oppure genera una collection dallo schema OpenAPI disponibile su `http://127.0.0.1:8000/openapi.json`
- **curl**: esempi riportati sopra per ogni endpoint

---

## Come funziona la pipeline 

```
Domanda utente (query parameter 'request')
      │
      ▼
Retrieval su ChromaDB (top-4 chunks via similarity search)
      │
      ▼
Formattazione Contesto (context_formatting: chunk uniti con \n\n)
      │
      ▼
Iniezione nel Prompt Template (variabili 'contesto' e 'domanda')
      │
      ▼
ChatGroq (openai/gpt-oss-120b, temp=0) con Structured Output
      │
      ▼
Validazione Pydantic (schema DocumentInfo)
      │
      ▼
JSON validato restituito al client
```

La pipeline è costruita con **LCEL** (LangChain Expression Language), che permette di comporre i vari passaggi con l'operatore `|`, in modo dichiarativo e leggibile.

---

## Limiti noti e possibili miglioramenti futuri

Progetto realizzato a scopo di apprendimento: alcuni aspetti da contesto di produzione non sono stati implementati, ma sono consapevole di cosa manca:

- **Asincronia della catena**: `catena_rag.invoke()` è bloccante; andrebbe sostituito con `ainvoke()` per sfruttare appieno l'asincronia di FastAPI
- **Nessun isolamento multi-utente**: un solo database ChromaDB condiviso, non adatto a un contesto multi-tenant

