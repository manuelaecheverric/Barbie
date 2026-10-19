"""
Registra en la biblioteca de la app (tabla public.documents) los documentos
que ya están en la base vectorial pero no en la tabla, por ejemplo las fichas
del corpus que se cargaron con scripts/cargar_documentos.py.

Se marcan como "base de conocimiento inicial" (sin dueño): aparecen en la
biblioteca pero nadie las puede borrar desde la app.

Ejecútalo desde la carpeta backend/ (con backend/.env configurado):
    python scripts/sincronizar_biblioteca.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from supabase import create_client  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from vectorstore import listar_documentos  # noqa: E402

settings = get_settings()
if not (settings.supabase_url and settings.supabase_service_role_key):
    sys.exit("Faltan SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en backend/.env")

db = create_client(settings.supabase_url, settings.supabase_service_role_key)
existentes = {fila["id"] for fila in db.table("documents").select("id").execute().data}

en_vectores = listar_documentos()
nuevos = [
    {
        "id": d["doc_id"],
        "user_id": None,
        "filename": d["filename"] or d["doc_id"],
        "content_type": None,
        "size_bytes": 0,
        "chunks": int(d["fragmentos"]),
        "status": "ready",
    }
    for d in en_vectores
    if d["doc_id"] and d["doc_id"] not in existentes
]

if nuevos:
    db.table("documents").insert(nuevos).execute()
for d in nuevos:
    print(f"  ✅ {d['filename']} ({d['chunks']} fragmentos)")
print(f"\nListo: {len(nuevos)} documento(s) nuevos en la biblioteca, "
      f"{len(en_vectores) - len(nuevos)} ya estaban.")
