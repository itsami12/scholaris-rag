"""Central configuration loaded from .env"""
import os
from dotenv import load_dotenv

load_dotenv()


def _resolve_backend_url() -> str:
	"""Prefer the internal backend URL for Hugging Face Docker Spaces."""
	backend_url = os.getenv("BACKEND_URL", "").strip()
	if backend_url:
		hf_url_markers = ("hf.space", "huggingface.co/spaces")
		if not any(marker in backend_url for marker in hf_url_markers):
			return backend_url
	return "http://127.0.0.1:8000"

# OCR
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY", "")

# Neo4j
NEO4J_URI      = os.getenv("NEO4J_URI", "")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE  = os.getenv("NEO4J_DATABASE", "neo4j")

# Nomic
NOMIC_API_KEY = os.getenv("NOMIC_API_KEY", "")
NOMIC_MODEL   = os.getenv("NOMIC_MODEL", "nomic-embed-text-v1.5")

# Qdrant
QDRANT_API_KEY    = os.getenv("QDRANT_API_KEY", "")
QDRANT_URL        = os.getenv("QDRANT_URL", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "scholaris_chunks")

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Backend
BACKEND_URL = _resolve_backend_url()
