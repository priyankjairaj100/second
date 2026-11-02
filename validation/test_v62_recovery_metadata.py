import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import check_v62_recovery_metadata as c
import collect_v62_recovery as collector


def accounting(jobs,recovery=False):
    rows={};lines=[]
    for label,job in jobs.items():
        state='COMPLETED' if recovery or job not in ('13569','13570') else 'TIMEOUT' if job=='13569' else 'CANCELLED'
        elapsed='0' if job=='13570' else '120'
        f=[job,'second-'+label,state,'0:0',elapsed,'00:00:00','2026-10-14T00:00:00','2026-10-14T00:02:00']
        lines.append('|'.join(f)+'|')
        rows[job]=dict(job_name=f[1],state=state,raw_state=state,exit_code='0:0',elapsed_seconds=elapsed,total_cpu=f[5],start=f[6],end=f[7])
    return dict(scheduler='\n'.join(lines)+'\n',scheduler_jobs=rows,scheduler_queue='')


class RecoveryMetadataTests(unittest.TestCase):
    def test_original_failed_rows_remain_required(self):
        m=accounting(c.JOBS);self.assertEqual(c.original_rows(m)['13569']['state'],'TIMEOUT')
        bad=copy.deepcopy(m);bad['scheduler']=bad['scheduler'].replace('TIMEOUT','COMPLETED')
        with self.assertRaises(ValueError):c.original_rows(bad)
        bad=copy.deepcopy(m);bad['scheduler']='\n'.join(m['scheduler'].splitlines()[:-1])
        with self.assertRaises(ValueError):c.original_rows(bad)
    def test_recovery_refuses_pending_failed_partial_and_over_cap(self):
        m=accounting(c.RECOVERY_JOBS,True);self.assertEqual(len(c.recovery_rows(m)),2)
        for new in ('TIMEOUT','PENDING','CANCELLED'):
            bad=dict(m,scheduler=m['scheduler'].replace('COMPLETED',new,1))
            with self.subTest(state=new),self.assertRaises(ValueError):c.recovery_rows(bad)
        with self.assertRaises(ValueError):c.recovery_rows(dict(m,scheduler_queue='15151|RUNNING|node'))
        with self.assertRaises(ValueError):c.recovery_rows(dict(m,scheduler=m['scheduler'].replace('|120|','|3901|',1)))
    def test_collector_refuses_active_queue_and_does_not_fake_success(self):
        good=accounting(c.RECOVERY_JOBS,True)['scheduler']
        with patch.object(collector,'command',side_effect=['15150|RUNNING|node']):
            with self.assertRaises(ValueError):collector.scheduler()
        with patch.object(collector,'command',side_effect=['',good,'steps']):self.assertTrue(collector.scheduler()['successful'])
        with patch.object(collector,'command',side_effect=['',good.replace('COMPLETED','TIMEOUT',1),'steps']):self.assertFalse(collector.scheduler()['successful'])
    def test_metadata_reader_refuses_symlink_and_original_path_filling(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d).resolve();p=r/'data.json';p.write_bytes(b'{}')
            self.assertEqual(collector.read(p),b'{}')
            q=r/'link';q.symlink_to(p)
            with self.assertRaises(ValueError):collector.read(q)
            (r/'artifact-audit.json').write_bytes(b'{}')
            with patch.object(collector,'CAMPAIGN',r):
                with self.assertRaises(ValueError):collector.old_bindings(dict(metadata_inputs={},binary_inputs={}))


if __name__=='__main__':unittest.main()
