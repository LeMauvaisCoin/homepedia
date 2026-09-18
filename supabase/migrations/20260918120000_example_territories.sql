-- Socle minimal servant le jeu d'exemple (LEM-9). Le modèle géographique
-- complet (millésimes, sources, publications) arrive avec LEM-17.

create extension if not exists postgis with schema extensions;

create table public.territories (
  -- Codes officiels géographiques en chaînes : « 01053 » garde son zéro initial.
  code text primary key,
  level text not null check (level in ('commune', 'departement', 'region')),
  name text not null,
  department_code text,
  region_code text,
  population integer check (population >= 0),
  centroid extensions.geometry(Point, 4326) not null
);

create index territories_level_name_idx on public.territories (level, name);

-- Seule l'API FastAPI lit cette table, avec un rôle qui contourne la RLS.
-- Sans policy, les rôles exposés par Supabase (anon, authenticated) n'y voient rien.
alter table public.territories enable row level security;
