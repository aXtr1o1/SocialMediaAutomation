-- Per-user ownership for crawled/processed articles (shared catalog sources).
-- Run in Supabase SQL editor. Adjust the old unique-constraint drop if your name differs.

alter table public.crawled_articles
  add column if not exists created_by uuid references auth.users (id);

alter table public.processed_content
  add column if not exists created_by uuid references auth.users (id);

-- Replace global (source_id, url) uniqueness with per-owner uniqueness.
-- Common PostgREST/Supabase names; ignore errors if already dropped.
do $$
begin
  alter table public.crawled_articles
    drop constraint if exists crawled_articles_source_id_url_key;
exception
  when undefined_object then null;
end $$;

drop index if exists crawled_articles_source_id_url_key;
drop index if exists crawled_articles_source_id_url_idx;

create unique index if not exists crawled_articles_owner_source_url_uidx
  on public.crawled_articles (created_by, source_id, url);

create index if not exists crawled_articles_created_by_idx
  on public.crawled_articles (created_by);

create index if not exists processed_content_created_by_idx
  on public.processed_content (created_by);
