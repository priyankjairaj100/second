import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_recovery as a


def plan():
    return dict(schema='second-artifact-audit-recovery-v62',campaign=str(a.CAMPAIGN),run_directory=str(a.RUN),
        program_sha256=a.PROGRAM,failure_archive_sha256=a.FAILURE,original_outcomes={'13569':'TIMEOUT','13570':'CANCELLED'},
        limits=dict(a.LIMITS),fresh_support_cpu_seconds=7204,trials=['primary','postrun'],automatic_retry=False,
        numerical_execution=False,old_campaign_mutation=False,numerical_sources={f'src/{i}.py':'0'*64 for i in range(432)},
        wrapper_sources={'audit_recovery.py':{},'PROTOCOL.txt':{},'test_audit_recovery.py':{}},
        metadata_inputs={str(a.ROOT/f'meta/{i}.json'):{} for i in range(1285)},binary_inputs={str(a.ROOT/f'bin/{i}.bin'):{} for i in range(33)})


class RecoveryGuards(unittest.TestCase):
    def valid(self,p):return a.validate_plan(p,a.RUN/'registration.json',a.digest(a.canonical(p)))
    def test_exact_registration_accepts_but_tampered_digest_and_path_refuse(self):
        p=plan();self.assertIs(self.valid(p),p)
        with self.assertRaises(ValueError):a.validate_plan(p,a.RUN/'registration.json','0'*64)
        with self.assertRaises(ValueError):a.validate_plan(p,a.CAMPAIGN/'registration.json',a.digest(a.canonical(p)))
    def test_old_failure_and_new_scope_cannot_be_promoted(self):
        for key,value in [('original_outcomes',{'13569':'COMPLETED','13570':'COMPLETED'}),('automatic_retry',True),('numerical_execution',True),('old_campaign_mutation',True)]:
            with self.subTest(key=key):
                p=plan();p[key]=value
                with self.assertRaises(ValueError):self.valid(p)
    def test_fresh_caps_fixed_and_not_old_budget(self):
        for key in a.LIMITS:
            p=plan();p['limits'][key]+=1
            with self.subTest(key=key),self.assertRaises(ValueError):self.valid(p)
        p=plan();p['fresh_support_cpu_seconds']=81012
        with self.assertRaises(ValueError):self.valid(p)
    def test_input_census_and_path_escape_refuse(self):
        for key in ('metadata_inputs','binary_inputs','numerical_sources','wrapper_sources'):
            p=plan();p[key].pop(next(iter(p[key])))
            with self.subTest(key=key),self.assertRaises(ValueError):self.valid(p)
        p=plan();p['numerical_sources']['../escape.py']=p['numerical_sources'].pop('src/0.py')
        with self.assertRaises(ValueError):self.valid(p)
    def test_bound_read_rejects_changed_bytes_wrong_extent_and_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d).resolve()/'input';p.write_bytes(b'abc');entry=dict(bytes=3,sha256=a.digest(b'abc'))
            self.assertEqual(a.read_bound(p,entry),b'abc')
            p.write_bytes(b'abd')
            with self.assertRaises(ValueError):a.read_bound(p,entry)
            with self.assertRaises(ValueError):a.read_bound(p,dict(bytes=2,sha256=a.digest(b'abd')))
            q=Path(d).resolve()/'link';q.symlink_to(p)
            with self.assertRaises(ValueError):a.read_bound(q,dict(bytes=3,sha256=a.digest(b'abd')))
    def test_attempt_and_output_are_exclusive(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'attempt.json';a.new(p,dict(status='started'))
            with self.assertRaises(FileExistsError):a.new(p,dict(status='complete'))
            self.assertEqual(a.strict(p.read_bytes()),dict(status='started'))
    def test_primary_link_checks_actual_output_registration_and_job(self):
        with tempfile.TemporaryDirectory() as d,patch.object(a,'RUN',Path(d).resolve()):
            p=plan();out=a.canonical(dict(status='verified',program_sha256=a.PROGRAM,slurm_job_id='999'))
            (Path(d)/'primary.json').write_bytes(out)
            receipt=dict(status='complete',trial='primary',registration_sha256=a.digest(a.canonical(p)),slurm_job_id='999',audit_output=dict(bytes=len(out),sha256=a.digest(out)))
            (Path(d)/'primary-wrapper.json').write_bytes(a.canonical(receipt));a.check_primary_link(p)
            receipt['slurm_job_id']='998';(Path(d)/'primary-wrapper.json').write_bytes(a.canonical(receipt))
            with self.assertRaises(ValueError):a.check_primary_link(p)
            receipt['slurm_job_id']='999';receipt['status']='failed';(Path(d)/'primary-wrapper.json').write_bytes(a.canonical(receipt))
            with self.assertRaises(ValueError):a.check_primary_link(p)
    def test_duplicate_json_and_nonfinite_values_refuse(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}'):
            with self.assertRaises(ValueError):a.strict(raw)


if __name__=='__main__':unittest.main()
