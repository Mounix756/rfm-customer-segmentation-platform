# Plateforme de segmentation clients RFM

Segmentation des clients du jeu UCI Online Retail II à partir de la récence,
de la fréquence et du montant des achats.

## Organisation

- `ml/` : préparation des données, analyse RFM, entraînement et évaluation du
  clustering et résultats.
- `docs/` : sujet du TP, rapport de segmentation et règles de contribution.
- `api/` et `frontend/` : dossiers prévus pour les futurs services et l’interface,
  pas encore présents dans le dépôt.

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
