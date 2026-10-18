"""
Paso 1: verifica que todo esté listo antes de empezar a programar.

Ejecútalo desde la carpeta backend/:
    python scripts/verificar_entorno.py

Revisa tres cosas:
  1. Que Ollama responda con el modelo de lenguaje (y en español).
  2. Que Ollama genere embeddings con bge-m3.
  3. Que Python se conecte a Supabase y la extensión pgvector esté activa.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
DATABASE_URL = os.getenv("DATABASE_URL", "")

todo_ok = True


def probar(nombre, funcion):
    global todo_ok
    print(f"\n▶ {nombre}...")
    try:
        funcion()
        print("  ✅ OK")
    except Exception as error:  # noqa: BLE001
        todo_ok = False
        print(f"  ❌ Falló: {error}")


def probar_llm():
    from langchain_ollama import ChatOllama

    llm = ChatOllama(model=LLM_MODEL, base_url=OLLAMA_URL, temperature=0)
    respuesta = llm.invoke("Responde en una sola frase en español: ¿quién es Barbie?")
    print(f"  Respuesta: {respuesta.content.strip()}")


def probar_embeddings():
    from langchain_ollama import OllamaEmbeddings

    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)
    vector = embeddings.embed_query("El novio de Barbie es Ken")
    print(f"  Dimensión del vector: {len(vector)} (bge-m3 debería dar 1024)")


def probar_supabase():
    import psycopg

    if not DATABASE_URL:
        raise RuntimeError("Falta DATABASE_URL en el archivo .env")
    # psycopg no entiende el prefijo de SQLAlchemy, así que lo quitamos aquí.
    url = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as conexion:
        fila = conexion.execute(
            "select extversion from pg_extension where extname = 'vector'"
        ).fetchone()
    if fila is None:
        raise RuntimeError(
            "Conectó, pero pgvector no está activo. En Supabase ve a "
            "Database > Extensions y activa 'vector'."
        )
    print(f"  pgvector versión {fila[0]}")


probar("Modelo de lenguaje en Ollama", probar_llm)
probar("Embeddings en Ollama", probar_embeddings)
probar("Conexión a Supabase + pgvector", probar_supabase)

print("\n" + ("🎉 Todo listo para el paso 2." if todo_ok else "⚠️ Revisa lo que falló."))
sys.exit(0 if todo_ok else 1)