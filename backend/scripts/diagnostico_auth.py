"""
Diagnóstico del 401 con ngrok: muestra qué usuario/clave está leyendo Python
(sin mostrar la clave completa) y prueba la conexión de tres formas.

Uso (desde backend/, con el venv activo):
    python scripts/diagnostico_auth.py
"""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from vectorstore import config  # noqa: E402  (carga el .env)


def describir(valor: str) -> str:
    if not valor:
        return "(VACÍO)"
    avisos = []
    if valor != valor.strip():
        avisos.append("tiene ESPACIOS al inicio o al final")
    if valor[:1] in "\"'" or valor[-1:] in "\"'":
        avisos.append("tiene COMILLAS")
    if "#" in valor:
        avisos.append("tiene #")
    oculto = valor[0] + "*" * (len(valor) - 2) + valor[-1] if len(valor) > 2 else "**"
    extra = f"  ⚠️ {', '.join(avisos)}" if avisos else ""
    return f"'{oculto}' ({len(valor)} caracteres){extra}"


print("\n▶ Archivos .env encontrados:")
for carpeta in (BACKEND, BACKEND.parent):
    archivo = carpeta / ".env"
    print(f"  {'✅' if archivo.exists() else '—'} {archivo}")

url = getattr(config, "OLLAMA_URL", None) or os.getenv("OLLAMA_URL", "")
user = getattr(config, "OLLAMA_USER", None) or os.getenv("OLLAMA_USER", "")
clave = getattr(config, "OLLAMA_PASS", None) or os.getenv("OLLAMA_PASS", "")

print("\n▶ Lo que está leyendo Python:")
print(f"  OLLAMA_URL  = {url!r}")
print(f"  OLLAMA_USER = {describir(user)}")
print(f"  OLLAMA_PASS = {describir(clave)}")

kwargs = config.ollama_client_kwargs()
auth = kwargs.get("auth")
print("\n▶ Lo que reciben el LLM y los embeddings (ollama_client_kwargs):")
if auth:
    print(f"  auth = ({describir(auth[0])}, {describir(auth[1])})")
else:
    print(f"  ⚠️ NO trae 'auth'. Contenido: {list(kwargs.keys()) or 'vacío'}")

import httpx  # noqa: E402

base = url.rstrip("/")
print("\n▶ Prueba 1: httpx con usuario y clave del .env")
try:
    r = httpx.get(f"{base}/api/tags", auth=(user, clave), timeout=20)
    print(f"  {'✅' if r.status_code == 200 else '❌'} {r.status_code}")
except Exception as e:
    print(f"  ❌ {e}")

print("\n▶ Prueba 2: cliente de Ollama con ollama_client_kwargs()")
try:
    from ollama import Client

    Client(host=base, **kwargs).list()
    print("  ✅ 200")
except Exception as e:
    print(f"  ❌ {e}")

print("\n▶ Prueba 3: escribe la clave a mano (la misma que usaste en curl)")
manual = input("  Clave (se verá en pantalla): ")
r = httpx.get(f"{base}/api/tags", auth=(user or "barbie", manual), timeout=20)
print(f"  {'✅' if r.status_code == 200 else '❌'} {r.status_code}")
if r.status_code == 200 and manual != clave:
    print("  ➜ La clave escrita a mano funciona pero NO es igual a la del .env.")