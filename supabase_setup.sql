-- ChapLife private cloud state
-- Run once in Supabase Dashboard > SQL Editor > New query.

create table if not exists public.chaplife_state (
  user_id uuid primary key references auth.users(id) on delete cascade,
  db_blob text not null,
  updated_at timestamptz not null default now()
);

alter table public.chaplife_state enable row level security;

drop policy if exists "chaplife users select own state" on public.chaplife_state;
create policy "chaplife users select own state"
on public.chaplife_state for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists "chaplife users insert own state" on public.chaplife_state;
create policy "chaplife users insert own state"
on public.chaplife_state for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists "chaplife users update own state" on public.chaplife_state;
create policy "chaplife users update own state"
on public.chaplife_state for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "chaplife users delete own state" on public.chaplife_state;
create policy "chaplife users delete own state"
on public.chaplife_state for delete
to authenticated
using (auth.uid() = user_id);

revoke all on table public.chaplife_state from anon;
grant select, insert, update, delete on table public.chaplife_state to authenticated;
