# Données sources

Le notebook utilise le jeu **UCI Online Retail II**. Les fichiers Excel sont
conservés en local et exclus du suivi Git.

## Installation

1. Télécharger l’[archive ZIP depuis UCI](https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip).
2. Extraire `online_retail_II.xlsx` dans ce dossier, au chemin
   `ml/data/online_retail_II.xlsx` depuis la racine du projet.
3. Conserver les deux feuilles `Year 2009-2010` et `Year 2010-2011` :
   le notebook les charge et les concatène.
4. Exécuter `ml/index.ipynb` avec `ml/` comme répertoire de travail.

Le fichier `online_retail_II-copy.xlsx` n’est pas nécessaire à l’exécution.

## Source et licence

Chen, D. (2012). *Online Retail II*. UCI Machine Learning Repository.
[DOI : 10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D).
Données sous licence **CC BY 4.0**.

Voir le [sujet du TP](../../docs/tp2-f1-segmentation-clients-rfm.md)
pour le schéma des données et les consignes d’analyse.
