"""
Paso 2 de la carga: dividir el texto en fragmentos (~600 caracteres, 100 de solapamiento).

- Markdown y Word: primero se corta por títulos (#, ##, ###) y a cada fragmento
  se le antepone su título, p. ej. "Ken, el novio de Barbie — Por qué se llama Ken".
  Así la búsqueda sabe de qué habla cada pedazo aunque el texto no lo repita.
- PDF, TXT y CSV: se corta por párrafos, líneas y palabras, en ese orden.
"""

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from . import config

_TITULOS = [("#", "titulo"), ("##", "seccion"), ("###", "subseccion")]


def _cortador(tamano: int = config.CHUNK_SIZE) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=tamano,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def _es_solo_cita(texto: str) -> bool:
    """True si todas las líneas empiezan con '>' (p. ej. la línea '> Tema: ...' de las fichas)."""
    lineas = [l for l in texto.splitlines() if l.strip()]
    return bool(lineas) and all(l.lstrip().startswith(">") for l in lineas)


def _fragmentar_markdown(documento: Document) -> list[Document]:
    secciones = MarkdownHeaderTextSplitter(_TITULOS, strip_headers=True).split_text(
        documento.page_content
    )
    fragmentos = []
    for seccion in secciones:
        texto = seccion.page_content.strip()
        if not texto or _es_solo_cita(texto):
            continue
        encabezado = " — ".join(
            seccion.metadata[clave]
            for _, clave in _TITULOS
            if seccion.metadata.get(clave)
        )
        tamano = max(config.CHUNK_SIZE - len(encabezado) - 1, 200)
        for pedazo in _cortador(tamano).split_text(texto):
            contenido = f"{encabezado}\n{pedazo}" if encabezado else pedazo
            metadatos = {**documento.metadata, "seccion": encabezado}
            fragmentos.append(Document(page_content=contenido, metadata=metadatos))
    return fragmentos


def fragmentar(documentos: list[Document], extension: str) -> list[Document]:
    fragmentos = []
    for documento in documentos:
        if extension in (".md", ".docx"):
            fragmentos.extend(_fragmentar_markdown(documento))
        else:
            fragmentos.extend(_cortador().split_documents([documento]))
    return [f for f in fragmentos if f.page_content.strip()]
