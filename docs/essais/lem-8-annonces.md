# LEM-8 — Sources d'annonces immobilières

Essai pour [LEM-8](https://linear.app/lemauvaiscoin/issue/LEM-8). Il recense
les portails d'annonces candidats, leurs conditions d'accès et de réutilisation,
puis mesure un échantillon sur les seules sources qui l'autorisent. Les
conclusions alimentent [LEM-12](https://linear.app/lemauvaiscoin/issue/LEM-12)
et la collecte de [LEM-23](https://linear.app/lemauvaiscoin/issue/LEM-23).

Hors périmètre, car suivis ailleurs : ventes réalisées DVF
([LEM-6](https://linear.app/lemauvaiscoin/issue/LEM-6)), indicateurs de loyers
par commune comme la carte des loyers
([LEM-7](lem-7-enrichissements.md)), flux temps réel
([LEM-10](https://linear.app/lemauvaiscoin/issue/LEM-10)) et Belgique
([LEM-44](https://linear.app/lemauvaiscoin/issue/LEM-44)).

## Conclusion

**Aucun grand portail commercial n'est collectable légalement par robot.**
Leboncoin l'interdit dans son `robots.txt` ; PAP et EtreProprio l'interdisent
dans leurs CGU ; SeLoger, Logic-Immo, Leboncoin, PAP, Figaro Immobilier,
Ouest-France Immo et EtreProprio servent une page anti-robot (DataDome ou
Cloudflare) dès la première requête, y compris sur leurs CGU. Contourner ces
protections est exclu. Les annonces forment des bases de données protégées par
le droit du producteur (articles L341-1 et L342-1 du Code de la propriété
intellectuelle), et les portails font condamner les extractions non autorisées.

La seule source d'annonces individuelles retenue est le site des
[cessions immobilières de l'État](https://cessions.immobilier-etat.gouv.fr/),
sous Licence Ouverte 2.0. Elle sert à construire et tester la chaîne de LEM-23
(dates, statut, retrait, localisation), pas à représenter le marché : environ
240 biens publics, prix rarement affiché.

Pour le marché privé, LEM-23 doit passer par un accord : partenariat ou licence
avec un portail, flux de quelques agences, ou dépôt d'annonces par les
utilisateurs. Les indicateurs agrégés d'annonces (carte des loyers,
observatoires locaux des loyers) restent la seule mesure ouverte de l'offre.
Crawl4AI n'a pas été utilisé : aucun portail ne le permettait.

## Décision de l'équipe

Le 27 novembre 2026, après cet essai, l'équipe a sorti le scraping de
portails et les annonces immobilières du périmètre principal (décision notée
dans [LEM-12](https://linear.app/lemauvaiscoin/issue/LEM-12)). Le socle
s'appuie sur les données ouvertes : ventes DVF, enrichissements territoriaux et
indicateurs de loyers d'annonce. [LEM-23](https://linear.app/lemauvaiscoin/issue/LEM-23)
et [LEM-30](https://linear.app/lemauvaiscoin/issue/LEM-30) restent en bonus
éventuel, à reprendre uniquement via sources ouvertes ou partenariat. Les
sections suivantes servent de référence si ce bonus est repris.

Le sujet Epitech (page 3) tolère le scraping de sites qui l'interdisent dans
leurs CGU, pour un usage académique et non commercial, tout en demandant de
privilégier les données ouvertes et de documenter les choix de collecte. Cette
tolérance n'engage pas les portails et ne change pas la décision.

## Reproduire les mesures

Deux scripts autonomes, lancés avec `uv run`. Ils écrivent leurs tableaux
Markdown sur la sortie standard et gardent leurs téléchargements dans
`.cache/lem-8/` (moins de 2 Mo, ignoré par Git). Mesures du 27 novembre 2026.

| Script                         | Contenu                                                                                    |
| ------------------------------ | ------------------------------------------------------------------------------------------ |
| `scripts/essais/lem_8.py`      | `robots.txt` et page de CGU de 14 portails, jeux BailleurVérif et Yanport sur data.gouv.fr |
| `scripts/essais/lem_8_etat.py` | Échantillon poli des cessions de l'État : 3 pages de liste et 22 fiches                    |

Règles suivies par les scripts : agent `homepedia-lem-8`, une requête toutes
les 2 à 3 secondes, une seule tentative par page, aucun contournement de page
anti-robot, aucune connexion. `lem_8_etat.py` ne garde que les champs du bien :
le bloc « Gestionnaire de l'annonce », les noms, téléphones et courriels sont
retirés avant l'écriture du cache. Aucune page brute n'est versionnée.

Le site des cessions de l'État n'envoie pas son certificat intermédiaire. Les
scripts utilisent `truststore` (vérificateur du système, qui le récupère) ; la
vérification TLS reste active. Sous Linux, ajouter le certificat intermédiaire
Sectigo au magasin du système si la connexion échoue.

## Portails candidats

`robots.txt` et CGU consultés le 27 novembre 2026. « Anti-robot » signifie que
la page a renvoyé un défi DataDome ou Cloudflare à une requête simple : la page
n'a pas été lue, et ces CGU restent à lire dans un navigateur par un humain.

| Portail                                                                                                                                                                                                                                                 | Exploitant                          | Accès                                           | `robots.txt`                                                                                                                                    | CGU                                                                                                                                                                                      | Décision                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| [Leboncoin](https://www.leboncoin.fr/robots.txt)                                                                                                                                                                                                        | LBC France (Adevinta)               | Crawl seulement, aucune API de lecture publique | En-tête : « It's forbidden to use search robots or other automatic methods to access Leboncoin.fr ». Aucun groupe `*`, liste blanche de moteurs | [CGU](https://www.leboncoin.fr/dc/cgu) : anti-robot (DataDome). Condamnation d'Entreparticuliers pour extraction de ses annonces immobilières (droit du producteur)                      | Écartée                                                     |
| [SeLoger](https://www.seloger.com/robots.txt)                                                                                                                                                                                                           | Digital Classifieds France (Aviv)   | Crawl seulement                                 | Recherche `/classified-search?` interdite, fiches autorisées                                                                                    | [CGU](https://www.seloger.com/cgu) : anti-robot (DataDome). SeLoger a fait condamner Jinka (cour d'appel de Versailles, 16 décembre 2025) pour extraction de ses annonces                | Écartée                                                     |
| [Logic-Immo](https://www.logic-immo.com/robots.txt)                                                                                                                                                                                                     | Aviv, comme SeLoger                 | Crawl seulement                                 | Recherche et API internes (`*bff/*`) interdites                                                                                                 | Anti-robot (DataDome)                                                                                                                                                                    | Écartée                                                     |
| [PAP](https://www.pap.fr/robots.txt)                                                                                                                                                                                                                    | PAP                                 | Crawl seulement                                 | Paramètres d'URL (`/*?*`) et `/annonce/liste/` interdits, longue liste de robots bannis                                                         | [CGU](https://www.pap.fr/groupe/cgu) lues : « interdit d'extraire, réutiliser ou indexer de manière automatisée ou manuelle tout ou partie du contenu », pénalité de 10 000 €            | Écartée                                                     |
| [Bien'ici](https://www.bienici.com/robots.txt)                                                                                                                                                                                                          | Bien'ici (réseaux d'agences)        | Crawl seulement                                 | Pages `/annonces-*` et tris interdits, recherche autorisée                                                                                      | Page CGU introuvable sans navigateur (application JavaScript)                                                                                                                            | À approfondir : partenariat                                 |
| [Figaro Immobilier](https://immobilier.lefigaro.fr/robots.txt)                                                                                                                                                                                          | Figaro Classifieds                  | Crawl seulement                                 | `/annonce/`, `/recherche/`, `/rest/` interdits                                                                                                  | Anti-robot (Cloudflare)                                                                                                                                                                  | Écartée                                                     |
| [Ouest-France Immo](https://www.ouestfrance-immo.com/robots.txt)                                                                                                                                                                                        | Ouest-France                        | Crawl seulement                                 | `robots.txt` lui-même bloqué (403)                                                                                                              | 403, page « Site actuellement indisponible »                                                                                                                                             | Écartée                                                     |
| [EtreProprio](https://www.etreproprio.com/robots.txt)                                                                                                                                                                                                   | EtreProprio                         | Crawl seulement                                 | Recherches `/annonces/` interdites                                                                                                              | [CGU](https://www.etreproprio.com/conditions-generales-utilisation) lues : « Toute extraction ou utilisation du contenu de la base non expressément autorisée » engage la responsabilité | Écartée                                                     |
| [ParuVendu](https://www.paruvendu.fr/robots.txt), [Superimmo](https://www.superimmo.com/robots.txt), [Green-Acres](https://www.green-acres.fr/robots.txt)                                                                                               | Divers                              | Crawl seulement                                 | Fiches autorisées, recherches en partie interdites (Green-Acres)                                                                                | Page CGU non trouvée depuis l'accueil ; Superimmo a renvoyé une vérification anti-robot au premier essai                                                                                 | Écartée : agrégateurs des mêmes annonces, CGU non vérifiées |
| [Immobilier des notaires](https://www.immobilier.notaires.fr/robots.txt)                                                                                                                                                                                | Notaires de France                  | Crawl seulement                                 | Autorisé, `Crawl-delay: 10`                                                                                                                     | [Mentions légales](https://www.immobilier.notaires.fr/fr/mentions-legales) : « Toute reproduction […] est interdite sans autorisation préalable écrite »                                 | À approfondir : demande écrite                              |
| [Licitor](https://www.licitor.com/robots.txt)                                                                                                                                                                                                           | Ferrari Conseil                     | Crawl                                           | Annonces autorisées                                                                                                                             | [Droits d'auteur](https://www.licitor.com/droits-auteur.html) : marque seulement, aucune clause sur la réutilisation                                                                     | À approfondir : enchères judiciaires, avis juridique        |
| [Cessions immobilières de l'État](https://cessions.immobilier-etat.gouv.fr/robots.txt)                                                                                                                                                                  | Direction de l'immobilier de l'État | Crawl, open data                                | `/biens/` et pagination autorisés                                                                                                               | [Mentions légales](https://cessions.immobilier-etat.gouv.fr/mentions-legales) : contenus « sous etalab-2.0 license » sauf propriété de tiers                                             | Retenue                                                     |
| [BailleurVérif](https://www.data.gouv.fr/datasets/annonces-de-location-francaises-non-conformes-observatoire-bailleurverif)                                                                                                                             | Projet individuel                   | Fichiers CSV sur data.gouv.fr                   | Sans objet                                                                                                                                      | Licence Ouverte 2.0 déclarée, sur un contenu issu d'un crawl de portails tiers                                                                                                           | Écartée                                                     |
| [Yanport, volumes par portail](https://www.data.gouv.fr/datasets/t2-2019-volume-dannonces-mensuelles-par-region-et-par-portail-a-la-vente-et-a-la-location)                                                                                             | Yanport                             | CSV trimestriels                                | Sans objet                                                                                                                                      | Licence non précisée ; série arrêtée en 2019                                                                                                                                             | Écartée                                                     |
| [Carte des loyers](https://www.data.gouv.fr/datasets/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025), [observatoires locaux des loyers](https://www.data.gouv.fr/datasets/resultats-nationaux-des-observatoires-locaux-des-loyers) | Ministère, ANIL, OLL                | Open data                                       | Sans objet                                                                                                                                      | Licence Ouverte 2.0 ; indicateurs d'annonces agrégés par commune ou zone                                                                                                                 | Retenue (indicateurs, LEM-7)                                |
| Flux d'agences (passerelles Poliris, Ubiflow, logiciels Apimo, Hektor, AC3)                                                                                                                                                                             | Agences, éditeurs de logiciels      | Export XML ou CSV par mandat de l'agence        | Sans objet                                                                                                                                      | Contrat avec chaque agence ou éditeur                                                                                                                                                    | À approfondir : partenariat                                 |
| Données d'annonces payantes (Yanport, MeilleursAgents, autres agrégateurs)                                                                                                                                                                              | Sociétés privées                    | API sous contrat                                | Sans objet                                                                                                                                      | Contrat payant                                                                                                                                                                           | À approfondir : décision humaine, abonnement payant         |

Points communs aux portails commerciaux :

- l'absence de groupe `*` chez Leboncoin rend ses pages « autorisées » au sens
  strict du protocole, mais son en-tête et ses CGU l'interdisent : le script
  les signale ensemble ;
- les portails sans clause lisible ne sont pas retenus pour autant : le droit
  du producteur de base de données s'applique sans clause, et ces sites
  reprennent les mêmes annonces d'agences que les grands portails ;
- aucun portail ne publie, à notre connaissance, d'API de lecture des
  annonces. Les API et passerelles destinées aux professionnels servent à
  publier des annonces, pas à les lire.

## Champs recherchés

Pour la consultation d'une annonce et le calcul d'indicateurs d'offre, LEM-23
doit viser ces champs. La colonne de droite indique ce que la source retenue
fournit.

| Champ                                                   | Usage                              | Cessions de l'État                           |
| ------------------------------------------------------- | ---------------------------------- | -------------------------------------------- |
| Identifiant stable de la source, URL                    | Dédoublonnage, retour à l'annonce  | Référence (n° de dossier), chemin            |
| Type de transaction (vente, location)                   | Séparer les marchés                | Vente seulement                              |
| Type de bien, surface, pièces                           | Prix au m², filtres                | Type 22/22, surface 18/22, pièces 2/22       |
| Prix demandé ou loyer (charges comprises ou non)        | Prix demandé au m², écart avec DVF | 1/22 (montant de première offre)             |
| DPE et GES                                              | Lien avec LEM-7                    | Dans les diagnostics PDF seulement           |
| Code INSEE (arrondissement pour Paris, Lyon, Marseille) | Jointure au COG                    | 22/22, arrondissement compris                |
| Adresse, IRIS, coordonnées et leur précision            | Carte, jointure fine               | Coordonnées 22/22, parcelle cadastrale 22/22 |
| Date de publication, date de modification               | Âge de l'annonce                   | 22/22                                        |
| Date d'observation (première et dernière vue)           | Durée de mise en vente, retrait    | Calculée par la collecte                     |
| Statut (en cours, expirée, vendue, retirée)             | Stock actif, retrait               | 20/22                                        |
| Type d'annonceur (particulier, agence), sans nom        | Segmenter l'offre                  | Sans objet (l'État)                          |
| Historique de prix                                      | Baisses de prix, tension           | Non publié                                   |

Indicateurs d'offre visés, par commune et par mois : stock d'annonces actives,
nouvelles annonces, annonces retirées, durée médiane de publication, prix
demandé médian au m², part des annonces avec baisse de prix, écart entre prix
demandé et prix de vente DVF.

## Mesures sur l'échantillon

### Cessions immobilières de l'État

Deux pages de la liste principale (24 annonces sur 20 pages, soit environ 240
annonces), une page des biens vendus (2 annonces, 3 pages au total) et
22 fiches lues.

| Mesure                                               | Valeur                                                                                     |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Doublons de référence                                | 0                                                                                          |
| Même code INSEE et même parcelle sous deux annonces  | 0                                                                                          |
| Coordonnées identiques entre deux annonces           | 0                                                                                          |
| Annonces présentes à la fois en liste et en vendus   | 0                                                                                          |
| Coordonnées à moins de 300 m du centre de la commune | 3 sur 22 : probable centroïde ; les 19 autres sont propres au bien                         |
| Codes INSEE d'arrondissement                         | 1 (`13205`, Marseille 5e)                                                                  |
| Type de vente                                        | Adjudication, appel d'offres, enchères en ligne ; manquant 3 fois                          |
| Prix affiché                                         | 1 sur 22 : « Montant de la première offre possible ». Sinon dans le cahier des charges PDF |

Statuts affichés sur les 20 fiches de la liste principale : 7 « Expiré »
(date limite des offres passée, l'annonce reste en ligne), 11 « Fini dans N
jours », 2 sans statut. Les 2 fiches de la liste des vendus portent « Vendu ».

### BailleurVérif

Fichier cumulatif publié sur data.gouv.fr le 1er juillet 2026, 2 027 annonces
de location. La description annonce un crawl de Leboncoin, SeLoger et PAP ;
toutes les lignes viennent en fait de la source `locservice`, sur un seul
instantané (2026-07-01). Aucun doublon d'identifiant, mais 144 lignes (7 %)
partagent code postal, surface et loyer avec une autre : probables annonces
republiées. Champs remplis à 100 %, localisation au code postal seulement (pas
de code INSEE, pas de coordonnées). Le jeu n'est plus mis à jour depuis juillet
et sa licence porte sur un contenu repris de portails tiers : écarté.

### Yanport

Volumes mensuels d'annonces par portail et par région, avril à juin 2019,
métropole seulement. En juin 2019, la somme sur les portails donne 4,09 millions
d'annonces de vente et 1,06 million de location. Leboncoin (859 378 ventes),
SeLoger (721 690) et AVendreALouer (861 317) dominent. Cette somme compte la
même annonce d'agence sur plusieurs portails : la multidiffusion fait du
dédoublonnage entre sources la première difficulté d'un agrégat de portails.
Série arrêtée en 2019, licence non précisée : écartée.

### Doublons entre sources

Non mesurables sur les portails commerciaux faute d'échantillon autorisé. La
multidiffusion d'agence (une même annonce sur 5 à 10 portails) est attendue
pour toute source tierce. Clé de rapprochement proposée pour LEM-23 : code
INSEE, type de bien, surface arrondie au m², nombre de pièces et prix ; puis
coordonnées à moins de 50 m si elles sont précises.

## Prix demandé, date d'observation et retrait

Ces trois notions restent séparées dans le modèle de LEM-23 :

1. **Prix demandé** : valeur affichée à la date d'observation. Chaque
   changement crée une nouvelle observation, jamais une mise à jour en place.
   Il n'est jamais comparé à un prix de vente sans le dire : le prix de vente
   vient de DVF (LEM-6).
2. **Date d'observation** : date de la collecte, distincte de la date de
   publication affichée par la source. Garder `first_seen_at` et
   `last_seen_at` pour chaque annonce. Les statuts relatifs (« Fini dans
   11 jours ») sont convertis en date absolue à partir de la date
   d'observation.
3. **Retrait** : une annonce est retirée quand elle n'apparaît plus dans deux
   collectes complètes successives, ou quand la source le dit (statut
   « Vendu », page 404 ou 410, liste des biens vendus). Une annonce
   « Expiré » n'est pas retirée : sur l'État, 7 annonces sur 20 restent en
   ligne après la date limite des offres. Retrait ne veut pas dire vente :
   seule DVF confirme une vente.

## Recommandation pour LEM-23

À appliquer seulement si le bonus est repris (voir « Décision de l'équipe »).

| Source                           | Mode de collecte                                                         | Limites                                                                                         |
| -------------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| Cessions immobilières de l'État  | Crawl hebdomadaire de la liste paginée et des fiches, 3 s entre requêtes | Environ 240 biens publics, souvent atypiques ; prix rarement affiché ; certificat TLS incomplet |
| Carte des loyers, OLL            | Fichiers annuels open data (déjà prévus par LEM-7)                       | Indicateurs agrégés, pas d'annonce individuelle, pas de prix de vente                           |
| Portail commercial               | Licence ou API sous contrat, après accord écrit                          | Coût et délai inconnus ; décision humaine                                                       |
| Agences partenaires              | Flux de passerelle (XML ou CSV) envoyé par l'agence ou son logiciel      | Couverture limitée aux agences signataires                                                      |
| Annonces déposées dans Homepedia | Formulaire, avec consentement et sans coordonnées publiques              | Volume nul au départ ; modération et RGPD à prévoir                                             |

Ordre proposé : construire la chaîne de collecte, d'historique et de retrait
sur les cessions de l'État, puis demander un accès à un ou deux portails
(SeLoger, Bien'ici, Leboncoin) et aux notaires en parallèle. Sans accord, le
produit affiche les indicateurs agrégés et les ventes DVF, sans annonces
privées.

## Décisions encore ouvertes

À trancher seulement si le bonus est repris.

- Lire dans un navigateur les CGU que les pages anti-robot ont bloquées
  (Leboncoin, SeLoger, Logic-Immo, Figaro, Ouest-France Immo, Superimmo,
  Bien'ici, ParuVendu, Green-Acres) et confirmer les décisions.
- Faire vérifier par un juriste les points de droit cités : droit du
  producteur, décisions Leboncoin et SeLoger contre Jinka, statut des
  enchères judiciaires (Licitor) et des informations publiques de l'État.
- Choisir qui contacte les portails et les notaires, et avec quelle offre.
- Vérifier le site [locations.immobilier-etat.gouv.fr](https://locations.immobilier-etat.gouv.fr/)
  (locations de l'État), non testé.
