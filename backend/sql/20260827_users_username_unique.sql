-- Enforce unique canonical usernames (trim + lower).
-- Run in Supabase SQL editor before relying on exact username login.

-- Canonicalize existing usernames
update public.users
set username = lower(trim(username))
where username is not null
  and username <> lower(trim(username));

-- Rename duplicate usernames (keep preferred row; rename the rest)
with ranked as (
  select
    id,
    row_number() over (
      partition by lower(trim(username))
      order by
        (is_deleted is true) asc,
        coalesce(updated_at, created_at) desc nulls last,
        id desc
    ) as rn
  from public.users
  where username is not null
    and trim(username) <> ''
)
update public.users u
set
  username = u.username || '_dup_' || left(replace(u.id::text, '-', ''), 8),
  updated_at = now()
from ranked r
where u.id = r.id
  and r.rn > 1;

-- Final normalize after rename
update public.users
set username = lower(trim(username))
where username is not null;

create unique index if not exists users_username_canonical_uidx
  on public.users (username)
  where username is not null;
