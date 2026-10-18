# agents/ — Agente LangGraph (Persona 1)

Aquí vive el agente. La API **no** importa LangGraph directamente: solo llama
tres funciones definidas en [`contract.py`](contract.py).

## Qué debe crear la Persona 1

Un archivo `agents/graph.py` (o el módulo que indique `AGENT_MODULE`) con:

```python
from agents.contract import AgentAnswer, HistoryItem, REJECTION_MESSAGE

def ask(question: str, user_id: str, history: list[HistoryItem]) -> AgentAnswer:
    # ejecutar el grafo de LangGraph
    # return {"answer": "...", "rejected": False,
    #         "sources": [{"document": "peliculas.pdf", "fragment": "...", "score": 0.82}]}
    ...

def ingest(file_path: str, document_id: str, filename: str) -> int:
    # extraer texto -> fragmentar -> embeddings -> ChromaDB
    # guardar metadata {"document_id": document_id, "filename": filename} en cada fragmento
    # return número de fragmentos
    ...

def delete_document(document_id: str) -> None:
    # collection.delete(where={"document_id": document_id})
    ...
```

Cuando no haya contexto suficiente, `ask` debe devolver
`{"answer": REJECTION_MESSAGE, "rejected": True, "sources": []}`.

El código de LangGraph, los nodos y los prompts pueden ir en más archivos dentro
de esta carpeta (`nodes.py`, `prompts.py`, `state.py`...). La base vectorial
puede ir en `../vectorstore/`.

## Activarlo

En `backend/.env`:

```
AGENT_MODE=real
AGENT_MODULE=agents.graph
OLLAMA_BASE_URL=http://localhost:11434
```

Mientras `AGENT_MODE=mock`, la app usa `mock_agent.py`, que responde con
datos fijos. Sirve para probar la interfaz sin el modelo.
