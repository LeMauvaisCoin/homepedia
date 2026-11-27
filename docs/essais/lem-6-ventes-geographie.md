# LEM-6 — Ventes immobilières (DVF) et découpages territoriaux

Essai pour [LEM-6](https://linear.app/lemauvaiscoin/issue/LEM-6). Il mesure,
sur les fichiers nationaux réels de **DVF géolocalisée** et les référentiels
géographiques officiels (**COG INSEE 2025**, contours **Etalab / IGN Admin
Express** et **Contours IRIS**), la couverture, les volumes, la complétude,
les doublons, le traitement des mutations multibiens et les règles de calcul du
prix au m². Les conclusions alimentent la synthèse
[LEM-12](lem-12-synthese.md), le schéma géographique
([LEM-17](https://linear.app/lemauvaiscoin/issue/LEM-17)), le collecteur
([LEM-20](https://linear.app/lemauvaiscoin/issue/LEM-20)) et les premiers
indicateurs de ventes
([LEM-19](https://linear.app/lemauvaiscoin/issue/LEM-19)).

Hors périmètre, car suivis ailleurs : enrichissements territoriaux
([LEM-7](lem-7-enrichissements.md)), urbanisme textuel
([LEM-5](https://linear.app/lemauvaiscoin/issue/LEM-5)), annonces et scraping
sortis en bonus éventuel ([LEM-8](https://linear.app/lemauvaiscoin/issue/LEM-8)),
flux temps réel ([LEM-10](https://linear.app/lemauvaiscoin/issue/LEM-10)) et
Belgique ([LEM-44](https://linear.app/lemauvaiscoin/issue/LEM-44)).

## Critères d'acceptation

| Critère                                                                 | Où il est rempli                                                                                                                        |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Sources, périodes et territoires (urbains, ruraux, zones peu/non couv.) | [Sources et périodes](#sources-et-périodes) et [Échantillon territorial](#échantillon-territorial)                                      |
| Volumes, complétude, doublons, validité des codes et couverture         | [Référentiels géographiques](#référentiels-géographiques) et [Mesures DVF nationales](#mesures-dvf-nationales)                          |
| Comptage des ventes et traitement des mutations multibiens              | [Comptage des ventes et multibiens](#comptage-des-ventes-et-multibiens)                                                                 |
| Règles de calcul du prix au m² et exclusions explicitées                | [Règles de calcul du prix au m²](#règles-de-calcul-du-prix-au-m) et [Biais de la moyenne de médianes](#biais-de-la-moyenne-de-médianes) |
| Résultats reproductibles et niveaux fiables pour LEM-12                 | [Reproduire les mesures](#reproduire-les-mesures) et [Niveaux fiables et seuils](#niveaux-fiables-et-seuils-de-publication)             |

## Reproduire les mesures

Deux scripts autonomes sans dépendance externe, lancés avec `uv run` dans cet
ordre. Ils téléchargent uniquement des ressources ouvertes sans clé et mettent
leurs fichiers en cache dans `.cache/lem-6/` (~290 Mo, ignoré par Git). Mesures
du 27 novembre 2026.

| Script                        | Contenu                                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------------------------ |
| `scripts/essais/lem_6_geo.py` | COG INSEE 2025, mouvements de communes, contours Etalab et couches WFS IGN (communes, ARM, IRIS) |
| `scripts/essais/lem_6.py`     | Inventaire DVF (fenêtre 5 ans), analyse nationale 2024–S1 2026, cascade d'exclusions et seuils   |

## Sources et périodes

### Ventes immobilières (DVF et DVF géolocalisée)

Les deux jeux publiés sur data.gouv.fr (Licence Ouverte 2.0) forment **une seule
famille de sources** : DVF géolocalisée (Etalab) enrichit les fichiers DGFiP
avec les coordonnées parcellaires WGS84 (`latitude`, `longitude`) et un format
CSV normalisé.

Livraison en vigueur au 27 novembre 2026 (publiée les 12–21 octobre 2026, fenêtre
glissante de 5 ans **juillet 2021 – juin 2026**) :

| Jeu               | Ressource                                      | Format  | Taille   | Mise à jour |
| ----------------- | ---------------------------------------------- | ------- | -------- | ----------- |
| DVF géolocalisée  | DVF 2021 (2e semestre)                         | csv.gz  | 75,5 Mo  | 2026-10-20  |
| DVF géolocalisée  | DVF 2022                                       | csv.gz  | 141,3 Mo | 2026-10-20  |
| DVF géolocalisée  | DVF 2023                                       | csv.gz  | 117,4 Mo | 2026-10-20  |
| DVF géolocalisée  | DVF 2024                                       | csv.gz  | 107,4 Mo | 2026-10-20  |
| DVF géolocalisée  | DVF 2025                                       | csv.gz  | 116,3 Mo | 2026-10-20  |
| DVF géolocalisée  | DVF 2026 (1er semestre)                        | csv.gz  | 51,7 Mo  | 2026-10-20  |
| DVF géolocalisée  | Fichier unique (juillet 2021 – juin 2026)      | csv.gz  | 609,5 Mo | 2026-10-21  |
| DVF brute (DGFiP) | 6 archives annuelles/semestrielles (2021–2026) | txt.zip | 374,1 Mo | 2026-10-12  |

**Point critique d'accès :** l'ancien répertoire `files.data.gouv.fr/geo-dvf/latest/csv/`
est marqué `[ARCHIVE] suppression au 31/11/2026`. Le collecteur de LEM-20 doit
résoudre les ressources stables via l'API data.gouv.fr du jeu
`5cc1b94a634f4165e96436c1` (`static.data.gouv.fr`), pas l'ancien annuaire.

L'analyse détaillée ci-dessous porte sur les **2,5 dernières années complètes**
(`2024`, `2025`, `2026-S1`), soit **8 996 395 lignes** et **3 268 074 mutations**
(275,4 Mo compressés), couvrant la bascule du COG au 1er janvier 2025.

### Référentiels géographiques

| Référentiel             | Source officielle                                                      | Usage                                                  |
| ----------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------ |
| COG INSEE 2025          | `v_commune_2025`, `v_departement_2025`, `v_region_2025`, `v_ctcd_2025` | Table pivot des codes chaînes, hiérarchie et libellés  |
| Mouvements de communes  | `v_mvt_commune_2025.csv` (INSEE)                                       | Rattachement des anciens codes aux communes courantes  |
| Contours administratifs | Etalab GeoJSON (`communes-100m`, `departements-100m`, `regions-100m`)  | Cartographie Mapbox / PostGIS légère en WGS84          |
| Contours IRIS           | IGN Géoplateforme WFS (`STATISTICALUNITS.IRIS:contours_iris`)          | Maille infra-communale (optionnelle, 49 386 polygones) |

## Échantillon territorial

Douze codes reprenant les 9 territoires partagés avec LEM-7 et LEM-5, complétés
par Marseille (`13055` / `13205`) et Mamoudzou (`97611`, Mayotte) pour couvrir
tous les cas limites DVF :

| Code    | Territoire               | Cas testé                                           | Statut COG 2025 | Dans `communes-100m` | IRIS IGN (types) |
| ------- | ------------------------ | --------------------------------------------------- | --------------- | -------------------- | ---------------- |
| `69123` | Lyon                     | Grande ville à arrondissements, Métropole de Lyon   | `COM`           | Oui                  | 0 (par ARM)      |
| `69381` | Lyon 1er                 | Arrondissement municipal                            | `ARM -> 69123`  | Oui                  | 11 (`A,H`)       |
| `75056` | Paris                    | Capitale à arrondissements, département-commune     | `COM`           | Oui                  | 0 (par ARM)      |
| `75111` | Paris 11e                | Arrondissement municipal                            | `ARM -> 75056`  | Oui                  | 63 (`H`)         |
| `13055` | Marseille                | Grande ville à arrondissements                      | `COM`           | Oui                  | 0 (par ARM)      |
| `13205` | Marseille 5e             | Arrondissement municipal                            | `ARM -> 13055`  | Oui                  | 20 (`A,H`)       |
| `67482` | Strasbourg               | Alsace-Moselle (hors DVF : Livre foncier)           | `COM`           | Oui                  | 116 (`A,H`)      |
| `15219` | Salers                   | Commune rurale (310 hab.), faible volume de ventes  | `COM`           | Oui                  | 1 (`Z`)          |
| `25390` | Pays-de-Montbenoît       | Commune nouvelle créée le 1er janvier 2025          | `COM`           | Oui                  | 1 (`Z`)          |
| `25303` | Hauterive-la-Fresse      | Ancien code absorbé par `25390` le 1er janvier 2025 | `OLD -> 25390`  | Non                  | 0                |
| `97411` | Saint-Denis (La Réunion) | Outre-mer couvert par DVF                           | `COM`           | Oui                  | 64 (`A,D,H`)     |
| `97611` | Mamoudzou (Mayotte)      | Outre-mer absent de DVF                             | `COM`           | Oui                  | 33 (`A,D,H`)     |

## Référentiels géographiques

### Inventaire COG 2025

| Niveau                                   | Effectif | Détail                                                                            |
| ---------------------------------------- | -------- | --------------------------------------------------------------------------------- |
| Régions (`REG`)                          | 18       | 13 métropolitaines + 5 DROM (`01`, `02`, `03`, `04`, `06`)                        |
| Départements (`DEP`)                     | 101      | 96 métropolitains (dont `2A`, `2B`) + 5 DROM (`971`–`974`, `976`)                 |
| Collectivités territoriales (`CTCD`)     | 100      | Distingue `69D` (Rhône, 208 communes) et `69M` (Métropole de Lyon, 58)            |
| Communes actives (`COM`)                 | 34 875   | Pivot national ; codes chaînes de 5 caractères                                    |
| Arrondissements municipaux (`ARM`)       | 45       | Paris (20), Lyon (9), Marseille (16), reliés à `COMPARENT`                        |
| Communes associées / déléguées           | 2 628    | `COMA` + `COMD`, sous-communes historiques                                        |
| Mouvements historiques (`v_mvt_commune`) | 13 534   | 4 155 anciens codes résolus sans ambiguïté vers un `COM` actif (scissions exclus) |

**Règle de résolution historique :** les mouvements de `v_mvt_commune_2025.csv`
doivent être rejoués **dans l'ordre chronologique (`DATE_EFF`)**, en repliant
également les chaînes intervenant le même jour (ex. `49144 -> 44225 -> 44180` le
1er janvier 2018) :

- un code actif dans COG 2025 (`COM`) n'est **jamais** réattribué (ex. `09277`
  Saint-Ybars a connu une scission en 1949 vers `09342` mais reste actif) ;
- les changements de chef-lieu avec réutilisation d'un ancien code se résolvent
  sans cycle (ex. `49126 -> 49069` en 2015 puis `49069 -> 49126` en 2025 :
  `49069` pointe vers `49126`) ;
- les scissions ambiguës (un code donnant plusieurs cibles à la même date)
  restent non résolues plutôt qu'affectées arbitrairement.

### Contours et pièges de jointure

| Fichier / couche                  | Taille (gz) | Entités | Arrondissements inclus | Remarque                                                    |
| --------------------------------- | ----------- | ------- | ---------------------- | ----------------------------------------------------------- |
| Etalab `communes-100m.geojson.gz` | 8,24 Mo     | 35 014  | 45 (`ARM`)             | 34 875/34 875 `COM` + 45 `ARM` + 94 COM d'outre-mer         |
| Etalab `communes-50m.geojson.gz`  | 17,58 Mo    | 35 014  | 45 (`ARM`)             | Plus fin pour le zoom communal ; `5m` pèse 89,96 Mo         |
| Etalab `departements-100m`        | 0,81 Mo     | 109     | 0                      | Inclut les COM outre-mer : filtrer sur les 101 `DEP` du COG |
| Etalab `regions-100m`             | 0,45 Mo     | 26      | 0                      | Inclut les COM outre-mer : filtrer sur les 18 `REG` du COG  |
| IGN WFS `commune`                 | API WFS     | 34 877  | 0                      | Sépare `commune` et `arrondissement_municipal` (45)         |
| IGN WFS `contours_iris`           | API WFS     | 49 386  | Oui (clé `code_insee`) | Paris/Lyon/Marseille rattachés au code `ARM`, pas `COM`     |

Règles critiques pour [LEM-17](https://linear.app/lemauvaiscoin/issue/LEM-17) :

1. **Séparer `level = 'commune'` et `level = 'arrondissement'` dans la table
   territoriale.** `communes-100m.geojson.gz` contient _à la fois_ `69123`
   (Lyon) et `69381`–`69389` (Lyon 1er–9e). Sans filtre sur `level`, les
   choroplèthes et sommes départementales compteraient Paris, Lyon et Marseille
   deux fois.
2. **Conserver `CTCD` en attribut** sur la table des communes pour distinguer au
   besoin la Métropole de Lyon (`69M`, 58 communes) du Rhône (`69D`, 208
   communes), tout en gardant `DEP = '69'` comme maille départementale standard.
3. **Conserver la table `territory_code_aliases`** issue de `v_mvt_commune_2025`
   (4 155 anciens codes résolus chronologiquement sans ambiguïté) pour convertir
   toute source publiée sur un COG antérieur (CORINE, CatNat dans LEM-7).
4. **Utiliser `communes-100m` (8,2 Mo) pour le socle cartographique**, avec
   `communes-50m` (17,6 Mo) si le zoom fin le justifie ; réserver `contours_iris`
   (49 386 polygones) aux sources réellement au grain IRIS (recensement, Filosofi
   IRIS si approfondi).

## Mesures DVF nationales

### Volumes (2024 – S1 2026)

| Période | Taille gz | Lignes    | `id_mutation` distincts | Lignes / mutation | Bornes de dates          |
| ------- | --------- | --------- | ----------------------- | ----------------- | ------------------------ |
| 2024    | 107,4 Mo  | 3 505 340 | 1 264 967               | 2,77              | 2024-01-01 .. 2024-12-31 |
| 2025    | 116,3 Mo  | 3 793 113 | 1 384 341               | 2,74              | 2025-01-01 .. 2025-12-31 |
| 2026-S1 | 51,7 Mo   | 1 697 942 | 618 766                 | 2,74              | 2026-01-01 .. 2026-06-30 |

Sur la fenêtre complète de 5 ans (juillet 2021 – juin 2026, 609,5 Mo compressés),
cela représente environ **19 à 20 millions de lignes** et **~7 millions de
mutations** (~4 millions de ventes résidentielles monobiens exploitables).

### Complétude des champs (8 996 395 lignes)

| Champ                       | Lignes remplies | Complétude | Lecture                                                    |
| --------------------------- | --------------- | ---------- | ---------------------------------------------------------- |
| `code_commune`              | 8 996 395       | 100,0 %    | Toujours rempli (chaîne 5 caractères)                      |
| `id_parcelle`               | 8 996 395       | 100,0 %    | Clé de jointure Cadastre (14 caractères)                   |
| `adresse_nom_voie`          | 8 947 938       | 99,5 %     | Souvent un lieu-dit en zone rurale                         |
| `valeur_fonciere`           | 8 891 579       | 98,8 %     | Absente sur 1,2 % des lignes (exclusions obligatoires)     |
| `latitude` / `longitude`    | 8 814 182       | 98,0 %     | Géolocalisation parcellaire Etalab                         |
| `surface_terrain`           | 6 183 387       | 68,7 %     | Souvent absente en copropriété (appartements)              |
| `adresse_numero`            | 5 705 601       | 63,4 %     | Absente sur terrains nus et parcelles rurales              |
| `type_local`                | 5 362 506       | 59,6 %     | Vide = terrain nu / non bâti (40,4 % des lignes)           |
| `surface_reelle_bati`       | 5 356 770       | 59,5 %     | Remplie sur les locaux bâtis ; `0` ou vide sur dépendances |
| `nombre_pieces_principales` | 5 356 770       | 59,5 %     | Cohérent avec `surface_reelle_bati`                        |

### Couverture, doublons et validité des codes

| Contrôle                                                               | Mesure          | Détail                                                                                                                          |
| ---------------------------------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Départements couverts                                                  | 97 / 101        | **Absents :** `57` (Moselle), `67` (Bas-Rhin), `68` (Haut-Rhin), `976` (Mayotte)                                                |
| Communes COG 2025 couvertes par DVF                                    | 33 253 / 34 875 | 1 622 communes absentes (Alsace-Moselle + Mayotte)                                                                              |
| Lignes consécutives identiques (mut/disp/parcelle/type/surface/valeur) | 1 401 557       | **15,58 % des lignes** (ventilation DGFiP multi-lots / natures de culture)                                                      |
| `code_commune` dans COG 2025 `COM`                                     | 8 652 217       | 96,17 % des lignes                                                                                                              |
| `code_commune` dans COG 2025 `ARM` (Paris, Lyon, Marseille)            | 342 214         | 3,80 % des lignes : **toujours au code arrondissement**, jamais `COM`                                                           |
| `code_commune` ancien code résolu par `v_mvt_commune_2025`             | 46              | 0,00 % (`49069 -> 49126`, `69159 -> 69114`, `12076 -> 12218`, `49144 -> 44180` ; `25303` déjà rétromappé en `25390` par Etalab) |
| `code_commune` hors COG 2025 / non résolu                              | 1 918           | 0,02 % : uniquement `97127` Saint-Martin (1 566) et `97123` Saint-Barthélemy (352), COM hors 101 départements                   |

**Constat clé sur la commune nouvelle `25390` :** sur la livraison d'octobre 2026,
Etalab a déjà appliqué le COG courant rétroactivement (`25390` compte 115 lignes
en 2024, 188 en 2025 et 28 au S1 2026 ; `25303` en compte 0). Les mutations hors
COG 2025 (`97127`, `97123`, soit 524 mutations en 2025) sont comptées et exclues
avant le calcul des indicateurs nationaux.

## Comptage des ventes et multibiens

Une ligne DVF n'est **jamais** une vente : on observe **2,74 à 2,77 lignes par
`id_mutation`**, et `valeur_fonciere` (le prix global de la disposition) est
répétée sur chaque ligne.

**Piège majeur DGFiP (produit cartésien local × nature de culture) :** sur une
parcelle portant plusieurs subdivisions fiscales (ex. mutation `2025-3` : une
maison de 190 m² / 6 pièces sur `010650000B1705` apparaît deux fois, une ligne
`sols 500 m²` et une ligne `terrains d'agrément 2 452 m²`), compter les lignes
résidentielles classe à tort la vente en multibien et supprime **76 628 ventes
monobiens valides en 2025 (+9,42 % des ventes conservées)**. En regroupant par
signature de local `(id_parcelle, type_local, surface, pièces, lots, adresse)` et
clé de subdivision fiscale `(code_nature_culture, code_nature_culture_speciale,
surface_terrain)` :

- **1 signature de local avec subdivisions fiscales distinctes** : repliée en
  **1 seul bien** (monobien) ;
- **1 signature de local répétée sur la même subdivision fiscale** : **répétition
  ambiguë** (impossible de distinguer 1 doublon DGFiP de 2 logements identiques,
  cf. documentation Cerema `nblocanc`), comptée à part et exclue ;
- **≥ 2 signatures de local distinctes** : vrai **multibien**.

### Répartition par `nature_mutation` (3 268 074 mutations, 2024–S1 2026)

| `nature_mutation`                    | Mutations | Part    | Décision                                         |
| ------------------------------------ | --------- | ------- | ------------------------------------------------ |
| `Vente`                              | 3 075 216 | 94,10 % | **Incluse** dans l'indicateur principal          |
| `Vente en l'état futur d'achèvement` | 135 399   | 4,14 %  | **Séparée** (neuf VEFA, +41 % à +77 % vs ancien) |
| `Echange`                            | 35 282    | 1,08 %  | Exclue                                           |
| `Vente terrain à bâtir`              | 11 426    | 0,35 %  | Exclue du prix au m² bâti                        |
| `Adjudication`                       | 6 293     | 0,19 %  | Exclue (enchères judiciaires, décote atypique)   |
| `Expropriation`                      | 4 458     | 0,14 %  | Exclue                                           |

### Structure des mutations après repli des subdivisions fiscales (2024–S1 2026)

| Catégorie de mutation                                          | Mutations | Part    | Traitement retenu                                              |
| -------------------------------------------------------------- | --------- | ------- | -------------------------------------------------------------- |
| Monobien **Maison** (+ dép./terrain, subdivisions repliées)    | 1 079 323 | 33,03 % | **Retenue** (1 vente = 1 `id_mutation`, segment `Maison`)      |
| Monobien **Appartement** (+ dép./terrain, subdivisions repli.) | 872 839   | 26,71 % | **Retenue** (1 vente = 1 `id_mutation`, segment `Appartement`) |
| Terrain nu / non bâti                                          | 851 297   | 26,05 % | Exclue du prix au m² bâti                                      |
| Dépendance seule (parking, cave, garage)                       | 162 180   | 4,96 %  | Exclue                                                         |
| Local pro / industriel / commercial seul                       | 129 603   | 3,97 %  | Exclue                                                         |
| Mixte (Maison + Appartement ou résidentiel + pro)              | 58 375    | 1,79 %  | Exclue (prix global non ventilable par type)                   |
| Multibien homogène Appartements                                | 56 125    | 1,72 %  | Exclue du prix au m² monobien (immeubles entiers / lots)       |
| Multibien homogène Maisons                                     | 35 117    | 1,07 %  | Exclue du prix au m² monobien (ventes en lot / indivision)     |
| Multi-disposition (`numero_disposition` > 1)                   | 17 242    | 0,53 %  | Exclue (plusieurs prix/actes dans une même `id_mutation`)      |
| Répétition ambiguë (même local et même subdivision fiscale)    | 5 973     | 0,18 %  | Comptée à part et exclue (ambiguïté 1 vs 2 biens identiques)   |

**Règle de comptage des ventes :**

- **Unité de compte :** `1 vente = 1 id_mutation` à disposition unique et commune
  unique résolue au COG 2025.
- **Dépendances rattachées :** un appartement ou une maison vendu avec parking,
  cave ou terrain reste un **monobien** — la `valeur_fonciere` porte sur le lot
  entier (prix de marché réel avec ses annexes) et la surface retenue est la
  `surface_reelle_bati` de l'unique local résidentiel (jamais la surface des
  dépendances, et sans sommer les répétitions de subdivisions fiscales).
- **Multibiens, mixtes et répétitions ambiguës :** exclus du calcul de prix au m²
  (4,62 % des mutations 2025 après repli des subdivisions fiscales) et tracés
  dans les métadonnées d'exclusion.

## Règles de calcul du prix au m²

### Cascade d'exclusions mesurée sur 2025 (France entière, périmètre COG 2025)

| Étape                                                 | Mutations 2025 | Part                    |
| ----------------------------------------------------- | -------------- | ----------------------- |
| Total `id_mutation` 2025                              | 1 384 341      | 100,00 %                |
| Exclues : multi-communes                              | 13 678         | 0,99 %                  |
| Exclues : hors COG 2025 (`97127`, `97123`)            | 524            | 0,04 %                  |
| Exclues : nature hors `Vente` / `VEFA`                | 21 691         | 1,57 %                  |
| Exclues : multi-dispositions                          | 1 156          | 0,08 %                  |
| Exclues : prix manquant ou multiple                   | 47 051         | 3,40 %                  |
| Exclues : prix symbolique (< 1 000 €)                 | 44 963         | 3,25 %                  |
| Exclues : répétition ambiguë du même local            | 2 508          | 0,18 %                  |
| Exclues : multibien ou mixte                          | 61 419         | 4,44 %                  |
| Exclues : non résidentiel (terrains, pro, dép.)       | 364 289        | 26,31 %                 |
| Exclues : surface hors `[9 ; 1 000]` m²               | 453            | 0,03 %                  |
| Mises à part : VEFA monobien (indicateur distinct)    | 7 837          | 0,57 %                  |
| Exclues : prix/m² aberrant hors `[200 ; 35 000]` €    | 4 902          | 0,35 %                  |
| **Conservées : `Vente` résidentielle monobien**       | **813 870**    | **58,79 %**             |
| _dont récupérées par repli des subdivisions fiscales_ | _76 628_       | _9,42 % des conservées_ |

### Distribution nationale 2025 (`Vente` vs `VEFA`)

| Segment                               | Effectif | p01   | p05   | Médiane (p50) | p95    | p99    |
| ------------------------------------- | -------- | ----- | ----- | ------------- | ------ | ------ |
| `Vente` Maison (avant bornes €/m²)    | 460 969  | 238   | 625   | 2 155         | 5 525  | 9 250  |
| `Vente` Maison (propre `[200;35000]`) | 457 360  | 342   | 672   | **2 166**     | 5 526  | 9 156  |
| `VEFA` Maison (propre)                | 261      | 1 267 | 1 821 | **3 827**     | 10 026 | 28 765 |
| `Vente` Appartement (avant bornes)    | 357 803  | 536   | 1 105 | 3 300         | 9 917  | 13 972 |
| `Vente` Appartement (propre)          | 356 510  | 637   | 1 131 | **3 308**     | 9 913  | 13 902 |
| `VEFA` Appartement (propre)           | 7 545    | 2 464 | 3 000 | **4 680**     | 8 145  | 11 117 |

Constats :

- Les bornes `[200 ; 35 000] €/m²` et `[9 ; 1 000] m²` éliminent seulement
  **0,39 %** des 1 384 341 mutations 2025 (453 surfaces + 4 902 prix/m²) tout en
  supprimant les ventes manifestement erronées (ex. `720 000 €/m²` à Paris 11e
  sur le calcul naïf).
- **Séparer systématiquement `Maison` et `Appartement`** (2 166 €/m² vs
  3 308 €/m² au national) et **ne pas mélanger `VEFA` dans `Vente`** (+41 % sur
  les appartements neufs, +77 % sur les maisons neuves).
- **Indicateurs à publier :** médiane €/m² (p50), intervalle interquartile
  (p25–p75), prix médian de vente (€), surface médiane (m²) et effectif `n`
  (nombre de ventes retenues + nombre de mutations exclues).

### Impact du calcul naïf vs calcul nettoyé sur l'échantillon

| Code    | Territoire               | Type        | Lignes naïves 2025 | Médiane naïve (€/m²) | Ventes propres 2025 | Médiane propre 2025 (€/m²) | Ventes 2,5 ans | Médiane 2,5 ans (€/m²) |
| ------- | ------------------------ | ----------- | ------------------ | -------------------- | ------------------- | -------------------------- | -------------- | ---------------------- |
| `69123` | Lyon                     | Appartement | 8 300              | 4 626                | 6 714               | 4 462                      | 15 562         | 4 455                  |
| `69123` | Lyon                     | Maison      | 227                | 5 596                | 187                 | 5 369                      | 406            | 5 520                  |
| `69381` | Lyon 1er                 | Appartement | 545                | 5 201                | 405                 | 4 800                      | 946            | 4 862                  |
| `69381` | Lyon 1er                 | Maison      | 2                  | 4 437                | 2                   | 4 437                      | 7              | 8 263                  |
| `75056` | Paris                    | Appartement | 37 787             | 10 267               | 29 279              | 9 706                      | 68 448         | 9 674                  |
| `75056` | Paris                    | Maison      | 194                | 14 891               | 147                 | 12 564                     | 300            | 12 527                 |
| `75111` | Paris 11e                | Appartement | 3 008              | 10 257               | 2 422               | 9 926                      | 5 742          | 9 857                  |
| `75111` | Paris 11e                | Maison      | 1                  | 720 000              | 0                   | -                          | 1              | 20 000                 |
| `13055` | Marseille                | Appartement | 12 808             | 3 433                | 10 449              | 3 186                      | 24 568         | 3 143                  |
| `13055` | Marseille                | Maison      | 1 687              | 4 797                | 1 430               | 4 670                      | 3 245          | 4 682                  |
| `13205` | Marseille 5e             | Appartement | 1 180              | 3 677                | 956                 | 3 433                      | 2 328          | 3 433                  |
| `13205` | Marseille 5e             | Maison      | 15                 | 4 424                | 14                  | 4 346                      | 35             | 5 405                  |
| `67482` | Strasbourg               | Tous        | 0                  | -                    | 0                   | -                          | 0              | -                      |
| `15219` | Salers                   | Maison      | 4                  | 1 450                | 3                   | 1 000                      | 10             | 739                    |
| `25390` | Pays-de-Montbenoît       | Appartement | 6                  | 2 318                | 4                   | 1 555                      | 7              | 2 426                  |
| `25390` | Pays-de-Montbenoît       | Maison      | 12                 | 3 045                | 8                   | 3 045                      | 20             | 2 533                  |
| `25303` | Hauterive-la-Fresse      | Tous        | 0                  | -                    | 0                   | -                          | 0              | -                      |
| `97411` | Saint-Denis (La Réunion) | Appartement | 1 206              | 2 708                | 996                 | 2 622                      | 2 362          | 2 628                  |
| `97411` | Saint-Denis (La Réunion) | Maison      | 386                | 3 203                | 300                 | 3 136                      | 677            | 3 214                  |
| `97611` | Mamoudzou (Mayotte)      | Tous        | 0                  | -                    | 0                   | -                          | 0              | -                      |

Le calcul naïf par ligne surestime systématiquement le nombre de ventes (+20 à
+30 %) et le prix médian au m² (+8,4 % à Lyon 1er, +18,5 % sur les maisons à
Paris, jusqu'à un aberrant `720 000 €/m²` à Paris 11e).

### Biais de la moyenne de médianes

Vérification directe sur 4 départements en 2025 : recalculer la médiane depuis
les ventes individuelles vs moyenner les médianes communales.

| Dép.  | Type        | Ventes | Communes | Vraie médiane dép. (€/m²) | Moyenne des médianes communales | Biais       |
| ----- | ----------- | ------ | -------- | ------------------------- | ------------------------------- | ----------- |
| `15`  | Maison      | 1 370  | 218      | 1 337                     | 1 268                           | -5,1 %      |
| `15`  | Appartement | 469    | 21       | 1 364                     | 1 152                           | **-15,5 %** |
| `69`  | Maison      | 5 793  | 262      | 3 574                     | 3 119                           | **-12,7 %** |
| `69`  | Appartement | 15 565 | 187      | 3 721                     | 2 862                           | **-23,1 %** |
| `75`  | Maison      | 147    | 1        | 12 564                    | 12 564                          | 0,0 %       |
| `75`  | Appartement | 29 279 | 1        | 9 706                     | 9 706                           | 0,0 %       |
| `974` | Maison      | 2 596  | 24       | 2 806                     | 2 717                           | -3,2 %      |
| `974` | Appartement | 2 101  | 21       | 2 857                     | 2 770                           | -3,0 %      |

Moyenner les médianes communales sous-estime le prix médian départemental de
**23,1 %** sur les appartements du Rhône. **Chaque niveau territorial**
(arrondissement, commune, département, région, national) **doit être agrégé
directement depuis la table des ventes nettoyées.**

## Niveaux fiables et seuils de publication

### Couverture communale par seuil d'effectif (33 253 communes couvertes DVF)

| Fenêtre                | Type        | ≥ 1 vente       | ≥ 5 ventes      | ≥ 10 ventes     | ≥ 15 ventes     | ≥ 20 ventes     | ≥ 30 ventes    |
| ---------------------- | ----------- | --------------- | --------------- | --------------- | --------------- | --------------- | -------------- |
| 1 an (2025)            | Maison      | 30 261 (91,0 %) | 17 796 (53,5 %) | 10 651 (32,0 %) | 7 348 (22,1 %)  | 5 498 (16,5 %)  | 3 527 (10,6 %) |
| 1 an (2025)            | Appartement | 7 011 (21,1 %)  | 3 514 (10,6 %)  | 2 535 (7,6 %)   | 2 030 (6,1 %)   | 1 755 (5,3 %)   | 1 400 (4,2 %)  |
| 2,5 ans (2024–S1 2026) | Maison      | 32 334 (97,2 %) | 25 682 (77,2 %) | 18 855 (56,7 %) | 14 469 (43,5 %) | 11 612 (34,9 %) | 8 176 (24,6 %) |
| 2,5 ans (2024–S1 2026) | Appartement | 8 707 (26,2 %)  | 4 733 (14,2 %)  | 3 598 (10,8 %)  | 3 043 (9,2 %)   | 2 658 (8,0 %)   | 2 184 (6,6 %)  |

### Stabilité empirique de la médiane d'une année sur l'autre (2024 vs 2025)

Variation relative absolue `|p50_2025 - p50_2024| / p50_2024` sur toutes les
communes ayant au moins une vente en 2024 et en 2025, classées selon
`min(n_2024, n_2025)` :

| Type        | Effectif annuel min | Communes | Dérive médiane | Dérive p90 |
| ----------- | ------------------- | -------- | -------------- | ---------- |
| Maison      | `1–4`               | 13 549   | **27,6 %**     | **88,4 %** |
| Maison      | `5–9`               | 5 995    | 15,7 %         | 45,8 %     |
| Maison      | `10–14`             | 2 674    | 10,8 %         | 30,7 %     |
| Maison      | `15–29`             | 3 043    | **8,1 %**      | 22,6 %     |
| Maison      | `30+`               | 2 840    | 4,5 %          | 12,8 %     |
| Appartement | `1–4`               | 2 494    | **17,7 %**     | **63,2 %** |
| Appartement | `5–9`               | 800      | 9,5 %          | 32,4 %     |
| Appartement | `10–14`             | 388      | 7,3 %          | 24,3 %     |
| Appartement | `15–29`             | 576      | **6,1 %**      | 20,1 %     |
| Appartement | `30+`               | 1 231    | 3,2 %          | 10,8 %     |

Ces mesures justifient directement les règles retenues pour [LEM-12](lem-12-synthese.md) et [LEM-19](https://linear.app/lemauvaiscoin/issue/LEM-19) :

1. **Niveaux publiés :** `national`, `region` (18), `departement` (101, dont 97
   couverts DVF et 4 explicitement marqués « hors DVF »), `commune` (34 875) et
   `arrondissement` (45 pour Paris, Lyon et Marseille). Pas d'indicateur DVF au
   grain IRIS ni au bâtiment individuel dans le socle initial.
2. **Seuils d'effectif justifiés par la courbe de stabilité :**
   - **`n < 5` ventes :** ne pas publier de prix médian au m² (dérive médiane
     annuelle de 27,6 % en maisons et p90 de 88,4 %). Afficher uniquement
     l'effectif `n` et le statut « effectif insuffisant ».
   - **`5 ≤ n < 15` ventes :** publier la médiane avec un badge « faible
     effectif » (dérive médiane encore entre 10,8 % et 15,7 % en maisons) et
     proposer la vue pluriannuelle (24–36 mois) ou le niveau départemental.
   - **`n ≥ 15` ventes :** publication normale avec effectif `n` et quartiles
     Q25–Q75 — c'est le palier où la dérive médiane annuelle passe sous 10 %
     pour les deux segments (8,1 % maisons, 6,1 % appartements), tout en
     couvrant 43,5 % des communes en maisons sur 2,5 ans.
3. **Zones non couvertes :** distinguer explicitement **« hors périmètre DVF »**
   (`57`, `67`, `68`, `976` — aucune donnée publiée par la DGFiP) de **« 0 vente
   sur la période »** ou **« effectif insuffisant »**.
4. **Fenêtre recommandée par défaut dans l'explorateur :** proposer **année
   civile** (2022, 2023, 2024, 2025) pour l'évolution temporelle et une
   **fenêtre glissante 24 ou 36 mois** en vue territoriale pour porter la
   couverture communale maisons (`n ≥ 5`) à plus de 77 % (contre 53,5 % sur 1 an
   seul).
