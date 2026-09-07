# Règles de commit

Chaque commit doit correspondre à une modification cohérente et être décrit par un message clair, rédigé en français. Utilisez le format suivant, inspiré de Conventional Commits :

```text
type(portée): description courte
```

La portée est facultative. Elle précise la partie concernée, par exemple `tp2`, `rfm` ou `notebook`.

## Types à utiliser

| Type | Usage |
| --- | --- |
| `docs` | Ajouter ou modifier un sujet, un rapport ou de la documentation. |
| `feat` | Ajouter une fonctionnalité ou une nouvelle étape d'analyse. |
| `fix` | Corriger une erreur dans le code ou les calculs. |
| `refactor` | Réorganiser le code sans modifier son comportement. |
| `test` | Ajouter ou modifier des tests. |
| `style` | Modifier uniquement la présentation du code. |
| `chore` | Modifier la configuration, les dépendances ou l'organisation du projet. |

## Rédaction du message

- Commencez la description par un verbe à l'infinitif : `ajouter`, `corriger`, `documenter`.
- Gardez un titre court, idéalement de 72 caractères maximum, sans point final.
- Décrivez le changement précisément ; évitez les messages comme `update`, `modifications` ou `corrections diverses`.
- Si nécessaire, ajoutez une ligne vide après le titre, puis expliquez la raison du changement et les vérifications réalisées.
- Séparez les changements indépendants en plusieurs commits.

## Exemples

```text
docs(tp2): ajouter le sujet de segmentation clients RFM
docs: documenter les règles de commit
feat(rfm): calculer les indicateurs par client
fix(rfm): compter les factures distinctes pour la fréquence
refactor(notebook): regrouper les étapes de nettoyage
chore: exclure les données brutes du suivi Git
```

## Avant chaque commit

1. Vérifiez les fichiers modifiés avec `git status` et examinez les changements avec `git diff`.
2. Effectuez les vérifications adaptées : relecture pour la documentation, exécution des cellules concernées ou des tests pour le code.
3. N'incluez ni secrets, ni fichiers temporaires, ni données personnelles. Conservez les données brutes volumineuses hors de Git et documentez leur téléchargement.
4. Pour les notebooks, supprimez les sorties inutiles ou volumineuses et vérifiez la cohérence des sorties conservées.
5. Ajoutez explicitement les fichiers concernés, puis relisez le contenu préparé avec `git diff --cached` avant de créer le commit.

Exemple pour une modification de documentation :

```bash
git add docs/regles-de-commit.md
git diff --cached
git commit -m "docs: documenter les règles de commit"
```
