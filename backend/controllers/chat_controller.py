from fastapi import APIRouter, Depends, status

from app.core.security import CurrentUser, get_current_user
from app.schemas import ChatRequest, ChatResponse, Conversation, Message
from services import get_chat_service
from services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse, summary="Enviar una pregunta al agente")
def ask(
    body: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return service.ask(user, body.question, body.conversation_id)


@router.get("/conversations", response_model=list[Conversation], summary="Historial de conversaciones del usuario")
def list_conversations(
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return service.list_conversations(user)


@router.get("/conversations/{conversation_id}/messages", response_model=list[Message],
            summary="Mensajes de una conversación")
def get_messages(
    conversation_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return service.get_messages(user, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Eliminar una conversación")
def delete_conversation(
    conversation_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    service.delete_conversation(user, conversation_id)
