"""
Pasos 3 a 5 de la carga, y la búsqueda.

Usa PGVector de LangChain sobre Postgres (Supabase) con la extensión pgvector.
LangChain crea solo dos tablas la primera vez:
    langchain_pg_collection  -> una fila por colección ("barbie")
    langchain_pg_embedding   -> una fila por fragmento: texto, vector y metadatos
Cada fragmento guarda en sus metadatos el doc_id y el nombre del archivo,
así se sabe de qué documento salió y se puede borrar.
"""

from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, text

from . import config
from .fragmentar import fragmentar
from .loaders import FORMATOS_SOPORTADOS, leer_archivo


@lru_cache
def _engine():
    if not config.DATABASE_URL:
        raise RuntimeError("Falta DATABASE_URL en backend/.env")
    # pool_pre_ping: revisa la conexión antes de usarla (Supabase cierra las inactivas).
    return create_engine(config.DATABASE_URL, pool_pre_ping=True)


@lru_cache
def _store():
    from langchain_postgres import PGVector

    return PGVector(
        embeddings=config.get_embeddings(),
        connection=_engine(),
        collection_name=config.COLLECTION_NAME,
        embedding_length=config.EMBED_DIM,
        use_jsonb=True,
        create_extension=False,  # pgvector ya está activo en Supabase
    )


def ingest(file_path: str, doc_id: str, filename: str) -> int:
    """Lee, fragmenta, genera embeddings y guarda. Devuelve cuántos fragmentos quedaron."""
    extension = Path(filename).suffix.lower()
    if extension not in FORMATOS_SOPORTADOS:
        raise ValueError(f"Formato no soportado: {extension}")

    documentos = leer_archivo(file_path, extension)
    fragmentos = fragmentar(documentos, extension)
    if not fragmentos:
        raise ValueError("No se pudo extraer texto del documento.")

    doc_id = str(doc_id)
    for numero, fragmento in enumerate(fragmentos):
        fragmento.metadata.update(doc_id=doc_id, filename=filename, fragmento=numero)

    # Si el documento ya estaba cargado, se reemplaza (no se duplica).
    delete_document(doc_id)
    ids = [f"{doc_id}:{numero}" for numero in range(len(fragmentos))]
    _store().add_documents(fragmentos, ids=ids)
    return len(fragmentos)


def delete_document(doc_id: str) -> int:
    """Borra todos los fragmentos de un documento. Devuelve cuántos borró."""
    _store()  # garantiza que las tablas existan
    consulta = text(
        """
        DELETE FROM langchain_pg_embedding
        WHERE collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = :coleccion
        )
        AND cmetadata->>'doc_id' = :doc_id
        """
    )
    with _engine().begin() as conexion:
        resultado = conexion.execute(
            consulta, {"coleccion": config.COLLECTION_NAME, "doc_id": str(doc_id)}
        )
    return resultado.rowcount


def search(query: str, k: int = 4, min_score: float | None = None) -> list[dict]:
    """Busca los k fragmentos más parecidos a la pregunta.

    score = similitud coseno entre 0 y 1 (1 = idéntico). Si se pasa min_score,
    se descartan los fragmentos por debajo de ese valor.
    """
    resultados = _store().similarity_search_with_score(query, k=k)
    fragmentos = []
    for documento, distancia in resultados:
        score = round(1 - float(distancia), 4)  # PGVector devuelve distancia coseno
        if min_score is not None and score < min_score:
            continue
        fragmentos.append(
            {
                "doc": documento.metadata.get("filename", ""),
                "doc_id": documento.metadata.get("doc_id", ""),
                "fragment": documento.page_content,
                "score": score,
            }
        )
    return sorted(fragmentos, key=lambda f: f["score"], reverse=True)


def listar_documentos() -> list[dict]:
    """Documentos que hay en la base vectorial, con su número de fragmentos."""
    _store()
    consulta = text(
        """
        SELECT cmetadata->>'doc_id' AS doc_id,
               cmetadata->>'filename' AS filename,
               COUNT(*) AS fragmentos
        FROM langchain_pg_embedding
        WHERE collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = :coleccion
        )
        GROUP BY 1, 2
        ORDER BY 2
        """
    )
    with _engine().connect() as conexion:
        filas = conexion.execute(consulta, {"coleccion": config.COLLECTION_NAME})
        return [dict(fila._mapping) for fila in filas]
