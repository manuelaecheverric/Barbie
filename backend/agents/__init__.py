"""
Agente Barbie (LangGraph + RAG).

⚠️ VERSIÓN FALSA (stub) para que la API y el frontend puedan integrarse
desde ya. Devuelve datos inventados con la forma exacta del contrato.
Cuando el grafo real esté listo, solo cambia el interior de ask();
la firma y la forma de la respuesta NO cambian.

Contrato:
    ask(question, user_id, history) -> {
        "answer": str,
        "rejected": bool,
        "sources": [{"doc": str, "fragment": str, "score": float}]
    }

    history: últimos ~6 mensajes, en orden cronológico:
        [{"role": "user" | "assistant", "content": str}, ...]
"""

MENSAJE_RECHAZO = (
    "¡Ay, qué pena! No tengo suficiente información en mi base de "
    "conocimiento para responder esa pregunta. 💖 Si quieres, puedes "
    "subir un documento sobre eso."
)

# Palabras que hacen que el stub simule un rechazo, para que el
# frontend pueda probar cómo se ve ese caso.
_PALABRAS_FUERA_DE_TEMA = ("sushi", "receta", "fútbol", "futbol", "clima")


def ask(question: str, user_id: str, history: list[dict] | None = None) -> dict:
    history = history or []
    pregunta = question.lower()

    if any(palabra in pregunta for palabra in _PALABRAS_FUERA_DE_TEMA):
        return {
            "answer": MENSAJE_RECHAZO,
            "rejected": True,
            "sources": [],
        }

    return {
        "answer": (
            "¡Hola! Soy Barbie 💖 (respuesta de prueba). Mi novio es Ken, "
            "¡nos conocimos en 1961!"
        ),
        "rejected": False,
        "sources": [
            {
                "doc": "ken.md",
                "fragment": "Ken Carson es el novio de Barbie desde 1961...",
                "score": 0.87,
            }
        ],
    }