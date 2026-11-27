# LEM-5 — Extraction des documents d'urbanisme

Essai pour [LEM-5](https://linear.app/lemauvaiscoin/issue/LEM-5). Il teste, sur
un corpus identifié de documents d'urbanisme, ce qui peut être extrait de façon
fiable : texte, passages classés par zone et par thème, champs structurés
(hauteur maximale, emprise au sol, stationnement) et couches géographiques du
Géoportail de l'Urbanisme. Il compare la lecture du PDF, l'OCR et une analyse
du texte par règles, sans fixer la sortie finale. Les conclusions alimentent
[LEM-12](https://linear.app/lemauvaiscoin/issue/LEM-12) et débloquent
[LEM-22](https://linear.app/lemauvaiscoin/issue/LEM-22).

Hors périmètre, car suivis ailleurs : sources chiffrées d'enrichissement
([LEM-7](https://linear.app/lemauvaiscoin/issue/LEM-7)), ventes DVF et
géographie ([LEM-6](https://linear.app/lemauvaiscoin/issue/LEM-6)), contours
communaux et jointures spatiales
([LEM-17](https://linear.app/lemauvaiscoin/issue/LEM-17)).

## Critères d'acceptation

| Critère                                                            | Où il est rempli                                                                                   |
| ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| Identifier les documents et expliquer le choix de l'échantillon    | [Corpus](#corpus), y compris RNU et carte communale                                                |
| Comparer texte extrait, passages classés, informations structurées | [Synthèse](#synthèse) et [Résultats par sortie](#résultats-par-sortie), dont les couches GPU       |
| Échantillon annoté, erreurs mesurées par sortie                    | [Échantillon annoté](#échantillon-annoté) : jeux `dev` et `test` séparés, précision et rappel      |
| Conserver document, version, page et passage                       | Chaque annotation et chaque sortie portent fichier, identifiant et version GPU, page et texte      |
| Recommander corpus, méthode et niveau de détail, avec limites      | [Recommandation pour LEM-12](#recommandation-pour-lem-12), [Licence et quotas](#licence-et-quotas) |

## Reproduire les mesures

Trois scripts autonomes, lancés avec `uv run` dans cet ordre. Ils n'utilisent
que des API publiques sans clé (API et WFS du Géoportail de l'Urbanisme, API
Géo) et écrivent leurs tableaux Markdown sur la sortie standard. PDF, modèle OCR
et pages OCR sont mis en cache dans `.cache/lem-5/` (ignoré par Git). Premier
lancement : environ 10 minutes, surtout l'OCR. Mesures du 27 novembre 2026.

| Fichier                                | Sorties testées                                                         |
| -------------------------------------- | ----------------------------------------------------------------------- |
| `scripts/essais/lem_5.py`              | Couverture GPU, corpus, texte (PyMuPDF, pypdf, OCR), scans tournés      |
| `scripts/essais/lem_5_reglement.py`    | Passages classés, champs structurés, précision et rappel par jeu        |
| `scripts/essais/lem_5_gpu.py`          | Zonage et prescriptions (WFS), RNU, carte communale, en-têtes de quotas |
| `scripts/essais/lem_5_annotations.csv` | Échantillon annoté : 191 lignes, colonne `split` (`dev` ou `test`)      |

L'OCR utilise le moteur Tesseract intégré à PyMuPDF et le modèle
`fra.traineddata` de `tessdata_best`, à 300 dpi. Aucun appel à un modèle de
langage.

## Corpus

### Couverture de l'échantillon partagé

Codes de l'échantillon de LEM-7, interrogés sur l'API du
[Géoportail de l'Urbanisme](https://www.geoportail-urbanisme.gouv.fr/) (GPU),
documents publiés et en vigueur.

| Code    | Territoire               | Document d'urbanisme en vigueur                     | Remarque                                  |
| ------- | ------------------------ | --------------------------------------------------- | ----------------------------------------- |
| `69123` | Lyon                     | PLUi de la Métropole (`200046977_PLUi_20261103`)    | Rien au code commune : chercher l'EPCI    |
| `69381` | Lyon 1er                 | Aucun                                               | Le GPU ne connaît pas les arrondissements |
| `75056` | Paris                    | PLU (`75056_PLU_20260616`), 2 PSMV, 1 SUP           |                                           |
| `75111` | Paris 11e                | Aucun                                               | Idem Lyon 1er                             |
| `67482` | Strasbourg               | PLUi de l'Eurométropole (`246700488_PLUi_20261001`) | Rien au code commune : chercher l'EPCI    |
| `15219` | Salers                   | PLU (`15219_PLU_20250428`)                          |                                           |
| `25390` | Pays-de-Montbenoît       | PLU (`25390_PLU_20220624`)                          | PLU de l'ancienne commune de Montbenoît   |
| `25303` | Hauterive-la-Fresse      | Aucun                                               | Ancien code : passer par `25390`          |
| `97411` | Saint-Denis (La Réunion) | PLU (`97411_PLU_20260805`)                          |                                           |

### Communes sans PLU

Deux communes réelles, hors échantillon, choisies dans les couches
`wfs_du:municipality` (`is_rnu`) et `wfs_du:doc_urba` (`typedoc = 'CC'`) :

| Code    | Commune               | Cas                                 | Ce que la chaîne renvoie                                                                     |
| ------- | --------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------- |
| `25002` | Abbans-Dessus         | Règlement national d'urbanisme      | Aucun document ; `is_rnu = true` ; la recherche par EPCI répond `HTTP 400`                   |
| `01002` | L'Abergement-de-Varey | Carte communale `01002_CC_20071207` | Trois PDF (rapport, liste des SUP, notice sanitaire), aucun règlement écrit : rien à classer |

Une commune au RNU suit les règles nationales : rien à extraire, afficher « RNU »
d'après `is_rnu`. Une carte communale n'a pas de règlement écrit : seuls ses
secteurs constructibles (`wfs_du:secteur_cc`) sont exploitables. La recherche
par EPCI ne doit servir qu'aux communes où `is_rnu` est faux.

### Documents retenus

Neuf fichiers, 1 588 pages. Le nom de version GPU (`originalName`) porte la date
d'approbation ; l'identifiant GPU change à chaque nouveau dépôt, le script
signale si le document épinglé est toujours celui en vigueur.

| Commune     | Fichier                                                      | Version GPU                    | Pages | Ce qu'il teste                                                        |
| ----------- | ------------------------------------------------------------ | ------------------------------ | ----- | --------------------------------------------------------------------- |
| Salers      | `15219_reglement_20250428.pdf`                               | `15219_PLU_20250428`           | 90    | Petit PLU Word, ancienne structure en 14 articles par zone            |
| Montbenoît  | `25390_reglement_20220624.pdf`                               | `25390_PLU_20220624`           | 48    | Petit PLU, structure modernisée en 9 articles                         |
| Montbenoît  | `25390_liste_des_servitudes_d_utilite_publique_20220624.pdf` | `25390_PLU_20220624`           | 34    | Annexe scannée (arrêtés préfectoraux de 2015) : OCR                   |
| Saint-Denis | `97411_reglement_20260805.pdf`                               | `97411_PLU_20260805`           | 154   | Outre-mer, tableaux, secteurs, annexes scannées et tournées           |
| Paris       | `75056_reglement_20260616.pdf`                               | `75056_PLU_20260616`           | 250   | Grand PLU bioclimatique, renvois aux documents graphiques             |
| Paris       | `EL7_PassageSaintSebastien18a26_19330114_act.pdf`            | `217500016_EL7_75056_20211214` | 2     | Servitude d'alignement : arrêté dactylographié de 1933 scanné         |
| Paris       | `EL7_QuaiDeSeine39_19990423_act.pdf`                         | `217500016_EL7_75056_20211214` | 3     | Même servitude : arrêté de 1999 scanné                                |
| Strasbourg  | `246700488_reglement_20261001.pdf`                           | `246700488_PLUi_20261001`      | 204   | PLUi, règles communes au titre II, valeurs par secteur                |
| Lyon        | `200046977_reglement_20261103.pdf`                           | `200046977_PLUi_20261103`      | 803   | Très gros PLUi, normes de stationnement en partie I, hauteurs en plan |

Pourquoi cet échantillon : il reprend les communes de LEM-7, couvre trois
tailles de document (48 à 803 pages), deux structures de règlement (ancienne en
14 articles, modernisée depuis 2016), un département d'outre-mer, deux PLUi et
trois scans d'époques différentes pour juger l'OCR. Pour chaque PLU, le
règlement écrit porte les règles ; le zonage et les prescriptions sont lus dans
les couches du GPU. Les OAP et les PSMV ne sont pas testés.

## Échantillon annoté

`scripts/essais/lem_5_annotations.csv`, une ligne par annotation avec jeu,
fichier, identifiant et version GPU, page du PDF (numérotée à partir de 1, pas
le numéro imprimé), zone, étiquette, valeur attendue et passage.

| Sortie    | `dev` | `test` | Contenu                                                                  |
| --------- | ----- | ------ | ------------------------------------------------------------------------ |
| `text`    | 12    | 5      | Passage transcrit depuis l'image de la page, comparé à chaque extracteur |
| `passage` | 34    | 35     | Ligne tirée au hasard, avec zone et thème attendus                       |
| `field`   | 54    | 51     | Zone ou secteur × champ, avec valeur attendue et passage justificatif    |

- **`dev`** : les règles ont été écrites, puis corrigées une fois, sur ce jeu.
  Ses scores sont optimistes.
- **`test`** : jeu tenu à l'écart. Pages tirées avec une autre graine (11), hors
  pages `dev` et hors pages de sommaire ; 17 zones ou secteurs absents de `dev`.
  Annoté et commité (`3d83399`) avant tout passage des règles ; règles non
  modifiées après lecture des scores. Lignes écartées comme en `dev` : en-têtes
  de page, pages sans ligne de texte.

Valeurs attendues pour les champs : un nombre (mètres, pourcentage, places par
logement), ou un statut :

| Statut           | Sens                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| `graphique`      | La valeur est sur le règlement graphique                             |
| `renvoi`         | La valeur est ailleurs dans le texte (dispositions générales, titre) |
| `relatif`        | Règle sans valeur (hauteur des voisins, prospect, existant)          |
| `niveaux`        | Hauteur exprimée en niveaux (R+2+C), sans mètres                     |
| `non_chiffre`    | Stationnement « selon les besoins »                                  |
| `non_reglemente` | Le texte dit explicitement que la règle n'est pas fixée              |
| `absent`         | Le texte de la zone ne traite pas le sujet                           |

La hauteur attendue est la plus haute cote absolue de la règle générale (le
faîtage quand égout et faîtage sont donnés), hors secteurs particuliers.

**Les annotations ont été faites par un agent, pas par un instructeur
d'urbanisme.** Une vérification humaine par sondage reste recommandée.

## Synthèse

Les chiffres `test` sont la mesure à retenir ; `dev` sert de comparaison.

| Sortie                   | Méthode                 | `dev`                                                                   | `test`                              | Verdict                                     |
| ------------------------ | ----------------------- | ----------------------------------------------------------------------- | ----------------------------------- | ------------------------------------------- |
| Texte, pages natives     | PyMuPDF                 | 6/7 exacts, 100 % des mots                                              | 2/4 exacts, 100 % des mots          | Fiable ; ordre perdu dans certains tableaux |
| Texte, pages natives     | OCR Tesseract           | 2/7 exacts, 80 % des mots                                               | 2/4 exacts, 100 % des mots          | Inutile quand la couche texte existe        |
| Texte, scans             | OCR Tesseract           | 4/5 exacts, 98 % des mots                                               | 1/1 exact                           | Fiable pour chercher, à relire pour citer   |
| Passages, zone           | Titres et en-têtes      | 33/34                                                                   | 34/35                               | Fiable                                      |
| Passages, thème          | Mots-clés               | 24/34 ; précision 78 %, rappel 69 %                                     | 28/35 ; précision 83 %, rappel 81 % | Suffisant pour chercher, pas pour décider   |
| Champs structurés        | Expressions régulières  | 37/54 justes (69 %)                                                     | 30/51 justes (59 %)                 | Non fiable                                  |
| Champs, nombres affichés | Expressions régulières  | précision 61 %, rappel 82 %                                             | précision 63 %, rappel 57 %         | Dangereux : 7 à 9 faux nombres par jeu      |
| Zonage GPU               | WFS `zone_urba`         | 48/49 zones annotées (`dev` et `test`) retrouvées en libellé ou préfixe | (jeux confondus)                    | Fiable, structuré, versionné                |
| Hauteurs du plan         | WFS `prescription_surf` | Strasbourg seulement : 1 334 polygones avec valeur                      | (jeux confondus)                    | Utilisable là où il existe                  |

Précision des nombres : part des nombres affichés qui sont justes. Rappel : part
des nombres attendus retrouvés.

## Résultats par sortie

### Texte extrait

- **Couche texte.** Les 6 règlements sont des PDF natifs. PyMuPDF et pypdf
  rendent les mêmes mots ; PyMuPDF lit les 803 pages de Lyon en 2 s, pypdf en
  14 s. Les passages non exacts sont des lignes de tableau : les mots sont là,
  dans un autre ordre (Saint-Denis pages 19 et 34).
- **OCR sur pages natives.** 83 à 99 % des mots retrouvés ; aucun mot utile sur
  le petit tableau de Lyon page 277 (`[ee||] endenprseaussr`).
- **OCR sur scans.** Arrêtés de 1999 et 2015 : passages exacts. Arrêté
  dactylographié de 1933 : 88 % des mots (« observetion », « préséntée »).
  Environ 4 s par page.
- **Scans tournés.** Saint-Denis finit par 7 pages d'annexes scannées, dont 6
  tournées de 90°. PyMuPDF ne donne ni confiance ni détection d'orientation
  Tesseract : le script lit chaque page dans les 4 orientations et garde celle
  dont les mots existent le plus dans le texte natif du document. Résultat :
  6 pages passent de 0 à 21 % de mots reconnus à 60 à 72 % (une page à 32 %),
  toutes avec la rotation de 90° ; la page de garde reste droite. Le passage
  « ordures ménagères » de la page 150 n'apparaît qu'une fois la page tournée.
  Coût : 4 lectures OCR par page sans texte.

### Passages classés

Chaque ligne reçoit la zone et le thème en vigueur, d'après les titres
d'article (`ARTICLE UA 10`, `Article 10 UAA :`, `Article Ud.10`, `UG.3.2`,
`2.5 -`), les en-têtes de page (`Zone UCe1`) et des mots-clés de thème.

| Thème         | Précision `dev` | Rappel `dev` | Précision `test` | Rappel `test` |
| ------------- | --------------- | ------------ | ---------------- | ------------- |
| aspect        | 75 %            | 86 %         | 88 %             | 78 %          |
| autre         | 60 %            | 43 %         | 60 %             | 60 %          |
| desserte      | 100 %           | 100 %        | 100 %            | 50 %          |
| destination   | 67 %            | 80 %         | 80 %             | 100 %         |
| emprise       | -               | -            | 100 %            | 100 %         |
| hauteur       | 100 %           | 50 %         | 100 %            | 75 %          |
| implantation  | 100 %           | 75 %         | 100 %            | 100 %         |
| paysage       | 100 %           | 67 %         | 50 %             | 100 %         |
| stationnement | 25 %            | 50 %         | 67 %             | 67 %          |
| **Moyenne**   | **78 %**        | **69 %**     | **83 %**         | **81 %**      |

Les effectifs par thème sont petits (1 à 9 lignes) : un écart de 20 points
correspond souvent à une seule ligne. Erreurs typiques : passages sans titre
de thème (caractère de la zone, figures, annexes), règles alternatives de
hauteur rangées sous un titre « aspect », annexe de risques de Montbenoît
rattachée à la dernière zone.

### Champs structurés

| Champ, jeu            | Justes    | Nombres affichés | Précision nombres | Rappel nombres | Précision statuts | Rappel statuts |
| --------------------- | --------- | ---------------- | ----------------- | -------------- | ----------------- | -------------- |
| Emprise, `dev`        | 13/18     | 7                | 57 %              | 80 %           | 82 %              | 69 %           |
| Hauteur, `dev`        | 11/18     | 11               | 45 %              | 71 %           | 86 %              | 55 %           |
| Stationnement, `dev`  | 13/18     | 5                | 100 %             | 100 %          | 62 %              | 62 %           |
| **Total `dev`**       | **37/54** | **23**           | **61 %**          | **82 %**       | **74 %**          | **62 %**       |
| Emprise, `test`       | 11/17     | 9                | 67 %              | 67 %           | 62 %              | 62 %           |
| Hauteur, `test`       | 8/17      | 9                | 56 %              | 50 %           | 38 %              | 43 %           |
| Stationnement, `test` | 11/17     | 1                | 100 %             | 50 %           | 62 %              | 67 %           |
| **Total `test`**      | **30/51** | **19**           | **63 %**          | **57 %**       | **56 %**          | **60 %**       |

- **Le nombre est rarement dans le texte de la zone.** En `dev`, 17 valeurs
  attendues sur 54 sont des nombres ; en `test`, 21 sur 51. Les autres renvoient
  à une autre partie du texte, au règlement graphique, ou n'existent pas.
- **Petits PLU : bon résultat, grandes villes : non.** Erreurs `test`
  marquantes : une hauteur en tableau par secteur (Saint-Denis `Upr`, `Upi`)
  lue comme un renvoi ; une zone `AUh` dont les articles s'écrivent `Auh`,
  donc introuvable ; « deux places » écrit en lettres (Salers `Nh`) ; à Lyon,
  « 5 % » de tolérance d'extension affiché comme emprise.
- **Faux nombres.** 9 sur 54 en `dev`, 7 sur 51 en `test` : un utilisateur ne
  peut pas les distinguer des vrais.

### Couches géographiques du GPU

Couches du WFS de la Géoplateforme (`https://data.geopf.fr/wfs/ows`,
`wfs_du:*`), filtrées par partition (`DU_<grille>`).

| Règlement   | Polygones de zone | Libellés | Libellés présents dans le texte | Zones annotées retrouvées | Valeurs utiles dans les prescriptions                               |
| ----------- | ----------------- | -------- | ------------------------------- | ------------------------- | ------------------------------------------------------------------- |
| Salers      | 42                | 19       | 19/19                           | 8/8                       | Aucune                                                              |
| Montbenoît  | 25                | 10       | 10/10                           | 7/7                       | Aucune                                                              |
| Saint-Denis | 259               | 33       | 33/33                           | 8/8                       | Aucune                                                              |
| Paris       | 1 153             | 4        | 4/4                             | 4/4                       | 4 092 polygones « Emprise au sol maximale », sans valeur dans `txt` |
| Strasbourg  | 2 433             | 105      | 96/105                          | 9/10 (préfixe)            | 1 334 polygones « Hauteur maximale » avec valeur (`7mET`, `12mHT`…) |
| Lyon        | 4 487             | 92       | 65/92                           | 12/12 (préfixe)           | Aucune ; les étiquettes du plan sont des secteurs de mixité sociale |

- **Zonage.** Chaque polygone porte libellé, type (`U`, `AUc`, `AUs`, `A`, `N`),
  version (`idurba`) et, sauf à Saint-Denis et Strasbourg, le nom du fichier de
  règlement (`nomfic`). Les libellés du plan sont souvent des secteurs (`UB1`,
  `UCA4`) d'une zone du texte (`UB`, `UCA`) : rapprocher par préfixe. Seul
  `IAUXZAA` (Strasbourg) n'a pas d'équivalent : le plan écrit `IAUX.zaa`.
- **Versions.** `idurba` vaut l'`originalName` de l'API, casse comprise
  (`PLUI` contre `PLUi`). À Lyon, l'identifiant `gpu_doc_id` du WFS diffère de
  celui de l'API : joindre par partition et `idurba`, pas par identifiant.
- **Valeurs renvoyées au plan.** Sur les 12 annotations `graphique` (`dev` et
  `test`), les 5 de Strasbourg ont une valeur dans les prescriptions
  (`typepsc = 39`). Paris et Lyon n'ont pas de hauteur typée dans le GPU. Le
  rattachement d'une parcelle à une valeur demande une jointure spatiale
  (LEM-17), non mesurée ici.

### Licence et quotas

Vérifié le 27 novembre 2026.

- **Données d'urbanisme** : [Licence ouverte Etalab](https://www.etalab.gouv.fr/wp-content/uploads/2014/05/Licence_Ouverte.pdf),
  d'après les [CGU du GPU](https://www.geoportail-urbanisme.gouv.fr/cgu/)
  (modifiées le 28 mars 2019, section 3). Réutilisation libre, avec mention de
  la source et de la date de mise à jour.
- **API REST du GPU** (`/api/document`) : aucun quota écrit dans les CGU, aucun
  en-tête de limite renvoyé. Appeler avec retenue et mettre en cache.
- **WFS Géoplateforme** : 30 requêtes par seconde par adresse IP, d'après la
  [fiche de l'API WFS](https://www.data.gouv.fr/dataservices/api-geoplateforme-diffusion-dobjets-wfs)
  et les en-têtes `ratelimit-limit: 30`, `x-ratelimit-limit-second: 1`. 5 000
  objets au plus par requête : paginer avec `startIndex` et `sortBy`.

## Recommandation pour LEM-12

**Corpus.** Le règlement écrit (`Pieces_ecrites/3_Reglement`) des PLU et PLUi en
vigueur, par l'API du GPU : `api/document?grid=<code commune>`, puis
`grid=<SIREN de l'EPCI>` si la commune n'a pas de document et que `is_rnu` est
faux. Convertir arrondissements et anciens codes en commune courante. Pour
chaque passage : identifiant et version GPU, fichier, page, texte. Ajouter le
zonage `wfs_du:zone_urba` (libellé, type, `idurba`) et, là où elles existent,
les prescriptions de hauteur. Communes au RNU et cartes communales : afficher
le statut, rien à extraire.

**Méthode.** PyMuPDF pour la couche texte ; OCR Tesseract français seulement
pour les pages sans texte, en essayant les 4 orientations. Découpage en
passages par titres et en-têtes, thème par mots-clés. Rapprochement zone du
texte – polygone par libellé ou préfixe de libellé.

**Niveau de détail exploitable.** Le passage cité par zone et par thème
(zone juste 34 fois sur 35, thème 28 fois sur 35 en `test`), et le zonage du
GPU comme donnée structurée. Ne pas publier de champ chiffré extrait du texte
par règles : en `test`, 37 % des nombres affichés sont faux et 43 % des
nombres attendus manquent. Afficher le statut (« fixé au règlement
graphique », « renvoi aux dispositions générales ») avec le passage.

**Limites.**

- Six règlements, 191 annotations faites par un agent ; effectifs par thème et
  par champ petits (intervalles larges).
- Une seule version par document ; stabilité des identifiants GPU non suivie.
- OAP et PSMV (qui priment dans leur périmètre à Paris, Lyon et Strasbourg) non
  testés. Hauteurs de Paris et Lyon absentes des couches GPU : seules les
  pièces graphiques PDF les portent.
- La « hauteur maximale » n'a pas de définition unique (égout, faîtage, façade,
  hors tout, niveaux) : une sortie structurée doit garder la référence de mesure
  (`ET`, `HT` à Strasbourg).
- Une extraction par modèle de langage, avec citation obligatoire du passage,
  reste à tester sur le jeu `test`, élargi, avant toute adoption.

## Décisions encore ouvertes

- Faire relire un sondage des annotations par une personne qui connaît
  l'urbanisme : au moins les 105 valeurs de champs et 20 passages.
- Choisir de tester ou non une extraction par modèle de langage, en fonction du
  budget de [LEM-34](https://linear.app/lemauvaiscoin/issue/LEM-34).
