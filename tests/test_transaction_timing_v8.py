"""Transaction boundary fixtures; no empirical data or performance claims."""
from pathlib import Path
import os
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

from src.run_store import strict_json, canonical_json, digest
from src.transaction_timing import (CACHE_MODES, accounting_partition, measure_command,
    run_measured_manifest, transaction_source_hashes, verify_phase_admission, build_role_measurement)
from src.worker_control import WorkerLimits


@unittest.skipUnless(hasattr(os,'sched_setaffinity'),'Linux worker limits required')
class TransactionTimingTests(unittest.TestCase):
    def limits(self):
        return WorkerLimits(5,3,256*1024*1024,1,(min(os.sched_getaffinity(0)),),0,8*1024*1024)

    def command(self, output, *, contract='canonical_state', outcome='complete', schema='timing-fixture-v1'):
        values={'schema':schema,'status':'complete','outcome':{'status':outcome}}
        if contract is not None:
            values['output_contract']=contract
        code=("from pathlib import Path; from src.run_store import RunStore,atomic_write; "
              "p=Path("+repr(str(output))+"); s=RunStore(p,{'fixture':True}); s.claim(); "
              "s.write_artifact('state.json',b'{}'); s.finish("+repr(values)+"); s.close(); "
              "atomic_write(p/'cleanup-completed.txt',b'complete')")
        return [sys.executable,'-c',code]

    def measure(self, root, **options):
        return measure_command(options.pop('command',self.command(root/'transaction')),
            root/'transaction',root/'observer',self.limits(),identity={'fixture':True},
            source_sha256=options.pop('source_sha256',transaction_source_hashes()),**options)

    def test_complete_boundary_and_disjoint_accounting(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);result=self.measure(root);receipt=result['receipt']
            self.assertTrue(result['new_latency_observation'])
            self.assertEqual(receipt['outcome']['status'],'complete')
            self.assertTrue((root/'transaction'/'cleanup-completed.txt').exists())
            self.assertEqual(receipt['observed_wall_ns'],receipt['accounting_sum_ns'])
            self.assertEqual(receipt['complete_transaction_wall_ns'],receipt['observed_wall_ns'])
            spans=receipt['timing_spans']
            self.assertEqual(spans[0]['start_offset_ns'],0)
            self.assertEqual(spans[-1]['end_offset_ns'],receipt['observed_wall_ns'])
            self.assertTrue(all(a['end_offset_ns']==b['start_offset_ns'] for a,b in zip(spans,spans[1:])))
            self.assertGreater(next(x['wall_ns'] for x in spans if x['name']=='worker_finalization_and_commit'),0)
            self.assertEqual(next(x['wall_ns'] for x in spans if x['name']=='worker_execution_and_cleanup'),
                             receipt['worker_outcome']['elapsed_wall_ns'])
            self.assertTrue(receipt['observer_receipt_excluded'])

    def test_reused_receipt_is_not_new_latency_and_checks_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); first=self.measure(root); again=self.measure(root)
            self.assertTrue(again['reused_receipt'])
            self.assertFalse(again['new_latency_observation'])
            self.assertEqual(first['receipt'],again['receipt'])
            self.assertEqual(len(list((root/'observer').glob('attempt-*'))),1)
            (root/'transaction'/'cleanup-completed.txt').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'differs from the saved'):
                self.measure(root)

    def test_fresh_rejects_partial_and_resume_labels_remaining_work(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'transaction';out.mkdir();(out/'partial.txt').write_text('partial')
            failed=self.measure(root)
            self.assertEqual(failed['receipt']['outcome']['status'],'incomplete')
            self.assertIsNone(failed['receipt']['complete_transaction_wall_ns'])
            self.assertFalse(failed['new_latency_observation'])
            resumed=measure_command(self.command(out),out,root/'resumed-observer',self.limits(),
                identity={'fixture':True},source_sha256=transaction_source_hashes(),cache_mode=CACHE_MODES[1])
            self.assertEqual(resumed['receipt']['outcome']['status'],'complete')
            self.assertEqual(resumed['receipt']['resumed_preexisting_file_count'],1)
            self.assertFalse(resumed['new_latency_observation'])
            self.assertFalse(resumed['receipt']['eligible_fresh_transaction_latency'])

    def test_missing_completion_and_nonzero_exit_are_incomplete(self):
        for command in ([sys.executable,'-c','pass'],[sys.executable,'-c','raise SystemExit(7)']):
            with self.subTest(command=command),tempfile.TemporaryDirectory() as folder:
                result=self.measure(Path(folder),command=command)
                self.assertEqual(result['receipt']['outcome']['status'],'incomplete')
                self.assertIsNone(result['receipt']['complete_transaction_wall_ns'])
                self.assertFalse(result['new_latency_observation'])

    def test_interruption_seals_incomplete_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch('src.transaction_timing.run_limited',side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    self.measure(root)
            saved=strict_json((root/'observer'/'result.json').read_bytes())
            self.assertEqual(saved['outcome']['status'],'incomplete')
            self.assertIsNone(saved['complete_transaction_wall_ns'])
            self.assertEqual(saved['accounting_sum_ns'],saved['observed_wall_ns'])

    def test_source_mismatch_never_launches(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);sources=transaction_source_hashes();sources[next(iter(sources))]='0'*64
            with patch('src.transaction_timing.run_limited',side_effect=AssertionError('must not launch')):
                result=self.measure(root,source_sha256=sources)
            self.assertEqual(result['receipt']['outcome']['status'],'incomplete')
            self.assertFalse((root/'transaction').exists())

    def test_output_contracts_cannot_be_silently_mixed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            failed=self.measure(root,command=self.command(root/'transaction',contract='model_only'))
            self.assertEqual(failed['receipt']['outcome']['status'],'incomplete')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            result=self.measure(root,command=self.command(root/'transaction',contract=None))
            self.assertEqual(result['receipt']['outcome']['status'],'complete')
            self.assertFalse(result['receipt']['child_output_contract_verified'])
            self.assertFalse(result['new_latency_observation'])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            failed=self.measure(root,command=self.command(root/'transaction',contract='canonical_state',
                                                       schema='calibration-model-fresh-v1'))
            self.assertEqual(failed['receipt']['outcome']['status'],'incomplete')

    def test_manifest_and_disjoint_tree_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'transaction'
            request={'schema':'measured-transaction-v1','command':self.command(out),
                     'transaction_root':str(out),'cwd':str(Path.cwd()),'cache_mode':CACHE_MODES[0],
                     'output_contract':'canonical_state','limits':self.limits().payload(),
                     'source_sha256':transaction_source_hashes(),'input_sha256':{},'budget':None,'identity':{'fixture':True}}
            manifest=root/'manifest.json';manifest.write_bytes(canonical_json(request))
            result=run_measured_manifest(manifest,root/'observer')
            self.assertTrue(result['new_latency_observation'])
            manifest.write_bytes(manifest.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'canonical'):
                run_measured_manifest(manifest,root/'other')
            with self.assertRaisesRegex(ValueError,'disjoint'):
                measure_command(self.command(out),out,out/'nested',self.limits(),identity={},
                                source_sha256=transaction_source_hashes())

    def test_accounting_rejects_overlap_and_wrong_nested_elapsed(self):
        worker={'timing_boundary':{'clock':'time.perf_counter_ns_same_controller_process',
                'start_ns':3,'cleanup_end_ns':6},'outcome':{'elapsed_wall_ns':3}}
        spans=accounting_partition(0,2,8,10,worker)
        self.assertEqual([x['wall_ns'] for x in spans],[2,1,3,2,2])
        worker['outcome']['elapsed_wall_ns']=4
        with self.assertRaises(ValueError):
            accounting_partition(0,2,8,10,worker)
        worker['outcome']['elapsed_wall_ns']=3
        with self.assertRaises(ValueError):
            accounting_partition(0,4,8,10,worker)
        with self.assertRaises(ValueError):
            accounting_partition(0,2,1,10,None)

    def test_timeout_cleans_descendant_in_another_session(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'transaction';pidfile=out/'descendant.pid'
            nested="import time; time.sleep(10)"
            code=("from pathlib import Path; import subprocess,sys,time; "
                  "p=Path("+repr(str(out))+"); p.mkdir(); "
                  "c=subprocess.Popen([sys.executable,'-c',"+repr(nested)+"],start_new_session=True); "
                  "(p/'descendant.pid').write_text(str(c.pid)); time.sleep(10)")
            limits=WorkerLimits(1,3,256*1024*1024,1,(min(os.sched_getaffinity(0)),),0,8*1024*1024)
            result=measure_command([sys.executable,'-c',code],out,root/'observer',limits,
                                   identity={},source_sha256=transaction_source_hashes())
            self.assertEqual(result['receipt']['outcome']['status'],'incomplete')
            self.assertEqual(result['receipt']['worker_outcome']['kind'],'wall_timeout')
            self.assertTrue(result['receipt']['adopted_descendant_resource_usage'])
            pid=int(pidfile.read_text())
            with self.assertRaises(ProcessLookupError):
                os.kill(pid,0)

    def test_existing_child_prevents_observer_adoption(self):
        child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(10)'])
        try:
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder); result=self.measure(root)
                self.assertEqual(result['receipt']['outcome']['status'],'incomplete')
                self.assertIn('no existing child',result['receipt']['outcome']['failure']['message'])
                self.assertIsNone(child.poll())
        finally:
            child.kill();child.wait()

    def test_measured_worker_is_debited_to_bound_phase_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);protocol=root/'protocol.json'
            raw=canonical_json({'schema':'calibration-protocol-v1','status':'experiments_paused',
                                'resources':{'phase_cpu_hour_caps':{'software_test':0.1}}})
            protocol.write_bytes(raw)
            config={'protocol_path':str(protocol),'protocol_sha256':digest(raw),'phase':'software_test'}
            result=self.measure(root,budget_config=config)
            row=result['receipt']
            self.assertEqual(row['outcome']['status'],'complete')
            self.assertIsNotNone(row['budget_attempt_id'])
            self.assertEqual(row['budget_debit']['state'],'settled')
            again=self.measure(root,budget_config=config)
            self.assertTrue(again['reused_receipt'])
            self.assertEqual(again['receipt']['budget_debit'],row['budget_debit'])

    def test_admission_rejects_missing_wrong_or_settled_allowance(self):
        from src.phase_budget import PhaseBudget
        from src.experiment_inventory import source_hashes
        repo=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);manifest=root/'manifest.json';output=root/'output'
            command=[sys.executable,str(repo/'scripts/run_model_fresh.py'),str(manifest),'--output',str(output)]
            budget=PhaseBudget(root/'budget',identity={'protocol_sha256':'1'*64,'source_sha256':source_hashes(repo)},
                               phase_cpu_seconds={'development':10})
            budget.reserve('development','attempt',5)
            admission={'phase_budget_root':str(budget.root),'phase_budget_binding_sha256':budget.identity_digest,
                       'attempt_id':'attempt','phase':'development','command':command,'cwd':str(repo)}
            with patch.dict(os.environ,{'CALIBRATION_PHASE_CPU_ADMISSION':canonical_json(admission).decode()}):
                self.assertEqual(verify_phase_admission('1'*64,'development',manifest,output),admission)
                with self.assertRaisesRegex(ValueError,'exact command'):
                    verify_phase_admission('1'*64,'development',manifest,root/'different')
                budget.settle('attempt',1)
                with self.assertRaisesRegex(ValueError,'settled'):
                    verify_phase_admission('1'*64,'development',manifest,output)
            with patch.dict(os.environ,{},clear=True):
                with self.assertRaisesRegex(ValueError,'active phase'):
                    verify_phase_admission('1'*64,'development',manifest,output)

    def test_role_helper_binds_protocol_and_admits_research_separately(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);protocol=root/'protocol.json';manifest=root/'run.json';request=root/'request.json'
            protocol_raw=canonical_json({'status':'development','resources':{'phase_cpu_hour_caps':{'development':1}}})
            protocol.write_bytes(protocol_raw)
            manifest_raw=canonical_json({'phase':'development','protocol':{'path':'protocol.json','sha256':digest(protocol_raw)}})
            manifest.write_bytes(manifest_raw)
            request.write_bytes(canonical_json({'schema':'isolated-child-request-v1','role':'repair',
                'output':str(root/'output'),'manifest_path':str(manifest),'manifest_sha256':digest(manifest_raw)}))
            measured=build_role_measurement(request,self.limits())
            self.assertEqual(measured['output_contract'],'canonical_state')
            self.assertEqual(measured['budget'],{'protocol_path':str(protocol),'protocol_sha256':digest(protocol_raw),
                                                'phase':'development'})
            self.assertEqual(set(measured['input_sha256']),{str(request),str(manifest),str(protocol)})
            changed=strict_json(request.read_bytes());changed['role']='quality';request.write_bytes(canonical_json(changed))
            with self.assertRaisesRegex(ValueError,'supported'):
                build_role_measurement(request,self.limits())


    def test_v9_absolute_observer_origin_must_match_worker(self):
        from src.transaction_timing import verify_observer_receipt
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); self.measure(root)
            path=root/'observer'/'result.json'
            receipt=strict_json(path.read_bytes())
            receipt['observer_clock']['start_ns']+=1
            receipt['observer_clock']['end_ns']+=1
            path.write_bytes(canonical_json(receipt))
            with self.assertRaisesRegex(ValueError,'clock origins differ'):
                verify_observer_receipt(root/'observer')


if __name__=='__main__':
    unittest.main()
