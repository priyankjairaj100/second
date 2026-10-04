"""Tiny correctness fixtures only; never research latency observations."""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from src.measured_comparison import (METHODS, build_measured_plan, measured_source_hashes,
    run_measured_comparison, verify_measured_archive, verify_role, verify_role_slot)
from src.run_store import canonical_json, digest, strict_json
from tests import test_worker_control as worker_fixtures


def fixture(root, *, mode='clean', quality=False, target=None, caps=None):
    campaign_path,manifest=worker_fixtures.CampaignControlTests().fixture(root)
    campaign=strict_json(campaign_path.read_bytes())
    if caps is not None:
        protocol=strict_json((root/'protocol.json').read_bytes())
        protocol['resources']={'phase_cpu_hour_caps':{'software_test':caps}}
        raw=canonical_json(protocol); (root/'protocol.json').write_bytes(raw)
        manifest['protocol']['sha256']=digest(raw)
        (root/'run.json').write_bytes(canonical_json(manifest))
    plan=build_measured_plan(manifest_path='run.json',manifest=manifest,
        target_manifest_sha256=target or campaign['entries'][0]['target_manifest_sha256'],
        worker_limits=campaign['worker_limits'],sources=measured_source_hashes(),
        method_order=list(METHODS),quality=quality,execution_mode=mode)
    path=root/'measured.json'; path.write_bytes(canonical_json(plan))
    return path,manifest


@unittest.skipUnless(hasattr(os,'wait4') and hasattr(os,'sched_setaffinity'),'Linux workers required')
class MeasuredComparisonTests(unittest.TestCase):
    def test_exact_four_contracts_clean_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); plan,_=fixture(root)
            validated=run_measured_comparison(plan,root/'result',validate_only=True)
            self.assertFalse(validated['checkpoint_parameters_loaded'])
            self.assertFalse((root/'result').exists())
            result=run_measured_comparison(plan,root/'result')
            self.assertEqual(result['outcome'],{'status':'complete'},result)
            self.assertEqual(verify_measured_archive(root/'result'),result)

            self.assertEqual(run_measured_comparison(plan,root/'result'),result)
            with self.assertRaisesRegex(ValueError,'parent slot'):
                verify_role_slot(result['methods']['repair'],root=root/'another-result',
                    plan_sha256=result['plan_sha256'],manifest_path=root/'run.json',
                    manifest_sha256=result['run_manifest_sha256'],role='repair')
            rows=result['methods']; pids=set()
            for role,row in rows.items():
                self.assertEqual(row['status'],'complete')
                self.assertTrue(row['exact_model_equal'])
                self.assertGreater(row['complete_wall_time_ns'],0)
                verify_role(row,result['target_manifest_sha256'])
                observer=strict_json(Path(row['timing_receipt_path']).read_bytes())
                self.assertEqual(observer['instrumentation_state']['mode'],'clean')
                worker_root=Path(row['timing_receipt_path']).parent/observer['attempt']/'worker'
                worker=strict_json((worker_root/'result.json').read_bytes())
                pids.add(worker['worker_pid'])
            self.assertEqual(len(pids),4)
            self.assertIsNone(rows['model_only_fresh']['exact_state_equal'])
            self.assertNotIn('state_reference',rows['model_only_fresh'])
            self.assertEqual(len({rows[name]['state_reference']['sha256'] for name in METHODS[1:]}),1)
            for role in (*METHODS,'setup'):
                self.assertEqual(len(list((root/'result'/'observations'/role).glob('attempt-*'))),1)

    def test_archive_budget_check_does_not_create_a_lock_or_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); plan,_=fixture(root,caps=0.001)
            result=run_measured_comparison(plan,root/'result')
            budget=next(root.glob('phase-cpu-budget-*'))
            (budget/'ledger.lock').unlink()
            before=(budget/'ledger.json').read_bytes()
            with patch('src.phase_budget.PhaseBudget.__init__',side_effect=AssertionError('read-only verifier created a writer')):
                with patch('src.run_store.RunStore.__init__',side_effect=AssertionError('read-only verifier constructed a store')):
                    self.assertEqual(verify_measured_archive(root/'result'),result)
            self.assertFalse((budget/'ledger.lock').exists())
            self.assertEqual((budget/'ledger.json').read_bytes(),before)

    def test_diagnostic_and_quality_are_explicit_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); plan,_=fixture(root,mode='diagnostic',quality=True)
            result=run_measured_comparison(plan,root/'result')
            self.assertEqual(result['outcome'],{'status':'complete'},result)
            self.assertEqual(result['quality']['output_contract'],'quality_evaluation')
            self.assertTrue(result['methods']['repair']['profiler_active'])
            self.assertEqual(verify_measured_archive(root/'result'),result)

    def test_budget_failures_keep_independent_baselines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); plan,_=fixture(root,caps=0.001)
            result=run_measured_comparison(plan,root/'result')
            self.assertEqual(result['outcome'],{'status':'failed'})
            self.assertEqual(result['setup']['status'],'failed')
            for role in ('repair','indexed_fresh'):
                self.assertEqual(result['methods'][role]['status'],'not_started')
            for role in ('model_only_fresh','direct_fresh'):
                self.assertEqual(result['methods'][role]['status'],'failed')
                self.assertIn('timing_receipt_path',result['methods'][role])
            self.assertEqual(verify_measured_archive(root/'result'),result)

    def test_artifact_and_convenience_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); plan,_=fixture(root)
            result=run_measured_comparison(plan,root/'result')
            row=dict(result['methods']['repair']); row['complete_wall_time_ns']+=1
            with self.assertRaisesRegex(ValueError,'convenience'):
                verify_role(row,result['target_manifest_sha256'])
            path=Path(result['methods']['repair']['model_reference']['path'])
            path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'tree changed'):
                verify_measured_archive(root/'result')

    def test_parent_interrupt_reuses_original_observer(self):
        from src import measured_comparison
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); plan,_=fixture(root)
            real=measured_comparison.invoke_role
            def stop(*args,**kwargs):
                real(*args,**kwargs)
                raise KeyboardInterrupt('after sealed setup')
            with patch('src.measured_comparison.invoke_role',side_effect=stop):
                with self.assertRaises(KeyboardInterrupt):
                    run_measured_comparison(plan,root/'result')
            path=root/'result'/'observations'/'setup'/'result.json'; saved=path.read_bytes()
            result=run_measured_comparison(plan,root/'result')
            self.assertEqual(result['outcome'],{'status':'complete'},result)
            self.assertEqual(path.read_bytes(),saved)
            self.assertEqual(len(list(path.parent.glob('attempt-*'))),1)

    def test_missing_original_observer_cannot_become_fast_success(self):
        from src import measured_comparison
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); plan,_=fixture(root)
            real=measured_comparison.invoke_role
            def stop(*args,**kwargs):
                row=real(*args,**kwargs)
                path=Path(row['timing_receipt_path'])
                value=strict_json(path.read_bytes()); value['status']='running'
                path.write_bytes(canonical_json(value))
                raise KeyboardInterrupt('lost original terminal observer')
            with patch('src.measured_comparison.invoke_role',side_effect=stop):
                with self.assertRaises(KeyboardInterrupt):
                    run_measured_comparison(plan,root/'result')
            partial=verify_measured_archive(root/'result')
            self.assertEqual(partial['status'],'failed')
            result=run_measured_comparison(plan,root/'result')
            self.assertEqual(result['outcome'],{'status':'failed'})
            self.assertIsNone(result['setup']['complete_wall_time_ns'])
            for name in ('model_only_fresh','direct_fresh'):
                self.assertEqual(result['methods'][name]['status'],'complete')
            self.assertEqual(verify_measured_archive(root/'result'),result)

    def test_inconsistent_target_preserves_all_planned_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); plan,_=fixture(root,target='f'*64)
            result=run_measured_comparison(plan,root/'result')
            self.assertEqual(result['outcome'],{'status':'failed'})
            self.assertEqual(result['methods']['model_only_fresh']['failure']['kind'],'output_verification_failure')
            self.assertEqual(set(result['methods']),set(METHODS))
            self.assertEqual(verify_measured_archive(root/'result'),result)

    def test_pause_blocks_before_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); plan,manifest=fixture(root)
            manifest['phase']='development'; (root/'run.json').write_bytes(canonical_json(manifest))
            value=strict_json(plan.read_bytes())
            from src.experiment_inventory import manifest_payload,manifest_binding
            value['manifest_payload']=manifest_payload(manifest); value['manifest_binding_sha256']=manifest_binding(manifest)
            plan.write_bytes(canonical_json(value))
            with self.assertRaisesRegex(ValueError,'paused'):
                run_measured_comparison(plan,root/'result')
            self.assertFalse((root/'result').exists())

if __name__=='__main__': unittest.main()
