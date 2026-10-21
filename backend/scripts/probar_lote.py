"""
Paso 6: corre ~20 preguntas de prueba contra el agente y guarda la evidencia.

Uso (desde la carpeta backend/, con el venv activo y Ollama abierto):
    python scripts/probar_lote.py

Resultado: docs/evidencias/paso6-resultados.md (en la raíz del repo).
Tarda unos 10 minutos (cada pregunta toma entre 20 y 30 s).
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
RAIZ = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from agents.graph import grafo  # noqa: E402

# search() es opcional: solo sirve para anotar el puntaje más alto de cada
# pregunta (útil para justificar el umbral en el documento).
search = None
try:
    from agents import search  # noqa: E402
except ImportError:
    try:
        from vectorstore.store import search  # noqa: E402
    except ImportError:
        search = None

SALIDA = RAIZ / "docs" / "evidencias" / "paso6-resultados.md"

# esperado:
#   "responde" -> debe contestar con fuentes
#   "rechaza"  -> debe dar la frase de rechazo (rejected=True)
#   "revisar"  -> lo revisas tú a mano (trampas de alucinación)
# conversacion: preguntas con el mismo id comparten historial.
PRUEBAS = [
    # --- En tema ---
    {"grupo": "En tema", "pregunta": "¿Quién eres?", "esperado": "responde"},
    {"grupo": "En tema", "pregunta": "¿Quién es tu novio?", "esperado": "responde"},
    {"grupo": "En tema", "pregunta": "¿Cuándo te separaste de Ken?", "esperado": "responde"},
    {"grupo": "En tema", "pregunta": "¿Quién te creó?", "esperado": "responde"},
    {"grupo": "En tema", "pregunta": "¿En qué año naciste?", "esperado": "responde"},
    {"grupo": "En tema", "pregunta": "¿Cómo se llaman tus hermanas?", "esperado": "responde"},
    {"grupo": "En tema", "pregunta": "¿Cuál es tu nombre completo?", "esperado": "responde"},
    {"grupo": "En tema", "pregunta": "¿En qué películas has salido?", "esperado": "responde"},
    {"grupo": "En tema", "pregunta": "¿Qué profesiones has tenido?", "esperado": "responde"},
    {"grupo": "En tema", "pregunta": "¿Quién te interpretó en la película de 2023?", "esperado": "responde"},
    # --- Seguimiento con historial ---
    {"grupo": "Seguimiento", "pregunta": "¿Quién es tu novio?", "esperado": "responde", "conversacion": "c1"},
    {"grupo": "Seguimiento", "pregunta": "¿Y cuándo lo conociste?", "esperado": "responde", "conversacion": "c1"},
    {"grupo": "Seguimiento", "pregunta": "¿Quién es tu mejor amiga?", "esperado": "responde", "conversacion": "c2"},
    {"grupo": "Seguimiento", "pregunta": "¿Y cuándo apareció ella por primera vez?", "esperado": "responde", "conversacion": "c2"},
    # --- Fuera de tema ---
    {"grupo": "Fuera de tema", "pregunta": "¿Cuál es la mejor receta de sushi?", "esperado": "rechaza"},
    {"grupo": "Fuera de tema", "pregunta": "¿Quién ganó el Mundial de 2022?", "esperado": "rechaza"},
    {"grupo": "Fuera de tema", "pregunta": "¿Cuál es la capital de Australia?", "esperado": "rechaza"},
    {"grupo": "Fuera de tema", "pregunta": "¿Cómo se calcula la derivada de x al cuadrado?", "esperado": "rechaza"},
    {"grupo": "Fuera de tema", "pregunta": "¿Qué pasó en El lago de los cisnes?", "esperado": "rechaza"},
    # --- Trampas: tema cercano, pero el dato no está en las fichas ---
    {"grupo": "Trampa", "pregunta": "¿Cuál es tu comida favorita?", "esperado": "revisar"},
    {"grupo": "Trampa", "pregunta": "¿Cuál es tu signo zodiacal?", "esperado": "revisar"},
    {"grupo": "Trampa", "pregunta": "¿Cuántos hijos tienes con Ken?", "esperado": "revisar"},
    {"grupo": "Trampa", "pregunta": "¿Qué sentiste cuando terminaste con Ken?", "esperado": "revisar"},
]


def _campo(obj, nombre, defecto=None):
    """Lee un campo tanto de un dict como de un objeto."""
    if isinstance(obj, dict):
        return obj.get(nombre, defecto)
    return getattr(obj, nombre, defecto)


def agrupar_fuentes(sources):
    """Una línea por documento, con su mejor puntaje, en orden de aparición."""
    mejores = {}
    for s in sources or []:
        doc = _campo(s, "doc", "?")
        score = _campo(s, "score", 0) or 0
        if doc not in mejores or score > mejores[doc]:
            mejores[doc] = score
    return [f"{doc} ({score:.3f})" for doc, score in mejores.items()]


def puntaje_maximo(pregunta):
    if search is None:
        return None
    try:
        resultados = search(pregunta, k=1, min_score=0.0)
    except Exception:
        return None
    if not resultados:
        return None
    primero = resultados[0]
    if isinstance(primero, (tuple, list)):
        return float(primero[-1])
    return _campo(primero, "score")


def evaluar(esperado, r):
    if r.get("error"):
        return "⚠️ error"
    if esperado == "responde":
        return "✅" if not r.get("rejected") and r.get("sources") else "❌"
    if esperado == "rechaza":
        return "✅" if r.get("rejected") else "❌"
    return "👀 revisar"


def limpiar(texto):
    return (texto or "").replace("|", "/").replace("\n", " ").strip()


def main():
    historiales = {}
    filas = []

    for i, p in enumerate(PRUEBAS, start=1):
        conv = p.get("conversacion")
        historial = historiales.get(conv, []) if conv else []
        print(f"[{i}/{len(PRUEBAS)}] {p['pregunta']}")

        # Se llama al grafo directamente (igual que ask) para ver también
        # la consulta reescrita y la ruta de nodos.
        inicio = time.time()
        try:
            r = grafo.invoke(
                {"question": p["pregunta"], "user_id": "prueba-paso6", "history": historial[-6:]}
            )
            r["error"] = False
        except Exception as e:  # Ollama o la base de datos fallaron
            r = {"answer": f"ERROR: {e}", "rejected": False, "sources": [], "error": True}
        segundos = time.time() - inicio

        if conv:
            historial = historial + [
                {"role": "user", "content": p["pregunta"]},
                {"role": "assistant", "content": r.get("answer", "")},
            ]
            historiales[conv] = historial

        fila = {
            **p,
            "r": r,
            "segundos": segundos,
            "veredicto": evaluar(p["esperado"], r),
            "max_score": puntaje_maximo(p["pregunta"]),
        }
        filas.append(fila)
        print(f"    {fila['veredicto']}  ({segundos:.1f} s)  {limpiar(r.get('answer'))[:90]}")
        print(f"    consulta: {r.get('consulta', '—')}  ·  ruta: {' → '.join(r.get('ruta', []))}")

    escribir_reporte(filas)
    print(f"\nListo. Evidencia guardada en: {SALIDA}")


def escribir_reporte(filas):
    ok = sum(1 for f in filas if f["veredicto"] == "✅")
    malas = sum(1 for f in filas if f["veredicto"].startswith("❌"))
    revisar = sum(1 for f in filas if f["veredicto"].startswith("👀"))
    errores = sum(1 for f in filas if f["veredicto"].startswith("⚠️"))

    lineas = [
        "# Paso 6 — Resultados de las preguntas de prueba",
        "",
        f"- Fecha: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Modelo: {os.getenv('LLM_MODEL', '?')} · Embeddings: {os.getenv('EMBED_MODEL', '?')}",
        f"- Umbral de similitud: {os.getenv('SIMILARITY_THRESHOLD', '0.5')}",
        f"- Resumen: {ok} correctas, {malas} incorrectas, {revisar} para revisar a mano, {errores} con error",
        "",
        "Nota: \"Score pregunta original\" es el mejor puntaje buscando la pregunta tal cual "
        "(sin reescribir). Las fuentes muestran el puntaje real que usó el agente, "
        "ya con la consulta reescrita.",
        "",
        "| # | Grupo | Pregunta | Esperado | Resultado | Tiempo | Score pregunta original | Fuentes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, f in enumerate(filas, start=1):
        score = f"{f['max_score']:.3f}" if isinstance(f["max_score"], (int, float)) else "—"
        fuentes = "<br>".join(agrupar_fuentes(f["r"].get("sources"))) or "—"
        lineas.append(
            f"| {i} | {f['grupo']} | {limpiar(f['pregunta'])} | {f['esperado']} | "
            f"{f['veredicto']} | {f['segundos']:.1f} s | {score} | {fuentes} |"
        )

    lineas += ["", "## Respuestas completas", ""]
    for i, f in enumerate(filas, start=1):
        r = f["r"]
        lineas += [
            f"### {i}. {f['pregunta']}",
            "",
            f"**Respuesta:** {limpiar(r.get('answer'))}",
            "",
            f"rechazada: {r.get('rejected')} · error: {r.get('error')} · {f['veredicto']}",
            "",
            f"ruta: {' → '.join(r.get('ruta', [])) or '—'}",
            "",
            f"consulta reescrita: {limpiar(r.get('consulta')) or '—'}",
            "",
        ]
        if r.get("sources"):
            lineas.append("**Fuentes:**")
            lineas.append("")
            for s in r["sources"]:
                frag = limpiar(_campo(s, "fragment", ""))[:200]
                lineas.append(
                    f"- `{_campo(s, 'doc', '?')}` ({(_campo(s, 'score', 0) or 0):.3f}): {frag}…"
                )
            lineas.append("")
        lineas += ["**¿Correcta según la ficha?** (escribe sí/no y por qué):", "", "---", ""]

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text("\n".join(lineas), encoding="utf-8")


if __name__ == "__main__":
    main()