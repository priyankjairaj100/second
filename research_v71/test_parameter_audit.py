"""Actual tiny NPZ fixtures; no checkpoint, feature generation or inference."""
import io,json,zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
import numpy as np
from research_v47.test_snapshot import full_fixture
from research_v47.snapshot import write_snapshot
from research_v71 import parameter_audit as p
from research_v67.io import info
from src.run_store import canonical_json


def call(root,reference):
    return p.verify(reference,root/'manifest.json',root/'parameters.npz',
        expected_manifest=info((root/'manifest.json').read_bytes()),expected_archive=info((root/'parameters.npz').read_bytes()))


class ParameterAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name).resolve()/'snapshot';self.reference=full_fixture()
        write_snapshot(self.reference,self.root)
    def tearDown(self):self.temp.cleanup()

    def test_every_saved_field_and_word_is_checked(self):
        result=call(self.root,self.reference)
        self.assertTrue(result['actual_all_parameter_words_equal']);self.assertEqual(result['arrays'],30)
        self.assertTrue(result['includes_embeddings_positions_norm_bias_head_and_stage_weights'])
        self.assertFalse(result['gpu_transfer_checked']);self.assertFalse(result['quality_evaluation'])

    def test_changed_embedding_norm_bias_and_head_words_refuse_even_with_new_archive_hash(self):
        path=self.root/'parameters.npz';original=path.read_bytes();manifest=json.loads((self.root/'manifest.json').read_bytes())
        for name in ['embeddings','positions','blocks/0/norm1_scale','blocks/1/qkv_bias','head','head_bias','final_scale','weights/block.0001.mlp_down']:
            path.write_bytes(original)
            with np.load(path,allow_pickle=False) as archive:arrays={k:archive[k] for k in archive.files}
            a=arrays[manifest['arrays'][name]['key']];a.flat[0]=np.nextafter(a.flat[0],float('inf'))
            np.savez(path,**arrays)
            with self.subTest(field=name),self.assertRaisesRegex(ValueError,'Actual saved parameter words'):call(self.root,self.reference)

    def test_extra_missing_duplicate_and_compressed_members_refuse(self):
        path=self.root/'parameters.npz'
        with zipfile.ZipFile(path) as z:members=[(i.filename,z.read(i)) for i in z.infolist()]
        cases=[members+[('extra.npy',members[0][1])],members[:-1],members[:-1]+[members[0]]]
        for selected in cases:
            with zipfile.ZipFile(path,'w') as z:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore',UserWarning)
                    for name,raw in selected:z.writestr(name,raw)
            with self.assertRaises(ValueError):call(self.root,self.reference)
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,raw in members:z.writestr(name,raw)
        with self.assertRaises(ValueError):call(self.root,self.reference)

    def test_oversized_header_is_refused_before_numpy_load(self):
        path=self.root/'parameters.npz'
        with zipfile.ZipFile(path) as z:members=[(i.filename,z.read(i)) for i in z.infolist()]
        out=io.BytesIO();np.lib.format.write_array_header_1_0(out,dict(descr='<f8',fortran_order=False,shape=(2**40,)))
        with zipfile.ZipFile(path,'w') as z:
            for index,(name,raw) in enumerate(members):z.writestr(name,out.getvalue() if index==0 else raw)
        with patch.object(p.np,'load',side_effect=AssertionError('Do not allocate invalid shapes')) as load:
            with self.assertRaisesRegex(ValueError,'NPY extent'):call(self.root,self.reference)
            load.assert_not_called()

    def test_config_and_field_census_cannot_be_rebound_to_another_reference(self):
        path=self.root/'manifest.json';original=path.read_bytes()
        for kind in ['config','missing','renamed']:
            obj=json.loads(original)
            if kind=='config':obj['config']['layernorm_epsilon']*=2
            elif kind=='missing':obj['arrays'].pop('head')
            else:obj['arrays']['head']['key']='other'
            path.write_bytes(canonical_json(obj))
            with self.assertRaises(ValueError):call(self.root,self.reference)


if __name__=='__main__':unittest.main()
