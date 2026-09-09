"""Export JSON des paramètres nécessaires à l'affectation K-means."""
import json
from pathlib import Path
import hashlib

FEATURES = ['Recency', 'Frequency', 'Monetary']


def export_model(rfm, scaler, model, names, audit, output):
    import numpy as np
    import sklearn
    caps = rfm[FEATURES].quantile(0.99)
    transformed = (np.log1p(rfm[FEATURES].clip(upper=caps, axis=1)).to_numpy() - scaler.mean_) / scaler.scale_
    labels = np.argmin(((transformed[:, None, :] - model.cluster_centers_) ** 2).sum(axis=2), axis=1)
    if not np.array_equal(labels, model.labels_):
        raise ValueError('Le modèle exporté ne reproduit pas les affectations entraînées.')
    payload = {
        'schema_version': 1,
        'algorithm': 'KMeans', 'k': int(model.n_clusters),
        'features': FEATURES, 'currency': 'GBP',
        'policy': 'positive_purchases',
        'preprocessing': {'quantile': 0.99, 'upper_caps': caps.to_list(), 'log': 'log1p', 'mean': scaler.mean_.tolist(), 'scale': scaler.scale_.tolist()},
        'centers': model.cluster_centers_.tolist(),
        'segments': {str(int(k)): v for k, v in names.items()},
        'training': { 'clients': len(rfm), 'seed': int(model.random_state), 'n_init': int(model.n_init), 'sklearn_version': sklearn.__version__, **{k: str(audit[k]) for k in ['window_start', 'window_end', 'reference_date']} },
    }
    semantics = json.loads((Path(__file__).parent / 'segment_semantics.json').read_text())
    payload['segment_definitions'] = {v['name']: v['description'] for v in semantics.values()}
    payload['model_id'] = 'rfm-' + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    Path(output).write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    return payload


if __name__ == '__main__':
    # Reproduire le modèle final depuis les RFM livrés et refuser toute divergence.
    import numpy as np
    import pandas as pd
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    base = Path(__file__).resolve().parent / 'outputs'
    rfm = pd.read_csv(base / 'rfm_clients_segments.csv')
    values = np.log1p(rfm[FEATURES].clip(upper=rfm[FEATURES].quantile(0.99), axis=1))
    scaler = StandardScaler().fit(values)
    model = KMeans(n_clusters=5, random_state=42, n_init=100).fit(scaler.transform(values))
    if not np.array_equal(model.labels_, rfm.Cluster.to_numpy()):
        raise ValueError('Les clusters diffèrent des CSV. Réexécuter le notebook pour exporter son modèle réel.')
    names = rfm[['Cluster', 'segment_name']].drop_duplicates().set_index('Cluster').segment_name.to_dict()
    audit = pd.read_csv(base / 'audit_retours.csv').iloc[0]
    export_model(rfm, scaler, model, names, audit, base / 'rfm_model.json')
    print(f'Modèle exporté : {len(rfm)} affectations identiques aux CSV.')
