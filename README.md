# 🔬 Scholaris — AI Research Paper Chatbot

> Upload research papers · Chat with context-aware AI · Explore with a knowledge graph · Export your conversations

---

## 📦 Tech Stack

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

## 🚀 Quick Start

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
# Terminal 1 — Backend
uvicorn backend.main:app --reload

# Terminal 2 — Frontend
streamlit run frontend/app.py
```

---
---

## 🌐 Live Demo

👉 Hugging Face Space:  
https://huggingface.co/spaces/itsami12/scholaris

---

## 🗂️ Project Structure

```
scholaris/
├── backend/
│   └── main.py              FastAPI app — all endpoints
├── frontend/
│   └── app.py               Streamlit UI
├── utils/
│   ├── document_processor.py  PDF/DOCX/TXT extraction + OCR
│   ├── metadata_extractor.py  Title, authors, DOI, keywords…
│   ├── chunker.py             Overlapping text chunker
│   ├── graph_store.py         Neo4j: Paper/Author/Keyword nodes
│   ├── vector_store.py        Qdrant: embeddings + search
│   ├── llm.py                 Groq: RAG chat + summarization
│   └── history_manager.py     Session persistence + export
├── chat_history/              Auto-created; JSON session files
├── config.py                  Centralized env var loader
├── requirements.txt
├── .env                       API keys & config
└── run.sh                     One-command startup
```

---

## 📋 Pipeline

```
Upload Document (PDF / DOCX / TXT)
        ↓
Document Type Detection
        ↓
Scanned PDF? → OCR.Space API
Else        → PyMuPDF
        ↓
Text Cleaning & Chunking (800 tokens, 150 overlap)
        ↓
Metadata Extraction (title, authors, journal, DOI, year, keywords)
        ↓
Neo4j Aura  ← Paper, Author, Keyword, Journal nodes + relationships
        ↓
Nomic Embeddings (nomic-embed-text-v1.5, dim=768)
        ↓
Qdrant Cloud ← chunk vectors + metadata payload
        ↓
User Query → vector search → top-6 chunks retrieved
        ↓
Groq LLM (llama-3.3-70b) + conversation history → answer
        ↓
Session saved to chat_history/<id>.json
```

---

## 💬 Chat History Features

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

## 🔌 API Reference

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

## 📝 Chat Request Format

```json
POST /chat
{
  "query":      "What is the main contribution of this paper?",
  "paper_id":   "uuid-optional-filter",
  "session_id": "uuid-optional-resumes-session"
}
```

If `session_id` is omitted, a new session is created automatically.
