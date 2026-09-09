# Entraîner et livrer un modèle cohérent

Le notebook, les résultats consommés par l'API et la documentation doivent
correspondre à la même exécution. Les données brutes restent locales ; les
artefacts nécessaires au lancement sont livrés avec le dépôt.

## Exécuter l'analyse

1. Préparer les données suivant [ml/data/README.md](../ml/data/README.md).
2. Installer les dépendances de `ml/requirements.txt` dans un environnement Python dédié.
3. Ouvrir `ml/index.ipynb` avec `ml/` comme répertoire de travail et exécuter toutes les cellules dans l'ordre.
4. Vérifier les diagnostics, les profils et les limites avant d'utiliser les résultats.

`ml/segment_semantics.json` centralise les noms, définitions et recommandations.
Toute modification doit rester justifiée par les profils observés. La dernière
cellule exporte le modèle puis lance automatiquement la synchronisation.
Si l'exécution échoue, ne pas déployer les résultats partiels.

## Synchroniser et vérifier

Depuis la racine, avec Python 3.10 ou supérieur (bibliothèque standard suffisante) :

```bash
python scripts/sync_artifacts.py
python scripts/sync_artifacts.py --check
```

Le script prépare un lot temporaire, vérifie chaque affectation client avec le
modèle figé, les populations, les montants, les périodes, les segments et le
choix commercial. Il vérifie également les définitions et recommandations
contre le référentiel métier. Il génère ensuite :

- `api/data/` : les 13 CSV, le modèle, sa fiche et le manifeste SHA-256.
- `docs/current-model.md` : la même fiche, avec les résultats de cette livraison.

La copie dans `api/data/` ne commence qu'après validation complète du lot.
`--check` ne modifie pas les artefacts livrés et échoue si une copie ou la fiche
documentaire diffère. Le modèle et la livraison ont des identifiants calculés
sur leur contenu, sans date variable qui provoquerait des changements artificiels.
Ces contrôles détectent des incohérences ; ils ne certifient ni la provenance
des données brutes ni la performance future du modèle.

## Tester et démarrer

```bash
api/.venv/bin/python -m unittest discover -s api/tests -v
python -m unittest discover -s n8n/evaluation -v
node --test n8n/tests/workflow.test.mjs
npm --prefix frontend run lint
npm --prefix frontend run build
cd n8n
docker compose up --build -d segmentation-api frontend
curl --fail http://localhost:8000/bundle-info
```

Créer préalablement l'environnement API selon [son guide](../api/README.md).
Le démarrage FastAPI vérifie les empreintes et la cohérence du lot avant de
charger les données en mémoire. Une livraison invalide empêche le démarrage.
Ne pas modifier les fichiers sous une API en cours d'exécution ; reconstruire
et redémarrer après synchronisation. Vérifier ensuite la recette manuelle de
l'interface et la [recette de l'assistant](../n8n/evaluation/README.md).

L'intégration continue vérifie la synchronisation et les tests sans données
Excel brutes ni clé fournisseur. Elle ne relance pas l'entraînement et ne
remplace pas une recette réelle de DeepSeek. Le rapport PDF du travail
collectif est conservé comme archive, sans modification automatique.
