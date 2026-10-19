"""Lógica del chat: conversación -> historial -> agente -> guardar pregunta y respuesta."""
import logging

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.security import CurrentUser
from services.agent_gateway import AGENT_DOWN_MESSAGE, AgentUnavailable, normalize_answer

logger = logging.getLogger(__name__)


def _title_from(question: str) -> str:
    title = " ".join(question.split())
    return title if len(title) <= 60 else title[:57].rstrip() + "…"


class ChatService:
    def __init__(self, repo, agent) -> None:
        self.repo = repo
        self.agent = agent

    def ask(self, user: CurrentUser, question: str, conversation_id: str | None) -> dict:
        question = question.strip()
        if not question:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La pregunta no puede estar vacía.")

        is_new = not conversation_id
        if conversation_id:
            conversation = self.repo.get_conversation(user.id, conversation_id)
            if conversation is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "La conversación no existe.")
        else:
            conversation = self.repo.create_conversation(user.id, _title_from(question))

        # Los últimos N mensajes, en orden cronológico, para preguntas de seguimiento
        window = get_settings().history_window
        previous = self.repo.list_messages(user.id, conversation["id"])[-window:] if window else []
        history = [{"role": m["role"], "content": m["content"]} for m in previous]

        # Primero se consulta al agente: si falla, no queda una pregunta huérfana en el historial
        try:
            result = normalize_answer(self.agent.ask(question, user.id, history))
        except AgentUnavailable as exc:
            self._discard(user, conversation, is_new)
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
        except Exception:
            logger.exception("Error ejecutando el agente")
            self._discard(user, conversation, is_new)
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, AGENT_DOWN_MESSAGE)

        question_msg = self.repo.add_message(conversation["id"], user.id, "user", question)
        answer_msg = self.repo.add_message(
            conversation["id"], user.id, "assistant", result["answer"],
            sources=result["sources"], rejected=result["rejected"],
        )
        conversation = self.repo.touch_conversation(conversation["id"])
        return {"conversation": conversation, "question": question_msg, "answer": answer_msg}

    def _discard(self, user: CurrentUser, conversation: dict, is_new: bool) -> None:
        if is_new:
            self.repo.delete_conversation(user.id, conversation["id"])

    def list_conversations(self, user: CurrentUser) -> list[dict]:
        return self.repo.list_conversations(user.id)

    def get_messages(self, user: CurrentUser, conversation_id: str) -> list[dict]:
        if self.repo.get_conversation(user.id, conversation_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "La conversación no existe.")
        return self.repo.list_messages(user.id, conversation_id)

    def delete_conversation(self, user: CurrentUser, conversation_id: str) -> None:
        if self.repo.get_conversation(user.id, conversation_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "La conversación no existe.")
        self.repo.delete_conversation(user.id, conversation_id)
