"""Held-job admission constraints; generated snapshots, no Slurm submission."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from research_v82 import submit
from research_v82.submit import held_ok
GOOD='JobState=PENDING Reason=JobHeldUser Priority=0 NumCPUs=1 Requeue=0 MinMemoryNode=16G ReqNodeList=csis.mn1 TimeLimit=00:10:00 JobName=second82-checks Dependency=afterok:15917(unfulfilled)'
class Held(unittest.TestCase):
    def test_exact_held_constraints_pass(self):self.assertTrue(held_ok(GOOD,'checks','15917'))
    def test_wrong_resources_or_released_state_refuse(self):
        for a,b in [('NumCPUs=1','NumCPUs=2'),('16G','32G'),('csis.mn1','csis.mn2'),('Requeue=0','Requeue=1'),('JobState=PENDING','JobState=RUNNING'),('00:10:00','00:20:00')]:
            self.assertFalse(held_ok(GOOD.replace(a,b),'checks','15917'))
    def test_wrong_job_or_dependency_refuse(self):
        self.assertFalse(held_ok(GOOD,'fetch','15917'));self.assertFalse(held_ok(GOOD,'checks','15916'))
        self.assertFalse(held_ok(GOOD.replace('afterok','afterany'),'checks','15917'))
    def test_field_prefixes_extra_dependencies_and_duplicates_refuse(self):
        for a,b in [('NumCPUs=1','NumCPUs=10'),('Requeue=0','Requeue=01'),('16G','16Gx'),('JobState=PENDING','JobState=PENDINGx'),('15917(unfulfilled)','159170(unfulfilled)'),('15917(unfulfilled)','15917(unfulfilled),afterany:9')]:
            self.assertFalse(held_ok(GOOD.replace(a,b),'checks','15917'))
        with self.assertRaises(ValueError):held_ok(GOOD+' NumCPUs=2','checks','15917')
    def test_registration_writer_matches_strict_reader_format(self):
        payload={'program_sha256':'a'*64}
        with tempfile.TemporaryDirectory() as directory,patch.object(submit,'RUN',Path(directory)):
            submit.write('registration.json',payload)
            self.assertEqual((Path(directory)/'registration.json').read_bytes(),json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
    def test_registration_write_never_overwrites_existing_intent(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(submit,'RUN',Path(directory)):
            submit.write('intent.json',{'attempt':1})
            with self.assertRaises(FileExistsError):submit.write('intent.json',{'attempt':2})
            self.assertEqual(json.loads((Path(directory)/'intent.json').read_text()),{'attempt':1})
if __name__=='__main__':unittest.main()

