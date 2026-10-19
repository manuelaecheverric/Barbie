# vectorstore/ — Base vectorial (Persona 1)

pgvector en Supabase (la misma base de datos del historial). Se conecta con
`DATABASE_URL` (prefijo `postgresql+psycopg://`, Session pooler).

- Cada fragmento guarda la metadata `doc_id` y `filename`, para borrar
  documentos y mostrar las fuentes en el chat.
- `doc_id` es el `id` de la tabla `public.documents`.
