"""Puente entre la API (Persona 2) y el agente (Persona 1).

La API usa solo este módulo. El código del agente vive en:
    agents/       -> ask(question, user_id, history)
    vectorstore/  -> ingest(file_path, doc_id, filename), delete_document(doc_id),
                     listar_documentos()

Contrato de ask():
    {"answer": str, "rejected": bool, "sources": [{"doc", "fragment", "score"}],
     "error": bool}   # error=True: Ollama o la base vectorial no respondieron

Con AGENT_MODE=mock se usa un agente simulado (services/mock_agent.py).
"""
import logging
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)

REJECTION_MESSAGE = "No tengo suficiente información en mi base de conocimiento para responder esa pregunta."
AGENT_DOWN_MESSAGE = "El agente no está disponible en este momento. Intenta de nuevo en unos segundos."


class AgentUnavailable(Exception):
    """El modelo (Ollama) o la base vectorial no respondieron."""


def normalize_answer(raw) -> dict:
    """Valida la respuesta del agente y la deja en el formato de la API.

    Lanza AgentUnavailable si el agente reporta error=True.
    """
    if isinstance(raw, str):
        raw = {"answer": raw}
    raw = dict(raw or {})
    answer = (raw.get("answer") or "").strip()

    if raw.get("error"):
        raise AgentUnavailable(answer or AGENT_DOWN_MESSAGE)

    rejected = bool(raw.get("rejected", False)) or not answer
    sources = []
    for s in raw.get("sources") or []:
        if isinstance(s, dict):
            sources.append(
                {
                    "document": str(s.get("doc") or s.get("document") or s.get("filename") or "documento"),
                    "fragment": str(s.get("fragment") or s.get("page_content") or "")[:1200],
                    "score": s.get("score"),
                    "document_id": s.get("doc_id") or s.get("document_id"),
                }
            )
    return {"answer": answer or REJECTION_MESSAGE, "rejected": rejected, "sources": [] if rejected else sources}


class RealAgent:
    """Llama al código de la Persona 1. Se importa solo cuando AGENT_MODE=real."""

    def __init__(self) -> None:
        import agents
        import vectorstore

        self._ask = agents.ask
        self._ingest = vectorstore.ingest
        self._delete = vectorstore.delete_document
        self._list = getattr(vectorstore, "listar_documentos", None)

    def ask(self, question, user_id, history):
        return self._ask(question, user_id, history)

    def ingest(self, file_path, doc_id, filename) -> int:
        return int(self._ingest(file_path, doc_id, filename) or 0)

    def delete_document(self, doc_id) -> None:
        self._delete(doc_id)

    def list_documents(self) -> list[dict]:
        return self._list() if self._list else []


@lru_cache
def get_agent():
    if get_settings().agent_mode == "real":
        logger.info("Usando el agente real (agents/ + vectorstore/)")
        return RealAgent()
    from services.mock_agent import MockAgent

    logger.warning("AGENT_MODE=mock: usando el agente simulado")
    return MockAgent()
