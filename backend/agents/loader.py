"""Carga el agente según AGENT_MODE y normaliza sus respuestas."""
import importlib
import logging
from functools import lru_cache

from agents.contract import REJECTION_MESSAGE, AgentAnswer
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ModuleAgent:
    """Adapta un módulo con funciones ask/ingest/delete_document al contrato."""

    def __init__(self, module_path: str):
        self.module = importlib.import_module(module_path)
        missing = [f for f in ("ask", "ingest", "delete_document") if not hasattr(self.module, f)]
        if missing:
            raise RuntimeError(f"El módulo '{module_path}' no implementa: {', '.join(missing)}")

    def ask(self, question, user_id, history) -> AgentAnswer:
        return normalize_answer(self.module.ask(question, user_id, history))

    def ingest(self, file_path, document_id, filename) -> int:
        return int(self.module.ingest(file_path, document_id, filename) or 0)

    def delete_document(self, document_id) -> None:
        self.module.delete_document(document_id)


def normalize_answer(raw) -> AgentAnswer:
    """Acepta variaciones razonables (str, dict con otras llaves) y devuelve el contrato."""
    if isinstance(raw, str):
        raw = {"answer": raw}
    raw = dict(raw or {})
    answer = (raw.get("answer") or raw.get("response") or raw.get("generation") or "").strip()
    rejected = bool(raw.get("rejected", False)) or not answer or answer.startswith(REJECTION_MESSAGE[:40])
    sources = []
    for s in raw.get("sources") or []:
        if isinstance(s, dict):
            sources.append(
                {
                    "document": str(s.get("doc") or s.get("document") or s.get("source") or s.get("filename") or "documento"),
                    "fragment": str(s.get("fragment") or s.get("page_content") or s.get("content") or "")[:1200],
                    "score": s.get("score"),
                    "document_id": s.get("doc_id") or s.get("document_id"),
                }
            )
    return {"answer": answer or REJECTION_MESSAGE, "rejected": rejected, "sources": [] if rejected else sources}


@lru_cache
def get_agent():
    settings = get_settings()
    if settings.agent_mode == "real":
        logger.info("Cargando agente real desde %s", settings.agent_module)
        return ModuleAgent(settings.agent_module)
    from agents.mock_agent import MockAgent

    logger.warning("AGENT_MODE=mock: usando el agente simulado")
    return MockAgent()
