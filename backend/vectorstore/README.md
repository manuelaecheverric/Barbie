# vectorstore/ — Base vectorial (Persona 1)

Configuración de ChromaDB y embeddings. La usa el agente en `agents/`.

Recomendaciones:

- Leer la ruta de persistencia de una variable de entorno, por ejemplo
  `CHROMA_PERSIST_DIR=./chroma_data`.
- Guardar en cada fragmento la metadata `document_id` y `filename`, para que la
  API pueda borrar documentos y mostrar las fuentes en el chat.
