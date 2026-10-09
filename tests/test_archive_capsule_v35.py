"""Integrity and target checks on the exported real-data capsule; no model run."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from research_v35.archive_capsule import load_capsule, DELETED, RETAINED
from src.run_store import canonical_json, strict_json

ROOT = Path(__file__).resolve().parents[1]
CAPSULE = ROOT/'data/gram_v35/wikitext-firststage.json'
EXPECTED = '59bf847f2765fc788a93fe53374aa91e7853d2981a18d46b1084d0807cf6c775'


class ArchiveCapsuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT/'tmp').mkdir(exist_ok=True)

    def mutated(self, change):
        value = strict_json(CAPSULE.read_bytes())
        change(value)
        raw = canonical_json(value)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            path = Path(directory)/'capsule.json'
            path.write_bytes(raw)
            return load_capsule(path, hashlib.sha256(raw).hexdigest())

    def test_exact_archived_source_words(self):
        value = load_capsule(CAPSULE, EXPECTED)
        self.assertEqual(value['weights'].shape, (4,768))
        self.assertEqual(value['reference'].shape, (4,768))
        for source in (DELETED, RETAINED):
            descriptor = value['descriptors'][source]
            self.assertEqual(len(descriptor.binary64()), 128*768*8)
            self.assertEqual(hashlib.sha256(descriptor.binary64()).hexdigest(),descriptor.source_sha256)
        self.assertIs(value['retained_descriptor'],value['descriptors'][RETAINED])

    def test_external_capsule_hash_required(self):
        with self.assertRaisesRegex(ValueError,'registered hash'):
            load_capsule(CAPSULE, '0'*64)

    def test_changed_normalization_rejected(self):
        with self.assertRaisesRegex(ValueError,'target differs'):
            self.mutated(lambda x:x.update(normalization=128))

    def test_changed_canonical_scale_rejected(self):
        with self.assertRaisesRegex(ValueError,'scales differ'):
            self.mutated(lambda x:x['scales_hex'].__setitem__(0,'0x1.0000000000000p+0'))

    def test_changed_reference_bytes_rejected(self):
        def change(value):
            raw=value['reference_indices']['base64']
            value['reference_indices']['base64']=('A' if raw[0]!='A' else 'B')+raw[1:]
        with self.assertRaisesRegex(ValueError,'byte hash differs'):
            self.mutated(change)


if __name__ == '__main__':
    unittest.main()
