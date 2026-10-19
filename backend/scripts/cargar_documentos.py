"""
Carga todos los archivos de una carpeta a la base vectorial.

Ejecútalo desde la carpeta backend/:
    python scripts/cargar_documentos.py ../data/corpus

El doc_id de cada archivo es "<carpeta>-<nombre sin extensión>",
p. ej. "corpus-03-ken". Si lo corres dos veces, reemplaza (no duplica).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # para importar vectorstore

from vectorstore import FORMATOS_SOPORTADOS, ingest  # noqa: E402

if len(sys.argv) != 2:
    print("Uso: python scripts/cargar_documentos.py <carpeta>")
    sys.exit(1)

carpeta = Path(sys.argv[1]).resolve()
archivos = sorted(
    a for a in carpeta.iterdir() if a.suffix.lower() in FORMATOS_SOPORTADOS
)
if not archivos:
    print(f"No hay archivos PDF, TXT, MD, DOCX o CSV en {carpeta}")
    sys.exit(1)

print(f"Cargando {len(archivos)} archivo(s) de {carpeta.name}/ ...\n")
inicio = time.time()
total = 0
for archivo in archivos:
    doc_id = f"{carpeta.name}-{archivo.stem}"
    try:
        n = ingest(str(archivo), doc_id, archivo.name)
        total += n
        print(f"  ✅ {archivo.name}: {n} fragmentos  (doc_id = {doc_id})")
    except Exception as error:  # noqa: BLE001
        print(f"  ❌ {archivo.name}: {error}")

print(f"\nListo: {total} fragmentos en {time.time() - inicio:.1f} s.")
