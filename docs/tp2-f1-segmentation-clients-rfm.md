# 3. TP 2 - Filière F1 : Segmentation clients RFM

> « Comprendre ses clients pour mieux les servir »

**Durée indicative :** 4 h · **Données réelles :** UCI Online Retail II · **Bonus facultatif :** 1 h supplémentaire.

## 3.1 Contexte et problématique

Un e-commerce de cadeaux basé au Royaume-Uni, dont de nombreux clients sont des grossistes, dispose de plus d'un million de lignes de transactions sur deux ans. La direction souhaite personnaliser ses campagnes marketing (courriels, promotions et relances) et réduire l'attrition. Elle ne dispose toutefois pas d'une typologie de ses clients.

Quels clients fidéliser en priorité ? Lesquels relancer ? Comment reconnaître ceux qui deviennent inactifs ? Une meilleure connaissance des comportements d'achat doit permettre de proposer des actions adaptées.

**Votre mission :** construire une segmentation clients à partir de la méthode **RFM : Récence, Fréquence, Montant**, identifier et nommer des segments actionnables, puis formuler des recommandations marketing pour chacun d'eux.

La démarche pourra être adaptée à un e-commerce ouest-africain ou à une plateforme de paiement mobile, en tenant compte des spécificités des transactions et des usages locaux.

## 3.2 Objectifs d'apprentissage

À l'issue du TP, vous devrez être capables de :

1. Nettoyer des transactions réelles et bruitées : annulations, retours, identifiants manquants et valeurs aberrantes.
2. Construire les variables RFM par client et transformer leurs distributions fortement asymétriques.
3. Justifier le nombre de segments à partir de plusieurs critères : silhouette, coude, stabilité et cohérence métier.
4. Interpréter et nommer les segments, puis les caractériser par leur taille, leur contribution au chiffre d'affaires, leur profil RFM, leurs produits et leurs pays.
5. Discuter des limites du clustering et des enjeux éthiques de la personnalisation.

**Prérequis conseillés :** manipulation de tableaux avec pandas, agrégations, visualisation et principes du clustering. Outils possibles : Python, Jupyter, pandas, NumPy, Matplotlib ou Seaborn, scikit-learn et openpyxl pour la lecture Excel.

## 3.3 Données

Le jeu [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) contient **1 067 371 lignes**, couvrant la période du **1er décembre 2009 au 9 décembre 2011**. Une ligne correspond à un article dans une facture ; elle ne représente donc pas nécessairement un achat distinct.

- [Télécharger l'archive ZIP](https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip).
- Fichier à utiliser : `online_retail_II.xlsx`.
- Feuilles à concaténer : `Year 2009-2010` et `Year 2010-2011`.
- Autre accès possible : `fetch_ucirepo(id=502)` depuis le package `ucimlrepo`. Vérifiez que l'import conserve toutes les colonnes nécessaires, notamment les identifiants.

Les noms ci-dessous constituent le schéma de référence du TP. Inspectez les colonnes du fichier : selon le mode d'import, vous pourrez notamment devoir renommer `Invoice` en `InvoiceNo`, `Price` en `UnitPrice` et `Customer ID` en `CustomerID`.

| Colonne de référence | Description |
| --- | --- |
| `InvoiceNo` | Identifiant de facture ; le préfixe `C` signale une annulation. |
| `StockCode` | Code produit, à conserver comme identifiant textuel. |
| `Description` | Libellé du produit. |
| `Quantity` | Quantité portée sur la ligne. |
| `InvoiceDate` | Date et heure de la transaction. |
| `UnitPrice` | Prix unitaire en livres sterling (£). |
| `CustomerID` | Identifiant client, parfois manquant. |
| `Country` | Pays associé au client. |

Calculez le nombre de pays et la part du Royaume-Uni sur les données chargées, en précisant le dénominateur : lignes, clients ou chiffre d'affaires. Ne supposez pas que ces proportions restent identiques après nettoyage.

**Référence à citer :** Chen, D. (2012). *Online Retail II*. UCI Machine Learning Repository. [DOI : 10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D). Données sous licence CC BY 4.0.

## 3.4 Travail demandé - Déroulé indicatif

Les durées proposées totalisent 4 h. Documentez vos décisions au fil du notebook et préparez les éléments du rapport pendant l'analyse.

### Partie 1 - Nettoyage des transactions (50 min)

1. Chargez et concaténez les deux feuilles. Inspectez les dimensions, les types, la période couverte, les valeurs manquantes et les doublons potentiels.
2. Analysez les annulations, les quantités négatives, les prix nuls ou négatifs et les identifiants clients manquants. Distinguez autant que possible les retours des anomalies.
3. Définissez une politique de nettoyage explicite : quelles lignes exclure, conserver ou analyser séparément ? Justifiez le traitement des doublons ; deux lignes identiques ne constituent pas automatiquement une erreur.
4. Examinez les valeurs extrêmes. Un achat important peut correspondre à un grossiste légitime : toute suppression ou limitation doit être motivée.
5. Calculez le montant de chaque ligne : `Quantity × UnitPrice`. Produisez un bilan des lignes et clients conservés ou exclus à chaque étape.

**Convention de départ :** vous pouvez construire le RFM principal sur les achats valides, avec client identifié, quantité et prix strictement positifs, hors factures d'annulation. Dans ce cas, le montant représente les achats retenus, sans déduction des retours. Conservez les données utiles à une analyse de sensibilité et expliquez cette limite.

**Attendu :** un tableau de transactions nettoyées et un bilan chiffré du nettoyage.

### Partie 2 - Construction et transformation des variables RFM (45 min)

1. Fixez une fenêtre d'observation commune et une date de référence, par exemple le lendemain de la dernière date de cette fenêtre. Documentez ces choix.
2. Construisez une table contenant une ligne par client :

| Variable | Définition attendue | Unité |
| --- | --- | --- |
| **R - Récence** | Nombre de jours entre la date de référence et le dernier achat valide du client. | Jours |
| **F - Fréquence** | Nombre de factures d'achat distinctes dans la fenêtre d'observation. | Factures |
| **M - Montant** | Somme des montants des lignes d'achat retenues pour le client. | £ |

3. Contrôlez l'unicité des clients et la validité des valeurs. Ne confondez pas fréquence d'achat, nombre de lignes et nombre d'articles.
4. Visualisez les distributions et les corrélations des trois variables.
5. Appliquez une transformation adaptée à l'asymétrie, par exemple `log1p`, puis une standardisation. Vérifiez le domaine de validité de la transformation, en particulier si vous retenez un montant net pouvant être négatif.
6. Conservez les variables originales pour l'interprétation métier et les variables transformées pour le clustering. Expliquez le rôle de chaque transformation.

**Attendu :** une table RFM vérifiée, des visualisations avant et après transformation et une description du prétraitement.

### Partie 3 - Clustering et choix de k (60 min)

1. Appliquez K-means aux variables RFM transformées et standardisées. Documentez les paramètres et fixez une graine aléatoire pour permettre la reproduction.
2. Comparez plusieurs valeurs de `k`, par exemple de 2 à 8, en calculant l'inertie et le score de silhouette.
3. Tracez la courbe du coude et celle de la silhouette. Si vous échantillonnez pour la silhouette, indiquez la taille et la graine de l'échantillon et utilisez une procédure comparable entre les modèles.
4. Évaluez la stabilité pour quelques valeurs candidates en répétant le clustering avec plusieurs graines. Utilisez, par exemple, l'indice de Rand ajusté pour comparer les partitions : les numéros de clusters ne sont pas des identités stables.
5. Examinez les tailles des groupes et leurs profils RFM. Repérez les segments minuscules ou difficiles à distinguer en termes d'action marketing.
6. Retenez un nombre de segments en croisant qualité statistique, stabilité et utilité métier.

**Attendu :** les graphiques de sélection, une comparaison des modèles candidats et une justification écrite du choix final. Aucun nombre de segments n'est imposé.

### Partie 4 - Caractérisation et recommandations (60 min)

1. Associez les segments aux clients, puis aux transactions pour analyser les pays et les produits.
2. Pour chaque segment, calculez l'effectif, la part des clients, la contribution au chiffre d'affaires et les moyennes RFM. Ajoutez les médianes si elles éclairent les distributions.
3. Identifiez les principaux pays et produits en précisant le critère utilisé : chiffre d'affaires, quantité ou nombre de clients.
4. Attribuez à chaque segment un nom fondé sur son profil observé. « Champions », « Clients occasionnels », « Achats anciens » ou « Achats anciens à faible montant » sont des exemples, pas des catégories à imposer au modèle.
5. Proposez une recommandation marketing de une à deux lignes par segment. Reliez chaque action aux résultats et suggérez un indicateur permettant d'en mesurer l'effet.

Pour les parts de chiffre d'affaires, utilisez un périmètre commun et explicite : le total des montants retenus des clients segmentés. Une récence élevée peut signaler une inactivité, mais ne prouve pas à elle seule une attrition.

**Attendu :** un tableau de synthèse, des profils comparables et des recommandations argumentées.

### Partie 5 - Discussion critique et éthique (25 min)

Répondez aux questions de la section 3.7 dans le rapport. Appuyez votre discussion sur les résultats obtenus et distinguez les constats mesurés des hypothèses ou vérifications restant à mener.

Discutez notamment les effets de la fenêtre d'observation, de l'ancienneté des clients, de la saisonnalité, des retours et du poids des grossistes. Proposez des garde-fous concrets pour la personnalisation : limitation des sollicitations, possibilité de refus, protection des données et contrôle des traitements inéquitables.

**Attendu :** une discussion critique reliée à votre segmentation.

## 3.5 Résultat attendu et livrables

À la fin du TP, vous devez disposer d'une segmentation exploitable et documentée comprenant :

1. Un jeu de clients nettoyé avec les variables RFM, les transformations documentées et le segment attribué.
2. Un choix de `k` argumenté par les courbes du coude et de silhouette, une vérification de stabilité et une lecture métier.
3. Des segments nommés et caractérisés dans un tableau de synthèse.
4. Des recommandations marketing par segment, en une à deux lignes chacune.
5. Un rapport de **2 à 3 pages** présentant la méthode, les choix, les résultats, les limites et les réponses aux questions.

### Modèle de tableau de synthèse

Les noms ci-dessous sont illustratifs. Adaptez les lignes à vos résultats et indiquez les unités ainsi que les critères de classement des pays et produits.

| Segment | Effectif | % CA | Récence moy. (jours) | Fréquence moy. (factures) | Montant moy. (£) | Top pays / produits |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Champions, si ce profil est observé | … | … | … | … | … | … |
| Achats anciens, si ce profil est observé | … | … | … | … | … | … |
| Autre segment à nommer | … | … | … | … | … | … |

**À remettre :**

- Le notebook complété pour les parties 1 à 4, exécutable de bout en bout, avec commentaires, graphiques et paramètres utilisés.
- La table clients RFM avec les segments, exportée en CSV, sans identifiants ajoutés permettant de retrouver des personnes.
- Le tableau de synthèse des segments et les recommandations associées.
- Le rapport de 2 à 3 pages, incluant la partie 5 et les réponses aux six questions.

Indiquez la source des données, les dépendances nécessaires, les graines aléatoires et la procédure d'exécution. Les résultats du rapport doivent correspondre aux sorties du notebook.

## 3.6 Grille d'évaluation - Sur 100 points

| Rubrique | Points |
| --- | ---: |
| Nettoyage des transactions - Partie 1 | 20 |
| Variables RFM et transformations - Partie 2 | 20 |
| Choix de k et clustering - Partie 3 | 25 |
| Caractérisation et recommandations - Partie 4 | 20 |
| Discussion critique et éthique - Partie 5 | 10 |
| Qualité du rapport et reproductibilité | 5 |
| **Total** | **100** |

L'évaluation porte sur la rigueur des choix, leur justification et la cohérence des conclusions. Un score de silhouette élevé ne suffit pas à lui seul à obtenir une bonne évaluation.

## 3.7 Questions à traiter dans le rapport

1. **Annulations et retours :** leur traitement change-t-il significativement les segments ? Comment le vérifier ? Proposez une comparaison entre deux politiques de traitement, sur un ensemble de clients commun, et précisez les résultats mesurés ou les vérifications restant à mener.
2. **Transformations :** pourquoi ne pas appliquer K-means directement sur les RFM bruts ? Que gagne-t-on avec une transformation logarithmique suivie d'une standardisation ? Quelles limites subsistent ?
3. **Redondance :** Fréquence et Montant sont souvent corrélés. Comment évaluer et traiter cette redondance ? Quelles conséquences vos choix peuvent-ils avoir sur l'interprétation ?
4. **Choix de k :** pourquoi la silhouette ne suffit-elle pas ? Discutez la stabilité, la taille des groupes et leur cohérence métier à partir de vos résultats.
5. **Validation sans vérité terrain :** comment défendre la qualité des segments en l'absence d'étiquettes de référence ? Quelles validations complémentaires proposer avant un usage opérationnel ?
6. **Éthique :** la personnalisation peut mener à une tarification différenciée. Quels garde-fous mettre en place pour éviter les pratiques injustes, la sollicitation excessive et l'utilisation abusive des données ?

## 3.8 Bonus facultatif - Interrogation en langage naturel (+ 1 h)

Ajoutez une couche d'interrogation des résultats associant une base vectorielle et un assistant destiné à l'équipe marketing.

Exemples de questions :

- « Combien de clients appartiennent au segment Champions ? »
- « Décris le segment Achats anciens à faible montant. »
- « Quelle part du chiffre d'affaires provient du segment Achats anciens ? »
- « Quelle action recommandes-tu pour les clients occasionnels ? »

Indexez les fiches descriptives des segments pour retrouver les informations pertinentes. Les réponses chiffrées doivent provenir des tables calculées : utilisez une lecture structurée ou une agrégation pour obtenir les valeurs exactes, puis citez le tableau, le segment et la période concernés.

L'assistant doit signaler une information absente et ne pas inventer de chiffres ou de segments. Évitez de transmettre les transactions individuelles lorsqu'une synthèse agrégée suffit.

**Livrable bonus :** une démonstration comprenant au moins trois questions avec des réponses vérifiées, ainsi qu'un exemple de question à laquelle l'assistant ne peut pas répondre à partir des résultats disponibles.
