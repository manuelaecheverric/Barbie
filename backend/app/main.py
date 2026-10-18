"""Punto de entrada de la API.

Ejecutar en local:  uvicorn app.main:app --reload --port 8000
Documentación interactiva: http://localhost:8000/docs
"""
import logging

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.security import get_current_user
from controllers import chat_controller, document_controller, user_controller

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API del agente experto en el universo Barbie. Todos los endpoints de /api requieren token de Supabase.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Todas las rutas de /api exigen un usuario autenticado, sin excepción.
api = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])
api.include_router(user_controller.router)
api.include_router(chat_controller.router)
api.include_router(document_controller.router)
app.include_router(api)


@app.get("/health", tags=["estado"], summary="Estado del servicio (para Render)")
def health():
    return {"status": "ok", "agent_mode": settings.agent_mode, "data_backend": settings.resolved_data_backend}
