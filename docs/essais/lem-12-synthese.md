# LEM-12 — Synthèse des essais et données publiables

Synthèse de la phase d'exploration pour
[LEM-12](https://linear.app/lemauvaiscoin/issue/LEM-12). Elle consolide les
quatre essais du socle français :

- **Ventes DVF et géographie** : [LEM-6](lem-6-ventes-geographie.md) ;
- **Enrichissements territoriaux** : [LEM-7](lem-7-enrichissements.md) et
  inventaire [LEM-54](../sources/FICHIERS_A_TELECHARGER.md) ;
- **Urbanisme textuel (PLU/PLUi)** : [LEM-5](https://linear.app/lemauvaiscoin/issue/LEM-5) ;
- **Annonces immobilières et scraping** : [LEM-8](https://linear.app/lemauvaiscoin/issue/LEM-8)
  (sorti du périmètre principal en bonus éventuel le 27 novembre 2026).

Les explorations liées aux bonus (**flux contextuel temps réel**
[LEM-10](https://linear.app/lemauvaiscoin/issue/LEM-10) et **parcours belge**
[LEM-44](https://linear.app/lemauvaiscoin/issue/LEM-44)) ont été détachées du
blocage de `LEM-12` afin de démarrer le socle français sans délai.

## Critères d'acceptation

| Critère                                                              | Où il est rempli                                                                                                                      |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Matrice information, source, grain, qualité, règle, limite, décision | [Matrice des sources et décisions](#matrice-des-sources-et-décisions)                                                                 |
| Décisions distinctes : territoires, ventes, bâtiments, sorties texte | [Décisions par entité](#décisions-par-entité)                                                                                         |
| Seuils justifiés par usage depuis les mesures observées              | [Seuils de publication](#seuils-de-publication)                                                                                       |
| Socle harmonisé, enrichissements et sources prioritaires             | [Socle, enrichissements et priorités](#socle-enrichissements-et-priorités)                                                            |
| Volumes, stockage, budget et décisions encore ouvertes               | [Volumes, calcul distribué et budget](#volumes-calcul-distribué-et-budget) et [Décisions encore ouvertes](#décisions-encore-ouvertes) |
| Mise à jour et découpage des tickets d'intégration                   | [Plan d'intégration et tickets Linear](#plan-dintégration-et-tickets-linear)                                                          |

## Décisions par entité

### 1. Territoires (référentiels hors comptage thématique)

- **Pivot officiel :** COG INSEE 2025 (`v_commune_2025`, `v_departement_2025`,
  `v_region_2025`, `v_ctcd_2025`, `v_mvt_commune_2025`). Tous les codes
  géographiques sont stockés en **chaînes** (`"01053"`, `"2A"`).
- **Niveaux du socle :** `national` (1), `region` (18), `departement` (101),
  `commune` (34 875), `arrondissement` (45 pour Paris, Lyon, Marseille).
  `CTCD` (`69D` vs `69M`) est conservé en attribut des communes.
- **Contours :** Etalab GeoJSON (`communes-100m`, `departements-100m`,
  `regions-100m`, filtrés sur le COG 2025 et en séparant strictement `COM` et
  `ARM` pour éviter tout double comptage). `contours_iris` (IGN WFS, 49 386
  polygones) est différé au lot où une source IRIS est intégrée.
- **Comptage pédagogique :** le COG et les contours sont des **référentiels
  structurels**, comptés hors des ~30 sources métier retenues (en cohérence avec
  la cible de 12 à 50 sources du sujet).

### 2. Ventes immobilières (DVF)

- **Source retenue :** **DVF géolocalisée (Etalab)** via `static.data.gouv.fr`
  (fenêtre glissante 5 ans juillet 2021 – juin 2026 ; 1 famille avec DVF brute).
  L'ancien dossier `files.data.gouv.fr/geo-dvf/latest/csv/` est abandonné
  (suppression annoncée le 31/11/2026).
- **Grain stocké :** ventes nettoyées au niveau mutation (`id_mutation`) dans
  PostgreSQL (avec `code_commune`, `code_arrondissement`, `type_local`,
  `nature_mutation`, `prix`, `surface`, `prix_m2`, `date_mutation`, `lat/lon`) +
  tables d'agrégats précalculés par `(territoire, niveau, période, type_local)`.
- **Comptage & multibiens :** `1 vente = 1 id_mutation` à disposition unique et
  commune unique résolue au COG 2025 (mutations hors COG comme `97127`/`97123`
  exclues), `Vente` résidentielle monobien (`1 Maison` ou `1 Appartement` +
  dépendances/terrains rattachés, après repli des répétitions DGFiP par
  subdivision fiscale). `VEFA` séparée de `Vente`. Multibiens, mixtes,
  répétitions ambiguës (Cerema `nblocanc`), non résidentiel et prix symboliques
  `< 1 000 €` exclus du prix au m² et comptabilisés dans les métadonnées
  d'exclusion.
- **Agrégation :** toujours calculée depuis les ventes nettoyées pour chaque
  niveau (`arrondissement`, `commune`, `departement`, `region`, `national`) ;
  **jamais de moyenne de médianes** (biais mesuré jusqu'à `-23,1 %` dans le
  Rhône).

### 3. Bâtiments, parcelles et logements

- **Pas de fiche bâtiment individuelle unifiée dans le socle initial.** Les
  essais LEM-7 et LEM-6 montrent qu'une adresse commune ne prouve pas qu'une
  vente DVF et un DPE concernent le même appartement, et que la BDNB (36,7 Go)
  est vide de DPE en zone rurale et à La Réunion.
- **Choix retenu :**
  - **BAN** et **Cadastre** comme référentiels d'adresses/parcelles (liaison par
    `id_parcelle` 14 car. et coordonnées, sans promesse de rapprochement
    logement par logement) ;
  - **DPE ADEME**, **RNIC** (copropriétés), **RPLS** (logements sociaux) et
    **Sitadel** (permis) agrégés au niveau **commune / arrondissement** ;
  - **BDNB** placée « à approfondir » (candidat Databricks PySpark si besoin en
    extension).

### 4. Sorties textuelles (urbanisme PLU/PLUi)

- **Corpus retenu (LEM-5) :** règlements écrits des PLU/PLUi en vigueur via
  l'API du Géoportail de l'Urbanisme (fallback EPCI si la commune n'a pas de
  document et `is_rnu = false`) + zonage structuré `wfs_du:zone_urba` et statut
  `is_rnu` / carte communale.
- **Méthode :** `PyMuPDF` pour le texte natif, `Tesseract` français (4
  orientations) uniquement pour les pages scannées sans couche texte.
  Classification des passages par zone (34/35 en `test`) et thème (précision
  83 %, rappel 81 % en `test`).
- **Niveau de détail publié :** **passages cités** (document, version GPU,
  page, zone, thème, texte exact) + zonage WFS structuré. **Aucun champ chiffré
  automatique** extrait par règles (37 % de faux nombres en `test`).
- **Stockage :** **MongoDB** (base non relationnelle retenue en complément de
  Supabase) pour les documents PLU/PLUi, passages indexés plein texte et
  traçabilité/rejets hétérogènes ; PDF bruts conservés sur Cloudflare R2.

## Matrice des sources et décisions

Comptage retenu : **29 sources thématiques retenues** (dans la fourchette de 12
à 50 du sujet, hors référentiels COG/contours), **9 à approfondir**, **2
écartées** (LEM-7) et **annonces/scraping déplacés en bonus éventuel** (LEM-8).

### Sources retenues (29)

| Domaine            | Source                                           | Grain et période                                                              | Qualité mesurée                                                             | Règle de publication                                                           | Limite principale                                                            | Décision         |
| ------------------ | ------------------------------------------------ | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- | ---------------- |
| **Socle immo**     | DVF & DVF géolocalisée (Etalab/DGFiP, 1 famille) | Vente (`id_mutation`) -> agrégats `ARM/COM/DEP/REG/NAT`, juil. 2021–juin 2026 | 97/101 dép., 98,8 % prix, 98,0 % coords, 58,8 % mutations monobiens propres | Séparer Maison/Appart et VEFA ; `n < 5` masqué, `5–14` averti, `≥ 15` fiable   | Absent en Alsace-Moselle (`57`, `67`, `68`) et Mayotte (`976`)               | **Retenue (P0)** |
| **Socle immo**     | BAN (adresses)                                   | Adresse, continu                                                              | Couverture nationale                                                        | Référentiel d'adresses / géocodage bulk                                        | Précision variable en rural                                                  | **Retenue (P1)** |
| **Socle immo**     | Cadastre Etalab                                  | Parcelle (14 car.), continu                                                   | 100 % des `id_parcelle` DVF remplis                                         | Jointure parcellaire / contexte carte                                          | Téléchargement communal ; parcelle ≠ logement                                | **Retenue (P2)** |
| **Socle immo**     | RNIC (copropriétés, quotidien)                   | Copropriété -> commune, T3 2025 / quotidien                                   | 619 402 copros, 476 codes `commune` mal formés                              | Agréger par `code_officiel_commune` (et `commune` pour ARM)                    | Utiliser l'extrait quotidien uniquement                                      | **Retenue (P1)** |
| **Énergie / log.** | DPE logements existants (ADEME)                  | Diagnostic -> commune/ARM, depuis juil. 2021                                  | 16 M lignes, étiquette 100 %, 3,3 % sans `code_insee_ban`                   | Distribution A–G + effectif ; préciser « parc diagnostiqué »                   | Biais de sélection (logements vendus/loués) ; `annee_construction` lacunaire | **Retenue (P0)** |
| **Énergie / log.** | Consommation électricité & gaz (Agence ORE)      | Commune × filière × secteur, 2011–2025                                        | 3,79 M lignes, DOM compris, zéro absent                                     | Agréger résidentiel ; signaler mailles secrétisées                             | Changement de grain ARM -> COM en 2018                                       | **Retenue (P1)** |
| **Énergie / log.** | LOVAC (logements vacants)                        | Commune/ARM, 2020–2026                                                        | 34 912 communes, 9 395 en secret `s` en 2025                                | Garder `s` distinct de `0` ; taux jusqu'à 2025                                 | Pas de taux de vacance 2026 (parc total 2025)                                | **Retenue (P1)** |
| **Énergie / log.** | Carte des loyers 2025                            | Commune/ARM, 2025                                                             | 34 900 communes ; 30 029 estimées sur maille élargie                        | Afficher loyer €/m² CC + indicateur de fiabilité / maille                      | Loyer d'annonce estimé, pas loyer signé                                      | **Retenue (P0)** |
| **Énergie / log.** | Sitadel (permis de construire)                   | Autorisation -> commune × année, 2013–2026                                    | 1,94 M lignes ; surface `0` fréquente                                       | Exclure annulations ; lire surface `0` comme `NULL`                            | Autorisation ≠ logement achevé                                               | **Retenue (P2)** |
| **Énergie / log.** | RPLS (logements sociaux)                         | Logement -> commune/ARM, 2025                                                 | 5,42 M logements ; DPE absent 100 % à La Réunion                            | Effectif et part parc social ; DPE avec couverture                             | DPE manquant 4–10 % métropole, 100 % Réunion                                 | **Retenue (P2)** |
| **Pop. / éco.**    | Recensement INSEE (Melodi : pop, log, emploi)    | Commune/ARM/IRIS, 2012, 2017, 2023                                            | 812 obs./territoire, 0 manquant, DOM inclus                                 | Arrondir estimations pondérées à l'affichage                                   | Estimations non entières                                                     | **Retenue (P0)** |
| **Pop. / éco.**    | Filosofi commune (INSEE Melodi)                  | Commune/ARM, 2023                                                             | Médiane niveau de vie quasi complète ; 25/27 mesures absentes               | Publier médiane + taux pauvreté si non secret (`OBS_STATUS=O`)                 | Secret statistique en rural (`15219` Salers)                                 | **Retenue (P0)** |
| **Pop. / éco.**    | Entreprises INSEE (`SIDE_STOCKS`, `SIDE_CREA`)   | Commune/ARM, 2012–2025                                                        | 0 manquant, vrais zéros                                                     | Publier stocks et créations annuels                                            | Agrégé par commune (pas de localisation commerce)                            | **Retenue (P1)** |
| **Services / éq.** | BPE (Base permanente des équipements, INSEE)     | Commune × type, 2025                                                          | Complète, 0 manquant                                                        | Absences de ligne = vrai `0` (sauf ancien code 400)                            | Présence ≠ qualité / capacité                                                | **Retenue (P0)** |
| **Services / éq.** | IPS écoles & collèges (Éducation nat.)           | Établissement -> commune/ARM, 2024–2026                                       | 97k écoles, quasi complet (`ips` en texte)                                  | Parser virgule ; pondérer/afficher effectif d'établissements                   | Quelques établissements sans IPS                                             | **Retenue (P1)** |
| **Services / éq.** | Valeur ajoutée des lycées GT                     | Lycée -> commune/ARM, 2025                                                    | Complet sur lycées GT                                                       | Garder `0` comme vraie valeur (« conforme attendu »)                           | Couvre uniquement les communes avec lycée                                    | **Retenue (P2)** |
| **Services / éq.** | APL médecins généralistes (DREES)                | Commune/ARM, 2022–2024                                                        | 34 890 communes, 0 manquant, vrais zéros (523)                              | Pondérer les agrégats supérieurs par population standardisée                   | Mayotte absente                                                              | **Retenue (P1)** |
| **Services / éq.** | FINESS (établissements de santé)                 | Établissement, mai 2026                                                       | 102 939 lignes, sans en-tête, DOM codés `9A`–`9F`                           | Reconstruire code INSEE 5 car. + géolocalisation                               | Format historique deux types de lignes                                       | **Retenue (P2)** |
| **Services / éq.** | Délinquance enregistrée (Intérieur)              | Commune × indicateur, 2016–2025                                               | 5,24 M lignes ; ~50 % `ndiff` en 2025                                       | Afficher « non diffusé » pour `ndiff`, garder vrais `0`                        | Fort secret en rural (`15219` : 9/15 `ndiff`)                                | **Retenue (P1)** |
| **Services / éq.** | Fibre optique (Arcep)                            | Commune/ARM, T2 2026                                                          | 34 919 communes, shapefile latin-1                                          | Recalculer le taux (`locaux raccordables / locaux`)                            | Colonne `couv` = classe, pas taux exact                                      | **Retenue (P1)** |
| **Services / éq.** | Qualité de l'eau potable (Hub'Eau)               | Prélèvement -> commune, continu                                               | Complet ; `< limite` codé `0`                                               | Conserver `resultat_alphanumerique` (éviter faux zéro)                         | Quotas API commune par commune à prévoir via zip annuels                     | **Retenue (P2)** |
| **Risques / env.** | CatNat (extrait GASPAR / Géorisques)             | Commune × arrêté, depuis 1982                                                 | 247 140 arrêtés (8 Mo zip), 582 anciens codes                               | Convertir anciens codes via COG ; comptage par aléa                            | Niveau commune seulement (pas parcelle)                                      | **Retenue (P0)** |
| **Risques / env.** | Radon (Géorisques)                               | Commune/ARM, en vigueur                                                       | 3 classes potentielles                                                      | Publier après clarification de l'écart API vs rapport Lyon                     | Contradiction API vs rapport sur Lyon 1er                                    | **Retenue (P1)** |
| **Risques / env.** | Inondation TRI / AZI / PPRN (GASPAR + API)       | Commune, nov. 2026                                                            | 32 798 PPRN dans GASPAR (8 Mo), TRI sur API                                 | Combiner GASPAR + TRI ; convertir anciens codes                                | Commune seulement ; ne vaut pas exposition parcellaire                       | **Retenue (P0)** |
| **Risques / env.** | Retrait-gonflement des argiles (Géorisques)      | Commune, 2026                                                                 | Statut communal sans compte                                                 | Publier le niveau communal (sans carte fine au socle)                          | Réponse point vide ambiguë ; carte fine = 122 Mo                             | **Retenue (P1)** |
| **Risques / env.** | Recul du trait de côte (décret 2026-95)          | Commune, 2026                                                                 | 371 communes concernées                                                     | Indicateur booléen / statut communal                                           | Taux INEC (284 Mo) laissés « à approfondir »                                 | **Retenue (P2)** |
| **Risques / env.** | CORINE Land Cover (SDES)                         | Commune (COG 2010), 1990–2018                                                 | 22 Mo CSV ; 1 015 codes à convertir ; doublons 2000–2012                    | Convertir via COG ; garder versions révisées ; `CLC_9` = absent                | Dernier millésime 2018                                                       | **Retenue (P2)** |
| **Urbanisme**      | Règlements écrits PLU/PLUi (API GPU)             | Document / passage (zone, thème, page), en vigueur                            | 34/35 zones et 28/35 thèmes justes en `test` ; Licence Ouverte              | Stocké dans **MongoDB** ; passages cités + version + page ; **0 chiffre auto** | OAP/PSMV non couverts ; hauteurs Paris/Lyon sur plans PDF                    | **Retenue (P0)** |
| **Urbanisme**      | Zonage & statut RNU/CC (WFS GPU)                 | Polygone `zone_urba` + `is_rnu`, en vigueur                                   | 48/49 zones annotées retrouvées ; limite 30 req/s                           | Stocké dans PostGIS ; jointure par `partition` + `idurba` + préfixe            | `gpu_doc_id` WFS diffère parfois de l'API                                    | **Retenue (P1)** |

### Sources à approfondir (9), écartées (2) et bonus différés

| Statut                | Sources                                                                                                                                                                                                                                                                                                                                                                                    | Motif                                                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| **À approfondir (9)** | BDNB (36,7 Go), SIRENE (2,2 Go), IRVE (44 % sans code commune), Arrêts transport (437 Mo, jointure spatiale), Filosofi IRIS, OCS GE (extraits régionaux), Qualité de l'air LCSQA (pas d'indice national communal), Projections climatiques DRIAS/Explore2 (compte requis, hors engagement cahier des charges), Prescriptions de hauteur GPU (seulement Strasbourg typé dans l'échantillon) | Volume élevé (candidats PySpark LEM-13/LEM-21), jointures spatiales (LEM-17), couverture partielle ou hors engagement initial. |
| **Écartées (2)**      | IRCOM impôts sur le revenu (redondant avec Filosofi), Brevet par établissement (série arrêtée en 2021)                                                                                                                                                                                                                                                                                     | Redondance ou série obsolète (LEM-7).                                                                                          |
| **Bonus différés**    | Annonces immobilières & scraping (`LEM-8`, `LEM-23`, `LEM-30`), Flux contextuel temps réel (`LEM-10`, `LEM-37`), Parcours belge (`LEM-44`, `LEM-39`)                                                                                                                                                                                                                                       | Hors socle principal français ; à reprendre après le socle si le temps le permet.                                              |

## Seuils de publication

Chaque règle découle directement des anomalies mesurées dans les essais :

| Domaine                         | Seuil / règle de publication                                                                                                                            | Justification empirique                                                                                                                                                                                                                                                                        |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **DVF — prix au m²**            | `n < 5` : médiane masquée (« effectif insuffisant ») ; `5 ≤ n < 15` : affichée avec badge « faible effectif » ; `n ≥ 15` : affichage standard + Q25–Q75 | Mesure nationale 2024 vs 2025 (`LEM-6`) : dérive médiane annuelle de 27,6 % (p90 88,4 %) pour `1–4` maisons, 15,7 % (`5–9`), 10,8 % (`10–14`), puis **8,1 %** (`15–29`) et **6,1 %** en appartements. Sur 2,5 ans, `n ≥ 5` couvre 77,2 % des communes en maisons et `n ≥ 15` en couvre 43,5 %. |
| **DVF — bornes aberrantes**     | Exclure prix `< 1 000 €`, surface hors `[9 ; 1 000] m²`, prix/m² hors `[200 ; 35 000] €/m²`                                                             | Écarte 3,63 % des 1 384 341 mutations 2025 au total (44 963 prix < 1 000 €, plus 0,39 % pour les bornes surface et €/m² : 453 + 4 902), bloquant les cas extrêmes (`720 000 €/m²` à Paris 11e).                                                                                                |
| **Zones non couvertes vs zéro** | Trois états distincts dans l'API et l'UI : `0` (vrai zéro), `NULL / non_couvert` (ex. DVF Alsace-Moselle/Mayotte), `non_diffuse` (secret statistique)   | `LEM-7` : 251k valeurs `ndiff` en délinquance, 9 395 `s` dans LOVAC, `resultat_numerique = 0` pour `< limite` dans Hub'Eau.                                                                                                                                                                    |
| **Urbanisme PLU/PLUi**          | Publier uniquement passages cités (avec document, version GPU, page) et zonage WFS ; interdire les champs chiffrés extraits par règles                  | `LEM-5` : 37 % de faux nombres affichés en `test` (précision 63 %, rappel 57 %) vs 34/35 zones et 83 % précision / 81 % rappel sur les passages.                                                                                                                                               |
| **Loyers (Carte des loyers)**   | Toujours afficher si la valeur est estimée au niveau commune ou sur maille élargie                                                                      | `LEM-7` : 30 029 communes sur 34 900 sont estimées sur une zone plus large que la commune.                                                                                                                                                                                                     |

## Socle, enrichissements et priorités

1. **Vague P0 — Socle national minimal démontrable (parcours comparer 2–4 communes) :**
   - Référentiels : COG 2025 + mouvements + contours Etalab (`communes-100m`, `departements-100m`, `regions-100m`).
   - Ventes : DVF géolocalisée (5 ans glissants, `LEM-19`).
   - Enrichissements cœur : Recensement INSEE, Filosofi commune, DPE ADEME, Carte des loyers, BPE, CatNat & Inondation (`LEM-18`).
   - Textuel : Règlements PLU/PLUi sur échantillon puis extension (`LEM-22`, MongoDB).
2. **Vague P1 — Enrichissement du socle (couverture complète des thèmes du produit) :**
   - BAN, RNIC, ORE, LOVAC, Entreprises INSEE, IPS écoles/collèges, APL médecins, Délinquance, Arcep fibre, Radon (après clarification Lyon), Argiles communal, Zonage WFS GPU.
3. **Vague P2 — Compléments et passage à l'échelle (`LEM-21`) :**
   - Cadastre, Sitadel, RPLS, Valeur ajoutée lycées, FINESS, Hub'Eau (zip annuels), Trait de côte, CORINE Land Cover, et éventuellement BDNB/SIRENE/arrêts via PySpark sur Databricks.

## Volumes, calcul distribué et budget

| Couche                            | Contenu                                                                                                                                                        | Volume brut estimé    | Volume publié estimé        | Hébergement / outil                       |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- | --------------------------- | ----------------------------------------- |
| **Cloudflare R2**                 | Archives brutes utiles (DVF 610 Mo, DPE, ORE, PDF PLU) + Parquet                                                                                               | ~2 à 5 Go (hors BDNB) | ~2 à 5 Go                   | R2 (10 Go gratuits/mois)                  |
| **Supabase (PostgreSQL/PostGIS)** | Territoires + contours (~10–20 Mo), ventes DVF nettoyées (~3,5–4 M lignes) + agrégats + indicateurs enrichis (~2–4 M lignes)                                   | —                     | ~1,5 à 3 Go (index compris) | Supabase Pro (~25 $/mois) ou Free en dev  |
| **MongoDB**                       | Corpus PLU/PLUi structuré (passages cités, index plein texte) + manifestes et rejets hétérogènes                                                               | —                     | < 300 Mo sur le socle       | Atlas M0 gratuit (512 Mo) ou Railway      |
| **Databricks (PySpark)**          | Traitement distribué reproductible (`LEM-13` / `LEM-21`) sur gros volumes : DVF 5 ans (~20 M lignes), DPE complet (16 M lignes), et éventuellement BDNB/SIRENE | 15 à 50 M lignes      | Parquet -> R2 -> Supabase   | Free Edition puis calcul plafonné         |
| **Railway + Vercel + Mintlify**   | FastAPI + MCP `mcp` v2 + worker `procrastinate` (Railway), SPA (Vercel Hobby), docs (Mintlify Starter)                                                         | —                     | —                           | ~5–15 $/mois Railway, 0 $ Vercel/Mintlify |

L'ensemble tient dans le **plafond global de 50 USD/mois** ([LEM-34](https://linear.app/lemauvaiscoin/issue/LEM-34)), sous réserve de ne pas embarquer la BDNB complète (36,7 Go) dans Supabase et de conserver uniquement les agrégats utiles des gros jeux (DPE, Sitadel, RPLS, Hub'Eau).

## Plan d'intégration et tickets Linear

- **[LEM-17](https://linear.app/lemauvaiscoin/issue/LEM-17) (Schéma géographique)** : modéliser COG 2025 (`national`, `region`, `departement`, `commune`, `arrondissement`), `CTCD`, `territory_code_aliases` (4 155 anciens codes résolus chronologiquement sans ambiguïté), contours `communes-100m`/`departements-100m`/`regions-100m` et tables `datasets`/`publications`.
- **[LEM-20](https://linear.app/lemauvaiscoin/issue/LEM-20) (Collecteur versionné)** : valider `collecte -> R2 -> manifeste/rejets MongoDB -> worker Procrastinate` sur DVF géolocalisée (`static.data.gouv.fr` via API data.gouv.fr).
- **[LEM-19](https://linear.app/lemauvaiscoin/issue/LEM-19) (Premiers indicateurs DVF)** : appliquer la cascade d'exclusions LEM-6, publier ventes + agrégats par niveau (`ARM/COM/DEP/REG/NAT`) avec seuils `n < 5` / `5–14` / `≥ 15` et distinction `hors DVF` (`57`, `67`, `68`, `976`).
- **[LEM-18](https://linear.app/lemauvaiscoin/issue/LEM-18) (Enrichissements)** : découper par vague P0 (Recensement, Filosofi, DPE, Carte des loyers, BPE, CatNat/Inondation) puis P1/P2.
- **[LEM-22](https://linear.app/lemauvaiscoin/issue/LEM-22) (Analyse textuelle)** : pipeline `GPU API -> R2 -> PyMuPDF/Tesseract -> MongoDB` (passages cités) + zonage WFS PostGIS, sans champs chiffrés automatiques.
- **[LEM-21](https://linear.app/lemauvaiscoin/issue/LEM-21) (Extension nationale & Databricks)** : exécuter DVF 5 ans + DPE 16 M lignes sur Databricks ([LEM-13](https://linear.app/lemauvaiscoin/issue/LEM-13)) et étendre les sources P1/P2.

## Décisions encore ouvertes

- **Radon (Lyon 1er)** : trancher la contradiction entre l'API Géorisques (classe 1) et le rapport communal (« important ») avant publication P1.
- **Annotations LEM-5** : faire relire un sondage humain d'une vingtaine de passages et décider si une extraction LLM est testée dans le budget LEM-34.
- **Sources « à approfondir »** : décider après P0 si BDNB, SIRENE, IRVE ou arrêts de transport entrent dans l'extension `LEM-21` (notamment comme démonstrateur PySpark multi-nœuds).
- **Licences et quotas API** : vérifier formellement les quotas des API appelées commune par commune (Géorisques, DiDo, Melodi) ; privilégier les fichiers complets (GASPAR zip, Hub'Eau zip annuels, DVF csv.gz) dès qu'ils existent.
