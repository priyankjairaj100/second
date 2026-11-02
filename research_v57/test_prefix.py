"""Tiny actual artifacts and sealed receipts; no empirical numerical execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from research_v53.test_postrun import TinyCampaign,BUDGET,write
from research_v57.prefix_audit import Inputs,check_states,verify_completed


class PrefixTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        for target,value in [('research_v53.test_state.BUDGET',BUDGET),('research_v57.prefix_audit.gram_budget',lambda _:BUDGET)]:
            p=patch(target,value);p.start();self.addCleanup(p.stop)
        self.case=TinyCampaign(Path(self.tmp.name).resolve())

    def states(self):
        return check_states(self.case.directory,self.case.program,self.case.completions,Inputs(),self.case.checkpoint_bytes,
            expected_stages=2,expected_codes=8)

    def seal(self):
        s=self.case.seal()
        for trial in ('prepare','cached'):
            path=self.case.directory/trial/'transaction.json';t=json.loads(path.read_bytes());t['budget']=s;write(path,t)
        return s

    def test_partial_models_verify_without_oracle_claim(self):
        result=self.states()
        self.assertEqual(len(result['originals']),3)
        self.assertEqual([r['retained_records'] for r in result['cached_steps']],[12,6])
        self.assertTrue(all(r['actual_export_matches_state'] for r in result['cached_steps']))
        self.assertFalse(result['full_campaign_verified']);self.assertFalse(result['oracle_comparison_performed'])

    def test_wrong_complete_model_export_refuses(self):
        write(self.case.directory/'cached/outputs/step-2-model.bin',self.case.model(0))
        with self.assertRaisesRegex(ValueError,'packed state codes'):self.states()

    def test_wrong_retained_membership_metadata_refuses(self):
        self.case.completions['cached']['steps'][1]['retained_ids']=['wrong']
        with self.assertRaisesRegex(ValueError,'membership'):self.states()

    def test_settled_prefix_verified_with_unrelated_live_reservation(self):
        s=self.seal();s['attempts']['other-live']={'state':'reserved','observed_cpu_ns':None}
        c,receipts=verify_completed(self.case.directory,self.case.program,Inputs(),s,version='v53')
        self.assertEqual(set(c),{'prepare','cached'});self.assertEqual(len(receipts),2)
        self.assertNotIn('other-live',receipts)
        bad=copy.deepcopy(s);key=next(iter(receipts));bad['attempts'][key]['observed_cpu_ns']+=1
        with self.assertRaisesRegex(ValueError,'debit'):verify_completed(self.case.directory,self.case.program,Inputs(),bad,version='v53')

    def test_failed_selected_worker_cannot_be_promoted(self):
        s=self.seal();path=self.case.directory/'cached/transaction.json';t=json.loads(path.read_bytes())
        t['worker_outcome']['status']='failed';write(path,t)
        with self.assertRaisesRegex(ValueError,'incomplete'):verify_completed(self.case.directory,self.case.program,Inputs(),s,version='v53')


if __name__=='__main__':unittest.main()
