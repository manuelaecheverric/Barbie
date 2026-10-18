"""
Configuración compartida del agente (la usan vectorstore/ y agents/).

Todas las variables se leen del archivo backend/.env (ver .env.example en la raíz).
"""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

# ---------- Ollama ----------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_USER = os.getenv("OLLAMA_USER", "")
OLLAMA_PASS = os.getenv("OLLAMA_PASS", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
EMBED_DIM = 1024  # bge-m3 produce vectores de 1024 números

# ---------- Base vectorial ----------
DATABASE_URL = os.getenv("DATABASE_URL", "")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "barbie")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))

# ---------- Fragmentación ----------
CHUNK_SIZE = 600  # caracteres por fragmento
CHUNK_OVERLAP = 100  # caracteres que se repiten entre fragmentos vecinos


def ollama_client_kwargs() -> dict:
    """Opciones de conexión a Ollama.

    En local no hace falta nada. En producción (Ollama detrás de ngrok con
    usuario y contraseña) se agregan las credenciales.
    """
    opciones = {"timeout": 120}
    if OLLAMA_USER:
        opciones["auth"] = (OLLAMA_USER, OLLAMA_PASS)
    return opciones


@lru_cache
def get_embeddings():
    """Modelo de embeddings (bge-m3 en Ollama). Se crea una sola vez."""
    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_URL,
        client_kwargs=ollama_client_kwargs(),
    )
