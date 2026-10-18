# Backend: API FastAPI

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

- Documentación interactiva: http://localhost:8000/docs
- Pruebas: `python -m pytest -q`. No necesitan Supabase porque usan el repositorio en memoria y el agente simulado.
- Para probar sin Supabase, pon `DATA_BACKEND=memory` en `.env`.

## Capas

| Carpeta | Responsabilidad |
|---|---|
| `app/core/config.py` | Variables de entorno |
| `app/core/security.py` | Validación del JWT de Supabase |
| `controllers/` | Rutas HTTP, sin lógica de negocio |
| `services/` | Reglas del chat y de la carga de documentos |
| `repositories/` | Acceso a Supabase Postgres (o memoria) |
| `agents/` | Agente LangGraph y su contrato con la API |
| `vectorstore/` | ChromaDB |
