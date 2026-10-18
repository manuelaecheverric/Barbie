"""
Prueba la búsqueda en la base vectorial y muestra los puntajes.
Sirve para ver si el umbral (SIMILARITY_THRESHOLD) separa bien
las preguntas del tema de las que no lo son.

Ejecútalo desde la carpeta backend/:
    python scripts/probar_busqueda.py                       -> preguntas de ejemplo
    python scripts/probar_busqueda.py "hermanas de Barbie"  -> tu propia pregunta
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vectorstore import config, search  # noqa: E402

PREGUNTAS_EJEMPLO = [
    # Del tema (deberían tener puntaje alto)
    "novio de Barbie",
    "¿Cuántas hermanas tiene Barbie?",
    "¿Quién dirigió la película Barbie?",
    "¿Quién creó a Barbie?",
    # Fuera del tema (deberían tener puntaje bajo)
    "receta para preparar sushi",
    "¿Quién ganó el mundial de fútbol?",
    # Solo debería encontrarse DESPUÉS de cargar data/demo
    "¿Cómo se llama la unicornio de El lago de los cisnes?",
]

preguntas = sys.argv[1:] or PREGUNTAS_EJEMPLO
umbral = config.SIMILARITY_THRESHOLD

for pregunta in preguntas:
    print(f"\n❓ {pregunta}")
    for r in search(pregunta, k=3):
        marca = "✅" if r["score"] >= umbral else "  "
        primera_linea = r["fragment"].splitlines()[0][:70]
        print(f"   {marca} {r['score']:.3f}  {r['doc']:<32} {primera_linea}")

print(f"\n✅ = puntaje mayor o igual al umbral actual ({umbral})")
