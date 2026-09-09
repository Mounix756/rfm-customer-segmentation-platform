"""Valider puis synchroniser modèle, tables et fiche documentaire en une commande."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'api'))
from bundle import DATA_FILES, model_card, create_manifest, validate_content, verify_bundle


def synchronize(check=False):
    source, target = ROOT/'ml/outputs', ROOT/'api/data'
    semantics = json.loads((ROOT/'ml/segment_semantics.json').read_text())
    with tempfile.TemporaryDirectory(prefix='rfm-sync-', dir=ROOT/'api') as temp:
        stage = Path(temp)/'data'; stage.mkdir()
        for name in (*DATA_FILES, 'rfm_model.json'): shutil.copy2(source/name, stage/name)
        model = validate_content(stage)
        if model['segment_definitions'] != {v['name']:v['description'] for v in semantics.values()}:
            raise ValueError('Définitions métier différentes du modèle : réexporter le modèle')
        from bundle import rows
        expected = {v['name']:v['recommendation'] for v in semantics.values()}
        if {r['Segment']:r['Recommandation marketing'] for r in rows(stage,'recommandations_segments.csv')} != expected:
            raise ValueError('Recommandations différentes du référentiel métier')
        card = model_card(stage)
        (stage/'model-card.md').write_text(card)
        (stage/'manifest.json').write_text(json.dumps(create_manifest(stage),indent=2,ensure_ascii=False)+'\n')
        identity = verify_bundle(stage)
        files = {p.name for p in stage.iterdir()}
        if check:
            if any(not (target/name).exists() or (target/name).read_bytes() != (stage/name).read_bytes() for name in files): raise ValueError('API non synchronisée')
            if (ROOT/'docs/current-model.md').read_text() != card: raise ValueError('Documentation non synchronisée')
            print('Cohérence vérifiée :', identity['bundle_id']); return
        # Aucun fichier existant n'est écrasé avant validation complète du lot.
        # Préserver les fichiers additionnels éventuels dans data/.
        for extra in target.iterdir():
            if extra.name not in files:
                if extra.is_dir(): shutil.copytree(extra, stage/extra.name)
                else: shutil.copy2(extra,stage/extra.name)
        staged_doc = Path(temp)/'current-model.md'
        staged_doc.write_text(card)
        backup = Path(temp)/'previous'
        os.replace(target, backup)
        try:
            os.replace(stage, target)
            os.replace(staged_doc, ROOT/'docs/current-model.md')
        except BaseException:
            if target.exists(): os.replace(target, stage)
            os.replace(backup, target)
            raise
        print('Livraison synchronisée :', identity['bundle_id'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Vérifier sans changer les fichiers livrés')
    args = parser.parse_args()
    try: synchronize(args.check)
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as error:
        print('Échec de synchronisation :', str(error), file=sys.stderr); sys.exit(1)
