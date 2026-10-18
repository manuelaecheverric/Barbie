-- =====================================================================
-- Pink Oracle: esquema de base de datos en Supabase
-- Ejecutar UNA vez en: Supabase > SQL Editor > New query > Run
-- =====================================================================

-- Conversaciones de cada usuario
create table if not exists public.conversations (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users (id) on delete cascade,
  title       text not null default 'Nueva conversación',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists conversations_user_idx on public.conversations (user_id, updated_at desc);

-- Mensajes (historial). sources = fragmentos usados por el agente
create table if not exists public.messages (
  id               uuid primary key default gen_random_uuid(),
  conversation_id  uuid not null references public.conversations (id) on delete cascade,
  user_id          uuid not null references auth.users (id) on delete cascade,
  role             text not null check (role in ('user', 'assistant')),
  content          text not null,
  sources          jsonb not null default '[]'::jsonb,
  rejected         boolean not null default false,
  created_at       timestamptz not null default now()
);
create index if not exists messages_conversation_idx on public.messages (conversation_id, created_at);

-- Documentos de la base de conocimiento (compartida entre usuarios)
create table if not exists public.documents (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users (id) on delete cascade,
  filename      text not null,
  content_type  text,
  size_bytes    bigint not null default 0,
  chunks        integer not null default 0,
  status        text not null default 'processing' check (status in ('processing', 'ready', 'error')),
  error         text,
  created_at    timestamptz not null default now()
);
create index if not exists documents_created_idx on public.documents (created_at desc);

-- ---------------------------------------------------------------------
-- Seguridad a nivel de fila (RLS)
-- El backend usa la llave de servicio, pero activamos RLS para que nadie
-- pueda leer datos ajenos usando la llave pública del frontend.
-- ---------------------------------------------------------------------
alter table public.conversations enable row level security;
alter table public.messages      enable row level security;
alter table public.documents     enable row level security;

drop policy if exists "conversaciones propias" on public.conversations;
create policy "conversaciones propias" on public.conversations
  for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "mensajes propios" on public.messages;
create policy "mensajes propios" on public.messages
  for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "documentos visibles" on public.documents;
create policy "documentos visibles" on public.documents
  for select to authenticated using (true);

drop policy if exists "documentos propios" on public.documents;
create policy "documentos propios" on public.documents
  for delete to authenticated using (auth.uid() = user_id);
