# Plateforme de segmentation clients RFM

Segmentation des clients du jeu UCI Online Retail II à partir de la récence,
de la fréquence et du montant des achats.

## Organisation

- `ml/` : préparation des données, analyse RFM, entraînement et évaluation du
  clustering et résultats.
- `docs/` : sujet du TP, rapport de segmentation et règles de contribution.
- `api/` : API FastAPI exposant les résultats de segmentation en JSON.
- `frontend/` : dossier prévu pour la future interface, pas encore présent.

## Partie machine learning

Le notebook [ml/index.ipynb](ml/index.ipynb) contient le traitement des
transactions, la construction des variables RFM, la comparaison des modèles
K-means et les recommandations marketing.

- `ml/requirements.txt` : dépendances Python.
- `ml/data/` : fichiers de données sources.
- `ml/outputs/` : tables CSV et image des recommandations.
- Le [rapport de segmentation](<docs/Min Rapport synthetique segmentation des clienteles.pdf>) se trouve dans `docs/`.

Exécuter le notebook avec `ml/` comme répertoire de travail : ses chemins
`data/` et `outputs/` sont relatifs à ce dossier.

Le [sujet du TP](docs/tp2-f1-segmentation-clients-rfm.md) décrit les objectifs,
les données et les livrables attendus.

## API

L’[API de segmentation](api/README.md) expose les clients RFM, la synthèse des
segments et les recommandations marketing. Elle lit les CSV de `api/data/`,
issus de `ml/outputs/`, sans entraîner de modèle.

Consulter son README pour l’installation, le lancement local ou avec Docker,
la mise à jour des données et la connexion à n8n.
