"""Vérifications HTTP sur les CSV livrés, avec un serveur local temporaire."""
import csv
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import urlopen
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
        cls.log = tempfile.TemporaryFile()
        cls.listener = socket.socket()
        cls.listener.bind(('127.0.0.1', 0))
        cls.url = f'http://127.0.0.1:{cls.listener.getsockname()[1]}'
        cls.server = subprocess.Popen(
            [sys.executable, '-m', 'uvicorn', 'main:app', '--fd', str(cls.listener.fileno())],
            cwd=API_DIR, pass_fds=(cls.listener.fileno(),), stdout=cls.log, stderr=cls.log,
        )
        cls.addClassCleanup(cls.cleanup_server)
        for _ in range(100):
            try:
                with urlopen(cls.url, timeout=1):
                    return
            except (URLError, TimeoutError):
                if cls.server.poll() is not None:
                    break
                time.sleep(0.1)
        cls.log.seek(0)
        raise RuntimeError(cls.log.read().decode())

    @classmethod
    def cleanup_server(cls):
        cls.server.terminate()
        try:
            cls.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.server.kill()
            cls.server.wait()
        cls.listener.close()
        cls.log.close()

    def get(self, path, params=None):
        url = self.url + path
        if params:
            url += '?' + urlencode(params)
        try:
            with urlopen(url, timeout=10) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

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
        expected = [r for r in csv_rows('rfm_clients_segments') if r['segment_name'] == 'À risque']
        status, body = self.get('/rfm-clients-segments', {'segment': '  À RISQUE  ', 'limit': 3, 'offset': 2})
        self.assertEqual(status, 200)
        self.assertEqual(body['pagination']['total'], len(expected))
        self.assertEqual(body['statistics']['row_count'], len(expected))
        self.assertEqual([str(r['CustomerID']) for r in body['data']], [r['CustomerID'] for r in expected[2:5]])
        self.assertAlmostEqual(body['statistics']['numeric']['Monetary']['sum'], sum(float(r['Monetary']) for r in expected), places=3)
        _, empty = self.get('/rfm-clients-segments', {'segment': 'À risque', 'offset': len(expected)})
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
                self.assertEqual(len(body['sources']), 3)

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


if __name__ == '__main__':
    unittest.main()
