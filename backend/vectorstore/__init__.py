"""
Base vectorial (pgvector en Supabase) y carga de documentos.

⚠️ VERSIÓN FALSA (stub) para integrar la API desde ya.
Las firmas NO cambian cuando llegue la versión real.

Contrato:
    ingest(file_path, doc_id, filename) -> int   (número de fragmentos)
    delete_document(doc_id) -> None

Formatos soportados: PDF, TXT, MD, DOCX, CSV.
La API debe validar la extensión antes de llamar a ingest().
"""

from pathlib import Path

FORMATOS_SOPORTADOS = {".pdf", ".txt", ".md", ".docx", ".csv"}


def ingest(file_path: str, doc_id: str, filename: str) -> int:
    extension = Path(filename).suffix.lower()
    if extension not in FORMATOS_SOPORTADOS:
        raise ValueError(f"Formato no soportado: {extension}")
    # Simula que el documento se dividió en 12 fragmentos.
    return 12


def delete_document(doc_id: str) -> None:
    # La versión real borrará todos los fragmentos con ese doc_id.
    return None