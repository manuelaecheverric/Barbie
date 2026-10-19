"""
Base vectorial (pgvector en Supabase) y carga de documentos.

Contrato (lo usa la API):
    ingest(file_path, doc_id, filename) -> int   (número de fragmentos)
    delete_document(doc_id) -> int               (fragmentos borrados)

Extra (lo usa el agente y los scripts):
    search(query, k=4, min_score=None) -> [{"doc", "doc_id", "fragment", "score"}]
    listar_documentos() -> [{"doc_id", "filename", "fragmentos"}]

Formatos soportados: PDF, TXT, MD, DOCX, CSV.
ingest() lanza ValueError si el formato no es válido o el archivo no tiene texto;
la API puede devolver ese mensaje al usuario.
"""

from .loaders import FORMATOS_SOPORTADOS
from .store import delete_document, ingest, listar_documentos, search

__all__ = [
    "FORMATOS_SOPORTADOS",
    "ingest",
    "delete_document",
    "search",
    "listar_documentos",
]
