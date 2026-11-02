"""Generated token/code files; numerical constructor mocked, no feature work."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,unittest
from research_v71.test_model_gate import fixture
from research_v71 import construction_flow as f
from src.run_store import canonical_json,digest

RECORDS=[dict(id=f'root-{i:02d}',tokens=[i]*128) for i in range(13)]
ROOT=digest(canonical_json(dict(records=RECORDS)))


class ConstructionFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.out=Path(self.temp.name).resolve()/'out';self.base,self.codes=fixture()
        self.blob=b''.join(s.packed_indices for s in self.codes)
        self.kw=dict(expected_root_sha256=ROOT,expected_candidate=f.info(self.blob),expected_target_sha256=self.base.digest,registration_sha256='a'*64)
    def tearDown(self):self.temp.cleanup()
    def calibrate(self,decoder,base,records,*,policy,progress):
        rows=[dict(stage_id=s.stage_id) for s in self.codes]
        for row in rows:progress(row)
        return self.codes,dict(target_sha256=base.digest,records=len(records),retained_tokens=len(records)*128,
            neural_stage_record_pairs=len(records)*len(self.codes),prior_model_access=False,prior_factor_access=False,stages=rows)
    def run_endpoint(self,endpoint=12):
        with patch.object(f.gate.sequential,'calibrate',side_effect=self.calibrate):
            return f.construct(endpoint,object(),self.base,RECORDS,self.blob,self.out,**self.kw)
    def audit(self,endpoint=12):return f.audit(self.out,self.base,RECORDS,self.blob,endpoint=endpoint,**self.kw)

    def test_both_exact_retained_endpoints_write_once_and_actual_codes_audit(self):
        for endpoint in [12,6]:
            self.out=Path(self.temp.name).resolve()/str(endpoint);r=self.run_endpoint(endpoint)
            self.assertEqual(r['retained_ids'],[r['id'] for r in RECORDS[-endpoint:]])
            a=self.audit(endpoint);self.assertEqual(a['stages'],2);self.assertEqual(a['actual_model_codes_compared'],9)
            self.assertFalse(a['numerical_constructor_independently_reexecuted'])
            with self.assertRaises(FileExistsError):self.run_endpoint(endpoint)

    def test_wrong_root_or_endpoint_prevents_constructor(self):
        with patch.object(f.gate.sequential,'calibrate') as called:
            for endpoint,kw in [(7,self.kw),(True,self.kw),(12,dict(self.kw,expected_root_sha256='0'*64))]:
                with self.assertRaises(ValueError):f.construct(endpoint,object(),self.base,RECORDS,self.blob,self.out,**kw)
            called.assert_not_called();self.assertFalse(self.out.exists())

    def test_constructor_refusal_preserves_partial_progress_and_diagnostics(self):
        def fail(*args,**kw):
            kw['progress'](dict(stage_id=self.codes[0].stage_id))
            e=ArithmeticError('generated refusal');e.service_diagnostics=dict(aborted=True,completed_stages=1);raise e
        with patch.object(f.gate.sequential,'calibrate',side_effect=fail):
            with self.assertRaises(ArithmeticError):f.construct(12,object(),self.base,RECORDS,self.blob,self.out,**self.kw)
        c=json.loads((self.out/'completion.json').read_bytes())
        self.assertEqual(c['status'],'failed');self.assertEqual(c['progress_events'],1)
        self.assertTrue(c['constructor_diagnostics']['aborted']);self.assertFalse((self.out/'model.bin').exists())
        with self.assertRaises(ValueError):self.audit()

    def test_changed_actual_model_progress_or_code_metadata_is_refused(self):
        self.run_endpoint()
        for name in ['model.bin','progress-0001.json','codes.json']:
            path=self.out/name;before=path.read_bytes();path.write_bytes(before+b'x')
            with self.subTest(artifact=name),self.assertRaises((ValueError,json.JSONDecodeError)):self.audit()
            path.write_bytes(before)


if __name__=='__main__':unittest.main()
