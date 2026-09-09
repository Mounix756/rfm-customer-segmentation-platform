"""Contrat de livraison des résultats, du modèle et de leur fiche documentaire."""
import csv
import hashlib
import json
import math
from pathlib import Path

DATA_FILES = tuple(name + '.csv' for name in (
    'rfm_clients_segments', 'tableau_synthese_segments', 'recommandations_segments',
    'evaluation_k', 'choix_k', 'profils_k_candidats', 'comparaison_k4_k5',
    'audit_retours', 'sensibilite_retours', 'migrations_retours', 'retours_par_segment',
    'profils_politiques_retours', 'stabilite_sensibilite_retours'))
ARTIFACTS = (*DATA_FILES, 'rfm_model.json', 'model-card.md')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def rows(folder, name):
    with (Path(folder) / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def validate_content(folder):
    from prediction import predict
    folder = Path(folder)
    model = json.loads((folder / 'rfm_model.json').read_text())
    content = {k:v for k,v in model.items() if k != 'model_id'}
    if model['model_id'] != 'rfm-' + digest(json.dumps(content, sort_keys=True).encode())[:16]:
        raise ValueError('Identifiant du modèle périmé')
    clients = rows(folder, 'rfm_clients_segments.csv')
    if len(clients) != model['training']['clients'] or len({r['CustomerID'] for r in clients}) != len(clients):
        raise ValueError('Population incohérente')
    counts, amounts, sums = {}, {}, {}
    for r in clients:
        values = [float(r[k]) for k in model['features']]
        if any(not math.isfinite(v) for v in values): raise ValueError('Valeur RFM non finie')
        result = predict(values, model)
        if result['cluster'] != int(r['Cluster']) or result['segment'] != r['segment_name']:
            raise ValueError('Le modèle et les affectations CSV divergent')
        segment = r['segment_name']
        counts[segment] = counts.get(segment, 0) + 1
        amounts[segment] = amounts.get(segment, 0) + float(r['Monetary'])
        sums.setdefault(segment, [0.0, 0.0, 0.0])
        sums[segment] = [a+b for a,b in zip(sums[segment], values)]
    expected = set(model['segments'].values())
    if len(expected) != model['k'] or set(model['segment_definitions']) != expected:
        raise ValueError('Noms de segments incohérents')
    for name in ['tableau_synthese_segments.csv', 'recommandations_segments.csv']:
        data = rows(folder, name)
        if len(data) != model['k'] or {r['Segment'] for r in data} != expected: raise ValueError('Segments manquants ou dupliqués')
        for r in data:
            if int(r['Effectif']) != counts[r['Segment']]: raise ValueError('Effectif de segment incohérent')
            for i, column in enumerate(['Recence_moy', 'Frequence_moy', 'Montant_moy'] if name == 'tableau_synthese_segments.csv' else []):
                if not math.isclose(float(r[column]), sums[r['Segment']][i]/counts[r['Segment']], abs_tol=1e-7):
                    raise ValueError('Profil moyen incohérent')
            if not math.isclose(float(r['Pct_CA']), 100*amounts[r['Segment']]/sum(amounts.values()), abs_tol=1e-7): raise ValueError('Part de CA incohérente')
    audit = rows(folder, 'audit_retours.csv')[0]
    if any(str(model['training'][k]) != audit[k] for k in ['window_start','window_end','reference_date']): raise ValueError('Périodes incohérentes')
    if int(audit['common_clients']) != len(clients) or not math.isclose(float(audit['gross_amount_GBP']), sum(amounts.values()), abs_tol=1e-5): raise ValueError('Périmètre monétaire incohérent')
    choices = rows(folder,'choix_k.csv')
    if int(next(r['k'] for r in choices if r['Critère']=='Choix commercial')) != model['k']: raise ValueError('Choix commercial incohérent')
    for name, column in [('retours_par_segment.csv','Segment_gross'), ('migrations_retours.csv','Segment_gross')]:
        if {r[column] for r in rows(folder,name)} != expected: raise ValueError('Segments de retours incohérents')
    comparison = rows(folder,'sensibilite_retours.csv')[0]
    if int(comparison['common_clients']) != len(clients): raise ValueError('Population de comparaison incohérente')
    matrix = rows(folder, 'migrations_retours.csv')
    migrated = 0
    for r in matrix:
        name = r['Segment_gross']
        if set(r) != expected | {'Segment_gross'} or sum(int(r[n]) for n in expected) != counts[name]:
            raise ValueError('Matrice de migration incohérente')
        migrated += counts[name] - int(r[name])
    if migrated != int(comparison['migrated_clients']) or not math.isclose(100*migrated/len(clients), float(comparison['migrated_pct']), abs_tol=1e-7):
        raise ValueError('Migration totale incohérente')
    for r in rows(folder, 'retours_par_segment.csv'):
        matching = next(m for m in matrix if m['Segment_gross'] == r['Segment_gross'])
        if int(r['Clients']) != counts[r['Segment_gross']] or int(r['Clients_migres']) != int(r['Clients'])-int(matching[r['Segment_gross']]):
            raise ValueError('Migration de segment incohérente')
    return model


def model_card(folder):
    model = json.loads((Path(folder)/'rfm_model.json').read_text())
    summary = rows(folder, 'tableau_synthese_segments.csv')
    audit = rows(folder, 'audit_retours.csv')[0]
    sensitivity = rows(folder, 'sensibilite_retours.csv')[0]
    text = f'''# Fiche de la livraison RFM

Fichier généré par `python scripts/sync_artifacts.py`. Ne pas modifier à la main.

- Modèle : `{model['model_id']}` ; K-means, k={model['k']}.
- Population : {model['training']['clients']} clients avec achats positifs.
- Fenêtre : {audit['window_start']} au {audit['window_end']}.
- Date de référence : {audit['reference_date']}.
- Devise : GBP (livres sterling). CA positif : {float(audit['gross_amount_GBP']):.2f} GBP.
- Prétraitement : plafonds au 99e percentile, log1p, StandardScaler figé.
- Entraînement : scikit-learn {model['training']['sklearn_version']}, seed={model['training']['seed']}, n_init={model['training']['n_init']}.

## Segments observés

| Segment | Clients | Part CA (%) | Récence moyenne (jours) | Factures moyennes | Montant moyen (GBP) |
| --- | ---: | ---: | ---: | ---: | ---: |
'''
    for r in summary:
        text += f"| {r['Segment']} | {r['Effectif']} | {float(r['Pct_CA']):.2f} | {float(r['Recence_moy']):.2f} | {float(r['Frequence_moy']):.2f} | {float(r['Montant_moy']):.2f} |\n"
    text += '\nLes noms sont relatifs à cette partition. Ils ne mesurent ni marge, ni fidélité future, ni attrition, ni nouveauté du client.\n\n'
    for name, definition in model['segment_definitions'].items(): text += f'- **{name}** : {definition}\n'
    text += '\n## Choix de k\n\n'
    for r in rows(folder,'choix_k.csv'): text += f"- {r['Critère']} : {r['k']}.\n"
    text += '\nLe choix commercial est une hypothèse à évaluer par des campagnes contrôlées ; aucun gain de marge n’est mesuré.\n'
    text += f"\n## Sensibilité aux retours\n\nARI : {float(sensitivity['ari']):.4f}. Clients migrés après appariement : {sensitivity['migrated_clients']} ({float(sensitivity['migrated_pct']):.2f} %). R, F, population et prétraitement sont figés ; seul M devient net. Les noms des groupes nets sont des repères et ne décrivent pas des changements de valeur validés.\n"
    text += '\n## Classement et limites\n\nLes trois dates de la fenêtre et de référence sont obligatoires. Une autre période impose le mode simulation, sans annualisation ni probabilité de confiance. Reproduire les affectations existantes vérifie l’implémentation, pas la performance future.\n'
    text += '\n## Provenance\n\nTables : ' + ', '.join(f'`{n}`' for n in DATA_FILES) + '. Les empreintes des fichiers sont enregistrées dans `manifest.json`. Le rapport PDF du travail collectif est une archive et ne remplace pas cette fiche générée.\n'
    return text


def create_manifest(folder):
    folder = Path(folder)
    files = {name: digest((folder/name).read_bytes()) for name in ARTIFACTS}
    return {'schema_version':1, 'bundle_id':'bundle-'+digest(json.dumps(files,sort_keys=True).encode())[:16], 'files': files}


def verify_bundle(folder):
    folder = Path(folder)
    manifest = json.loads((folder/'manifest.json').read_text())
    if manifest != create_manifest(folder): raise ValueError('Empreintes de livraison invalides : synchroniser les artefacts')
    model = validate_content(folder)
    if (folder/'model-card.md').read_text() != model_card(folder): raise ValueError('Fiche du modèle périmée')
    return { 'bundle_id':manifest['bundle_id'], 'model_id':model['model_id'] }
