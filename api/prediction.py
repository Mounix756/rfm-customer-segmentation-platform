"""Prédiction par centroïde le plus proche avec prétraitement figé."""
import json
import math
from functools import lru_cache
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent / 'data' / 'rfm_model.json'


@lru_cache(maxsize=1)
def load_model():
    model = json.loads(MODEL_PATH.read_text())
    if model['schema_version'] != 1 or model['features'] != ['Recency', 'Frequency', 'Monetary']:
        raise ValueError('Format de modèle incompatible')
    p = model['preprocessing']
    if model['policy'] != 'positive_purchases' or p['log'] != 'log1p':
        raise ValueError('Prétraitement incompatible')
    if any(len(p[k]) != 3 for k in ['upper_caps', 'mean', 'scale']) or len(model['centers']) != model['k']:
        raise ValueError('Dimensions invalides')
    if any(not math.isfinite(x) for k in ['upper_caps', 'mean', 'scale'] for x in p[k]):
        raise ValueError('Paramètres non finis')
    if any(v <= 0 for v in p['scale']) or any(v < 0 for v in p['upper_caps']):
        raise ValueError('Paramètres invalides')
    for i, center in enumerate(model['centers']):
        if len(center) != 3 or any(not math.isfinite(x) for x in center) or str(i) not in model['segments']:
            raise ValueError('Centroïde invalide')
    return model


def predict(values, model):
    p = model['preprocessing']
    capped = [min(v, cap) for v, cap in zip(values, p['upper_caps'])]
    transformed = [(math.log1p(v) - mean) / scale for v, mean, scale in zip(capped, p['mean'], p['scale'])]
    distances = [math.dist(transformed, center) for center in model['centers']]
    cluster = min(range(len(distances)), key=distances.__getitem__)
    return {
        'cluster': cluster, 'segment': model['segments'][str(cluster)],
        'model_id': model['model_id'], 'k': model['k'],
        'input': dict(zip(model['features'], values)),
        'capped_features': [name for name, value, cap in zip(model['features'], values, p['upper_caps']) if value > cap],
        'distance_to_center': distances[cluster],
        'training': model['training'],
        'notice': 'Affectation au centroïde le plus proche, sans probabilité de confiance. Modèle historique : utiliser une période et des définitions RFM comparables.',
    }
