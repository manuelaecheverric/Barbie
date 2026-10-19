"""Agente SIMULADO para desarrollar y probar la aplicación web mientras la
Persona 1 termina el agente real con LangGraph + RAG.

No usa ningún modelo: busca palabras clave en una mini base de conocimiento
fija. Sirve para probar el chat, las fuentes y los rechazos en la interfaz.
Se activa con AGENT_MODE=mock.
"""
import math
import os
import unicodedata

from agents.contract import REJECTION_MESSAGE, AgentAnswer, HistoryItem

_KNOWLEDGE = [
    {
        "keywords": ["creo", "creadora", "creador", "origen", "historia", "1959", "ruth", "handler", "nacio", "inventó", "invento"],
        "fragment": (
            "La muñeca Barbie fue creada por Ruth Handler, cofundadora de Mattel, y se presentó "
            "el 9 de marzo de 1959 en la American International Toy Fair de Nueva York."
        ),
        "document": "historia-de-la-muneca.md",
    },
    {
        "keywords": ["ken", "novio", "1961"],
        "fragment": "Ken Carson fue presentado por Mattel en 1961 como el compañero de Barbie.",
        "document": "personajes.md",
    },
    {
        "keywords": ["hermana", "hermanas", "skipper", "stacie", "chelsea", "familia"],
        "fragment": (
            "Las hermanas de Barbie más conocidas son Skipper, Stacie y Chelsea. "
            "Skipper apareció en 1964 como la hermana menor."
        ),
        "document": "personajes.md",
    },
    {
        "keywords": ["pelicula", "peliculas", "2023", "gerwig", "margot", "robbie"],
        "fragment": (
            "La película 'Barbie' de 2023 fue dirigida por Greta Gerwig y protagonizada por "
            "Margot Robbie como Barbie y Ryan Gosling como Ken."
        ),
        "document": "peliculas.md",
    },
]


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


class MockAgent:
    def ask(self, question: str, user_id: str, history: list[HistoryItem]) -> AgentAnswer:
        words = set(_normalize(question).replace("?", " ").replace("¿", " ").replace(",", " ").split())
        hits = []
        for item in _KNOWLEDGE:
            overlap = len(words & {_normalize(k) for k in item["keywords"]})
            if overlap:
                hits.append((overlap, item))
        if not hits:
            return {"answer": REJECTION_MESSAGE, "rejected": True, "sources": []}

        hits.sort(key=lambda h: h[0], reverse=True)
        top = [item for _, item in hits[:2]]
        answer = " ".join(item["fragment"] for item in top)
        return {
            "answer": f"{answer}\n\n(Respuesta del agente simulado: aún no está conectado el modelo local.)",
            "rejected": False,
            "sources": [
                {"doc": item["document"], "fragment": item["fragment"], "score": round(0.7 + 0.1 * n, 2)}
                for n, item in hits[:2]
            ],
        }

    def ingest(self, file_path: str, document_id: str, filename: str) -> int:
        size = os.path.getsize(file_path)
        if size == 0:
            raise ValueError("El archivo está vacío.")
        # Simula fragmentos de ~1000 caracteres
        return max(1, math.ceil(size / 1000))

    def delete_document(self, document_id: str) -> None:
        return None
