"""Repositorio sobre Supabase Postgres (tablas en supabase/schema.sql).

Usa la llave de servicio (solo en el backend, nunca en el frontend) y filtra
SIEMPRE por user_id, de modo que cada usuario solo accede a lo suyo.
"""
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from repositories.base import Row


class SupabaseRepository:
    def __init__(self, url: str, service_role_key: str) -> None:
        self.client: Client = create_client(url, service_role_key)

    # ---------- Conversaciones ----------
    def create_conversation(self, user_id: str, title: str) -> Row:
        res = self.client.table("conversations").insert({"user_id": user_id, "title": title}).execute()
        return res.data[0]

    def list_conversations(self, user_id: str) -> list[Row]:
        res = (
            self.client.table("conversations").select("*").eq("user_id", user_id)
            .order("updated_at", desc=True).limit(100).execute()
        )
        return res.data

    def get_conversation(self, user_id: str, conversation_id: str) -> Row | None:
        res = (
            self.client.table("conversations").select("*")
            .eq("id", conversation_id).eq("user_id", user_id).limit(1).execute()
        )
        return res.data[0] if res.data else None

    def touch_conversation(self, conversation_id: str) -> Row:
        now = datetime.now(timezone.utc).isoformat()
        res = self.client.table("conversations").update({"updated_at": now}).eq("id", conversation_id).execute()
        return res.data[0]

    def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        self.client.table("conversations").delete().eq("id", conversation_id).eq("user_id", user_id).execute()

    # ---------- Mensajes ----------
    def add_message(self, conversation_id, user_id, role, content, sources=None, rejected=False) -> Row:
        res = self.client.table("messages").insert({
            "conversation_id": conversation_id, "user_id": user_id, "role": role,
            "content": content, "sources": sources or [], "rejected": rejected,
        }).execute()
        return res.data[0]

    def list_messages(self, user_id: str, conversation_id: str) -> list[Row]:
        res = (
            self.client.table("messages").select("*")
            .eq("conversation_id", conversation_id).eq("user_id", user_id)
            .order("created_at").execute()
        )
        return res.data

    # ---------- Documentos ----------
    def create_document(self, user_id, filename, content_type, size_bytes) -> Row:
        res = self.client.table("documents").insert({
            "user_id": user_id, "filename": filename, "content_type": content_type,
            "size_bytes": size_bytes, "status": "processing",
        }).execute()
        return res.data[0]

    def update_document(self, document_id: str, **fields: Any) -> Row:
        res = self.client.table("documents").update(fields).eq("id", document_id).execute()
        return res.data[0]

    def get_document(self, document_id: str) -> Row | None:
        res = self.client.table("documents").select("*").eq("id", document_id).limit(1).execute()
        return res.data[0] if res.data else None

    def list_documents(self) -> list[Row]:
        res = self.client.table("documents").select("*").order("created_at", desc=True).execute()
        return res.data

    def delete_document(self, document_id: str) -> None:
        self.client.table("documents").delete().eq("id", document_id).execute()
