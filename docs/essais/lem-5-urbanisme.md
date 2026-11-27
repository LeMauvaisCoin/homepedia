# LEM-5 — Extraction des documents d'urbanisme

Essai pour [LEM-5](https://linear.app/lemauvaiscoin/issue/LEM-5). Il teste, sur
un corpus identifié de documents d'urbanisme, ce qui peut être extrait de façon
fiable : texte, passages classés par zone et par thème, et quelques champs
structurés (hauteur maximale, emprise au sol, stationnement). Il compare la
lecture du PDF, l'OCR et une analyse du texte par règles, sans fixer la sortie
finale. Les conclusions alimentent
[LEM-12](https://linear.app/lemauvaiscoin/issue/LEM-12) et débloquent
[LEM-22](https://linear.app/lemauvaiscoin/issue/LEM-22).

Hors périmètre, car suivis ailleurs : sources chiffrées d'enrichissement
([LEM-7](https://linear.app/lemauvaiscoin/issue/LEM-7)), ventes DVF et
géographie ([LEM-6](https://linear.app/lemauvaiscoin/issue/LEM-6)), contours
communaux ([LEM-17](https://linear.app/lemauvaiscoin/issue/LEM-17)). Les
couches géographiques du Géoportail de l'Urbanisme (zonage, prescriptions,
servitudes en polygones) ne sont pas mesurées ici : l'essai porte sur les pièces
écrites.

## Reproduire les mesures

Deux scripts autonomes, lancés avec `uv run`, dans cet ordre. Ils n'utilisent
que des API publiques sans clé (Géoportail de l'Urbanisme, API Géo) et écrivent
leurs tableaux Markdown sur la sortie standard. Les PDF, le modèle OCR français
et les pages OCR sont mis en cache dans `.cache/lem-5/` (43 Mo, ignoré par Git).
Premier lancement : environ 5 minutes, dont 4 d'OCR ; ensuite quelques
secondes. Mesures du 27 novembre 2026.

| Fichier                                | Sorties testées                                             |
| -------------------------------------- | ----------------------------------------------------------- |
| `scripts/essais/lem_5.py`              | Couverture GPU, corpus, texte extrait (PyMuPDF, pypdf, OCR) |
| `scripts/essais/lem_5_reglement.py`    | Passages classés (zone, thème), champs structurés           |
| `scripts/essais/lem_5_annotations.csv` | Échantillon annoté : 100 lignes, référence des deux scripts |

L'OCR utilise le moteur Tesseract intégré à PyMuPDF et le modèle
`fra.traineddata` de `tessdata_best`, à 300 dpi. Aucun appel à un modèle de
langage.

## Corpus

### Couverture de l'échantillon partagé

Les codes de l'échantillon de LEM-7 ont été interrogés sur l'API du
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

Aucune commune de l'échantillon n'est au règlement national d'urbanisme (RNU).
Une commune au RNU n'a pas de document local dans le GPU : rien à extraire, les
règles nationales s'appliquent. Les cartes communales n'ont pas de règlement
écrit. Ces deux cas ne sont pas dans l'échantillon.

### Documents retenus

Neuf fichiers, 1 588 pages. Le nom de version GPU (`originalName`) porte la date
d'approbation ; l'identifiant GPU change à chaque nouveau dépôt, le script
signale donc si le document épinglé est toujours celui en vigueur.

| Commune     | Fichier                                                      | Version GPU                    | Pages | Ce qu'il teste                                                        |
| ----------- | ------------------------------------------------------------ | ------------------------------ | ----- | --------------------------------------------------------------------- |
| Salers      | `15219_reglement_20250428.pdf`                               | `15219_PLU_20250428`           | 90    | Petit PLU Word, ancienne structure en 14 articles par zone            |
| Montbenoît  | `25390_reglement_20220624.pdf`                               | `25390_PLU_20220624`           | 48    | Petit PLU, structure modernisée en 9 articles                         |
| Montbenoît  | `25390_liste_des_servitudes_d_utilite_publique_20220624.pdf` | `25390_PLU_20220624`           | 34    | Annexe scannée (arrêtés préfectoraux de 2015) : OCR                   |
| Saint-Denis | `97411_reglement_20260805.pdf`                               | `97411_PLU_20260805`           | 154   | Outre-mer, tableaux, secteurs, annexes scannées en fin de fichier     |
| Paris       | `75056_reglement_20260616.pdf`                               | `75056_PLU_20260616`           | 250   | Grand PLU bioclimatique, renvois aux documents graphiques             |
| Paris       | `EL7_PassageSaintSebastien18a26_19330114_act.pdf`            | `217500016_EL7_75056_20211214` | 2     | Servitude d'alignement : arrêté dactylographié de 1933 scanné         |
| Paris       | `EL7_QuaiDeSeine39_19990423_act.pdf`                         | `217500016_EL7_75056_20211214` | 3     | Même servitude : arrêté de 1999 scanné                                |
| Strasbourg  | `246700488_reglement_20261001.pdf`                           | `246700488_PLUi_20261001`      | 204   | PLUi, règles communes au titre II, valeurs par secteur                |
| Lyon        | `200046977_reglement_20261103.pdf`                           | `200046977_PLUi_20261103`      | 803   | Très gros PLUi, normes de stationnement en partie I, hauteurs en plan |

Pourquoi cet échantillon : il reprend les communes de LEM-7 pour rester
comparable, couvre trois tailles de document (48 à 803 pages), deux structures
de règlement (ancienne en 14 articles, modernisée depuis 2016), un département
d'outre-mer, deux PLUi intercommunaux et trois scans d'époques différentes pour
juger l'OCR. Seul le règlement écrit est pris pour chaque PLU : c'est la pièce
qui porte les règles. Le règlement graphique (plans) et les orientations
d'aménagement ne sont pas testés.

## Échantillon annoté

`scripts/essais/lem_5_annotations.csv` contient 100 lignes, chacune avec
fichier, identifiant et version GPU, page du PDF (numérotée à partir de 1, pas
le numéro imprimé) et passage :

- `text` (12) : passage transcrit depuis l'image de la page, comparé à chaque
  extracteur. 5 sur des scans, 7 sur des pages natives choisies difficiles
  (listes à puces, tableaux, cellules fusionnées).
- `passage` (34) : ligne tirée au hasard (graine fixe, 6 pages par règlement),
  avec la zone et le thème attendus. Deux tirages écartés (une ligne de
  sommaire, un en-tête de page).
- `field` (54) : 18 zones ou secteurs (3 par règlement) × 3 champs, avec la
  valeur attendue et le passage qui la justifie.

Valeurs attendues pour les champs : un nombre (mètres, pourcentage, places par
logement), ou un statut quand le texte ne donne pas de nombre :

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
d'urbanisme.** Elles demandent une vérification humaine par sondage avant de
servir de référence (voir la dernière section).

## Synthèse

| Sortie                               | Méthode                           | Mesure                                                                  | Verdict                                        |
| ------------------------------------ | --------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------- |
| Texte, pages natives                 | PyMuPDF                           | 6/7 passages exacts, 100 % des mots ; 803 pages en 2 s                  | Fiable                                         |
| Texte, pages natives                 | pypdf                             | Mêmes mots que PyMuPDF ; 7 fois plus lent                               | Fiable, sans intérêt face à PyMuPDF            |
| Texte, pages natives                 | OCR Tesseract                     | 2/7 exacts, 80 % des mots ; 0 % sur un petit tableau ; 1 à 4 s par page | À éviter quand la couche texte existe          |
| Texte, scans                         | OCR Tesseract                     | 4/5 passages exacts, 98 % des mots                                      | Fiable pour la recherche, pas pour citer       |
| Passages classés, zone               | Règles (titres, en-têtes de page) | 33/34 lignes                                                            | Fiable                                         |
| Passages classés, thème              | Mots-clés des titres              | 24/34 lignes ; 20/34 zone et thème au premier essai                     | Utilisable pour chercher, pas pour décider     |
| Champs structurés                    | Expressions régulières            | 37/54 justes (31 % d'erreur) ; 24/54 au premier essai                   | Non fiable sans validation humaine             |
| Champs structurés, valeurs chiffrées | Expressions régulières            | 14/17 nombres attendus trouvés, mais 9 nombres faux affichés sur 54     | Dangereux : un faux nombre ressemble à un vrai |

## Résultats par sortie

### Texte extrait

- **Couche texte.** Les 6 règlements sont des PDF natifs (Word, Acrobat,
  pilotes d'impression). PyMuPDF et pypdf rendent les mêmes mots sur les pages
  comparées ; PyMuPDF lit les 803 pages de Lyon en 2 s, pypdf en 14 s.
- **Pages sans texte dans un PDF natif.** Saint-Denis finit par 7 pages
  d'annexes scannées et tournées de 90° (périmètres de captage) : sans OCR,
  elles sont perdues ; l'OCR testé ne redresse pas les pages tournées.
  Strasbourg a 12 pages vides ou presque.
- **Ordre de lecture.** Sur les pages natives, le seul passage non exact est
  une ligne de tableau à cellule fusionnée (Saint-Denis, page 19) : les mots
  sont là, dans un autre ordre. Lyon place le tableau des coefficients d'emprise
  (page 277) après le texte qui le suit sur la page.
- **OCR sur pages natives.** 83 à 99 % des mots retrouvés selon le document.
  Sur le petit tableau de Lyon, l'OCR ne restitue aucun mot utile
  (`[ee||] endenprseaussr`). L'OCR n'apporte rien quand la couche texte existe.
- **OCR sur scans.** Arrêtés de 1999 et 2015 : passages exacts. Arrêté
  dactylographié de 1933 : 88 % des mots (« observetion », « préséntée »). La
  liste des servitudes de Montbenoît (34 pages, 32 scannées) se lit en
  4 s par page.

### Passages classés

Chaque ligne reçoit la zone et le thème en vigueur, d'après les titres
d'article (`ARTICLE UA 10`, `Article 10 UAA :`, `Article Ud.10`, `UG.3.2`,
`2.5 -`), les en-têtes de page (`Zone UCe1`) et dix thèmes par mots-clés
(destination, implantation, emprise, hauteur, aspect, paysage, stationnement,
desserte, autre).

- **Zone : 33/34.** L'erreur restante est une page de sommaire ignorée
  (Strasbourg page 9). Au premier essai : 27/34, à cause des sommaires, d'un
  en-tête `Zone URm 1` écrit avec une espace, et des annexes de figures placées
  après la dernière zone (Paris) qui héritaient de la zone N.
- **Thème : 24/34.** Les erreurs viennent des passages sans titre de thème :
  caractère de la zone, figures, coefficient de biotope, performances
  énergétiques, règles alternatives de hauteur rangées sous un titre
  « aspect ». Paris fait 2/5 : ses figures et son préambule de zone sont pris
  pour du stationnement.
- **Traçabilité.** Chaque ligne garde fichier, version, page et texte : un
  passage restitué peut toujours être vérifié dans le PDF.

### Champs structurés

| Champ                | Annotations | Justes | Taux d'erreur | Nombres attendus | Nombres trouvés | Nombres faux affichés |
| -------------------- | ----------- | ------ | ------------- | ---------------- | --------------- | --------------------- |
| Emprise au sol (%)   | 18          | 13     | 28 %          | 5                | 4               | 3                     |
| Hauteur maximale (m) | 18          | 11     | 39 %          | 7                | 5               | 6                     |
| Places par logement  | 18          | 13     | 28 %          | 5                | 5               | 0                     |
| **Total**            | 54          | 37     | 31 %          | 17               | 14              | 9                     |

- **Le nombre est rarement dans le texte de la zone.** Sur 54 valeurs
  attendues, 17 seulement sont des nombres. Les autres renvoient à une autre
  partie du texte (11) ou au règlement graphique (8), ou n'existent pas sous
  forme chiffrée (18). À Paris, Lyon et Strasbourg, les hauteurs sont sur le plan des
  hauteurs ; les normes de stationnement sont dans les dispositions communes,
  par secteur de stationnement (Lyon) ou par périmètre I à V (Strasbourg) :
  elles dépendent d'une autre carte que le zonage.
- **Petits PLU : bon résultat.** Salers et Montbenoît : 16/18 justes. Les deux
  erreurs sont des hauteurs dont le faîtage est coupé par un saut de page.
- **Grandes villes : erreurs graves.** Lyon : 2/9. L'extraction affiche « 5 % »
  d'emprise (une tolérance d'extension) au lieu de « non réglementé », et des
  hauteurs de gabarit secondaire au lieu de « graphique ».
- **Valeurs par secteur.** Les tableaux et listes de secteurs (`URi1a ≤ 40 %`,
  `UB1 : 75 %`) se lisent quand le secteur est nommé sur la même ligne.
  Strasbourg UD affiche 65 %, valeur du seul périmètre « Ceinture verte », au
  lieu du renvoi aux règles communes.

Les règles ont été corrigées une fois après le premier passage, sur ce même
échantillon (titres sur deux lignes, sommaires, sortie des chapitres de zone,
secteurs). Les scores finaux sont donc optimistes ; ceux du premier passage
sont donnés à titre de comparaison.

## Recommandation pour LEM-12

**Corpus.** Le règlement écrit (`Pieces_ecrites/3_Reglement`) des PLU et PLUi en
vigueur, récupéré par l'API du GPU : `api/document?grid=<code commune>`, puis
`grid=<SIREN de l'EPCI>` (champ `codeEpci` de l'API Géo) si la commune n'a pas de
document propre. Convertir arrondissements et anciens codes en commune courante
avant la requête. Conserver pour chaque passage l'identifiant GPU, le nom de
version (`originalName`), le nom du fichier, la page du PDF et le texte. Les
servitudes d'utilité publique sont surtout des scans d'actes : passer par leurs
données géographiques plutôt que par leurs PDF (non mesuré ici).

**Méthode.** Couche texte avec PyMuPDF pour toutes les pages ; OCR Tesseract en
français seulement pour les pages sans texte (scans, annexes). Découpage en
passages par règles (zone par titres et en-têtes, thème par mots-clés), qui se
transpose d'un règlement à l'autre sans réglage par document au-delà des motifs
de titres listés dans le script.

**Niveau de détail exploitable.** Le passage cité : « pour la zone UB de tel
PLU, voici les passages sur la hauteur, page 79 ». La zone est fiable, le thème
suffit pour chercher et afficher avec la source. Ne pas publier de champ chiffré
(hauteur, emprise, stationnement) extrait automatiquement : 9 nombres faux sur
54, et dans les grandes villes la vraie valeur n'est pas dans le texte. Afficher
au mieux le statut (« fixé au règlement graphique », « renvoi aux dispositions
générales ») avec le passage.

**Limites.**

- Six règlements, 100 annotations faites par un agent, règles ajustées sur le
  même échantillon : les taux sont indicatifs, pas des garanties.
- Une seule version par document ; aucune mesure de la stabilité des
  identifiants GPU dans le temps.
- Le règlement graphique, les OAP et les PSMV (présents à Paris, Lyon et
  Strasbourg, qui priment dans leur périmètre) ne sont pas testés. Or ils
  portent une grande part des valeurs chiffrées.
- La « hauteur maximale » n'a pas de définition unique (égout, faîtage, façade,
  hors tout, niveaux) : toute sortie structurée devra garder l'unité de mesure.
- Une extraction par modèle de langage, avec citation obligatoire du passage,
  reste à tester. Elle devra être mesurée sur ce même fichier d'annotations,
  agrandi, avant toute adoption.

## Décisions encore ouvertes

- Faire relire par une personne qui connaît l'urbanisme un sondage des
  annotations : au moins les 54 valeurs de champs et 10 passages.
- Mesurer les couches géographiques du GPU (zonage, prescriptions de hauteur,
  secteurs de stationnement) : elles pourraient donner les valeurs que le texte
  renvoie au règlement graphique.
- Choisir de tester ou non une extraction par modèle de langage, en fonction du
  budget de [LEM-34](https://linear.app/lemauvaiscoin/issue/LEM-34).
- Vérifier la licence et les quotas de l'API du GPU avant collecte nationale.
