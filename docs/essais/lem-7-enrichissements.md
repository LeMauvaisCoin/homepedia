# LEM-7 — Sources d'enrichissement territorial

Essai pour [LEM-7](https://linear.app/lemauvaiscoin/issue/LEM-7). Il mesure,
sur un même échantillon de territoires, toutes les sources candidates qui
enrichissent les communes au-delà des ventes : énergie, revenus, population,
économie, logement, équipements, éducation, santé, sécurité, infrastructures,
risques et environnement. Le sujet demande « at least a dozen data sources, and
a maximum of 50 » sur ces thèmes. Les conclusions alimentent
[LEM-12](https://linear.app/lemauvaiscoin/issue/LEM-12) ; l'intégration est
suivie dans [LEM-18](https://linear.app/lemauvaiscoin/issue/LEM-18).

Hors périmètre, car suivis ailleurs : ventes DVF et géographie
([LEM-6](https://linear.app/lemauvaiscoin/issue/LEM-6)), urbanisme textuel
([LEM-5](https://linear.app/lemauvaiscoin/issue/LEM-5)), annonces
([LEM-8](https://linear.app/lemauvaiscoin/issue/LEM-8)), flux temps réel
([LEM-10](https://linear.app/lemauvaiscoin/issue/LEM-10)) et Belgique
([LEM-44](https://linear.app/lemauvaiscoin/issue/LEM-44)).

## Reproduire les mesures

Quatre scripts autonomes, lancés avec `uv run`. Ils n'utilisent que des API
publiques sans clé et des fichiers ouverts, et écrivent leurs tableaux
Markdown sur la sortie standard. Les fichiers téléchargés sont mis en cache
dans `.cache/lem-7/` (1,2 Go, ignoré par Git). Mesures du 13 novembre 2026.

| Script                                  | Thèmes                                                          |
| --------------------------------------- | --------------------------------------------------------------- |
| `scripts/essais/lem_7.py`               | Énergie, revenus, équipements, risques Géorisques               |
| `scripts/essais/lem_7_population.py`    | Recensement, entreprises, logement                              |
| `scripts/essais/lem_7_services.py`      | Éducation, santé, délinquance, fibre, recharge, transports, eau |
| `scripts/essais/lem_7_environnement.py` | Argiles, inondation, trait de côte, sols, air, climat           |

## Échantillon

Neuf codes du Code officiel géographique (COG) au 1er janvier 2025, choisis
pour tester les jointures difficiles. Il peut servir aussi à LEM-6.

| Code    | Territoire               | Ce qu'il teste                                       |
| ------- | ------------------------ | ---------------------------------------------------- |
| `69123` | Lyon                     | Commune à arrondissements, grande ville              |
| `69381` | Lyon 1er                 | Code d'arrondissement municipal                      |
| `75056` | Paris                    | Commune à arrondissements, capitale                  |
| `75111` | Paris 11e                | Code d'arrondissement municipal                      |
| `67482` | Strasbourg               | Alsace-Moselle, absente des fichiers DVF             |
| `15219` | Salers                   | Commune rurale de 310 habitants (secret statistique) |
| `25390` | Pays-de-Montbenoît       | Commune nouvelle créée le 1er janvier 2025           |
| `25303` | Hauterive-la-Fresse      | Ancien code absorbé par `25390`                      |
| `97411` | Saint-Denis (La Réunion) | Département d'outre-mer                              |

## Synthèse

36 ressources mesurées ou vérifiées. **25 retenues**, 9 à approfondir,
2 écartées. Une famille compte une fois, même avec plusieurs ressources ou
millésimes. Les familles retenues ajoutent environ 20 familles au socle DVF,
COG, BAN et cadastre, dans la cible de 15 à 20 familles du cahier des charges
et sous le maximum de 50 du sujet.

| Thème           | Ressource                                                                                                                                                                                                                             | Grain                         | Période                   | Décision      | Motif principal                                                                                  |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | ------------------------- | ------------- | ------------------------------------------------------------------------------------------------ |
| Énergie         | [DPE logements existants](https://data.ademe.fr/datasets/dpe03existant) (ADEME)                                                                                                                                                       | Logement diagnostiqué         | Depuis juillet 2021       | Retenue       | National, DOM compris, étiquette toujours remplie. Biais : seuls les logements diagnostiqués.    |
| Énergie         | [BDNB](https://www.data.gouv.fr/datasets/base-de-donnees-nationale-des-batiments) `batiment_groupe_complet` (CSTB)                                                                                                                    | Groupe de bâtiments           | Millésime 2026-02         | À approfondir | Rien à La Réunion, classe DPE vide en zone rurale, export de 36,7 Go.                            |
| Énergie         | [Consommation d'électricité et de gaz par commune](https://www.data.gouv.fr/datasets/65f1185fd7321d8e647ba548) (Agence ORE)                                                                                                           | Commune × filière × secteur   | 2011 à 2025               | Retenue       | DOM compris. Grain arrondissement jusqu'en 2017, commune ensuite.                                |
| Revenus         | Filosofi `DS_FILOSOFI_CC` (INSEE, API Melodi)                                                                                                                                                                                         | Commune, arrondissement       | 2023                      | Retenue       | Médiane du niveau de vie partout. Seules 2 mesures sur 27 publiées à la commune.                 |
| Revenus         | Filosofi à l'IRIS ou carroyé à 200 m (INSEE)                                                                                                                                                                                          | IRIS, carreau                 | Selon millésime           | À approfondir | Utile pour comparer des quartiers. Non mesuré.                                                   |
| Revenus         | Impôt sur le revenu par commune, IRCOM (DGFiP)                                                                                                                                                                                        | Commune                       | Selon millésime           | Écartée       | Redondant avec Filosofi. Non mesuré.                                                             |
| Population      | Recensement `DS_RP_POPULATION_PRINC`, `DS_RP_LOGEMENT_PRINC`, `DS_RP_EMPLOI_LR_PRINC` (INSEE, API Melodi)                                                                                                                             | Commune, arrondissement, IRIS | 2012, 2017, 2023          | Retenue       | 812 observations par territoire, aucune manquante, DOM compris.                                  |
| Économie        | Stocks et créations d'entreprises `DS_SIDE_STOCKS_COM`, `DS_SIDE_CREA_COM` (INSEE)                                                                                                                                                    | Commune, arrondissement       | 2014-2024, 2012-2025      | Retenue       | Aucune valeur manquante, vrais zéros.                                                            |
| Économie        | [Base SIRENE](https://www.data.gouv.fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret) (INSEE)                                                                                                           | Établissement                 | Mise à jour mensuelle     | À approfondir | Utile pour localiser des commerces (question des franchises). Parquet de 2,2 Go, non téléchargé. |
| Logement        | [Logements vacants du parc privé, LOVAC](https://www.data.gouv.fr/datasets/logements-vacants-du-parc-prive-en-france-et-par-commune-departement-region)                                                                               | Commune, arrondissement       | 2020 à 2026               | Retenue       | Fichier de 7,6 Mo. Secret noté `s` pour 9 395 communes en 2025.                                  |
| Logement        | [Carte des loyers 2025](https://www.data.gouv.fr/datasets/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025)                                                                                                        | Commune, arrondissement       | 2025                      | Retenue       | 34 900 communes, mais 30 029 estimées sur une zone plus large que la commune.                    |
| Logement        | [Sitadel, autorisations créant des logements](https://www.data.gouv.fr/datasets/liste-des-permis-de-construire-et-autres-autorisations-durbanisme) (SDES, API DiDo)                                                                   | Autorisation                  | 2013 à septembre 2026     | Retenue       | Exclure les annulations ; surface 0 à traiter comme absente.                                     |
| Logement        | RPLS, logements sociaux détaillés (SDES, API DiDo)                                                                                                                                                                                    | Logement social               | 1er janvier 2025          | Retenue       | Toujours rempli sauf le DPE, absent à 100 % à La Réunion.                                        |
| Logement        | [RNIC, registre des copropriétés](https://www.data.gouv.fr/datasets/registre-national-dimmatriculation-des-coproprietes)                                                                                                              | Copropriété                   | 3e trimestre 2025         | Retenue       | Deux colonnes de code commune différentes, à choisir selon le niveau.                            |
| Équipements     | Base permanente des équipements `DS_BPE` (INSEE)                                                                                                                                                                                      | Commune × type d'équipement   | 2025                      | Retenue       | Complète, sans valeur manquante.                                                                 |
| Éducation       | IPS des écoles `fr-en-ips-ecoles-ap2022` (Éducation nationale)                                                                                                                                                                        | École                         | 2024-2025                 | Retenue       | 97 080 lignes, IPS manquant pour 2 écoles sur 67 à Strasbourg.                                   |
| Éducation       | IPS des collèges `fr-en-ips-colleges-ap2023`                                                                                                                                                                                          | Collège                       | 2025-2026                 | Retenue       | Aucun IPS manquant dans l'échantillon.                                                           |
| Éducation       | Valeur ajoutée des lycées généraux `fr-en-indicateurs-de-resultat-des-lycees-gt_v2`                                                                                                                                                   | Lycée                         | 2025                      | Retenue       | Le zéro est une vraie valeur (« conforme à l'attendu »).                                         |
| Éducation       | Brevet par établissement `fr-en-dnb-par-etablissement`                                                                                                                                                                                | Collège                       | Dernière session 2021     | Écartée       | La série s'arrête en 2021.                                                                       |
| Santé           | [Accessibilité aux médecins généralistes, APL](https://data.drees.solidarites-sante.gouv.fr/explore/dataset/530_l-accessibilite-potentielle-localisee-apl/) (DREES)                                                                   | Commune, arrondissement       | 2022 à 2024               | Retenue       | 34 890 communes, aucune valeur manquante, Mayotte absente.                                       |
| Santé           | [FINESS, établissements](https://www.data.gouv.fr/datasets/finess-extraction-du-fichier-des-etablissements)                                                                                                                           | Établissement                 | Extraction du 4 mai 2026  | Retenue       | Code INSEE à reconstituer depuis département et commune.                                         |
| Sécurité        | [Délinquance enregistrée par commune](https://www.data.gouv.fr/datasets/bases-statistiques-communale-departementale-et-regionale-de-la-delinquance-enregistree-par-la-police-et-la-gendarmerie-nationales) (ministère de l'Intérieur) | Commune × indicateur          | 2016 à 2025               | Retenue       | 15 indicateurs. Près de la moitié des valeurs 2025 non diffusées.                                |
| Infrastructures | [Fibre, déploiements par commune](https://www.data.gouv.fr/datasets/le-marche-du-haut-et-tres-haut-debit-fixe-deploiements) (Arcep)                                                                                                   | Commune, arrondissement       | 2e trimestre 2026         | Retenue       | 34 919 communes. Taux à calculer, la colonne `couv` est une classe.                              |
| Infrastructures | [Bornes de recharge, IRVE](https://www.data.gouv.fr/datasets/fichier-consolide-des-bornes-de-recharge-pour-vehicules-electriques)                                                                                                     | Point de charge               | 12 novembre 2026          | À approfondir | Code commune vide pour 44 % des points : rattacher par coordonnées.                              |
| Infrastructures | [Arrêts de transport en France](https://www.data.gouv.fr/datasets/arrets-de-transport-en-france)                                                                                                                                      | Arrêt                         | Export du 13 janvier 2026 | À approfondir | Pas de code commune : jointure spatiale nécessaire. Lien avec LEM-10.                            |
| Environnement   | Qualité de l'eau distribuée (API Hub'Eau)                                                                                                                                                                                             | Commune × prélèvement         | Continu                   | Retenue       | Mesures « sous la limite » codées 0 : garder la valeur texte.                                    |
| Risques         | Géorisques `gaspar/risques`                                                                                                                                                                                                           | Commune                       | Continu                   | À approfondir | Liste déclarative : 2 risques à Paris, 17 à Lyon.                                                |
| Risques         | Géorisques CatNat (API et [extrait GASPAR](https://files.georisques.fr/GASPAR/gaspar.zip))                                                                                                                                            | Commune × arrêté              | Depuis 1982               | Retenue       | 247 140 arrêtés, 582 rattachés à d'anciens codes.                                                |
| Risques         | Géorisques `radon`                                                                                                                                                                                                                    | Commune, arrondissement       | Zonage en vigueur         | Retenue       | Contredit le rapport Géorisques pour Lyon : à clarifier avant publication.                       |
| Risques         | Inondation : TRI, AZI, PPRN (API Géorisques et extrait GASPAR)                                                                                                                                                                        | Commune                       | 2 novembre 2026           | Retenue       | Commune seulement ; anciens codes présents dans l'extrait.                                       |
| Risques         | Retrait-gonflement des argiles (rapport Géorisques par commune)                                                                                                                                                                       | Commune                       | 2026                      | Retenue       | Statut communal disponible sans compte. Exposition fine : carte de 122 Mo.                       |
| Risques         | [Recul du trait de côte](https://www.data.gouv.fr/datasets/indicateur-national-de-lerosion-cotiere-inec-mise-a-jour-2026-taux-devolution-du-trait-de-cote-1) : liste du décret 2026-95                                                | Commune                       | 2026                      | Retenue       | 371 communes. Les taux de recul INEC (284 Mo) restent à approfondir.                             |
| Environnement   | [CORINE Land Cover, statistiques par commune](https://www.statistiques.developpement-durable.gouv.fr/media/2546/download) (SDES)                                                                                                      | Commune (COG 2010)            | 1990 à 2018               | Retenue       | Découpage de 2010 : 1 015 codes à convertir.                                                     |
| Environnement   | OCS GE (IGN)                                                                                                                                                                                                                          | Polygone                      | Selon région              | À approfondir | Extraits régionaux seulement sur data.gouv.                                                      |
| Environnement   | Qualité de l'air, stations LCSQA                                                                                                                                                                                                      | Station                       | Horaire                   | À approfondir | Aucune station à Salers ni à Pays-de-Montbenoît ; pas d'indice national par commune.             |
| Climat          | Projections DRIAS, Explore2 (Météo-France)                                                                                                                                                                                            | Maille, territoire            | Horizons futurs           | À approfondir | DRIAS demande un compte. Le cahier des charges n'engage aucune prévision climatique.             |

## Règles communes

Ces règles valent pour toutes les sources retenues.

1. **Convertir les codes au COG courant avant d'agréger.** Les sources ne
   suivent pas la même règle :
   - au code d'arrondissement pour Paris et Lyon : DPE, BDNB, radon, LOVAC,
     loyers, RPLS, Éducation nationale, APL, FINESS, Arcep, IRVE ;
   - au code de commune seulement : risques GASPAR, CatNat, inondation,
     argiles, Sitadel, Hub'Eau, ORE depuis 2018 ;
   - les deux : INSEE Melodi, délinquance, RNIC (une colonne chacun).
2. **Rattacher les anciens codes.** Le DPE, l'ORE, CatNat, GASPAR, Sitadel et
   CORINE répondent encore sur d'anciens codes (`25303`). L'API Melodi et la
   plupart des fichiers récents les refusent. CORINE est au COG 2010. Utiliser
   la table des mouvements de communes de l'INSEE.
3. **Garder l'absence distincte du zéro.** Une valeur absente reste `NULL`, un
   zéro reste `0`, une valeur non diffusée est affichée « non diffusé ».

| Source                | Valeur zéro                                            | Donnée absente ou non diffusée                         |
| --------------------- | ------------------------------------------------------ | ------------------------------------------------------ |
| DPE                   | Aucune consommation nulle observée                     | Pas de DPE : parc non diagnostiqué, pas un zéro        |
| ORE                   | Aucune consommation nulle observée                     | Maille secrétisée (618 à Paris en 2025)                |
| Filosofi              | Sans objet                                             | `OBS_STATUS = O` ; taux de pauvreté secret à Salers    |
| BPE                   | Pas de ligne : zéro équipement de ce type              | Erreur 400 sur un ancien code : pas un zéro            |
| Entreprises INSEE     | Vrai zéro (1 086 à Salers)                             | Aucune valeur manquante                                |
| LOVAC                 | Vrai zéro                                              | `s` : secret statistique                               |
| Sitadel               | Surface 0 avec logements créés : à lire comme absent   | -                                                      |
| Délinquance           | 222 776 vrais zéros en 2025                            | `est_diffuse = ndiff`, `nombre = NA` : 251 145 valeurs |
| APL                   | 523 communes à 0 : aucune offre accessible             | Aucune valeur manquante                                |
| Valeur ajoutée lycées | 0 : résultat conforme à l'attendu                      | Champ vide                                             |
| Hub'Eau               | `resultat_numerique = 0` pour « < limite » : faux zéro | Garder `resultat_alphanumerique`                       |
| CORINE                | 78 227 surfaces nulles réelles                         | Classe `CLC_9` « pas de donnée » outre-mer             |
| Argiles (point)       | -                                                      | Réponse vide : absence de donnée ou d'aléa, ambiguë    |

## Résultats par thème

### Énergie

- **DPE.** 16 003 705 lignes, dont 527 695 (3,3 %) sans `code_insee_ban`.
  Lyon : 61 DPE au code commune, 13 424 au seul 1er arrondissement.
  L'étiquette, la consommation par m² et le point géocodé sont toujours
  remplis ; `annee_construction` manque dans 24 % (Lyon 1er) à 75 %
  (Paris 11e) des cas. Les étiquettes suivent le bâti : Salers n'a que des D à
  G, Strasbourg a des A.
- **BDNB.** La classe DPE manque dans 20 % (Lyon 1er) à 100 % (Salers,
  Pays-de-Montbenoît) des groupes de bâtiments ; rien pour Saint-Denis. Compter
  les lignes d'une grande commune et lire l'échantillon dans la même requête
  échoue (erreur 500 après 10 secondes à Strasbourg).
- **ORE.** Arrondissements de 2011 à 2017, commune depuis 2018 : la série de
  Paris et Lyon change de grain. Aucune consommation nulle.

### Revenus, population et économie

- **Filosofi 2023.** Médianes de 20 240 € (Saint-Denis) à 34 270 €
  (Paris 11e). Les 25 autres mesures (déciles, prestations) ne sont pas
  publiées à la commune.
- **Recensement.** Logements vacants 14,5 % à Salers, 12,1 % à Paris 11e ;
  chômage 25,3 % à Saint-Denis, 15,5 % à Strasbourg. Environ 280 valeurs sur
  285 sont des estimations pondérées non entières : arrondir à l'affichage.
- **Entreprises.** 560 409 établissements à Paris en 2024, 84 à Salers ;
  119 767 créations à Paris en 2025.

### Logement

- **LOVAC.** 34 912 communes, aucune valeur vide. Le parc privé total s'arrête
  à 2025 : pas de taux de vacance 2026.
- **Carte des loyers.** 31,72 €/m² à Paris 11e, 7,76 €/m² à Salers. Salers
  n'a que 46 annonces : son loyer est estimé sur une zone de 799 annonces.
  Loyer d'annonce charges comprises, pas loyer signé.
- **Sitadel.** 1 941 999 autorisations. Paris : 3 822 autorisations
  (2 259 autorisées, 113 annulées, 876 commencées, 574 terminées) ; surface
  habitable à 0 dans 2 080 cas. L'API répond « 400 Le fichier est vide. »
  quand aucune ligne ne correspond.
- **RPLS.** 5 416 826 logements sociaux. Étiquette DPE manquante pour 4 à 10 %
  des logements en métropole.
- **RNIC.** 619 402 copropriétés. La colonne `commune` mélange arrondissements
  et commune ; `code_officiel_commune` est toujours à la commune ; 476 codes
  `commune` n'ont pas 5 caractères.

### Équipements, éducation, santé et sécurité

- **BPE 2025.** 31 types d'équipement à Pays-de-Montbenoît, 220 à Paris.
- **Éducation.** Le champ `ips` est stocké en texte ; le taux de réussite du
  brevet aussi (`"78,30%"`).
- **APL 2024.** De 1,33 (Pays-de-Montbenoît) à 6,53 (Strasbourg)
  consultations par an et par habitant. Moyenne à pondérer par la population
  standardisée.
- **FINESS.** 102 939 établissements, fichier sans en-tête avec deux types de
  lignes. Départements d'outre-mer codés `9A` à `9F`.
- **Délinquance.** 5 238 000 lignes, géographie 2026. Salers : 9 indicateurs
  sur 15 non diffusés.

### Infrastructures

- **Arcep.** Strasbourg : 180 662 locaux raccordables à la fibre sur 194 462.
  Fichier en shapefile, lu en latin-1.
- **IRVE.** 169 279 points de charge ; code commune vide pour 73 880,
  non vérifié pour 79 455. Aucun point à Saint-Denis par le code commune, mais
  129 points dans un rectangle autour de la ville par les coordonnées.
- **Arrêts.** 457 777 arrêts issus de 418 jeux GTFS, fichier de 437 Mo.

### Risques et environnement

- **Géorisques.** Rapport communal sans compte : argiles « important » à Paris,
  « modéré » ailleurs en métropole. La recherche argiles par code commune
  demande un compte (`401 Inscription gratuite obligatoire`). Le radon donne
  la classe 1 pour Lyon 1er alors que le rapport indique « important ».
- **Extrait GASPAR.** Zip de 8 Mo : 247 140 arrêtés CatNat sur 34 699 communes,
  32 798 plans de prévention. Les territoires à risque important d'inondation
  ne sont que dans l'API.
- **Trait de côte.** Seule Saint-Denis est concernée dans l'échantillon ; le
  décret et le rapport Géorisques concordent.
- **CORINE.** Saint-Denis : 3 478 ha artificialisés en 2018. Les années 2000 à
  2012 apparaissent deux fois (version d'origine et révisée). `25390` ne couvre
  que l'ancienne commune de Montbenoît.
- **Air.** 510 stations actives ; stations trouvées par nom de commune :
  Paris 13, Strasbourg 4, Lyon 3, Saint-Denis 2.
- **Eau.** Paris : 51 723 résultats en 2025, Salers : 85.

## Volumes et coûts nationaux

Estimation sans collecte exhaustive. France : 34 875 communes au
1er janvier 2025. Toutes les sources sont gratuites.

| Source                                  | Volume brut                                      | Après agrégation par commune                                                             |
| --------------------------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| DPE                                     | 16 003 705 lignes, 230 colonnes                  | Environ 250 000 lignes (7 étiquettes)                                                    |
| ORE                                     | 3 787 334 lignes, CSV de 794 Mo                  | Moins de 100 000 lignes en résidentiel                                                   |
| Filosofi, recensement, BPE, entreprises | API Melodi, de 27 à 812 observations par commune | De 1 à 28 millions d'observations brutes, quelques centaines de milliers après sélection |
| LOVAC, loyers, APL, Arcep               | Moins de 35 Mo chacun, une ligne par commune     | 35 000 lignes chacun                                                                     |
| Sitadel, RPLS                           | 1,9 et 5,4 millions de lignes (API DiDo)         | Agrégats par commune et par année                                                        |
| RNIC                                    | 619 402 lignes, 453 Mo                           | 35 000 lignes                                                                            |
| Éducation, FINESS                       | 21 000 à 140 000 établissements                  | Garder les établissements géolocalisés                                                   |
| Délinquance                             | 5 238 000 lignes, 40 Mo compressés               | Identique, déjà par commune                                                              |
| GASPAR                                  | Zip de 8 Mo                                      | Identique                                                                                |
| CORINE                                  | CSV de 22 Mo                                     | 35 000 lignes par millésime                                                              |
| Hub'Eau                                 | Zip annuels de 230 à 290 Mo, ou API              | Indicateurs de conformité par commune                                                    |
| BDNB, SIRENE, arrêts, INEC, IRVE        | De 118 Mo (IRVE) à 36,7 Go (BDNB)                | Traitement distribué à prévoir (LEM-13)                                                  |

Après agrégation, les sources retenues tiennent en quelques millions de lignes,
compatible avec le budget de 50 USD par mois de
[LEM-34](https://linear.app/lemauvaiscoin/issue/LEM-34). Le coût réel est le
temps de collecte des API appelées commune par commune (Géorisques, DiDo,
Hub'Eau), dont les quotas n'ont pas été vérifiés. Les gros fichiers (BDNB,
SIRENE, arrêts, DPE complet) sont les candidats naturels au traitement PySpark
de LEM-13.

## Décisions encore ouvertes

- Choisir entre le radon de l'API et le rapport communal Géorisques, qui se
  contredisent pour Lyon.
- Retenir ou non les jointures spatiales (IRVE, arrêts, INEC, argiles fines,
  air) : elles demandent les contours communaux de LEM-17.
- Décider si la question « risque à 15 ans » justifie un compte DRIAS ou
  Explore2, contre le cahier des charges actuel.
- Vérifier les licences et quotas de chaque source retenue avant
  l'intégration (contrat source de LEM-18).
