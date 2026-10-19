"""
Chatea con el agente en la consola, mostrando por qué nodos pasó cada pregunta.

Ejecútalo desde la carpeta backend/:
    python scripts/probar_agente.py              -> chat interactivo (escribe 'salir' para terminar)
    python scripts/probar_agente.py --diagrama   -> imprime el grafo en formato Mermaid
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.graph import grafo  # noqa: E402

if "--diagrama" in sys.argv:
    # Pega el resultado en https://mermaid.live para ver el dibujo del grafo.
    print(grafo.get_graph().draw_mermaid())
    sys.exit(0)

historial: list[dict] = []
print("Chat con el agente. Escribe 'salir' para terminar.\n")

while True:
    pregunta = input("🙋 Tú: ").strip()
    if pregunta.lower() in {"salir", "exit", "q"}:
        break
    inicio = time.time()
    estado = grafo.invoke({"question": pregunta, "user_id": "prueba", "history": historial})
    segundos = time.time() - inicio

    print(f"🤖 Agente: {estado['answer']}")
    print(f"   ruta: {' → '.join(estado['ruta'])}")
    if estado.get("consulta"):
        print(f"   consulta reescrita: {estado['consulta']}")
    print(f"   rechazada: {estado['rejected']}   tiempo: {segundos:.1f} s")
    for fuente in estado["sources"]:
        print(f"   📄 {fuente['score']:.3f}  {fuente['doc']}")
    print()

    historial += [
        {"role": "user", "content": pregunta},
        {"role": "assistant", "content": estado["answer"]},
    ]
    historial = historial[-6:]
