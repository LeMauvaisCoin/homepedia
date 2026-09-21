-- Example dataset: the twelve prefectures of the Auvergne-Rhône-Alpes region.
--
-- Source: API Découpage administratif (https://geo.api.gouv.fr/communes/{code}
-- with fields=nom,code,population,centre,codeDepartement,codeRegion), INSEE/IGN
-- data under Licence Ouverte 2.0, retrieved on 18 September 2026.
-- Loaded by `supabase start` and `supabase db reset`, locally only.

insert into public.territories
  (code, level, name, department_code, region_code, population, centroid)
values
  ('01053', 'commune', 'Bourg-en-Bresse', '01', '84', 42372, extensions.st_setsrid(extensions.st_makepoint(5.2469, 46.2027), 4326)),
  ('03190', 'commune', 'Moulins', '03', '84', 19206, extensions.st_setsrid(extensions.st_makepoint(3.3255, 46.5591), 4326)),
  ('07186', 'commune', 'Privas', '07', '84', 8538, extensions.st_setsrid(extensions.st_makepoint(4.5949, 44.7214), 4326)),
  ('15014', 'commune', 'Aurillac', '15', '84', 26214, extensions.st_setsrid(extensions.st_makepoint(2.4416, 44.9281), 4326)),
  ('26362', 'commune', 'Valence', '26', '84', 64458, extensions.st_setsrid(extensions.st_makepoint(4.9164, 44.9234), 4326)),
  ('38185', 'commune', 'Grenoble', '38', '84', 156140, extensions.st_setsrid(extensions.st_makepoint(5.7155, 45.1842), 4326)),
  ('42218', 'commune', 'Saint-Étienne', '42', '84', 173136, extensions.st_setsrid(extensions.st_makepoint(4.3665, 45.4241), 4326)),
  ('43157', 'commune', 'Le Puy-en-Velay', '43', '84', 18540, extensions.st_setsrid(extensions.st_makepoint(3.8973, 45.0283), 4326)),
  ('63113', 'commune', 'Clermont-Ferrand', '63', '84', 146351, extensions.st_setsrid(extensions.st_makepoint(3.1127, 45.787), 4326)),
  ('69123', 'commune', 'Lyon', '69', '84', 519127, extensions.st_setsrid(extensions.st_makepoint(4.8351, 45.758), 4326)),
  ('73065', 'commune', 'Chambéry', '73', '84', 59964, extensions.st_setsrid(extensions.st_makepoint(5.9064, 45.5822), 4326)),
  ('74010', 'commune', 'Annecy', '74', '84', 132117, extensions.st_setsrid(extensions.st_makepoint(6.1264, 45.9024), 4326))
on conflict (code) do nothing;
