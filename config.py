"""Central configuration loaded from .env"""
import os
from dotenv import load_dotenv

load_dotenv()

# OCR
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY", "")

# Neo4j
NEO4J_URI      = os.getenv("NEO4J_URI", "")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

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
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
