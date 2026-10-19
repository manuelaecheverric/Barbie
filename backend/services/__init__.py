from services.agent_gateway import get_agent
from repositories import get_repository
from services.chat_service import ChatService
from services.document_service import DocumentService


def get_chat_service() -> ChatService:
    return ChatService(get_repository(), get_agent())


def get_document_service() -> DocumentService:
    return DocumentService(get_repository(), get_agent())
