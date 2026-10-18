from functools import lru_cache

from app.core.config import get_settings


@lru_cache
def get_repository():
    settings = get_settings()
    if settings.resolved_data_backend == "supabase":
        from repositories.supabase_repo import SupabaseRepository

        return SupabaseRepository(settings.supabase_url, settings.supabase_service_role_key)
    from repositories.memory_repo import MemoryRepository

    return MemoryRepository()
