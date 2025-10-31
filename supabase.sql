-- ====================================================
-- SUPABASE SCHEMA - LIGA DE DARDOS
-- ====================================================

-- 🔹 Tabla de perfiles (usuarios)
create table if not exists public.profiles (
  id uuid references auth.users on delete cascade primary key,
  email text unique not null,
  role text default 'player' check (role in ('admin','player')),
  created_at timestamp default now()
);

-- sincroniza el email al crearse un usuario
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email);
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

-- 🔹 Tabla de equipos
create table if not exists public.teams (
  id uuid default gen_random_uuid() primary key,
  name text not null unique,
  player_email text references public.profiles(email),
  created_at timestamp default now()
);

-- 🔹 Tabla de jornadas
create table if not exists public.jornadas (
  id uuid default gen_random_uuid() primary key,
  number int not null,
  match_date date,
  created_at timestamp default now()
);

-- 🔹 Tabla de partidos
create table if not exists public.matches (
  id uuid default gen_random_uuid() primary key,
  jornada_id uuid references public.jornadas(id) on delete cascade,
  team1_id uuid references public.teams(id) on delete cascade,
  team2_id uuid references public.teams(id) on delete cascade,
  score1 int,
  score2 int,
  played boolean default false,
  single_player boolean default false,
  no_show boolean default false,
  created_at timestamp default now()
);

-- ====================================================
-- 🔹 Función: calcular clasificación
-- ====================================================
create or replace view public.clasificacion as
select
  t.id,
  t.name as equipo,
  count(m.id) filter (where m.played or m.no_show) as jj,
  count(m.id) filter (
    where (m.score1 > m.score2 and m.team1_id = t.id and not m.no_show)
       or (m.score2 > m.score1 and m.team2_id = t.id and not m.no_show)
  ) as g,
  count(m.id) filter (
    where (m.score1 < m.score2 and m.team1_id = t.id and not m.no_show)
       or (m.score2 < m.score1 and m.team2_id = t.id and not m.no_show)
  ) as p,
  coalesce(sum(case
    when m.team1_id = t.id then m.score1
    when m.team2_id = t.id then m.score2
  end),0) as gf,
  coalesce(sum(case
    when m.team1_id = t.id then m.score2
    when m.team2_id = t.id then m.score1
  end),0) as gc,
  coalesce(sum(case
    when ((m.score1 > m.score2 and m.team1_id = t.id) or (m.score2 > m.score1 and m.team2_id = t.id))
         and not m.single_player then 3
    when ((m.score1 > m.score2 and m.team1_id = t.id) or (m.score2 > m.score1 and m.team2_id = t.id))
         and m.single_player then 2
    when ((m.score1 < m.score2 and m.team1_id = t.id) or (m.score2 < m.score1 and m.team2_id = t.id))
         and not m.no_show then 1
    when (m.no_show and ((m.team1_id = t.id and m.score1 > m.score2) or (m.team2_id = t.id and m.score2 > m.score1)))
         then 3
    else 0
  end),0) as puntos
from public.teams t
left join public.matches m
  on t.id in (m.team1_id, m.team2_id)
group by t.id, t.name
order by puntos desc, gf-gc desc, gf desc;

-- ====================================================
-- 🔹 Reglas de seguridad (RLS)
-- ====================================================
alter table public.teams enable row level security;
alter table public.matches enable row level security;
alter table public.jornadas enable row level security;

-- solo admin puede ver todos los equipos
create policy "admin puede ver todo" on public.teams
  for select using (auth.uid() in (select id from public.profiles where role='admin'));

-- cada jugador solo puede ver su equipo
create policy "jugador ve su equipo" on public.teams
  for select using (player_email = auth.email());

-- admin puede insertar o borrar
create policy "admin modifica equipos" on public.teams
  for all using (auth.uid() in (select id from public.profiles where role='admin'));

-- los jugadores pueden ver sus partidos
create policy "ver partidos" on public.matches
  for select using (
    auth.email() in (
      select player_email from public.teams where id in (team1_id, team2_id)
    )
  );

-- los jugadores pueden actualizar sus propios partidos
create policy "editar resultados propios" on public.matches
  for update using (
    auth.email() in (
      select player_email from public.teams where id in (team1_id, team2_id)
    )
  );

-- admin puede todo
create policy "admin full acceso matches" on public.matches
  for all using (auth.uid() in (select id from public.profiles where role='admin'));

-- ====================================================
-- 🔹 Asignar rol admin (ejemplo)
-- Ejecuta después de crear tu usuario:
-- update public.profiles set role='admin' where email='TU_EMAIL';
-- ====================================================