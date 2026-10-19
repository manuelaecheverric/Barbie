"""
Grafo del agente con LangGraph.

    START
      │
    recibir ──► clasificar ──┬── saludo ────► saludar ──────────────► END
                             │
                             └── pregunta ──► reescribir ──► recuperar
                                                                │
                              ┌── ningún fragmento ≥ umbral ────┤
                              │                                 ▼
                              │                              evaluar (LLM: ¿SI/NO?)
                              │                                 │
                              ├──────────────── NO ─────────────┤
                              ▼                                 ▼ SI
                           rechazar ──► END                  generar ──► END

Estrategias contra alucinaciones:
  1. Umbral mínimo de similitud (nodo recuperar).
  2. Nodo dedicado a validar si el contexto es suficiente (nodo evaluar).
  3. Prompt que obliga a responder solo con el contexto (nodo generar).
  4. Rechazo explícito con la frase exigida (nodo rechazar y revisión en generar).
  5. Fuentes: cada respuesta devuelve los fragmentos usados.
"""

import operator
import re
import unicodedata
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

import vectorstore
from vectorstore import config

from . import prompts
from .llm import get_llm

TOP_K = 4
MAX_LARGO_PREGUNTA = 500


class Estado(TypedDict, total=False):
    # Entrada
    question: str
    user_id: str
    history: list[dict]
    # Intermedios
    intencion: str  # "saludo" | "gracias" | "despedida" | "vacio" | "pregunta"
    consulta: str  # pregunta reescrita para la búsqueda
    fragmentos: list[dict]  # [{"doc", "doc_id", "fragment", "score"}]
    contexto_suficiente: bool
    # Salida
    answer: str
    rejected: bool
    sources: list[dict]
    # Para depurar: nombres de los nodos por los que pasó
    ruta: Annotated[list[str], operator.add]


# ---------------------------------------------------------------- utilidades
def _normalizar(texto: str) -> str:
    """minúsculas, sin tildes ni signos: '¡Hola, Barbie!' -> 'hola barbie'."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9ñ ]+", " ", texto).strip()


_SALUDOS = {
    "saludo": [
        "buenos dias", "buenas tardes", "buenas noches", "buen dia", "buenas",
        "hola", "holi", "holis", "hey", "hi", "hello", "saludos", "que tal",
        "como estas", "como te va", "como vas",
    ],
    "gracias": ["muchas gracias", "mil gracias", "gracias", "thanks", "genial", "perfecto"],
    "despedida": ["hasta luego", "hasta pronto", "nos vemos", "adios", "chao", "chau", "bye"],
}
_RELLENO = {"barbie", "muneca", "amiga", "y", "a", "ti", "tu", "muy", "bien", "ok", "oki", "vale"}


def _formatear_contexto(fragmentos: list[dict]) -> str:
    return "\n\n".join(
        f"[{i}] (de {f['doc']})\n{f['fragment']}" for i, f in enumerate(fragmentos, 1)
    )


def _formatear_historial(history: list[dict]) -> str:
    if not history:
        return "(sin historial)"
    lineas = []
    for mensaje in history[-6:]:
        quien = "Usuario" if mensaje.get("role") == "user" else "Asistente"
        lineas.append(f"{quien}: {str(mensaje.get('content', ''))[:300]}")
    return "\n".join(lineas)


def _limpiar_consulta(texto: str, respaldo: str) -> str:
    """Se queda con la primera línea útil de lo que devolvió el LLM."""
    for linea in texto.strip().splitlines():
        linea = re.sub(r"^(consulta|query)\s*:\s*", "", linea.strip(), flags=re.I)
        linea = linea.strip(" \"'`¿?¡!.")
        if linea:
            return linea[:200]
    return respaldo


_PALABRAS_VACIAS = {
    "cual", "cuales", "quien", "quienes", "como", "cuando", "donde", "cuanto",
    "cuantos", "cuantas", "porque", "sobre", "para", "esta", "este", "eres",
    "barbie",  # aparece en casi todo, así que no sirve para comparar
}

# El usuario le habla a Barbie de "tú": se pasa a tercera persona con reglas.
_SEGUNDA_PERSONA = {
    "tu": "", "tus": "", "tú": "", "te": "", "ti": "", "contigo": "",
    "eres": "es", "estas": "está", "estás": "está", "tienes": "tiene",
    "tenias": "tenía", "tenías": "tenía", "tuviste": "tuvo", "vives": "vive",
    "naciste": "nació", "haces": "hace", "hiciste": "hizo", "trabajas": "trabaja",
    "trabajaste": "trabajó", "llamas": "llama", "fuiste": "fue", "has": "ha",
    "puedes": "puede", "sabes": "sabe", "conoces": "conoce", "conociste": "conoció",
    "quieres": "quiere", "sales": "sale", "saliste": "salió", "usas": "usa",
    "manejas": "maneja", "estudiaste": "estudió", "vienes": "viene",
    "apareciste": "apareció", "actuaste": "actuó", "cumples": "cumple",
}
# Palabras que apuntan a algo dicho antes ("¿y cuándo apareció él?").
_REFERENCIAS = {"él", "ella", "ellos", "ellas", "eso", "esa", "ese", "su", "sus", "aquel", "aquella"}


_NO_SON_VERBOS = {"contraste", "desgaste", "gaste", "baste", "chiste", "triste", "quiste", "despiste", "embiste"}


def _preterito_tercera(palabra: str) -> str | None:
    """Verbos en pasado de 'tú': terminaste -> terminó, conociste -> conoció."""
    p = palabra.lower()
    if len(p) < 6 or p in _NO_SON_VERBOS:
        return None
    if p.endswith("aste"):
        return p[:-4] + "ó"
    if p.endswith("iste"):
        return p[:-4] + "ió"
    return None


def _a_tercera_persona(pregunta: str) -> str:
    """'¿Quién es tu novio?' -> 'Quién es novio de Barbie'. Sin LLM: no puede inventar."""
    palabras = re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", pregunta)
    cambios = set()
    salida = []
    for palabra in palabras:
        reemplazo = _SEGUNDA_PERSONA.get(palabra.lower())
        if reemplazo is None:
            reemplazo = _preterito_tercera(palabra)
        if reemplazo is None:
            salida.append(palabra)
            continue
        if palabra.lower() in ("tu", "tus", "tú"):
            cambios.add("de")  # tu novio -> novio de Barbie
        elif palabra.lower() in ("te", "ti", "contigo"):
            cambios.add("a")  # te creó -> creó a Barbie
        else:
            cambios.add("verbo")  # tienes -> tiene Barbie
        if reemplazo:
            salida.append(reemplazo)
    texto = " ".join(salida)
    if cambios and "barbie" not in texto.lower():
        enlace = "de " if "de" in cambios else "a " if "a" in cambios else ""
        texto += f" {enlace}Barbie"
    return texto or pregunta


def _tiene_referencia(pregunta: str) -> bool:
    palabras = re.findall(r"[\wáéíóúüñ]+", pregunta.lower())
    # "el" sin tilde al final de la pregunta casi siempre es "él" ("¿y cuándo nació el?")
    if any(p in _REFERENCIAS for p in palabras) or palabras[-1:] == ["el"]:
        return True
    # Preguntas que continúan la anterior: "¿y cuándo terminaron?", "¿y después?"
    return palabras[:1] == ["y"] and len(palabras) <= 6


def _raices(texto: str) -> set[str]:
    """Primeras 5 letras de las palabras importantes ('tienes' y 'tiene' -> 'tiene')."""
    return {
        p[:5] for p in _normalizar(texto).split()
        if len(p) >= 4 and p not in _PALABRAS_VACIAS
    }


def _consulta_es_coherente(consulta: str, pregunta: str, history: list[dict]) -> bool:
    """La consulta reescrita debe compartir al menos una palabra con la pregunta
    o con el último mensaje. Si no, Qwen probablemente copió un ejemplo del prompt."""
    ultimo = history[-1]["content"] if history else ""
    return bool(_raices(consulta) & (_raices(pregunta) | _raices(ultimo)))


# --------------------------------------------------------------------- nodos
def recibir(estado: Estado) -> dict:
    pregunta = (estado.get("question") or "").strip()[:MAX_LARGO_PREGUNTA]
    return {"question": pregunta, "history": estado.get("history") or [], "ruta": ["recibir"]}


def clasificar(estado: Estado) -> dict:
    """Detecta saludos, agradecimientos y despedidas con reglas (rápido y sin LLM).
    Si después de quitar esas frases queda contenido, es una pregunta."""
    texto = f" {_normalizar(estado['question'])} "
    if not texto.strip():
        return {"intencion": "vacio", "ruta": ["clasificar"]}

    encontrada = None
    for tipo, frases in _SALUDOS.items():
        for frase in frases:
            if f" {frase} " in texto:
                encontrada = encontrada or tipo
                texto = texto.replace(f" {frase} ", " ")
    resto = [p for p in texto.split() if p not in _RELLENO]
    intencion = encontrada if (encontrada and not resto) else "pregunta"
    return {"intencion": intencion, "ruta": ["clasificar"]}


def saludar(estado: Estado) -> dict:
    return {
        "answer": prompts.RESPUESTAS_SALUDO[estado["intencion"]],
        "rejected": False,
        "sources": [],
        "ruta": ["saludar"],
    }


def reescribir(estado: Estado) -> dict:
    """Prepara la consulta de búsqueda en dos pasos:
    1. Si la pregunta tiene "él", "ella", "eso"... y hay historial, Qwen lo
       reemplaza por el nombre ("¿y cuándo apareció él?" -> "¿y cuándo apareció Ken?").
    2. Reglas fijas pasan "tú" a "Barbie" ("tu novio" -> "novio de Barbie")."""
    pregunta = estado["question"]
    if estado["history"] and _tiene_referencia(pregunta):
        prompt = prompts.PROMPT_RESOLVER_REFERENCIAS.format(
            historial=_formatear_historial(estado["history"]),
            pregunta=pregunta,
        )
        respuesta = get_llm(max_tokens=60).invoke([HumanMessage(content=prompt)])
        resuelta = _limpiar_consulta(respuesta.content, respaldo=pregunta)
        # Si Qwen cambió el tema en vez de solo reemplazar el pronombre, se descarta.
        if _consulta_es_coherente(resuelta, pregunta, []):
            pregunta = resuelta
    return {"consulta": _a_tercera_persona(pregunta), "ruta": ["reescribir"]}


def recuperar(estado: Estado) -> dict:
    """Busca con la consulta reescrita y con la pregunta original, y se queda
    con los mejores fragmentos que superen el umbral de similitud."""
    mejores: dict[str, dict] = {}
    for texto in {estado["consulta"], estado["question"]}:
        for f in vectorstore.search(texto, k=TOP_K):
            clave = f["doc_id"] + f["fragment"][:80]
            if clave not in mejores or f["score"] > mejores[clave]["score"]:
                mejores[clave] = f
    ordenados = sorted(mejores.values(), key=lambda f: f["score"], reverse=True)
    aceptados = [f for f in ordenados if f["score"] >= config.SIMILARITY_THRESHOLD]
    return {"fragmentos": aceptados[:TOP_K], "ruta": ["recuperar"]}


def evaluar(estado: Estado) -> dict:
    """Nodo validador: el LLM dice si el contexto alcanza para responder (SI/NO)."""
    # Se usa la consulta reescrita: ya dice "Ken" en vez de "él" y "Barbie" en vez de "tú".
    prompt = prompts.PROMPT_EVALUAR.format(
        contexto=_formatear_contexto(estado["fragmentos"]),
        pregunta=estado["consulta"],
    )
    respuesta = get_llm(max_tokens=5).invoke([HumanMessage(content=prompt)])
    veredicto = _normalizar(respuesta.content)
    return {"contexto_suficiente": veredicto.startswith(("si", "yes")), "ruta": ["evaluar"]}


def generar(estado: Estado) -> dict:
    mensajes = [
        SystemMessage(content=prompts.PROMPT_SISTEMA),
        HumanMessage(
            content=prompts.PROMPT_GENERAR.format(
                contexto=_formatear_contexto(estado["fragmentos"]),
                pregunta=estado["question"],
                consulta=estado["consulta"],
            )
        ),
    ]
    respuesta = get_llm(max_tokens=400).invoke(mensajes).content.strip()

    # Si aun así el modelo dice que no sabe, se trata como rechazo.
    if _normalizar(prompts.FRASE_RECHAZO)[:40] in _normalizar(respuesta):
        return {
            "answer": prompts.MENSAJE_RECHAZO,
            "rejected": True,
            "sources": [],
            "ruta": ["generar"],
        }
    fuentes = [
        {"doc": f["doc"], "fragment": f["fragment"], "score": f["score"]}
        for f in estado["fragmentos"]
    ]
    return {"answer": respuesta, "rejected": False, "sources": fuentes, "ruta": ["generar"]}


def rechazar(estado: Estado) -> dict:
    return {
        "answer": prompts.MENSAJE_RECHAZO,
        "rejected": True,
        "sources": [],
        "ruta": ["rechazar"],
    }


# ----------------------------------------------------------- decisiones
def despues_de_clasificar(estado: Estado) -> str:
    return "reescribir" if estado["intencion"] == "pregunta" else "saludar"


def despues_de_recuperar(estado: Estado) -> str:
    return "evaluar" if estado["fragmentos"] else "rechazar"


def despues_de_evaluar(estado: Estado) -> str:
    return "generar" if estado["contexto_suficiente"] else "rechazar"


# ---------------------------------------------------------------- grafo
def construir_grafo():
    g = StateGraph(Estado)
    g.add_node("recibir", recibir)
    g.add_node("clasificar", clasificar)
    g.add_node("saludar", saludar)
    g.add_node("reescribir", reescribir)
    g.add_node("recuperar", recuperar)
    g.add_node("evaluar", evaluar)
    g.add_node("generar", generar)
    g.add_node("rechazar", rechazar)

    g.add_edge(START, "recibir")
    g.add_edge("recibir", "clasificar")
    g.add_conditional_edges("clasificar", despues_de_clasificar, ["saludar", "reescribir"])
    g.add_edge("reescribir", "recuperar")
    g.add_conditional_edges("recuperar", despues_de_recuperar, ["evaluar", "rechazar"])
    g.add_conditional_edges("evaluar", despues_de_evaluar, ["generar", "rechazar"])
    g.add_edge("saludar", END)
    g.add_edge("generar", END)
    g.add_edge("rechazar", END)
    return g.compile()


grafo = construir_grafo()
