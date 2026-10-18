"""Repositorio en memoria: para pruebas y desarrollo sin Supabase.
Los datos se pierden al reiniciar el servidor."""
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from repositories.base import Row


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryRepository:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.conversations: dict[str, Row] = {}
        self.messages: list[Row] = []
        self.documents: dict[str, Row] = {}

    def create_conversation(self, user_id: str, title: str) -> Row:
        row = {"id": str(uuid.uuid4()), "user_id": user_id, "title": title, "created_at": _now(), "updated_at": _now()}
        with self._lock:
            self.conversations[row["id"]] = row
        return dict(row)

    def list_conversations(self, user_id: str) -> list[Row]:
        rows = [dict(c) for c in self.conversations.values() if c["user_id"] == user_id]
        return sorted(rows, key=lambda c: c["updated_at"], reverse=True)

    def get_conversation(self, user_id: str, conversation_id: str) -> Row | None:
        row = self.conversations.get(conversation_id)
        return dict(row) if row and row["user_id"] == user_id else None

    def touch_conversation(self, conversation_id: str) -> Row:
        with self._lock:
            self.conversations[conversation_id]["updated_at"] = _now()
            return dict(self.conversations[conversation_id])

    def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        with self._lock:
            if self.conversations.get(conversation_id, {}).get("user_id") == user_id:
                del self.conversations[conversation_id]
                self.messages = [m for m in self.messages if m["conversation_id"] != conversation_id]

    def add_message(self, conversation_id, user_id, role, content, sources=None, rejected=False) -> Row:
        row = {
            "id": str(uuid.uuid4()), "conversation_id": conversation_id, "user_id": user_id, "role": role,
            "content": content, "sources": sources or [], "rejected": rejected, "created_at": _now(),
        }
        with self._lock:
            self.messages.append(row)
        return dict(row)

    def list_messages(self, user_id: str, conversation_id: str) -> list[Row]:
        return [dict(m) for m in self.messages if m["conversation_id"] == conversation_id and m["user_id"] == user_id]

    def create_document(self, user_id, filename, content_type, size_bytes) -> Row:
        row = {
            "id": str(uuid.uuid4()), "user_id": user_id, "filename": filename, "content_type": content_type,
            "size_bytes": size_bytes, "chunks": 0, "status": "processing", "error": None, "created_at": _now(),
        }
        with self._lock:
            self.documents[row["id"]] = row
        return dict(row)

    def update_document(self, document_id: str, **fields: Any) -> Row:
        with self._lock:
            self.documents[document_id].update(fields)
            return dict(self.documents[document_id])

    def get_document(self, document_id: str) -> Row | None:
        row = self.documents.get(document_id)
        return dict(row) if row else None

    def list_documents(self) -> list[Row]:
        return sorted((dict(d) for d in self.documents.values()), key=lambda d: d["created_at"], reverse=True)

    def delete_document(self, document_id: str) -> None:
        with self._lock:
            self.documents.pop(document_id, None)
