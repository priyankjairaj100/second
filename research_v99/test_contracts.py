"""Actual on-disk producer/child admission agreement; no model or network."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from src.run_store import canonical_json,digest
from research_v99.contracts import target_contract,budget,admit
from research_v99.config import design

class Contracts(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        self.sha='a'*64;self.p=dict(design(),sources={'fixture.py':dict(bytes=4,sha256='b'*64)})
        self.c=target_contract('gpt2',self.sha,'54321',0,root=self.root,cwd=self.root,executable='/usr/bin/python3')
        self.b=budget(self.p,self.sha,root=self.root)
        binding=dict(schema='limited-worker-identity-v1',identity=self.c['identity'],command=self.c['command'],
            cwd=str(self.root),limits=self.c['limits'].payload(),phase_budget=dict(binding_sha256=self.b.identity_digest,
                phase='admission',directory=str(self.b.root)))
        self.attempt=digest(canonical_json(dict(worker=binding,attempt=str(self.c['worker_root']/'attempt-0001'))))
        self.b.reserve('admission',self.attempt,602)
        self.env=dict(phase_budget_root=str(self.b.root),phase_budget_binding_sha256=self.b.identity_digest,
            attempt_id=self.attempt,phase='admission',command=self.c['command'],cwd=str(self.root))
    def verify(self):
        with patch.dict(os.environ,CALIBRATION_PHASE_CPU_ADMISSION=canonical_json(self.env).decode()):
            return admit(self.c,self.p,self.sha)
    def test_producer_and_child_share_actual_identity_without_writes(self):
        before=(self.b.root/'ledger.json').read_bytes();self.assertEqual(self.verify(),self.env)
        self.assertEqual(before,(self.b.root/'ledger.json').read_bytes())
    def test_old_worker_command_refuses(self):
        self.env['command']=[s.replace('research_v99','research_v82') for s in self.env['command']]
        with self.assertRaises(ValueError):self.verify()
    def test_other_profile_cannot_spend_same_reservation(self):
        self.c=target_contract('distilgpt2',self.sha,'54321',0,root=self.root,cwd=self.root,executable='/usr/bin/python3')
        with self.assertRaises(ValueError):self.verify()
    def test_changed_source_or_cap_refuses(self):
        for key,value in [('sources',{'other.py':dict(bytes=4,sha256='b'*64)}),('phase_cpu_seconds',{'admission':1205})]:
            with self.subTest(key=key),patch.dict(self.p,{key:value}):
                with self.assertRaises(ValueError):self.verify()
    def test_completed_allowance_cannot_be_reused(self):
        self.b.settle(self.attempt,100)
        with self.assertRaises(ValueError):self.verify()
    def test_missing_read_only_ledger_is_not_created(self):
        missing=self.root/'other'
        with self.assertRaises((ValueError,FileNotFoundError)):budget(self.p,self.sha,root=missing,read_only=True)
        self.assertFalse(missing.exists())
    def test_two_unknown_reservations_charge_full_allowance(self):
        self.b.reserve('admission','c'*64,602);s=budget(self.p,self.sha,root=self.root,read_only=True)
        self.assertEqual(s['charged_cpu_seconds'],{'admission':1204});self.assertEqual(s['reserved_unknown_attempts'],2)
        with self.assertRaises(Exception):self.b.reserve('admission','d'*64,602)

if __name__=='__main__':unittest.main()
