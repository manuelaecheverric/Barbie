"""Contrato entre la API (Persona 2) y el agente LangGraph (Persona 1).

El módulo del agente (por defecto `agents/graph.py`) debe exponer estas tres
funciones con exactamente estas firmas. La API las llama y no le importa
cómo estén construidas por dentro (LangGraph, pgvector, Ollama...).

    def ask(question: str, user_id: str, history: list[HistoryItem]) -> AgentAnswer
    def ingest(file_path: str, doc_id: str, filename: str) -> int
    def delete_document(doc_id: str) -> None

- `ask` recibe en `history` los últimos mensajes (HISTORY_WINDOW, 6 por defecto)
  como [{role, content}] y devuelve {answer, rejected, sources:[{doc, fragment, score}]}.
  Si no hay contexto suficiente devuelve `rejected=True` y en `answer` el
  mensaje de rechazo (ver REJECTION_MESSAGE).
- `ingest` extrae el texto, lo fragmenta, genera embeddings y los guarda en la
  base vectorial (pgvector en Supabase) con metadata `doc_id` y `filename`. Devuelve cuántos
  fragmentos guardó. Si falla, lanza una excepción con un mensaje claro.
- `delete_document` borra de la base vectorial todos los fragmentos de ese
  `doc_id`.

La base de conocimiento es compartida por todos los usuarios.
"""
from typing import Literal, Protocol, TypedDict

REJECTION_MESSAGE = "No tengo suficiente información en mi base de conocimiento para responder esa pregunta."


class HistoryItem(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class SourceItem(TypedDict, total=False):
    doc: str  # nombre del archivo
    fragment: str  # texto del fragmento usado
    score: float  # similitud (0 a 1)
    doc_id: str


class AgentAnswer(TypedDict):
    answer: str
    rejected: bool
    sources: list[SourceItem]


class Agent(Protocol):
    def ask(self, question: str, user_id: str, history: list[HistoryItem]) -> AgentAnswer: ...

    def ingest(self, file_path: str, doc_id: str, filename: str) -> int: ...

    def delete_document(self, doc_id: str) -> None: ...
