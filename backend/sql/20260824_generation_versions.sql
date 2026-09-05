-- Generation drafts + version history (run in Supabase SQL editor)

create table if not exists public.generation_drafts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  article_id uuid not null,
  platform text not null check (platform in ('linkedin', 'bluesky')),
  current_version_id uuid null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists generation_drafts_user_article_idx
  on public.generation_drafts (user_id, article_id);

create index if not exists generation_drafts_user_updated_idx
  on public.generation_drafts (user_id, updated_at desc);

create table if not exists public.generation_versions (
  id uuid primary key default gen_random_uuid(),
  draft_id uuid not null references public.generation_drafts (id) on delete cascade,
  version_number int not null check (version_number > 0),
  full_post text not null,
  label text not null default '',
  source text not null check (source in ('generate', 'regenerate', 'restore')),
  target_text text null,
  instruction text null,
  replacement_text text null,
  created_at timestamptz not null default now(),
  unique (draft_id, version_number)
);

create index if not exists generation_versions_draft_idx
  on public.generation_versions (draft_id, version_number);

-- Optional FK after both tables exist
do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'generation_drafts_current_version_id_fkey'
  ) then
    alter table public.generation_drafts
      add constraint generation_drafts_current_version_id_fkey
      foreign key (current_version_id)
      references public.generation_versions (id)
      on delete set null;
  end if;
end $$;
