---
title: Scholaris
emoji: 🔬
colorFrom: blue
colorTo: indigo
sdk: docker
sdk_version: "latest"
app_file: frontend/app.py
app_port: 7860
pinned: false
---

# Scholaris

Scholaris is an AI research paper chatbot with a Streamlit frontend and a FastAPI backend.

## Space setup

This Space runs both services in one Docker container:

- FastAPI backend on `127.0.0.1:8000`
- Streamlit frontend on `0.0.0.0:7860`

## Required secrets

Add these in the Hugging Face Space settings:

- `OCR_SPACE_API_KEY`
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`
- `NOMIC_API_KEY`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `GROQ_API_KEY`

If you want persistent chat history, enable persistent storage and set `HISTORY_DIR=/data/chat_history`.

## Local development

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
streamlit run frontend/app.py
```
