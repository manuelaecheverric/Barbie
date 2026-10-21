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

Rechazo con sugerencias (v4):
  Cuando hay fragmentos "cercanos" (score ≥ UMBRAL_SUGERENCIAS) que no alcanzan
  para responder, el rechazo ofrece esos temas ("Ken, mi familia..."). Los temas
  salen de los nombres de los documentos, con reglas y sin LLM: no puede
  sugerir temas que no existan en la base.

Búsqueda por palabra clave (v5):
  bge-m3 da puntajes bajos a preguntas cortas con un nombre ("¿quién es Raquelle?").
  Si un fragmento cercano contiene literalmente una palabra importante de la
  pregunta (un nombre, por ejemplo), pasa al nodo evaluar aunque esté bajo el
  umbral. El nodo evaluar sigue decidiendo si alcanza para responder.

Respuestas cortas ("sí", "claro", "dale") (v5):
  Barbie termina sus respuestas ofreciendo más ("¿Quieres que te cuente algo más
  sobre Ken?"). Si el usuario responde "sí", la pregunta se arma con esa oferta:
  "Cuéntame algo más sobre Ken".

Preguntas de seguimiento ("¿y cuándo lo conociste?"):
  1. Qwen intenta reemplazar el pronombre por el nombre (PROMPT_RESOLVER_REFERENCIAS).
  2. Si su respuesta no trae ninguna palabra nueva de la conversación, se usa un
     plan B sin LLM: la consulta se arma con la pregunta anterior del usuario
     + la nueva ("Quién es novio de Barbie. Y cuándo lo conoció Barbie").
"""

import operator
import re
import unicodedata
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

import vectorstore
from vectorstore import config

from . import prompts
from .llm import get_llm

TOP_K = 4
MAX_LARGO_PREGUNTA = 500

# Fragmentos con score entre este valor y el umbral no sirven para responder,
# pero sí para sugerir temas parecidos en el rechazo.
# Preguntas fuera de tema (sushi) dan 0.31–0.38, así que no reciben sugerencias.
UMBRAL_SUGERENCIAS = 0.42
MAX_TEMAS_SUGERIDOS = 3

# Cuántos fragmentos se piden a la base por cada búsqueda (después se quedan TOP_K).
K_CANDIDATOS = 8
# Un fragmento con una palabra clave de la pregunta pasa a evaluar si tiene al menos
# este puntaje. Las preguntas fuera de tema no tienen la palabra, así que no pasan.
UMBRAL_PALABRA_CLAVE = 0.35


class Estado(TypedDict, total=False):
    # Entrada
    question: str
    user_id: str
    history: list[dict]
    # Intermedios
    intencion: str  # "saludo" | "gracias" | "despedida" | "vacio" | "afirmacion" | "pregunta"
    consulta: str  # pregunta reescrita para la búsqueda
    consulta_sola: str  # solo en el plan B: la pregunta nueva sin la anterior
    fragmentos: list[dict]  # [{"doc", "doc_id", "fragment", "score"}] ≥ umbral
    cercanos: list[dict]  # fragmentos ≥ UMBRAL_SUGERENCIAS (para sugerir temas)
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
        "como estas", "como te va", "como vas", "que onda", "que pasa", "que hay", "que hubo", "holaa"
    ],
    "gracias": ["muchas gracias", "mil gracias", "gracias", "thanks", "genial", "perfecto"],
    "despedida": ["hasta luego", "hasta pronto", "nos vemos", "adios", "chao", "chau", "bye"],
}
_RELLENO = {"barbie", "muñeca", "amiga", "y", "a", "ti", "tu", "muy", "bien", "ok", "oki", "vale"}


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
        linea = re.sub(r"^(consulta|query|nueva pregunta)\s*:\s*", "", linea.strip(), flags=re.I)
        linea = linea.strip(" \"'`¿?¡!.")
        if linea:
            return linea[:200]
    return respaldo


# ----------------------------------------------- rechazo con sugerencias (v4)
def _nombre_tema(doc: str) -> str:
    """'03-ken.md' -> 'Ken' (según prompts.TEMAS_POR_DOCUMENTO).
    Si el archivo no está en la tabla: '10-moda-y-estilo.md' -> 'moda y estilo'."""
    base = re.sub(r"\.\w+$", "", (doc or "").strip().lower())
    if base in prompts.TEMAS_POR_DOCUMENTO:
        return prompts.TEMAS_POR_DOCUMENTO[base]
    legible = re.sub(r"^\d+[-_ ]*", "", base)
    return re.sub(r"[-_]+", " ", legible).strip()


def _temas_sugeridos(fragmentos: list[dict]) -> list[str]:
    temas = []
    for f in fragmentos:
        tema = _nombre_tema(f.get("doc", ""))
        if tema and tema not in temas:
            temas.append(tema)
        if len(temas) == MAX_TEMAS_SUGERIDOS:
            break
    return temas


def _unir_temas(temas: list[str]) -> str:
    """['Ken', 'mi familia', 'mis amigas'] -> 'Ken, mi familia y mis amigas'."""
    if len(temas) == 1:
        return temas[0]
    return ", ".join(temas[:-1]) + " y " + temas[-1]


def _mensaje_rechazo(cercanos: list[dict] | None) -> str:
    temas = _temas_sugeridos(cercanos or [])
    if not temas:
        return prompts.MENSAJE_RECHAZO
    return prompts.MENSAJE_RECHAZO_CON_TEMAS.format(temas=_unir_temas(temas))


# Respuestas cortas a la oferta de Barbie ("¿Quieres que te cuente algo más?").
_AFIRMACIONES = {
    "si", "sip", "sii", "siii", "claro", "dale", "bueno", "ok", "okay", "va", "vale",
    "porfa", "por favor", "obvio", "de una", "si porfa", "si por favor", "si claro",
    "claro que si", "si quiero", "me encantaria", "si me encantaria", "cuentame",
    "cuentame mas", "dime mas", "mas", "quiero saber mas", "si cuentame",
}

# Palabras de pedido que no sirven como palabra clave ("háblame de Raquelle").
_PALABRAS_PEDIDO = {
    "hablame", "cuentame", "dime", "cuenta", "habla", "sabes", "saber", "quiero",
    "puedes", "podrias", "conoces", "informacion", "sobre", "algo", "favor", "porfa",
    "tienes", "tiene", "eres", "todo", "acerca",
}


def _palabras_clave(texto: str) -> set[str]:
    """'¿Quién es Raquelle?' -> {'raquelle'}."""
    return {
        p for p in _normalizar(texto).split()
        if len(p) >= 4 and p not in _PALABRAS_VACIAS and p not in _PALABRAS_PEDIDO
    }


def _contiene_palabra(fragmento: dict, palabras: set[str]) -> bool:
    texto = f" {_normalizar(fragmento.get('fragment', '') + ' ' + fragmento.get('doc', ''))} "
    return any(f" {p} " in texto for p in palabras)


def _pregunta_desde_afirmacion(history: list[dict]) -> str:
    """El usuario dijo "sí": arma la pregunta con lo último que ofreció Barbie.
    '¿Quieres que te cuente algo más sobre Ken?' -> 'Cuéntame algo más sobre Ken'."""
    ultimo = next(
        (str(m.get("content", "")) for m in reversed(history) if m.get("role") != "user"), ""
    )
    # Rechazo con sugerencias: "...temas parecidos que conozco: Ken y mis amigas."
    temas = re.search(r"que conozco:\s*([^.]+)\.", ultimo)
    if temas:
        return f"Cuéntame sobre {temas.group(1).strip()}"
    ofertas = re.findall(r"¿([^¿?]+)\?", ultimo)
    if ofertas:
        oferta = re.sub(
            r"^(te gustar[ií]a|quieres|quisieras|deseas)\s+(que te cuente|saber|conocer|escuchar)\s+",
            "", ofertas[-1].strip(), flags=re.I,
        )
        if oferta and not re.search(r"\beso\b", oferta.lower()):
            return f"Cuéntame {oferta}"
    return _ultima_pregunta_usuario(history)


def _mi_a_barbie(texto: str) -> str:
    """Lo que ofreció Barbie habla de ella en primera persona:
    'más sobre mi familia' -> 'más sobre familia de Barbie'."""
    texto = re.sub(r"\bmis?\s+([\wáéíóúüñ]+)", r"\1 de Barbie", texto, flags=re.I)
    return re.sub(r"\bm[ií]\b", "Barbie", texto, flags=re.I)


_PALABRAS_VACIAS = {
    "cual", "cuales", "quien", "quienes", "como", "cuando", "donde", "cuanto",
    "cuantos", "cuantas", "porque", "sobre", "para", "esta", "este", "eres",
    "barbie",  # aparece en casi todo, así que no sirve para comparar
    # palabras cortas sin significado propio
    "que", "los", "las", "del", "con", "por", "una", "uno", "sus", "mas", "fue",
    "era", "hay", "muy", "les", "ese", "esa",
}

# El usuario le habla a Barbie de "tú": se pasa a tercera persona con reglas.
_PRONOMBRES_TU = {"tu", "tus", "tú"}  # tu novio -> novio de Barbie
_PRONOMBRES_TE = {"te", "ti", "contigo"}  # te creó -> creó a Barbie

# Verbos en segunda persona -> tercera persona.
_VERBOS = {
    "eres": "es", "estas": "está", "estás": "está", "tienes": "tiene",
    "tenias": "tenía", "tenías": "tenía", "tuviste": "tuvo", "vives": "vive",
    "naciste": "nació", "haces": "hace", "hiciste": "hizo", "trabajas": "trabaja",
    "llamas": "llama", "fuiste": "fue", "has": "ha", "habias": "había", "habías": "había",
    "puedes": "puede", "pudiste": "pudo", "sabes": "sabe", "conoces": "conoce",
    "quieres": "quiere", "quisiste": "quiso", "sales": "sale", "usas": "usa",
    "manejas": "maneja", "vienes": "viene", "viniste": "vino", "cumples": "cumple",
    "estuviste": "estuvo", "dijiste": "dijo", "dices": "dice", "pusiste": "puso",
    "sientes": "siente", "sentiste": "sintió", "pediste": "pidió", "llevas": "lleva",
    "juegas": "juega", "prefieres": "prefiere", "piensas": "piensa", "crees": "cree",
    "vas": "va", "gustas": "gusta", "vistes": "viste", "tocas": "toca", "cantas": "canta",
}

# Palabras que terminan en -aste/-iste pero no son verbos en pasado de "tú".
_NO_SON_VERBOS = {
    "contraste", "desgaste", "gaste", "baste", "chiste", "triste", "quiste",
    "despiste", "embiste", "existe", "consiste", "subsiste", "insiste", "resiste",
    "asiste", "persiste",
}

# Palabras que apuntan a algo dicho antes ("¿y cuándo apareció él?").
_REFERENCIAS = {"él", "ella", "ellos", "ellas", "eso", "esa", "ese", "su", "sus", "aquel", "aquella"}
# "lo", "la", "le"... también son artículos ("la capital"), así que solo cuentan
# como referencia cuando van antes de un verbo de "tú" ("lo conociste").
_CLITICOS = {"lo", "la", "le", "los", "las", "les"}


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


def _verbo_tercera(palabra: str) -> str | None:
    """Devuelve el verbo en tercera persona, o None si la palabra no es un verbo de 'tú'."""
    if not palabra:
        return None
    return _VERBOS.get(palabra.lower()) or _preterito_tercera(palabra)


def _a_tercera_persona(pregunta: str) -> str:
    """Pasa la pregunta de "tú" a "Barbie" con reglas fijas (sin LLM: no puede inventar).

    '¿Quién es tu novio?'          -> 'Quién es novio de Barbie'
    '¿Quién te creó?'              -> 'Quién creó a Barbie'
    '¿Cuándo te separaste de Ken?' -> 'Cuándo se separó Barbie de Ken'  (te reflexivo -> se)
    '¿En qué películas has salido?'-> 'En qué películas ha salido Barbie'
    """
    palabras = re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", pregunta)
    cambios = set()
    salida = []
    pos_verbo = None  # dónde poner "Barbie" si solo cambió un verbo

    for i, palabra in enumerate(palabras):
        p = palabra.lower()
        siguiente = palabras[i + 1] if i + 1 < len(palabras) else ""

        if p in _PRONOMBRES_TU:
            cambios.add("de")
            continue
        if p in _PRONOMBRES_TE:
            # "te separaste", "te llamas": es reflexivo -> "se separó", "se llama"
            if p == "te" and _verbo_tercera(siguiente):
                salida.append("se")
            else:
                cambios.add("a")
            continue

        verbo = _verbo_tercera(palabra)
        if verbo:
            cambios.add("verbo")
            salida.append(verbo)
            if pos_verbo is None:
                pos_verbo = len(salida)
                # "ha salido": Barbie va después del participio
                if verbo in ("ha", "había") and re.search(r"(ado|ido|to|so|cho)$", siguiente.lower()):
                    pos_verbo += 1
            continue

        salida.append(palabra)

    if cambios and not any(s.lower() == "barbie" for s in salida):
        if "de" in cambios:
            salida.append("de Barbie")
        elif "a" in cambios:
            salida.append("a Barbie")
        elif pos_verbo is not None:
            salida.insert(min(pos_verbo, len(salida)), "Barbie")
        else:
            salida.append("Barbie")
    texto = " ".join(salida)
    return texto or pregunta


def _tiene_referencia(pregunta: str) -> bool:
    palabras = re.findall(r"[\wáéíóúüñ]+", pregunta.lower())
    # "el" sin tilde al final de la pregunta casi siempre es "él" ("¿y cuándo nació el?")
    if any(p in _REFERENCIAS for p in palabras) or palabras[-1:] == ["el"]:
        return True
    for p, siguiente in zip(palabras, palabras[1:]):
        if p in _CLITICOS and _verbo_tercera(siguiente):
            return True
    # Preguntas que continúan la anterior: "¿y cuándo terminaron?", "¿y después?"
    return palabras[:1] == ["y"] and len(palabras) <= 7


def _raices(texto: str, minimo: int = 4) -> set[str]:
    """Primeras 5 letras de las palabras importantes ('tienes' y 'tiene' -> 'tiene')."""
    return {
        p[:5] for p in _normalizar(texto).split()
        if len(p) >= minimo and p not in _PALABRAS_VACIAS
    }


def _consulta_es_coherente(consulta: str, pregunta: str) -> bool:
    """La consulta reescrita debe compartir al menos una palabra con la pregunta.
    Si no, Qwen probablemente cambió el tema o copió algo del prompt."""
    return bool(_raices(consulta) & _raices(pregunta))


def _agrego_contexto(consulta: str, pregunta: str, history: list[dict]) -> bool:
    """¿Qwen agregó alguna palabra de los últimos mensajes (p. ej. 'Ken')?
    Se usan palabras de 3+ letras para no perder nombres cortos como Ken."""
    previo = " ".join(str(m.get("content", "")) for m in history[-2:])
    nuevas = _raices(consulta, minimo=3) - _raices(pregunta, minimo=3)
    return bool(nuevas & _raices(previo, minimo=3))


def _ultima_pregunta_usuario(history: list[dict]) -> str:
    for mensaje in reversed(history):
        contenido = str(mensaje.get("content", "")).strip()
        if mensaje.get("role") == "user" and contenido:
            return contenido[:MAX_LARGO_PREGUNTA]
    return ""


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

    sin_relleno = " ".join(p for p in texto.split() if p != "barbie")
    if estado.get("history") and sin_relleno in _AFIRMACIONES:
        return {"intencion": "afirmacion", "ruta": ["clasificar"]}

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
    """Prepara la consulta de búsqueda:
    1. Si es una pregunta de seguimiento y hay historial, Qwen reemplaza
       "él", "lo", "ella"... por el nombre ("¿y cuándo lo conociste?" -> "...a Ken").
       Si Qwen no lo logra, plan B sin LLM: se antepone la pregunta anterior.
    2. Reglas fijas pasan "tú" a "Barbie" ("tu novio" -> "novio de Barbie")."""
    pregunta = estado["question"]
    history = estado["history"]
    consulta_previa = ""

    if estado.get("intencion") == "afirmacion":
        # "sí" -> "Cuéntame algo más sobre Ken" (la pregunta real reemplaza al "sí")
        nueva = _pregunta_desde_afirmacion(history) or pregunta
        return {
            "question": nueva,
            "consulta": _a_tercera_persona(_mi_a_barbie(nueva)),
            "consulta_sola": "",
            "ruta": ["reescribir"],
        }

    if history and _tiene_referencia(pregunta):
        prompt = prompts.PROMPT_RESOLVER_REFERENCIAS.format(
            historial=_formatear_historial(history),
            pregunta=pregunta,
        )
        respuesta = get_llm(max_tokens=60).invoke([HumanMessage(content=prompt)])
        resuelta = _limpiar_consulta(respuesta.content, respaldo=pregunta)

        if _consulta_es_coherente(resuelta, pregunta) and _agrego_contexto(resuelta, pregunta, history):
            pregunta = resuelta
        else:
            # Plan B: Qwen no resolvió la referencia (o cambió el tema).
            anterior = _ultima_pregunta_usuario(history)
            if anterior:
                consulta_previa = _a_tercera_persona(anterior)

    consulta = _a_tercera_persona(pregunta)
    if consulta_previa:
        # Se busca con las dos: la combinada encuentra el tema anterior y la sola
        # sirve si en realidad la pregunta nueva no dependía de la anterior.
        return {
            "consulta": f"{consulta_previa}. {consulta}",
            "consulta_sola": consulta,
            "ruta": ["reescribir"],
        }
    return {"consulta": consulta, "consulta_sola": "", "ruta": ["reescribir"]}


def recuperar(estado: Estado) -> dict:
    """Busca con la consulta reescrita y con la pregunta original, y se queda
    con los mejores fragmentos que superen el umbral de similitud, o que
    contengan una palabra clave de la pregunta (un nombre como "Raquelle").
    También guarda los "cercanos" para sugerir temas si hay que rechazar."""
    mejores: dict[str, dict] = {}
    textos = {estado["consulta"], estado["question"], estado.get("consulta_sola") or ""} - {""}
    for texto in textos:
        for f in vectorstore.search(texto, k=K_CANDIDATOS):
            clave = f["doc_id"] + f["fragment"][:80]
            if clave not in mejores or f["score"] > mejores[clave]["score"]:
                mejores[clave] = f
    ordenados = sorted(mejores.values(), key=lambda f: f["score"], reverse=True)
    claves = _palabras_clave(estado["consulta"]) | _palabras_clave(estado["question"])
    aceptados = [
        f for f in ordenados
        if f["score"] >= config.SIMILARITY_THRESHOLD
        or (f["score"] >= UMBRAL_PALABRA_CLAVE and _contiene_palabra(f, claves))
    ]
    cercanos = [f for f in ordenados if f["score"] >= UMBRAL_SUGERENCIAS]
    return {"fragmentos": aceptados[:TOP_K], "cercanos": cercanos, "ruta": ["recuperar"]}


def evaluar(estado: Estado) -> dict:
    """Nodo validador: el LLM dice si el contexto alcanza para responder (SI/NO).
    Recibe la consulta reescrita (dice "Ken" en vez de "él" y "Barbie" en vez de "tú")
    y también la pregunta original, por si la reescritura quedó rara."""
    prompt = prompts.PROMPT_EVALUAR.format(
        contexto=_formatear_contexto(estado["fragmentos"]),
        pregunta=estado["consulta"],
        pregunta_original=estado["question"],
    )
    respuesta = get_llm(max_tokens=5).invoke([HumanMessage(content=prompt)])
    veredicto = _normalizar(respuesta.content)
    return {"contexto_suficiente": veredicto.startswith(("si", "yes")), "ruta": ["evaluar"]}


def generar(estado: Estado) -> dict:
    mensajes = [
        SystemMessage(content=prompts.PROMPT_SISTEMA),
        # Ejemplo de una respuesta bien escrita (few-shot)
        HumanMessage(
            content=prompts.PROMPT_GENERAR.format(
                contexto=prompts.EJEMPLO_FRAGMENTOS,
                pregunta=prompts.EJEMPLO_PREGUNTA,
                consulta="Quién es novio de Barbie",
            )
        ),
        AIMessage(content=prompts.EJEMPLO_RESPUESTA),
        # Pregunta real
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
            "answer": _mensaje_rechazo(estado.get("cercanos")),
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
        "answer": _mensaje_rechazo(estado.get("cercanos")),
        "rejected": True,
        "sources": [],
        "ruta": ["rechazar"],
    }


# ----------------------------------------------------------- decisiones
def despues_de_clasificar(estado: Estado) -> str:
    return "reescribir" if estado["intencion"] in ("pregunta", "afirmacion") else "saludar"


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