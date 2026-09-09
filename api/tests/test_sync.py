"""Synchronisation sur une copie temporaire du projet, sans modifier la livraison."""
import contextlib
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import sync_artifacts


class SynchronizationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'api/data',self.root/'api/data')
        shutil.copytree(ROOT/'api/data',self.root/'ml/outputs')
        shutil.copyfile(ROOT/'ml/segment_semantics.json',self.root/'ml/segment_semantics.json')
        (self.root/'docs').mkdir()
        shutil.copyfile(ROOT/'docs/current-model.md',self.root/'docs/current-model.md')

    def run_sync(self,check=False):
        with patch.object(sync_artifacts,'ROOT',self.root),contextlib.redirect_stdout(io.StringIO()):
            sync_artifacts.synchronize(check)

    def test_documentation_drift_detected_and_repaired(self):
        self.run_sync(check=True)
        (self.root/'docs/current-model.md').write_text('Périmé')
        with self.assertRaisesRegex(ValueError,'Documentation'): self.run_sync(check=True)
        self.run_sync()
        self.run_sync(check=True)

    def test_invalid_source_does_not_change_delivery(self):
        original=(self.root/'api/data/rfm_model.json').read_bytes()
        (self.root/'ml/outputs/rfm_model.json').write_text('{}')
        with self.assertRaises((KeyError,ValueError)): self.run_sync()
        self.assertEqual((self.root/'api/data/rfm_model.json').read_bytes(),original)

    def test_additional_files_preserved(self):
        extra=self.root/'api/data/local-note.txt';extra.write_text('À conserver')
        self.run_sync()
        self.assertEqual(extra.read_text(),'À conserver')

    def test_documentation_failure_restores_data(self):
        real_replace=sync_artifacts.os.replace
        def replace(source,target):
            if Path(target)==self.root/'docs/current-model.md': raise OSError('Écriture documentaire impossible')
            return real_replace(source,target)
        original=(self.root/'api/data/manifest.json').read_bytes()
        with patch.object(sync_artifacts.os,'replace',side_effect=replace):
            with self.assertRaises(OSError):self.run_sync()
        self.assertEqual((self.root/'api/data/manifest.json').read_bytes(),original)
        self.run_sync(check=True)
