"""
Muestra por dentro qué hizo el agente con una pregunta.

Uso (desde backend/, con el venv activo y ngrok/Ollama encendidos):
    python scripts/diagnosticar.py "quienes son tus hermanas"
    python scripts/diagnosticar.py "si" --oferta "¿Quieres que te cuente algo más sobre Ken?"

Imprime: la ruta por el grafo, la consulta reescrita, el veredicto del
evaluador, los fragmentos usados (con puntaje) y la respuesta final.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.graph import grafo  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnóstico del agente Barbie")
    parser.add_argument("pregunta", help="La pregunta, entre comillas")
    parser.add_argument(
        "--oferta",
        default="",
        help="Última respuesta de Barbie (para probar un 'sí' de seguimiento)",
    )
    args = parser.parse_args()

    history = []
    if args.oferta:
        history = [
            {"role": "user", "content": "(pregunta anterior)"},
            {"role": "assistant", "content": args.oferta},
        ]

    inicio = time.time()
    r = grafo.invoke({"question": args.pregunta, "history": history})
    segundos = time.time() - inicio

    print("=" * 70)
    print("PREGUNTA:        ", args.pregunta)
    print("INTENCIÓN:       ", r.get("intencion"))
    print("RUTA:            ", " -> ".join(r.get("ruta", [])))
    print("PREGUNTA USADA:  ", r.get("question"))
    print("CONSULTA:        ", r.get("consulta"))
    if r.get("consulta_sola"):
        print("CONSULTA SOLA:   ", r.get("consulta_sola"))
    print("EVALUADOR DIJO:  ", r.get("contexto_suficiente", "(no pasó por evaluar)"))
    print("RECHAZADA:       ", r.get("rejected"))
    print(f"TIEMPO:           {segundos:.1f} s")

    print("\nFRAGMENTOS USADOS (≥ umbral o con palabra clave):")
    for f in r.get("fragmentos", []):
        print(f"  {f['score']:.3f}  {f['doc']:<40} | {f['fragment'][:80].replace(chr(10), ' ')}")
    if not r.get("fragmentos"):
        print("  (ninguno)")

    cercanos = [f for f in r.get("cercanos", []) if f not in r.get("fragmentos", [])]
    if cercanos:
        print("\nOTROS CERCANOS (no se usaron):")
        for f in cercanos[:6]:
            print(f"  {f['score']:.3f}  {f['doc']:<40} | {f['fragment'][:80].replace(chr(10), ' ')}")

    print("\nRESPUESTA:")
    print(r.get("answer"))
    print("=" * 70)


if __name__ == "__main__":
    main()