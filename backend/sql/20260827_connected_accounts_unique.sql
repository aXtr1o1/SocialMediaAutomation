-- Enforce one connected account per user + platform + provider identity.
-- Run in Supabase SQL editor before relying on atomic upserts.

alter table public.connected_accounts
  alter column connected_at set default now();

-- Keep the newest row per identity; remove older duplicates
with ranked as (
  select
    id,
    row_number() over (
      partition by user_id, platform_id, provider_user_id
      order by coalesce(updated_at, connected_at, created_at) desc nulls last, id desc
    ) as rn
  from public.connected_accounts
  where provider_user_id is not null
)
delete from public.connected_accounts ca
using ranked r
where ca.id = r.id
  and r.rn > 1;

-- Non-partial unique index so PostgREST upsert on_conflict inference works.
-- Multiple NULLs in provider_user_id remain allowed (Postgres UNIQUE semantics).
create unique index if not exists connected_accounts_user_platform_provider_uidx
  on public.connected_accounts (user_id, platform_id, provider_user_id);
