# API de segmentation marketing

Cette API FastAPI expose les résultats CSV de la segmentation RFM en JSON,
avec pagination et statistiques. Elle alimente n8n et l'interface web.
Elle classe aussi un client via le modèle exporté, sans réentraînement.

## Organisation et données

- `main.py` : application et routes HTTP.
- `prediction.py` : prétraitement figé et affectation au centroïde le plus proche.
- `requirements.txt` : dépendances Python.
- `data/` : copies des tables de résultats et de diagnostic produites par le [notebook RFM](../ml/index.ipynb).
- `Dockerfile` et `docker-compose.yml` : lancement en conteneur.

Les chemins sont résolus à partir de `main.py`, indépendamment du répertoire
de travail. Les fichiers Excel bruts ne sont pas utilisés par l’API.

Après une nouvelle exécution du notebook, actualiser les copies depuis la
racine du dépôt :

```bash
python scripts/sync_artifacts.py
python scripts/sync_artifacts.py --check
```

Redémarrer ensuite l’API : les tables sont mises en cache en mémoire après
leur première lecture. Avec Docker, reconstruire également l’image, car les
CSV y sont copiés lors de la construction.

## Installation et lancement local

Utiliser Python 3.10 ou supérieur ; l’image Docker utilise Python 3.12.
Depuis la racine du dépôt :

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Si un environnement virtuel a été copié depuis l’ancien dossier, le recréer
au nouvel emplacement : ses scripts peuvent contenir des chemins absolus.

Documentation interactive :

- Swagger UI : http://127.0.0.1:8000/docs
- ReDoc : http://127.0.0.1:8000/redoc
- Schéma OpenAPI : http://127.0.0.1:8000/openapi.json

## Routes et réponses

| Route GET | Contenu |
| --- | --- |
| `/` | Présentation et liste des routes de données |
| `/recommandations-segments` | Recommandations marketing par segment |
| `/rfm-clients-segments` | Clients et variables RFM avec segments attribués |
| `/tableau-synthese-segments` | Synthèse statistique des segments |
| `/evaluation-k` | Métriques pour chaque valeur de k |
| `/choix-k` | Choix par critère statistique et choix commercial |
| `/comparaison-segmentations` | Profils candidats et correspondance k=4 / k=5 |
| `/sensibilite-retours` | Audit, comparaison, migrations, profils et stabilité achats/net |
| `/segments/{segment}` | Synthèse, recommandation et effet des retours pour un segment |

Les trois routes historiques, `/evaluation-k` et `/choix-k` retournent `dataset`, `description`, `source_file`,
`statistics`, `pagination` et `data`.

- `statistics.row_count` : nombre total de lignes.
- `statistics.columns` : noms des colonnes.
- `statistics.numeric` : effectif, somme, moyenne, minimum et maximum des colonnes numériques.
- `statistics.categorical` : effectif, nombre de valeurs distinctes et jusqu’à dix valeurs les plus fréquentes des colonnes textuelles.
- `pagination` : décalage, limite, nombre de lignes retournées et total.
- `data` : lignes du CSV converties en JSON.

Les statistiques portent sur toutes les lignes retenues avant pagination :
la table entière sans filtre, ou les clients du segment demandé avec filtre. Les cellules vides deviennent `null` ; les valeurs interprétables
comme nombres sont converties automatiquement, y compris les identifiants
clients numériques. Les agrégats sur ces identifiants n’ont pas de sens métier.

### Routes regroupées

`/comparaison-segmentations` contient les sections `profils` et
`correspondance_k4_k5`.

`/sensibilite-retours` contient `audit`, `comparaison`, `migrations`,
`par_segment`, `profils` et `stabilite`. Chaque section utilise l’enveloppe
`dataset`, `description`, `source_file`, `statistics`, `pagination`, `data` et
retourne sa table entière. Ces deux routes n’appliquent pas de pagination.
L’audit précise la fenêtre et la date de référence des analyses de retours.

Les colonnes `0` à `4` de la correspondance k=4 / k=5 sont les numéros des
clusters à k=5. Les colonnes des migrations achats/net représentent les groupes
nets alignés sur les segments initiaux : leurs noms ne valident pas de nouveaux
profils métier. L’API restitue les mesures du notebook sans recalculer le clustering.

`/segments/{segment}` retourne `segment`, `synthese`, `recommandation`,
`effet_retours` et `sources` (un fichier source par section). Les trois sections
métier sont des objets, sans enveloppe de pagination. Cette route ne retourne
pas les transactions ni la liste des clients.

### Filtrer les clients d’un segment

Le paramètre `segment` de `/rfm-clients-segments` accepte les noms de la table
de synthèse. La casse et les espaces en début/fin sont ignorés ; les accents
restent nécessaires. La même règle s’applique à `/segments/{segment}`.
Un segment inconnu retourne `404` et un filtre vide retourne `422`.

```bash
curl --get "http://127.0.0.1:8000/rfm-clients-segments" --data-urlencode "segment=Achats anciens" --data-urlencode "limit=10"
curl "http://127.0.0.1:8000/segments/Champions"
curl "http://127.0.0.1:8000/evaluation-k"
curl "http://127.0.0.1:8000/sensibilite-retours"
```

### Pagination

`offset` vaut `0` par défaut et doit être positif ou nul. La liste des clients
utilise `limit=25` par défaut, avec un maximum de 500. Pour les autres tables,
`limit` reste facultatif et doit être supérieur ou égal à 1 ; sans limite,
toutes les lignes restantes sont retournées. Utiliser `/clients/export` pour
exporter toute une sélection de clients.

```bash
curl "http://127.0.0.1:8000/rfm-clients-segments?limit=10&offset=0"
```

Une livraison incomplète empêche le démarrage de l’API. Des paramètres
de pagination invalides entraînent une réponse `422`. La route `/` décrit
les endpoints ; `/bundle-info` identifie les données validées au démarrage.

## Lancement avec Docker

Depuis la racine du dépôt :

```bash
cd api
docker compose up --build -d
docker compose ps
```

L’API est accessible à `http://127.0.0.1:8000`. Le contrôle de santé interroge
la route `/`. Pour arrêter le service, exécuter `docker compose down` depuis
`api/`.

## Connexion à n8n

Si n8n tourne directement sur la même machine, utiliser
`http://127.0.0.1:8000/recommandations-segments`.

Si n8n tourne dans un conteneur connecté au même réseau Docker, utiliser le
nom du service :

```text
http://segmentation-api:8000/recommandations-segments
http://segmentation-api:8000/rfm-clients-segments
http://segmentation-api:8000/tableau-synthese-segments
```

Avec les commandes ci-dessus et sans surcharge du nom de projet Compose,
le réseau par défaut est `api_default`. Pour y connecter un conteneur n8n
existant, remplacer `NOM_DU_CONTENEUR_N8N` par son nom réel :

```bash
docker network ls
docker network connect api_default NOM_DU_CONTENEUR_N8N
```

Adapter le nom du réseau si le projet Compose a été renommé. Cette connexion
manuelle doit être rétablie si le conteneur n8n est recréé ; pour une intégration
durable, déclarer le réseau partagé dans la configuration Compose de n8n.

L’API fournit les données ; aucun workflow n8n ni assistant conversationnel
n’est inclus dans ce dossier.


## Vérification

Depuis `api/`, avec les dépendances installées :

```bash
python -m unittest discover -s tests -v
```

Les tests exercent les routes ASGI réelles sans ouvrir de port réseau. Ils vérifient les routes existantes et nouvelles,
les correspondances avec les CSV, le filtrage avant pagination/statistiques,
les noms accentués, les erreurs et le schéma OpenAPI. Aucune dépendance de test
supplémentaire n’est nécessaire.

## Classer un client

`POST /predict` applique le modèle final à des indicateurs RFM saisis, sans
réentraînement ni ajout aux CSV. Exemple depuis un terminal :

```bash
curl --fail http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  --data '{"recency":30,"frequency":8,"monetary":2500,"observation_start":"2009-12-01","observation_end":"2011-12-09","reference_date":"2011-12-10","mode":"historical"}'
```

- `recency` : entier de 0 à 1 000 000, jours depuis le dernier achat valide.
- `frequency` : entier de 1 à 1 000 000 000, nombre de factures distinctes.
- `monetary` : nombre strictement positif, au plus 10^15, total des achats
  positifs en GBP. Les retours ne sont pas déduits.

Les trois valeurs RFM et les trois dates sont obligatoires ; champs supplémentaires, booléens, chaînes à la place de nombres
et valeurs non finies sont rejetés (`422`). Les bornes supérieures sont des
limites techniques, pas des plages de pertinence statistique.

La réponse contient `segment`, `cluster`, `model_id`, `k`, `input`,
`capped_features`, `distance_to_center`, `training`, `recommendation` et `notice`.
La distance standardisée n'est pas une probabilité de confiance. Les indicateurs
d'un client actuel ou calculés sur une fenêtre différente constituent une
simulation dont la pertinence doit être évaluée.

`GET /model-info` donne l'identifiant du modèle et sa période d'entraînement.
Une livraison absente, altérée ou incohérente empêche le démarrage de l’API. Le fichier
`api/data/rfm_model.json` contient les plafonds au 99e percentile, la moyenne
et l'échelle du StandardScaler, les centroïdes K-means et les noms des segments.
L'API applique `log1p(min(valeur, plafond))`, standardise puis choisit le centroïde
le plus proche. Aucun chargement de pickle et aucune dépendance scikit-learn
ne sont nécessaires dans le service d'inférence.

Le notebook exporte directement ces paramètres en dernière section. Le script
`ml/export_model.py` permet aussi de reproduire le modèle depuis les CSV RFM
avec k=5, seed=42 et n_init=100 ; il refuse l'export si une seule affectation
diffère des CSV livrés. Utiliser l'environnement ML pour l'exécuter :

```bash
python ml/export_model.py
python scripts/sync_artifacts.py
```

Après toute analyse complète, synchroniser ensemble les CSV et le modèle :

```bash
python scripts/sync_artifacts.py
python scripts/sync_artifacts.py --check
cd n8n
docker compose up --build -d segmentation-api frontend
```

Le modèle est chargé en cache. Reconstruire l'image recharge les paramètres.
Les tests comparent les prédictions aux affectations de tous les clients des CSV.

## Contrat temporel du classement

Consulter `/model-info` avant la saisie : les dates de l'exemple correspondent
à la livraison actuelle et peuvent changer après réentraînement.
`observation_start` et `observation_end` délimitent les jours inclus dans la
fenêtre ; `reference_date` doit être strictement postérieure à sa fin.
Les dates sont au format ISO `AAAA-MM-JJ`. La récence doit placer le dernier
achat à l'intérieur de cette fenêtre, sinon la requête est rejetée (`422`).

- `mode: "historical"` (défaut) exige exactement les dates d'entraînement.
- `mode: "simulation"` autorise une autre période cohérente, avec une réserve
  explicite dans le résultat. Aucun ajustement annuel n'est effectué.

La réponse ajoute `temporal_context`, `segment_definition` et `bundle_id`.
Des dates cohérentes ne prouvent pas la validité commerciale d'un classement
sur une autre population. L'API ne peut pas vérifier que les RFM déclarés ont
réellement été calculés sur les transactions de la période saisie.

## Recherche et export de tous les clients

`GET /rfm-clients-segments` applique les filtres avant pagination et statistiques :

| Paramètre | Comportement |
| --- | --- |
| `q` | Recherche partielle sur identifiant, pays ou nom de segment, sans distinction de casse ni d'accents |
| `segment`, `country` | Correspondance exacte, sans distinction de casse ni d'accents |
| `recency_min`, `recency_max` | Bornes inclusives, en jours |
| `frequency_min`, `frequency_max` | Bornes inclusives, en factures distinctes |
| `monetary_min`, `monetary_max` | Bornes inclusives, en GBP |
| `sort_by` | CustomerID, Recency, Frequency, Monetary, CountryMode ou segment_name |
| `order` | asc ou desc ; les égalités conservent l'ordre des identifiants |
| `limit`, `offset` | Taille de page (1 à 500, défaut 25) et décalage |

Les filtres se cumulent. Une borne minimale supérieure au maximum produit `422`.
`GET /clients/filters` fournit les pays et segments de toute la population.
`GET /clients/export` applique les mêmes filtres et le même tri, mais exporte
**toutes les lignes correspondantes**, indépendamment de `limit` et `offset`.
Le CSV utilise UTF-8 avec BOM et un point-virgule ; les champs texte pouvant
être interprétés comme des formules de tableur sont neutralisés.
L'en-tête `X-Total-Count` indique le nombre de clients exportés.

```bash
curl --fail --get http://localhost:8000/clients/export \
  --data-urlencode 'country=United Kingdom' \
  --data-urlencode 'monetary_min=1000' \
  --data-urlencode 'sort_by=Monetary' \
  --data-urlencode 'order=desc' --output clients.csv
```

## Cohérence de la livraison

La [procédure de synchronisation](../docs/model-lifecycle.md) valide les
empreintes, affectations et agrégats, puis génère la [fiche du modèle](../docs/current-model.md).
`GET /bundle-info` identifie la livraison effectivement chargée. Ne pas copier
un CSV isolé dans une API en fonctionnement : synchroniser puis redémarrer.
