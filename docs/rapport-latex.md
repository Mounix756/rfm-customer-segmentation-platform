# Rapport LaTeX

Le fichier [rapport-segmentation-rfm.tex](rapport-segmentation-rfm.tex) contient
la version actualisée du mini-rapport : travail collectif, méthode, choix de k,
segments, vérification des retours, extensions et limites. Il est autonome et
ne nécessite ni image externe ni fichier bibliographique.

## Avec Overleaf

1. Créer un projet vide et importer `rapport-segmentation-rfm.tex`.
2. Sélectionner ce fichier comme document principal et choisir le compilateur pdfLaTeX.
3. Recompiler, vérifier la mise en page et télécharger le PDF.

## En local

Avec une distribution LaTeX comprenant pdfLaTeX, le français et les packages
utilisés dans le préambule, exécuter depuis la racine du dépôt :

```bash
mkdir -p /tmp/rfm-rapport-build
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=/tmp/rfm-rapport-build docs/rapport-segmentation-rfm.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=/tmp/rfm-rapport-build docs/rapport-segmentation-rfm.tex
```

Le PDF se trouve dans `/tmp/rfm-rapport-build/rapport-segmentation-rfm.pdf`.
Les coupures prévues organisent le document en trois pages ; vérifier le rendu
avec le compilateur utilisé avant remise.

Le [PDF du rapport](Min_Rapport_du_Projet_Final_de_TAISS_2026.pdf) est disponible
dans `docs/`. Les chiffres de cette
version LaTeX correspondent à la livraison indiquée en fin de rapport : ils
ne sont pas actualisés automatiquement. Après réentraînement, comparer le
texte et les tableaux à [la fiche générée](current-model.md) avant compilation.
