"""Exact registry and held/released boundaries without empirical success fixtures."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from research_v99 import protocol
from research_v99.config import design
from research_v99.software import SUITES
from research_v80.io import info,write
from src.run_store import canonical_json
class Protocol(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        (self.root/'fixture.py').write_bytes(b'pass\n');self.sources={'fixture.py':info(b'pass\n')}
        self.p=dict(design(),sources=self.sources,source_count=1,source_inventory=info(canonical_json(self.sources)),
            recovery_terminal={'path':str(self.root/'gates/v89-terminal.json')},
            software_suites={k:dict(modules=v[0],tests=v[1]) for k,v in SUITES.items()},
            expected_software_tests=sum(v[1] for v in SUITES.values()))
        self.sha=info(canonical_json(self.p))['sha256'];write(self.root/'program.json',self.p)
        write(self.root/'inventory.json',self.sources);write(self.root/'registration.json',dict(program_sha256=self.sha))
        self.patch=patch.object(protocol,'RUN',self.root);self.patch.start();self.addCleanup(self.patch.stop)
    def test_registry_reopens_actual_source_bytes(self):
        self.assertEqual(protocol.program(self.sha),self.p)
        (self.root/'fixture.py').write_bytes(b'fail\n')
        with self.assertRaises(ValueError):protocol.program(self.sha)
    def test_wrong_expected_hash_and_registration_refuse(self):
        with self.assertRaises(ValueError):protocol.program('0'*64)
        (self.root/'registration.json').write_bytes(canonical_json(dict(program_sha256='0'*64)))
        with self.assertRaises(ValueError):protocol.program(self.sha)
    def test_unregistered_candidate_is_not_execution_permission(self):
        (self.root/'registration.json').unlink()
        self.assertEqual(protocol.program(self.sha,registered=False),self.p)
        with self.assertRaises(ValueError):protocol.program(self.sha)
    def test_missing_actual_held_chain_refuses_entry(self):
        row=dict(name='checks',operation='checks',arguments=[],job_id='76543',program_sha256=self.sha)
        write(self.root/'checks-submission.json',row)
        with self.assertRaises(ValueError):protocol.allocation('checks',self.sha,'76543')
    def test_release_response_race_is_avoided_but_terminal_requires_response(self):
        row=dict(name='checks',operation='checks',arguments=[],job_id='76543',program_sha256=self.sha)
        write(self.root/'checks-submission.json',row);write(self.root/'checks-held-chain.json',dict(program_sha256=self.sha,jobs=[row]))
        protocol.allocation('checks',self.sha,'76543')
        with self.assertRaises(ValueError):protocol.allocation('checks',self.sha,'76543',require_release=True)
        write(self.root/'checks-release.json',dict(program_sha256=self.sha,job_id='76543',released=True))
        protocol.allocation('checks',self.sha,'76543',require_release=True)
    def test_other_job_and_duplicate_held_rows_refuse(self):
        row=dict(name='checks',operation='checks',arguments=[],job_id='76543',program_sha256=self.sha)
        write(self.root/'checks-submission.json',row);write(self.root/'checks-held-chain.json',dict(program_sha256=self.sha,jobs=[row,row]))
        for job in ('76543','wrong'):
            with self.assertRaises(ValueError):protocol.allocation('checks',self.sha,job)
if __name__=='__main__':unittest.main()
