"""
Textos y prompts del agente.

Paso 4: versión NEUTRA (sin personalidad). En el paso 5 solo se cambian
los textos de este archivo para darle la voz de Barbie; el grafo no cambia.
"""

# Frase exigida por el enunciado. Se usa tal cual para detectar rechazos,
# así que si la cambias, cámbiala solo aquí.
FRASE_RECHAZO = (
    "No tengo suficiente información en mi base de conocimiento "
    "para responder esa pregunta."
)

MENSAJE_RECHAZO = (
    f"{FRASE_RECHAZO} Si quieres, puedes subir un documento sobre ese tema "
    "para que pueda aprender de él."
)

MENSAJE_ERROR = (
    "En este momento no puedo responder porque el modelo no está disponible. "
    "Intenta de nuevo en unos segundos."
)

RESPUESTAS_SALUDO = {
    "saludo": "¡Hola! Puedes preguntarme sobre Barbie: su historia, su familia, "
    "sus amigas, sus películas o sus profesiones.",
    "gracias": "¡Con gusto! ¿Quieres preguntar algo más sobre Barbie?",
    "despedida": "¡Hasta pronto!",
    "vacio": "Escribe una pregunta sobre Barbie.",
}

# ---------- Nodo: reescribir consulta ----------
# "tú" -> "Barbie" se hace con reglas en graph.py (sin LLM).
# Este prompt solo se usa cuando la pregunta tiene "él", "ella", "eso", "su"...
# y hay historial. Va sin ejemplos a propósito: Qwen 3B tiende a copiarlos.
PROMPT_RESOLVER_REFERENCIAS = """Conversación anterior:
{historial}

Nueva pregunta: {pregunta}

En la nueva pregunta, reemplaza las palabras "él", "ella", "ellos", "eso", "su" o "sus" por el nombre de la persona o cosa a la que se refieren según la conversación anterior.
Si a la pregunta le falta decir de quién se habla, agrega esos nombres.
No cambies ninguna otra palabra. No respondas la pregunta.
Escribe solamente la nueva pregunta ya reescrita."""

# ---------- Nodo: evaluar contexto ----------
PROMPT_EVALUAR = """Lee los fragmentos y decide si contienen la información necesaria para responder la pregunta.

Fragmentos:
{contexto}

Pregunta: {pregunta}

Si algún fragmento contiene la respuesta, aunque use otras palabras, escribe SI.
Si ninguno la contiene, o solo hablan de temas parecidos, escribe NO.
Responde únicamente SI o NO."""

# ---------- Nodo: generar respuesta ----------
PROMPT_SISTEMA = f"""Eres un asistente que responde preguntas sobre Barbie.

Reglas obligatorias:
1. Responde ÚNICAMENTE con la información de los fragmentos de contexto. No uses lo que sepas por tu cuenta.
2. Si los fragmentos no contienen la respuesta, responde exactamente: "{FRASE_RECHAZO}"
3. No inventes nombres, fechas, cifras ni detalles que no estén en los fragmentos.
4. Responde en español, de forma breve y clara (máximo 4 oraciones)."""

PROMPT_GENERAR = """Fragmentos de contexto:
{contexto}

Pregunta del usuario: {pregunta}
(La pregunta se refiere a: {consulta})"""
