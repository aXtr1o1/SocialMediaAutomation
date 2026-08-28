-- OAuth pending state (shared across workers; run in Supabase SQL editor)

create table if not exists public.oauth_pending_states (
  state text primary key,
  platform text not null check (platform in ('linkedin', 'bluesky')),
  user_id uuid not null,
  intent text not null default 'add',
  session_payload jsonb null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);

create index if not exists oauth_pending_states_expires_idx
  on public.oauth_pending_states (expires_at);

create index if not exists oauth_pending_states_platform_idx
  on public.oauth_pending_states (platform);
