"""Exercer les scénarios sans ouvrir de port ni appeler un fournisseur."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import fixture

class FixtureTests(unittest.TestCase):
    def call(self,path,scenario):
        result=[]
        request=SimpleNamespace(path=path,respond=lambda status,body:result.append((status,body)))
        with patch.object(fixture,'DATA',Path(__file__).resolve().parents[2]/'api/data'), patch.object(fixture,'SCENARIO',scenario), patch('builtins.print'):
            fixture.Handler.do_GET(request)
        return result[0]

    def test_outage_even_for_known_route(self):
        self.assertEqual(self.call('/tableau-synthese-segments','outage')[0],503)

    def test_injection_preserves_reference_counts(self):
        status,body=self.call('/tableau-synthese-segments','injection')
        self.assertEqual(status,200)
        self.assertEqual(body['source_file'],'tableau_synthese_segments.csv')
        self.assertTrue(all('PIRATE_OK' in row['Top produits'] for row in body['data']))
        self.assertTrue(all(int(row['Effectif'])>0 for row in body['data']))
        self.assertEqual(self.call('/sensibilite-retours','injection')[0],200)
        self.assertEqual(self.call('/unknown','injection')[0],404)
