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

La sélection de `k` compare l’inertie, la silhouette, les indices
Calinski–Harabasz et Davies–Bouldin, ainsi que la stabilité entre graines.
Le compromis statistique est distingué du choix commercial de cinq segments.
Une comparaison des profils à quatre et cinq segments documente ce choix ;
son bénéfice commercial reste à valider par des campagnes.

- `ml/requirements.txt` : dépendances Python.
- `ml/data/` : fichiers de données sources.
- `ml/outputs/` : tables CSV et image des recommandations.
- Le [rapport de segmentation](<docs/Min Rapport synthetique segmentation des clienteles.pdf>) se trouve dans `docs/`.

Exécuter le notebook avec `ml/` comme répertoire de travail : ses chemins
`data/` et `outputs/` sont relatifs à ce dossier.

Les diagnostics sont exportés dans `evaluation_k.csv`, `choix_k.csv`,
`profils_k_candidats.csv` et `comparaison_k4_k5.csv` sous `ml/outputs/`.
Le rapport PDF, rédigé séparément, doit être actualisé pour intégrer ces analyses.

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
segments et les recommandations marketing. Elle lit les CSV de `api/data/`,
issus de `ml/outputs/`, sans entraîner de modèle.

Consulter son README pour l’installation, le lancement local ou avec Docker,
la mise à jour des données et la connexion à n8n.
