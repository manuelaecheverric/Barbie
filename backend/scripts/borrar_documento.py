"""
Borra un documento de la base vectorial, o muestra qué documentos hay.

Ejecútalo desde la carpeta backend/:
    python scripts/borrar_documento.py                 -> lista los documentos
    python scripts/borrar_documento.py <doc_id>        -> borra ese documento
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vectorstore import delete_document, listar_documentos  # noqa: E402

if len(sys.argv) == 1:
    documentos = listar_documentos()
    if not documentos:
        print("La base vectorial está vacía.")
    for d in documentos:
        print(f"  {d['doc_id']:<45} {d['fragmentos']:>3} fragmentos  ({d['filename']})")
    sys.exit(0)

doc_id = sys.argv[1]
borrados = delete_document(doc_id)
print(f"Borrados {borrados} fragmentos de '{doc_id}'.")
