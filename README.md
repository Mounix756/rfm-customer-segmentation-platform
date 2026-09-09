# Plateforme de segmentation clients RFM

Segmentation des clients du jeu UCI Online Retail II à partir de la récence,
de la fréquence et du montant des achats.

## Origine du projet et contributions

Ce projet est issu d'un travail de groupe réalisé lors du **Togo AI Summer School**,
autour de la segmentation clients RFM. Le travail collectif constitue le socle
de l'analyse présentée dans le [notebook](ml/index.ipynb).

Les membres du groupe sont :

- AKAYA Eniwinéwé Henri
- ALKISSANKDEI T. Djamal
- BLAISE Mouné Tchoubou
- LARE V. Donné
- METO Kemi Gédéon
- OPEKOU-DOUDOE Christian
- TORA Dkawlma Emmanuel

À partir de ce travail collectif, j'ai poursuivi le projet à titre personnel
pour en faire une plateforme utilisable : approfondissement des analyses,
ajout d'une API FastAPI et d'un workflow n8n avec un assistant conversationnel
et une mémoire PostgreSQL. Une interface web complète ces ajouts pour explorer les résultats, consulter
les diagnostics et échanger avec l'assistant.

## Organisation

- `ml/` : préparation des données, analyse RFM, entraînement et évaluation du
  clustering et résultats.
- `docs/` : sujet du TP, rapport de segmentation et règles de contribution.
- `api/` : API FastAPI exposant les résultats de segmentation en JSON.
- `n8n/` : workflow du chatbot marketing et guide d’installation.
- `frontend/` : plateforme web React et serveur de connexion à FastAPI et n8n.

## Lancer le projet étape par étape

Les commandes suivantes utilisent Bash (Linux, macOS ou WSL). Deux parcours
sont possibles : pour explorer directement la plateforme, passer de l'étape 1
à l'étape 3 ; pour reproduire l'analyse, réaliser aussi l'étape 2.
Les résultats nécessaires à l'API sont déjà fournis dans le dépôt.

### 1. Préparer et cloner le dépôt

Installer Git, Docker avec le plugin Compose et Python 3.12 pour reproduire
l'environnement Python utilisé par le projet. Pour une utilisation uniquement
avec Docker, Python et Node.js ne sont pas nécessaires sur l'hôte.
Les instructions d'installation Docker sont dans le [guide n8n](n8n/README.md).

```bash
git --version
docker --version
docker compose version
git clone https://github.com/Mounix756/rfm-customer-segmentation-platform.git
cd rfm-customer-segmentation-platform
```

Conserver ce répertoire comme point de départ des étapes. Les commandes `cd`
ci-dessous précisent les changements nécessaires.

### 2. Télécharger les données et exécuter le notebook

Cette étape permet de reproduire le nettoyage, le calcul RFM, l'entraînement,
le choix de k et la vérification des retours. Elle ne nécessite ni n8n ni clé API.

Télécharger et extraire le fichier suivant selon le [guide des données](ml/data/README.md) :

```text
ml/data/online_retail_II.xlsx
```

Conserver les deux feuilles `Year 2009-2010` et `Year 2010-2011`.
Le fichier Excel brut n'est pas inclus dans Git. Depuis la racine :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r ml/requirements.txt
python -m pip install jupyterlab
cd ml
python -m jupyterlab index.ipynb
```

Dans JupyterLab, ouvrir `index.ipynb`, choisir le noyau de cet environnement,
puis **Kernel > Restart Kernel and Run All Cells**. Le répertoire de travail
doit être `ml/`, car les chemins `data/`, `outputs/` et
`segment_semantics.json` sont relatifs à ce dossier. Avec VS Code, sélectionner
l'interpréteur `.venv/bin/python` et vérifier ce même répertoire de travail.

Attendre la fin de toutes les cellules, y compris l'analyse des retours et
l'export du modèle. L'exécution peut prendre plusieurs minutes. Si une cellule
échoue, corriger l'erreur avant de poursuivre : des exports partiels ne doivent
pas être déployés.

La dernière cellule synchronise automatiquement les résultats vers `api/data/`
et génère `docs/current-model.md`. Après avoir arrêté JupyterLab avec `Ctrl+C`,
vérifier depuis la racine :

```bash
cd ..
python scripts/sync_artifacts.py --check
```

La commande doit afficher `Cohérence vérifiée`. Si les résultats sont complets
mais les copies ne sont pas synchronisées :

```bash
python scripts/sync_artifacts.py
python scripts/sync_artifacts.py --check
```

Consulter les tableaux et graphiques avant utilisation. Les dépendances ML ne
sont pas toutes figées : une autre version peut modifier les résultats. Les
versions et l'identifiant du modèle livré figurent dans la [fiche générée](docs/current-model.md).
Le PDF et sa source LaTeX doivent être relus manuellement après réentraînement.

### 3. Préparer la configuration Docker

Depuis la racine :

```bash
cd n8n
# Première installation uniquement : ne pas écraser un .env existant.
cp -n .env.example .env
openssl rand -hex 32
```

Ouvrir `n8n/.env` dans un éditeur. Générer trois valeurs distinctes en répétant
`openssl rand -hex 32`, puis renseigner :

| Variable | Valeur à fournir |
| --- | --- |
| `POSTGRES_PASSWORD` | Mot de passe personnel de la base de mémoire |
| `SESSION_SECRET` | Secret stable pour les sessions de l'interface |
| `N8N_WEBHOOK_TOKEN` | Jeton personnel pour protéger le webhook, distinct de la clé DeepSeek |

Les deux premières variables sont obligatoires pour démarrer Compose.
Le jeton webhook peut rester vide pour explorer les données sans chatbot.
Ne pas versionner `.env`. Conserver le mot de passe PostgreSQL et le secret de
session entre les redémarrages. Modifier seulement `POSTGRES_PASSWORD` dans
`.env` ne change pas le mot de passe d'une base déjà initialisée.

### 4. Démarrer les quatre services

Toujours depuis `n8n/` :

```bash
docker compose up --build -d
docker compose ps
```

Compose construit le frontend et l'API, puis démarre n8n et PostgreSQL.
Attendre que l'API et PostgreSQL soient sains (`healthy`).

| Service | Adresse locale ou accès |
| --- | --- |
| Interface web | <http://127.0.0.1:3001> |
| Documentation interactive API | <http://127.0.0.1:8000/docs> |
| Livraison du modèle | <http://127.0.0.1:8000/bundle-info> |
| Éditeur n8n | <http://127.0.0.1:5678> |
| PostgreSQL | Réseau Docker uniquement, hôte `postgres`, port `5432` |

Les ports correspondent aux valeurs par défaut de `.env`. Il n'est pas
nécessaire d'installer PostgreSQL séparément ni d'importer un script SQL :
Compose crée la base et le rôle `rfm_memory` au premier démarrage du volume.
PostgreSQL conserve les conversations ; les résultats RFM restent dans les
CSV de l'API. Les pages d'analyse et de classement fonctionnent avant la
configuration de l'assistant.

### 5. Configurer l'assistant dans n8n

Ouvrir l'éditeur n8n et créer le compte propriétaire local. Ce compte est
indépendant du compte DeepSeek. Importer le fichier
[n8n/taiss-tp-final.json](n8n/taiss-tp-final.json), puis configurer les trois accès :

| Nœud | Credential et paramètres |
| --- | --- |
| `Modele DeepSeek` | Credential **OpenAI** compatible : clé API **DeepSeek**, Base URL `https://api.deepseek.com` ; conserver les paramètres du modèle importé |
| `Memoire session` | Credential **Postgres** : Host `postgres`, Database `rfm_memory`, User `rfm_memory`, Port `5432`, mot de passe `POSTGRES_PASSWORD`, SSL désactivé sur ce réseau Docker local |
| `Webhook` | Credential **Header Auth** : Name `X-RFM-Token`, Value identique à `N8N_WEBHOOK_TOKEN` |

Le type de credential OpenAI désigne ici le protocole compatible : une clé
OpenAI n'est pas nécessaire. Les appels DeepSeek nécessitent un compte et des
crédits fournisseur. La table `rfm_chat_histories` est créée au premier usage
de la mémoire ; aucun nom d'utilisateur PostgreSQL supplémentaire n'est à créer.

Enregistrer et publier le workflow. Son URL de production est
`http://localhost:5678/webhook/rfm-chat`. Si le jeton `.env` a été renseigné après
le démarrage, recréer le frontend pour lui transmettre la valeur :

```bash
docker compose up -d frontend
```

Le [guide n8n détaillé](n8n/README.md) accompagne l'import, la création des
credentials, la publication et les essais dans Postman. Modifier le JSON du
dépôt ne met pas automatiquement à jour le workflow déjà importé dans n8n.

### 6. Vérifier le fonctionnement

Dans l'interface, suivre ces parcours :

1. Ouvrir **Vue d'ensemble** et vérifier que les données sont chargées.
2. Dans **Segments & clients**, chercher un identifiant, filtrer et exporter la sélection complète.
3. Dans **Qualité du modèle**, consulter les critères de k et la sensibilité aux retours.
4. Dans **Classer un client**, conserver la période historique et essayer une récence de 30 jours, 8 factures et un montant de 2 500 GBP.
5. Dans **Assistant marketing**, envoyer « Bonjour », puis une question sur les Champions et une question de suivi dans la même conversation.

Pour Postman, utiliser `POST http://localhost:5678/webhook/rfm-chat`, les
en-têtes `Content-Type: application/json` et `X-RFM-Token: votre jeton`, puis
le corps JSON :

```json
{
  "sessionId": "test-rfm-001",
  "message": "Bonjour"
}
```

Réutiliser le même `sessionId` pour poursuivre la conversation. La réponse
attendue contient `ok`, `sessionId` et `answer`. La [recette de qualité](n8n/evaluation/README.md)
explique les contrôles approfondis de l'assistant.

### 7. Actualiser, diagnostiquer et arrêter

Après une nouvelle exécution complète du notebook, depuis la racine :

```bash
python scripts/sync_artifacts.py --check
cd n8n
docker compose up --build -d segmentation-api frontend
```

Depuis `n8n/`, consulter les journaux ou arrêter les services :

```bash
docker compose logs --tail=100 segmentation-api frontend n8n postgres
docker compose stop
# Reprendre avec les volumes existants :
docker compose up -d
```

Les volumes conservent la configuration n8n et la mémoire PostgreSQL.
`docker compose down -v` supprime ces volumes et leurs données : ne pas utiliser
cette commande pour un arrêt courant. Les procédures de sauvegarde et les
solutions aux erreurs de connexion sont dans le [guide n8n](n8n/README.md).

Pour développer sans Docker, suivre les guides [API](api/README.md) et
[frontend](frontend/README.md), qui précisent les environnements et les terminaux
à lancer séparément.

## Partie machine learning

Le notebook [ml/index.ipynb](ml/index.ipynb) contient le traitement des
transactions, la construction des variables RFM, la comparaison des modèles
K-means et les recommandations marketing.

La sélection de `k` compare l’inertie, la silhouette, les indices
Calinski-Harabasz et Davies-Bouldin, ainsi que la stabilité entre graines.
Le compromis statistique est distingué du choix commercial de cinq segments.
Une comparaison des profils à quatre et cinq segments documente ce choix ;
son bénéfice commercial reste à valider par des campagnes.

- `ml/requirements.txt` : dépendances Python.
- `ml/data/` : fichiers de données sources.
- `ml/outputs/` : tables CSV et image des recommandations.
- Le [rapport de segmentation](<docs/Min_Rapport_du_Projet_Final_de_TAISS_2026.pdf>) se trouve dans `docs/`.
- Une [version LaTeX actualisée](docs/rapport-latex.md) est disponible avec ses instructions de compilation.

Exécuter le notebook avec `ml/` comme répertoire de travail : ses chemins
`data/` et `outputs/` sont relatifs à ce dossier.

Les diagnostics sont exportés dans `evaluation_k.csv`, `choix_k.csv`,
`profils_k_candidats.csv` et `comparaison_k4_k5.csv` sous `ml/outputs/`.
Le rapport PDF et sa source LaTeX doivent être relus après toute nouvelle analyse.

La partie 5 mesure aussi l’effet des retours sur les mêmes clients : achats
positifs contre montant net, à `k = 5` et prétraitement fixé. Elle exporte
`audit_retours.csv`, `sensibilite_retours.csv`, `migrations_retours.csv`,
`retours_par_segment.csv`, `profils_politiques_retours.csv` et
`stabilite_sensibilite_retours.csv`. La conclusion est générée à partir des
mesures, avec une vérification sur dix graines supplémentaires. Cette variante
ne remplace pas les segments principaux servis par l’API.

Le [sujet du TP](docs/tp2-f1-segmentation-clients-rfm.md) décrit les objectifs,
les données et les livrables attendus.

## API

L’[API de segmentation](api/README.md) expose les clients RFM, la synthèse des
segments, les recommandations marketing et les diagnostics de sélection de k
et de sensibilité aux retours. Elle propose une fiche par segment et un filtre
pour consulter les clients d’un groupe. Elle lit les CSV de `api/data/`,
issus de `ml/outputs/`, sans entraîner de modèle.

Consulter son README pour l’installation, le lancement local ou avec Docker,
la mise à jour des données et la connexion à n8n.


## Assistant marketing n8n

Le [guide n8n](n8n/README.md) explique l’installation locale avec Docker,
l’import du [workflow](n8n/taiss-tp-final.json), la création des credentials
DeepSeek et du jeton webhook, les tests et la publication. Le workflow interroge
les résultats agrégés, les diagnostics de k et la sensibilité aux retours.
Une mémoire de dix interactions, liée au `sessionId` obligatoire, permet de
reprendre une discussion. L’historique est conservé dans PostgreSQL et survit aux redémarrages. Le
Compose de `n8n/` démarre le frontend, n8n, l’API et PostgreSQL ; le guide explique le
mot de passe local et le credential Postgres à configurer.

Pour démarrer depuis un clone sans réentraîner le modèle, suivre le
[parcours d'installation complet](n8n/README.md#parcours-depuis-un-clone) :
les CSV sont fournis, Compose initialise l'API et PostgreSQL, puis trois
credentials sont à configurer dans n8n. Après une mise à jour du dépôt,
[appliquer aussi le prompt dans n8n](n8n/README.md#mettre-à-jour-un-workflow-déjà-importé)
: le workflow importé n'est pas synchronisé automatiquement avec le fichier JSON.

## Interface web

[RFM studio](frontend/README.md) propose un tableau de bord, les fiches des
segments, une exploration paginée des clients, les diagnostics du modèle et
un assistant conversationnel. Son guide explique le lancement local et les
variables serveur à configurer. Le jeton n8n reste hors du navigateur.

La plateforme complète se lance avec Docker depuis `n8n/` :

```bash
docker compose up --build -d
```

Préparer `n8n/.env` selon le [guide Docker du frontend](frontend/README.md#démarrer-avec-docker),
puis ouvrir <http://127.0.0.1:3001>. Node.js n'est pas requis sur l'hôte.

La vue **Classer un client** attribue un segment à partir de la récence, de la
fréquence et du montant des achats positifs. FastAPI applique les paramètres
figés du modèle exporté par le notebook. Consulter le [contrat de prédiction](api/README.md#classer-un-client)
pour les unités, les limites et la synchronisation du modèle avec les données.

## Interprétation et validation

Les noms des segments décrivent des achats observés : un montant élevé ne
prouve pas une marge élevée, un achat récent ne prouve pas qu'un client est
nouveau, et une récence élevée ne mesure pas une attrition. Les campagnes
proposées sont des hypothèses à tester avec un groupe témoin.

- [Fiche générée de la livraison](docs/current-model.md) : chiffres, périodes et limites du modèle courant.
- [Entraînement et synchronisation](docs/model-lifecycle.md) : livrer ensemble modèle, données et documentation.
- [Recette de l'assistant](n8n/evaluation/README.md) : exactitude, mémoire, concision, pannes et injections.

Le rapport PDF constitue une synthèse datée ; la fiche générée documente les
résultats de la livraison utilisée par la plateforme.
