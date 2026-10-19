# agents/ — Agente LangGraph (Persona 1)

Aquí vive el agente. La API **no** importa LangGraph directamente: solo llama
tres funciones definidas en [`contract.py`](contract.py).

## Qué debe crear la Persona 1

Un archivo `agents/graph.py` (o el módulo que indique `AGENT_MODULE`) con:

```python
from agents.contract import AgentAnswer, HistoryItem, REJECTION_MESSAGE

def ask(question: str, user_id: str, history: list[HistoryItem]) -> AgentAnswer:
    # history = últimos 6 mensajes [{"role": "user"|"assistant", "content": "..."}]
    # return {"answer": "...", "rejected": False,
    #         "sources": [{"doc": "peliculas.pdf", "fragment": "...", "score": 0.82}]}
    ...

def ingest(file_path: str, doc_id: str, filename: str) -> int:
    # extraer texto -> fragmentar -> embeddings (bge-m3 en Ollama) -> pgvector
    # guardar metadata {"doc_id": doc_id, "filename": filename} en cada fragmento
    # return número de fragmentos
    ...

def delete_document(doc_id: str) -> None:
    # borrar de pgvector todos los fragmentos con ese doc_id
    ...
```

Si no hay contexto suficiente: `{"answer": REJECTION_MESSAGE, "rejected": True, "sources": []}`.

La API ya se encarga de: autenticación, validar formato y tamaño del archivo,
guardar el archivo temporal, llamar `ingest` en segundo plano, guardar el
historial en Supabase y pasarte los últimos 6 mensajes.

## Variables de entorno que puede leer el agente

```
OLLAMA_URL=https://tu-dominio.ngrok-free.app   # o http://localhost:11434
OLLAMA_USER=...
OLLAMA_PASS=...
OLLAMA_MODEL=qwen2.5:3b
EMBEDDING_MODEL=bge-m3
DATABASE_URL=postgresql+psycopg://...           # Session pooler de Supabase
```

Consejos:
- ngrok gratis puede mostrar una página de advertencia; enviar el header
  `ngrok-skip-browser-warning: true` en las llamadas a Ollama la evita.
- Render no tiene IPv6: en Supabase usa la cadena del **Session pooler**
  (host `aws-0-...pooler.supabase.com`, puerto 5432), no la conexión directa.

## Activarlo

En `backend/.env`: `AGENT_MODE=real` y `AGENT_MODULE=agents.graph`.
Mientras `AGENT_MODE=mock`, la app usa `mock_agent.py`, que responde con datos fijos.
