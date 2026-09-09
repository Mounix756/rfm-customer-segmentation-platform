"""Vérifications ASGI des routes réelles, sans port réseau ni service externe."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import quote, urlencode
from unittest.mock import patch

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))
import main


def csv_rows(name):
    with (API_DIR / 'data' / f'{name}.csv').open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bundle import verify_bundle
        main.app.state.bundle = verify_bundle(main.DATA_DIR)

    def request(self, path, params=None, body=None):
        import asyncio
        from urllib.parse import unquote
        async def call():
            sent = []
            payload = json.dumps(body).encode() if body is not None else b''
            received = False
            async def receive():
                nonlocal received
                if not received:
                    received = True
                    return {'type': 'http.request', 'body': payload, 'more_body': False}
                await asyncio.Future()
            async def send(message): sent.append(message)
            scope = {'type':'http', 'asgi':{'version':'3.0'}, 'http_version':'1.1',
                     'method':'POST' if body is not None else 'GET', 'scheme':'http',
                     'path':unquote(path), 'raw_path':path.encode(), 'root_path':'',
                     'query_string':urlencode(params or {}).encode(),
                     'headers':[(b'content-type', b'application/json')],
                     'server':('test',80), 'client':('test',1234)}
            task = asyncio.create_task(main.app(scope, receive, send))
            # Garder la boucle active même dans les environnements qui filtrent
            # les notifications par socket entre threads.
            for _ in range(2000):
                if task.done(): break
                await asyncio.sleep(0.005)
            else:
                task.cancel()
                raise TimeoutError('Réponse ASGI absente après 10 secondes')
            await task
            status = next(m['status'] for m in sent if m['type']=='http.response.start')
            headers = dict(next(m['headers'] for m in sent if m['type']=='http.response.start'))
            raw = b''.join(m.get('body',b'') for m in sent if m['type']=='http.response.body')
            return status, headers, raw
        return asyncio.run(call())

    def get(self, path, params=None):
        status, _, raw = self.request(path, params)
        return status, json.loads(raw)

    def period(self):
        training = self.get('/model-info')[1]['training']
        return {name: str(training[key])[:10] for name,key in [
            ('observation_start','window_start'), ('observation_end','window_end'), ('reference_date','reference_date')]}

    def post(self, body):
        status, _, raw = self.request('/predict', body=body)
        return status, json.loads(raw)

    def test_existing_routes(self):
        for route, dataset in [
            ('recommandations-segments', 'recommandations_segments'),
            ('rfm-clients-segments', 'rfm_clients_segments'),
            ('tableau-synthese-segments', 'tableau_synthese_segments'),
        ]:
            with self.subTest(route=route):
                status, body = self.get('/' + route, {'limit': 2, 'offset': 1})
                self.assertEqual(status, 200)
                self.assertEqual(len(body['data']), 2)
                self.assertEqual(body['pagination']['total'], len(csv_rows(dataset)))
                self.assertEqual(body['source_file'], dataset + '.csv')

    def test_metrics_and_choices_match_exports(self):
        for route, dataset in [('evaluation-k', 'evaluation_k'), ('choix-k', 'choix_k')]:
            status, body = self.get('/' + route)
            self.assertEqual(status, 200)
            expected = csv_rows(dataset)
            self.assertEqual([r['k'] for r in body['data']], [int(r['k']) for r in expected])
        _, body = self.get('/evaluation-k')
        self.assertIsNone(body['data'][0]['inertia_gain_pct'])
        self.assertAlmostEqual(body['data'][0]['silhouette'], float(csv_rows('evaluation_k')[0]['silhouette']))

    def test_candidate_comparison(self):
        status, body = self.get('/comparaison-segmentations')
        self.assertEqual(status, 200)
        self.assertEqual(set(body), {'profils', 'correspondance_k4_k5'})
        counts = body['correspondance_k4_k5']['data']
        total = sum(sum(v for k, v in row.items() if k != 'Cluster_k4') for row in counts)
        self.assertEqual(total, len(csv_rows('rfm_clients_segments')))

    def test_returns_sections_and_conservation(self):
        status, body = self.get('/sensibilite-retours')
        self.assertEqual(status, 200)
        self.assertEqual(set(body), {'audit', 'comparaison', 'migrations', 'par_segment', 'profils', 'stabilite'})
        for section in body.values():
            self.assertTrue(section['source_file'].endswith('.csv'))
        comparison = body['comparaison']['data'][0]
        self.assertAlmostEqual(comparison['ari'], float(csv_rows('sensibilite_retours')[0]['ari']))
        rows = body['migrations']['data']
        self.assertEqual(sum(sum(v for k, v in row.items() if k != 'Segment_gross') for row in rows), comparison['common_clients'])
        self.assertEqual(sum(r['Clients_migres'] for r in body['par_segment']['data']), comparison['migrated_clients'])
        self.assertEqual(len(body['stabilite']['data']), 10)

    def test_filter_before_pagination_and_statistics(self):
        expected = [r for r in csv_rows('rfm_clients_segments') if r['segment_name'] == 'Achats anciens']
        status, body = self.get('/rfm-clients-segments', {'segment': '  ACHATS ANCIENS  ', 'limit': 3, 'offset': 2})
        self.assertEqual(status, 200)
        self.assertEqual(body['pagination']['total'], len(expected))
        self.assertEqual(body['statistics']['row_count'], len(expected))
        self.assertEqual([str(r['CustomerID']) for r in body['data']], [r['CustomerID'] for r in expected[2:5]])
        self.assertAlmostEqual(body['statistics']['numeric']['Monetary']['sum'], sum(float(r['Monetary']) for r in expected), places=3)
        _, empty = self.get('/rfm-clients-segments', {'segment': 'Achats anciens', 'offset': len(expected)})
        self.assertEqual(empty['data'], [])
        self.assertEqual(empty['pagination']['total'], len(expected))

    def test_segment_detail_for_every_segment(self):
        for expected in csv_rows('tableau_synthese_segments'):
            name = expected['Segment']
            with self.subTest(segment=name):
                status, body = self.get('/segments/' + quote(name.casefold(), safe=''))
                self.assertEqual(status, 200)
                self.assertEqual(body['segment'], name)
                self.assertEqual(body['synthese']['Effectif'], int(expected['Effectif']))
                self.assertEqual(body['recommandation']['Segment'], name)
                self.assertEqual(body['effet_retours']['Segment_gross'], name)
                self.assertEqual(len(body['sources']), 4)
                self.assertTrue(body['definition'])

    def test_errors(self):
        for path, params, expected in [
            ('/rfm-clients-segments', {'segment': 'inconnu'}, 404),
            ('/segments/inconnu', None, 404),
            ('/rfm-clients-segments', {'segment': ''}, 422),
            ('/evaluation-k', {'limit': 0}, 422),
            ('/choix-k', {'offset': -1}, 422),
            ('/rfm-clients-segments', {'offset': 'abc'}, 422),
        ]:
            with self.subTest(path=path, params=params):
                self.assertEqual(self.get(path, params)[0], expected)

    def test_missing_csv(self):
        main.load_dataset.cache_clear()
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(main.DATASETS, {'evaluation_k': {'file': Path(directory) / 'absent.csv'}}):
                with self.assertRaises(main.HTTPException) as error:
                    main.read_dataset('evaluation_k')
                self.assertEqual(error.exception.status_code, 404)
                self.assertEqual(error.exception.detail, 'Fichier introuvable: absent.csv')
        main.load_dataset.cache_clear()

    def test_discovery_and_openapi(self):
        _, root = self.get('/')
        status, schema = self.get('/openapi.json')
        self.assertEqual(status, 200)
        for route in root['endpoints']:
            self.assertIn(route, schema['paths'])
        params = schema['paths']['/rfm-clients-segments']['get']['parameters']
        self.assertIn('segment', [p['name'] for p in params])

    def test_prediction_http_and_validation(self):
        post = self.post
        row = csv_rows('rfm_clients_segments')[0]
        body = dict(recency=int(row['Recency']), frequency=int(row['Frequency']), monetary=float(row['Monetary']), **self.period())
        status, result = post(body)
        self.assertEqual(status, 200)
        self.assertEqual(result['segment'], row['segment_name'])
        self.assertEqual(result['model_id'], self.get('/model-info')[1]['model_id'])
        for key, value in [('recency', -1), ('frequency', 0), ('frequency', 1.5), ('monetary', 0), ('monetary', -20), ('frequency', True), ('recency', '12')]:
            self.assertEqual(post({**body, key: value})[0], 422)
        self.assertEqual(post({**body, 'other': 1})[0], 422)
        self.assertEqual(post({})[0], 422)

    def test_temporal_contract(self):
        body = dict(recency=30, frequency=2, monetary=500.0, **self.period())
        self.assertTrue(self.post(body)[1]['temporal_context']['matches_training'])
        for change in [{'observation_start':'2009-02-30'}, {'reference_date':body['observation_end']},
                       {'recency':0}, {'recency':900}, {'mode':'autre'}, {'observation_start':'2009-01-01'}]:
            with self.subTest(change=change): self.assertEqual(self.post({**body, **change})[0],422)
        other = {**body, 'observation_start':'2025-01-01', 'observation_end':'2025-01-31', 'reference_date':'2025-02-01'}
        self.assertEqual(self.post(other)[0],422)
        status, result = self.post({**other, 'mode':'simulation'})
        self.assertEqual(status,200)
        self.assertFalse(result['temporal_context']['matches_training'])
        self.assertEqual(result['temporal_context']['observation_days'],31)
        self.assertEqual(self.post({**other,'mode':'simulation','recency':60})[0],422)
        for date_key in self.period():
            missing = dict(body); del missing[date_key]
            self.assertEqual(self.post(missing)[0],422)

    def test_global_search_filters_and_export(self):
        import io
        all_rows = csv_rows('rfm_clients_segments')
        last = all_rows[-1]
        status, result = self.get('/rfm-clients-segments', {'q':last['CustomerID']})
        self.assertEqual(status,200)
        self.assertEqual(result['pagination']['total'],1)
        self.assertEqual(str(result['data'][0]['CustomerID']),last['CustomerID'])
        filters = dict(country='united kingdom', monetary_min=1000, monetary_max=5000,
                       frequency_min=2, recency_max=200, sort_by='Monetary', order='desc', limit=3, offset=2)
        expected = [r for r in all_rows if r['CountryMode']=='United Kingdom' and
                    1000 <= float(r['Monetary']) <= 5000 and int(r['Frequency'])>=2 and int(r['Recency'])<=200]
        expected.sort(key=lambda r:int(r['CustomerID']))
        expected.sort(key=lambda r:float(r['Monetary']),reverse=True)
        status, result = self.get('/rfm-clients-segments',filters)
        self.assertEqual(status,200)
        self.assertEqual(result['pagination']['total'],len(expected))
        self.assertEqual([str(r['CustomerID']) for r in result['data']],[r['CustomerID'] for r in expected[2:5]])
        self.assertAlmostEqual(result['statistics']['numeric']['Monetary']['sum'],sum(float(r['Monetary']) for r in expected),places=4)
        status, headers, raw = self.request('/clients/export',filters)
        self.assertEqual(status,200)
        exported = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),delimiter=';'))
        self.assertEqual([r['CustomerID'] for r in exported],[r['CustomerID'] for r in expected])
        self.assertEqual(int(headers[b'x-total-count']),len(expected))
        self.assertEqual(self.get('/rfm-clients-segments', {'q':'introuvable-xyz'})[1]['data'],[])
        self.assertGreater(self.get('/rfm-clients-segments', {'q':'actifs a montant eleve'})[1]['pagination']['total'],0)
        self.assertEqual(self.get('/clients/filters')[0],200)
        for invalid in [{'recency_min':20,'recency_max':10}, {'sort_by':'secret'}, {'order':'other'},
                        {'limit':501}, {'monetary_min':'nan'}, {'frequency_min':1.5}]:
            self.assertEqual(self.get('/rfm-clients-segments',invalid)[0],422)

    def test_prediction_matches_every_exported_client(self):
        from prediction import load_model, predict
        model = load_model()
        for row in csv_rows('rfm_clients_segments'):
            result = predict([float(row[k]) for k in model['features']], model)
            self.assertEqual(result['cluster'], int(row['Cluster']))
            self.assertEqual(result['segment'], row['segment_name'])
        caps = model['preprocessing']['upper_caps']
        self.assertEqual(predict([x * 2 for x in caps], model)['capped_features'], model['features'])
        self.assertEqual(predict(caps, model)['cluster'], predict([x * 2 for x in caps], model)['cluster'])


if __name__ == '__main__':
    unittest.main()
