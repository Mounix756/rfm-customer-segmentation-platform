# Fiche de la livraison RFM

Fichier généré par `python scripts/sync_artifacts.py`. Ne pas modifier à la main.

- Modèle : `rfm-3ab5423591563489` ; K-means, k=5.
- Population : 5878 clients avec achats positifs.
- Fenêtre : 2009-12-01 07:45:00 au 2011-12-09 12:50:00.
- Date de référence : 2011-12-10 12:50:00.
- Devise : GBP (livres sterling). CA positif : 17685460.64 GBP.
- Prétraitement : plafonds au 99e percentile, log1p, StandardScaler figé.
- Entraînement : scikit-learn 1.9.0, seed=42, n_init=100.

## Segments observés

| Segment | Clients | Part CA (%) | Récence moyenne (jours) | Factures moyennes | Montant moyen (GBP) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Champions | 587 | 59.18 | 18.00 | 28.56 | 17829.92 |
| Actifs à montant élevé | 1250 | 24.12 | 58.36 | 8.56 | 3412.10 |
| Achats anciens | 1335 | 10.10 | 303.15 | 3.56 | 1337.73 |
| Achats récents occasionnels | 1126 | 4.35 | 32.30 | 2.50 | 683.75 |
| Achats anciens à faible montant | 1580 | 2.25 | 416.98 | 1.23 | 252.15 |

Les noms sont relatifs à cette partition. Ils ne mesurent ni marge, ni fidélité future, ni attrition, ni nouveauté du client.

- **Champions** : Groupe présentant les achats les plus fréquents et les montants moyens les plus élevés dans cette partition. Ce nom ne mesure ni fidélité future ni rentabilité.
- **Actifs à montant élevé** : Achats relativement récents et montant moyen élevé par rapport aux autres groupes, hors Champions. Les marges ne sont pas disponibles.
- **Achats anciens** : Dernier achat relativement ancien, avec des montants et fréquences supérieurs au groupe ancien à faible montant. Aucun départ futur n'est prédit.
- **Achats récents occasionnels** : Achats récents et fréquence relativement faible. Le groupe ne permet pas d'affirmer que le client est nouveau.
- **Achats anciens à faible montant** : Achats anciens, faible fréquence et faible montant moyen relativement à cette population. Aucun jugement sur la valeur personnelle du client.

## Choix de k

- Silhouette (maximum) : 2.
- Calinski-Harabasz (maximum) : 2.
- Davies-Bouldin (minimum) : 2.
- Coude géométrique indicatif : 4.
- Compromis statistique (rangs moyens) : 2.
- Choix commercial : 5.

Le choix commercial est une hypothèse à évaluer par des campagnes contrôlées ; aucun gain de marge n’est mesuré.

## Sensibilité aux retours

ARI : 0.5810. Clients migrés après appariement : 1671 (28.43 %). R, F, population et prétraitement sont figés ; seul M devient net. Les noms des groupes nets sont des repères et ne décrivent pas des changements de valeur validés.

## Classement et limites

Les trois dates de la fenêtre et de référence sont obligatoires. Une autre période impose le mode simulation, sans annualisation ni probabilité de confiance. Reproduire les affectations existantes vérifie l’implémentation, pas la performance future.

## Provenance

Tables : `rfm_clients_segments.csv`, `tableau_synthese_segments.csv`, `recommandations_segments.csv`, `evaluation_k.csv`, `choix_k.csv`, `profils_k_candidats.csv`, `comparaison_k4_k5.csv`, `audit_retours.csv`, `sensibilite_retours.csv`, `migrations_retours.csv`, `retours_par_segment.csv`, `profils_politiques_retours.csv`, `stabilite_sensibilite_retours.csv`. Les empreintes des fichiers sont enregistrées dans `manifest.json`. Le rapport PDF du travail collectif est une archive et ne remplace pas cette fiche générée.
