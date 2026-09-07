# API de segmentation marketing

Cette API FastAPI expose les résultats CSV de la segmentation RFM en JSON,
avec pagination et statistiques. Elle peut alimenter n8n et la future interface.
Elle ne réalise ni entraînement ni prédiction pour de nouveaux clients.

## Organisation et données

- `main.py` : application et routes HTTP.
- `requirements.txt` : dépendances Python.
- `data/` : copies des trois tables produites par le [notebook RFM](../ml/index.ipynb).
- `Dockerfile` et `docker-compose.yml` : lancement en conteneur.

Les chemins sont résolus à partir de `main.py`, indépendamment du répertoire
de travail. Les fichiers Excel bruts ne sont pas utilisés par l’API.

Après une nouvelle exécution du notebook, actualiser les copies depuis la
racine du dépôt :

```bash
cp ml/outputs/recommandations_segments.csv api/data/
cp ml/outputs/rfm_clients_segments.csv api/data/
cp ml/outputs/tableau_synthese_segments.csv api/data/
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

Chaque route de données retourne `dataset`, `description`, `source_file`,
`statistics`, `pagination` et `data`.

- `statistics.row_count` : nombre total de lignes.
- `statistics.columns` : noms des colonnes.
- `statistics.numeric` : effectif, somme, moyenne, minimum et maximum des colonnes numériques.
- `statistics.categorical` : effectif, nombre de valeurs distinctes et jusqu’à dix valeurs les plus fréquentes des colonnes textuelles.
- `pagination` : décalage, limite, nombre de lignes retournées et total.
- `data` : lignes du CSV converties en JSON.

Les statistiques portent sur la table entière, même lorsque la réponse est
paginée. Les cellules vides deviennent `null` ; les valeurs interprétables
comme nombres sont converties automatiquement, y compris les identifiants
clients numériques. Les agrégats sur ces identifiants n’ont pas de sens métier.

### Pagination

`offset` vaut `0` par défaut et doit être positif ou nul. `limit` est facultatif
et doit être supérieur ou égal à `1`. Sans limite, toutes les lignes restantes
sont retournées.

```bash
curl "http://127.0.0.1:8000/rfm-clients-segments?limit=10&offset=0"
```

Un CSV absent entraîne une réponse `404` sur la route concernée ; des paramètres
de pagination invalides entraînent une réponse `422`. La route `/` ne vérifie
pas la présence des CSV.

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
