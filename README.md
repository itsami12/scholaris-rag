# ≡ƒö¼ Scholaris ΓÇö AI Research Paper Chatbot

> Upload research papers ┬╖ Chat with context-aware AI ┬╖ Explore with a knowledge graph ┬╖ Export your conversations

---

## ≡ƒôª Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Streamlit |
| **Backend** | FastAPI |
| **LLM** | Groq (`llama-3.3-70b-versatile`) |
| **Embeddings** | Nomic (`nomic-embed-text-v1.5`) |
| **Vector DB** | Qdrant Cloud |
| **Graph DB** | Neo4j Aura |
| **OCR** | OCR.Space API (for scanned PDFs) |
| **PDF parsing** | PyMuPDF |

---

## ≡ƒÜÇ Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
All API keys are pre-filled in `.env`. Edit if needed.

### 3. Run everything
```bash
bash run.sh
```

| Service | URL |
|---|---|
| Streamlit UI | http://localhost:8501 |
| FastAPI backend | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |

### Or run manually
```bash
# Terminal 1 ΓÇö Backend
uvicorn backend.main:app --reload

# Terminal 2 ΓÇö Frontend
streamlit run frontend/app.py
```

## ≡ƒÜÇ Deploy on Render

This repo is set up for two Render web services:

1. `scholaris-backend` runs the FastAPI app.
2. `scholaris-frontend` runs the Streamlit app.

Use the included [render.yaml](render.yaml) blueprint, or create the services manually with these start commands:

```bash
# Backend
uvicorn backend.main:app --host 0.0.0.0 --port $PORT

# Frontend
streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
```

Set these environment variables in Render:

| Variable | Service | Notes |
|---|---|---|
| `OCR_SPACE_API_KEY` | Backend | Required for scanned PDFs |
| `NEO4J_URI` | Backend | Neo4j Aura URI |
| `NEO4J_USERNAME` | Backend | Neo4j username |
| `NEO4J_PASSWORD` | Backend | Neo4j password |
| `NOMIC_API_KEY` | Backend | Nomic embeddings key |
| `QDRANT_URL` | Backend | Qdrant Cloud URL |
| `QDRANT_API_KEY` | Backend | Qdrant Cloud API key |
| `GROQ_API_KEY` | Backend | Groq API key |
| `BACKEND_URL` | Frontend | Set to your backend service URL, for example `https://scholaris-backend.onrender.com` |

The repo now includes [\.env.example](.env.example) as a template for both local development and Render settings.

## ≡ƒñù Deploy both frontend and backend in one Hugging Face Space

Use a **Docker Space**. The container starts the FastAPI backend on `127.0.0.1:8000` and Streamlit on Hugging Face's public port `7860`.

### Steps
1. Create a new Space on Hugging Face.
2. Choose **Docker** as the SDK.
3. Connect this GitHub repo.
4. Let Spaces build from the included [Dockerfile](Dockerfile).
5. Add these secrets in the Space settings:
   - `OCR_SPACE_API_KEY`
   - `NEO4J_URI`
   - `NEO4J_USERNAME`
   - `NEO4J_PASSWORD`
   - `NOMIC_API_KEY`
   - `QDRANT_URL`
   - `QDRANT_API_KEY`
   - `GROQ_API_KEY`
6. If you enable persistent storage, set `HISTORY_DIR` to `/data/chat_history`.
7. Deploy the Space and use the public Space URL, for example `https://your-name-scholaris.hf.space`.

### Important
- You do not need a separate `BACKEND_URL` for the Space itself because the frontend talks to the backend on `http://127.0.0.1:8000` inside the same container.
- The container must expose only the Streamlit app publicly on port `7860`.
- Without persistent storage, chat history resets when the Space restarts.

---

## ≡ƒùé∩╕Å Project Structure

```
scholaris/
Γö£ΓöÇΓöÇ backend/
Γöé   ΓööΓöÇΓöÇ main.py              FastAPI app ΓÇö all endpoints
Γö£ΓöÇΓöÇ frontend/
Γöé   ΓööΓöÇΓöÇ app.py               Streamlit UI
Γö£ΓöÇΓöÇ utils/
Γöé   Γö£ΓöÇΓöÇ document_processor.py  PDF/DOCX/TXT extraction + OCR
Γöé   Γö£ΓöÇΓöÇ metadata_extractor.py  Title, authors, DOI, keywordsΓÇª
Γöé   Γö£ΓöÇΓöÇ chunker.py             Overlapping text chunker
Γöé   Γö£ΓöÇΓöÇ graph_store.py         Neo4j: Paper/Author/Keyword nodes
Γöé   Γö£ΓöÇΓöÇ vector_store.py        Qdrant: embeddings + search
Γöé   Γö£ΓöÇΓöÇ llm.py                 Groq: RAG chat + summarization
Γöé   ΓööΓöÇΓöÇ history_manager.py     Session persistence + export
Γö£ΓöÇΓöÇ chat_history/              Auto-created; JSON session files
Γö£ΓöÇΓöÇ config.py                  Centralized env var loader
Γö£ΓöÇΓöÇ requirements.txt
Γö£ΓöÇΓöÇ .env                       API keys & config
ΓööΓöÇΓöÇ run.sh                     One-command startup
```

---

## ≡ƒôï Pipeline

```
Upload Document (PDF / DOCX / TXT)
        Γåô
Document Type Detection
        Γåô
Scanned PDF? ΓåÆ OCR.Space API
Else        ΓåÆ PyMuPDF
        Γåô
Text Cleaning & Chunking (800 tokens, 150 overlap)
        Γåô
Metadata Extraction (title, authors, journal, DOI, year, keywords)
        Γåô
Neo4j Aura  ΓåÉ Paper, Author, Keyword, Journal nodes + relationships
        Γåô
Nomic Embeddings (nomic-embed-text-v1.5, dim=768)
        Γåô
Qdrant Cloud ΓåÉ chunk vectors + metadata payload
        Γåô
User Query ΓåÆ vector search ΓåÆ top-6 chunks retrieved
        Γåô
Groq LLM (llama-3.3-70b) + conversation history ΓåÆ answer
        Γåô
Session saved to chat_history/<id>.json
```

---

## ≡ƒÆ¼ Chat History Features

| Feature | Description |
|---|---|
| **Persistent sessions** | Every conversation saved as JSON |
| **Sidebar history** | Browse past conversations like ChatGPT |
| **Context window** | Last 10 turns sent as LLM context |
| **Export one session** | Download as `.md` file |
| **Export all sessions** | One Markdown file with full history |
| **Delete session** | Remove individual conversation |
| **Delete all** | Clear entire history |
| **Auto-title** | First user message becomes session title |

---

## ≡ƒöî API Reference

### Documents
| Method | Path | Description |
|---|---|---|
| `POST` | `/upload` | Ingest a document |
| `GET` | `/papers` | List all papers |
| `GET` | `/papers/{id}` | Paper metadata |
| `DELETE` | `/papers/{id}` | Delete paper |

### Chat
| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | Context-aware Q&A |
| `POST` | `/summarize/{id}` | Summarize paper |

### History
| Method | Path | Description |
|---|---|---|
| `GET` | `/history` | List all sessions |
| `GET` | `/history/{sid}` | Full session with messages |
| `DELETE` | `/history/{sid}` | Delete one session |
| `DELETE` | `/history` | Delete ALL sessions |
| `PATCH` | `/history/{sid}/rename` | Rename session |
| `GET` | `/history/{sid}/export` | Session as Markdown |
| `GET` | `/history/export/all` | All history as Markdown |

---

## ≡ƒô¥ Chat Request Format

```json
POST /chat
{
  "query":      "What is the main contribution of this paper?",
  "paper_id":   "uuid-optional-filter",
  "session_id": "uuid-optional-resumes-session"
}
```

If `session_id` is omitted, a new session is created automatically.
