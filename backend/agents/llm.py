"""Modelo de lenguaje local (Ollama)."""

from functools import lru_cache

from langchain_ollama import ChatOllama

from vectorstore import config


@lru_cache
def get_llm(max_tokens: int = 400):
    """ChatOllama con temperatura 0 (respuestas estables, menos inventos).

    keep_alive deja el modelo cargado en memoria 30 minutos para que
    las preguntas siguientes respondan más rápido.
    """
    return ChatOllama(
        model=config.LLM_MODEL,
        base_url=config.OLLAMA_URL,
        temperature=0,
        num_predict=max_tokens,
        num_ctx=4096,
        keep_alive="30m",
        client_kwargs=config.ollama_client_kwargs(),
    )
