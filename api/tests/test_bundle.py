"""La livraison doit refuser les fichiers altérés, même avec des hashes recalculés."""
import csv
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bundle import verify_bundle, create_manifest
from client_query import export_csv


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)/'data'
        shutil.copytree(Path(__file__).resolve().parents[1]/'data', self.folder)

    def rehash(self):
        (self.folder/'manifest.json').write_text(json.dumps(create_manifest(self.folder)))

    def test_current_delivery(self):
        self.assertTrue(verify_bundle(self.folder)['bundle_id'].startswith('bundle-'))

    def test_tampered_file(self):
        with (self.folder/'evaluation_k.csv').open('a') as f: f.write('\n')
        with self.assertRaises(ValueError): verify_bundle(self.folder)

    def test_missing_file(self):
        (self.folder/'evaluation_k.csv').unlink()
        with self.assertRaises(OSError): verify_bundle(self.folder)

    def test_forged_counts_with_valid_hashes(self):
        path = self.folder/'tableau_synthese_segments.csv'
        with path.open(encoding='utf-8-sig') as f:
            reader = csv.DictReader(f); fields=reader.fieldnames; rows=list(reader)
        rows[0]['Effectif']='1'
        with path.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader(); writer.writerows(rows)
        self.rehash()
        with self.assertRaisesRegex(ValueError,'Effectif'): verify_bundle(self.folder)

    def test_stale_documentation_with_valid_hashes(self):
        with (self.folder/'model-card.md').open('a') as f: f.write('stale\n')
        self.rehash()
        with self.assertRaisesRegex(ValueError,'Fiche'): verify_bundle(self.folder)

    def test_changed_centroid(self):
        path=self.folder/'rfm_model.json'; model=json.loads(path.read_text())
        model['centers'][0][0]+=1; path.write_text(json.dumps(model)); self.rehash()
        with self.assertRaisesRegex(ValueError,'Identifiant'): verify_bundle(self.folder)

    def test_csv_formula_protection(self):
        result=export_csv([{'text':'=SUM(A1:A2)','amount':-10},{'text':' @cmd','amount':2}],['text','amount'])
        rows=list(csv.DictReader(io.StringIO(result.lstrip('\ufeff')),delimiter=';'))
        self.assertEqual(rows[0],{'text':"'=SUM(A1:A2)",'amount':'-10'})
        self.assertTrue(rows[1]['text'].startswith("'"))
