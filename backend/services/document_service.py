"""Carga de documentos: validar -> guardar temporal -> registrar -> procesar con el agente."""
import logging
import os
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings
from app.core.security import CurrentUser

logger = logging.getLogger(__name__)
INGEST_DOWN_MESSAGE = (
    "No se pudo procesar el documento porque el modelo de embeddings o la base vectorial "
    "no respondieron. Elimínalo y vuelve a subirlo en unos minutos."
)
_CHUNK = 1024 * 1024


def _safe_name(filename: str) -> str:
    name = Path(filename or "documento").name
    return re.sub(r"[^\w.\- ()áéíóúÁÉÍÓÚñÑ]", "_", name)[:150] or "documento"


class DocumentService:
    def __init__(self, repo, agent) -> None:
        self.repo = repo
        self.agent = agent

    async def receive(self, user: CurrentUser, upload: UploadFile) -> tuple[dict, str]:
        """Valida y guarda el archivo. Devuelve (registro, ruta temporal)."""
        settings = get_settings()
        filename = _safe_name(upload.filename or "")
        ext = Path(filename).suffix.lower()
        allowed = settings.allowed_extension_set
        if ext not in allowed:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Formato no permitido ({ext or 'sin extensión'}). Usa: {', '.join(sorted(allowed))}.",
            )

        max_bytes = settings.max_upload_mb * 1024 * 1024
        os.makedirs(settings.upload_dir, exist_ok=True)
        tmp_path = os.path.join(settings.upload_dir, f"{uuid.uuid4()}{ext}")
        size = 0
        try:
            with open(tmp_path, "wb") as out:
                while chunk := await upload.read(_CHUNK):
                    size += len(chunk)
                    if size > max_bytes:
                        raise HTTPException(
                            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"El archivo supera el límite de {settings.max_upload_mb} MB.",
                        )
                    out.write(chunk)
            if size == 0:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo está vacío.")
        except HTTPException:
            _remove(tmp_path)
            raise

        doc = self.repo.create_document(user.id, filename, upload.content_type, size)
        return doc, tmp_path

    def process(self, document_id: str, tmp_path: str, filename: str) -> None:
        """Se ejecuta en segundo plano: extrae, fragmenta y guarda embeddings."""
        try:
            chunks = self.agent.ingest(tmp_path, document_id, filename)
            self.repo.update_document(document_id, status="ready", chunks=chunks, error=None)
        except ValueError as exc:
            # Formato inválido, archivo sin texto, PDF escaneado...: mensaje del agente para el usuario
            logger.warning("Documento rechazado %s: %s", filename, exc)
            self.repo.update_document(document_id, status="error", error=str(exc)[:300] or "Error al procesar.")
        except Exception:
            logger.exception("Error procesando %s", filename)
            self.repo.update_document(document_id, status="error", error=INGEST_DOWN_MESSAGE)
        finally:
            _remove(tmp_path)

    def list(self, user: CurrentUser) -> list[dict]:
        return [{**d, "is_owner": d.get("user_id") == user.id} for d in self.repo.list_documents()]

    def delete(self, user: CurrentUser, document_id: str) -> None:
        doc = self.repo.get_document(document_id)
        if doc is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "El documento no existe.")
        if doc.get("user_id") is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Los documentos de la base inicial no se pueden eliminar.")
        if doc["user_id"] != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo quien subió el documento puede eliminarlo.")
        try:
            self.agent.delete_document(document_id)
        except Exception:
            logger.exception("No se pudo borrar %s de la base vectorial", document_id)
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "No se pudo borrar el documento de la base vectorial.")
        self.repo.delete_document(document_id)


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
