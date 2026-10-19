"""Modelos de entrada y salida de la API (Pydantic)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Source(BaseModel):
    document: str
    fragment: str
    score: float | None = None
    document_id: str | None = None


class Message(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    sources: list[Source] = []
    rejected: bool = False
    created_at: datetime


class Conversation(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    conversation: Conversation
    question: Message
    answer: Message


class Document(BaseModel):
    id: str
    user_id: str | None = None  # None = base de conocimiento inicial (corpus)
    filename: str
    content_type: str | None = None
    size_bytes: int
    chunks: int = 0
    status: Literal["processing", "ready", "error"]
    error: str | None = None
    created_at: datetime
    is_owner: bool = False


class Me(BaseModel):
    id: str
    email: str | None = None
