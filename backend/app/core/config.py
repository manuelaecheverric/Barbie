"""Configuración central leída desde variables de entorno (.env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Pink Oracle API"
    app_env: str = "development"

    # Orígenes permitidos para CORS, separados por coma
    frontend_url: str = "http://localhost:5173"

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    # Solo si el proyecto usa la llave JWT "legacy" (HS256). Si se deja vacío
    # se validan los tokens con las llaves públicas (JWKS) del proyecto.
    supabase_jwt_secret: str = ""

    # "supabase" para producción, "memory" para desarrollo/pruebas sin base de datos
    data_backend: str = ""

    # Agente: "mock" (simulado) o "real" (código LangGraph de la Persona 1)
    agent_mode: str = "mock"
    agent_module: str = "agents.graph"
    history_window: int = 6

    # Documentos
    max_upload_mb: int = 15
    allowed_extensions: str = ".pdf,.txt,.md,.csv,.docx"
    upload_dir: str = "/tmp/pink-oracle-uploads"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.frontend_url.split(",") if o.strip()]

    @property
    def resolved_data_backend(self) -> str:
        if self.data_backend:
            return self.data_backend
        return "supabase" if self.supabase_url and self.supabase_service_role_key else "memory"

    @property
    def allowed_extension_set(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_extensions.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
