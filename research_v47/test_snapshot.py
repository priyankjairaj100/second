import json
import os
from pathlib import Path
import tempfile
import unittest
import numpy as np
from research_v46.test_evaluator import fixture
from research_v47.snapshot import write_snapshot,load_snapshot


def full_fixture():
    result=fixture()
    result.config.vocabulary_size=11;result.config.max_sequence_length=8;result.config.block_count=2
    result.config.feedforward_width=8
    return result


class SnapshotTests(unittest.TestCase):
    def test_every_word_and_likelihood_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'snapshot';source=full_fixture();manifest=write_snapshot(source,path)
            actual=load_snapshot(path/'manifest.json',path/'parameters.npz')
            self.assertEqual(len(manifest['arrays']),30)
            np.testing.assert_array_equal(source.logits([1,2,4,3]),actual.logits([1,2,4,3]))
            with self.assertRaises(ValueError):actual.base._tokens([True])

    def test_tampered_word_commitment_refused(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'snapshot';manifest=write_snapshot(full_fixture(),path)
            manifest['arrays']['head']['word_sha256']='0'*64
            (path/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'Parameter words changed'):
                load_snapshot(path/'manifest.json',path/'parameters.npz')

    @unittest.skipUnless(os.environ.get('V47_TEST_EXPORTED_ARRAYS'),'Actual archive check follows CPU export')
    def test_actual_export_on_gpu_runtime_without_inference(self):
        from research_v47.campaign import ROOT,dependencies,validate
        validate(dependencies())
        path=ROOT/'local_runs/cpu-parameters-v47-20261010-a/outputs'
        evaluator=load_snapshot(path/'manifest.json',path/'parameters.npz')
        self.assertEqual(len(evaluator.weights),24)
        self.assertEqual(evaluator.config.vocabulary_size,50257)


if __name__=='__main__':unittest.main()
