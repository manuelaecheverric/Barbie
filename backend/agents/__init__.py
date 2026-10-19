"""
Agente Barbie (LangGraph + RAG).

Contrato (lo usa la API):
    ask(question, user_id, history) -> {
        "answer": str,
        "rejected": bool,
        "sources": [{"doc": str, "fragment": str, "score": float}],
        "error": bool,   # True solo si el modelo o la base no respondieron
    }

    history: últimos ~6 mensajes, en orden cronológico:
        [{"role": "user" | "assistant", "content": str}, ...]

El agente NO guarda el historial: la API guarda la pregunta y la respuesta
en Supabase después de llamar a ask(), y en la siguiente pregunta se los pasa.
"""

import logging

from .prompts import MENSAJE_ERROR, MENSAJE_RECHAZO

logger = logging.getLogger("agente_barbie")


def ask(question: str, user_id: str, history: list[dict] | None = None) -> dict:
    try:
        from .graph import grafo

        estado = grafo.invoke(
            {"question": question, "user_id": user_id, "history": history or []}
        )
        return {
            "answer": estado["answer"],
            "rejected": estado["rejected"],
            "sources": estado["sources"],
            "error": False,
        }
    except Exception:  # noqa: BLE001
        logger.exception("El agente falló respondiendo: %r", question)
        return {"answer": MENSAJE_ERROR, "rejected": True, "sources": [], "error": True}


__all__ = ["ask", "MENSAJE_RECHAZO"]
