# API de segmentation marketing

Cette API FastAPI expose les résultats CSV de la segmentation RFM en JSON,
avec pagination et statistiques. Elle peut alimenter n8n et la future interface.
Elle ne réalise ni entraînement ni prédiction pour de nouveaux clients.

## Organisation et données

- `main.py` : application et routes HTTP.
- `requirements.txt` : dépendances Python.
- `data/` : copies des tables de résultats et de diagnostic produites par le [notebook RFM](../ml/index.ipynb).
- `Dockerfile` et `docker-compose.yml` : lancement en conteneur.

Les chemins sont résolus à partir de `main.py`, indépendamment du répertoire
de travail. Les fichiers Excel bruts ne sont pas utilisés par l’API.

Après une nouvelle exécution du notebook, actualiser les copies depuis la
racine du dépôt :

```bash
cp ml/outputs/*.csv api/data/
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
curl --get "http://127.0.0.1:8000/rfm-clients-segments" --data-urlencode "segment=À risque" --data-urlencode "limit=10"
curl "http://127.0.0.1:8000/segments/Champions"
curl "http://127.0.0.1:8000/evaluation-k"
curl "http://127.0.0.1:8000/sensibilite-retours"
```

### Pagination

`offset` vaut `0` par défaut et doit être positif ou nul. `limit` est facultatif
et doit être supérieur ou égal à `1`. Sans limite, toutes les lignes restantes
sont retournées.

```bash
curl "http://127.0.0.1:8000/rfm-clients-segments?limit=10&offset=0"
```

Un CSV absent entraîne une réponse `404` sur la route concernée (y compris
une route regroupée qui en dépend) ; des paramètres
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


## Vérification

Depuis `api/`, avec les dépendances installées :

```bash
python -m unittest discover -s tests -v
```

Les tests démarrent un serveur HTTP temporaire sur une adresse locale et un
port disponible, puis l’arrêtent. Ils vérifient les routes existantes et nouvelles,
les correspondances avec les CSV, le filtrage avant pagination/statistiques,
les noms accentués, les erreurs et le schéma OpenAPI. Aucune dépendance de test
supplémentaire n’est nécessaire.
