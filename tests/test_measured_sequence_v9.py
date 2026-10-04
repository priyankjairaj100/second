"""Software correctness only: matched sequence timing/lineage controls."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.measured_sequence import (build_measured_sequence_plan,build_measured_sequence_campaign,
    measured_sequence_orders,validate_measured_sequence_campaign_files,verify_measured_sequence_manifest,
    run_measured_sequence,run_measured_sequence_campaign,verify_measured_sequence_archive,derive_step_manifest,_lifetime,validate_sequence_context)
from src.run_store import canonical_json,digest,strict_json
from src.transaction_timing import transaction_source_hashes
from tests.test_sequence_campaign_v8 import fixture as warm_fixture


def fixture(root,*,phase='software_test',pause=False,requests=None,quality=False):
    old_path,old,protocol=warm_fixture(root,phase=phase,pause=pause)
    manifest=strict_json((root/'sequence0.json').read_bytes())
    if requests is not None:
        manifest['requests']=requests
        original=old['workloads'][0]['requests'];removed=[]
        replacement=[]
        for i,item in enumerate(requests):
            previous=list(removed);removed+=item['deleted_ids']
            replacement.append(dict(original[0],request_id=item['request_id'],deleted_ids=item['deleted_ids'],
                previously_deleted_ids=sorted(previous),cumulative_deleted_ids=[x for x in ['a','b','c'] if x in removed],
                starting_state='original' if i==0 else requests[i-1]['request_id']))
        old['workloads'][0]['requests']=replacement
    sources=transaction_source_hashes();order,prep=measured_sequence_orders(71,'root0','three',0)
    plan=build_measured_sequence_plan(manifest_path='sequence0.json',manifest=manifest,
        target_manifest_sha256=old['entries'][0]['target_manifest_sha256'],worker_limits=old['worker_limits'],
        sources=sources,method_order=order,preparation_order=prep,quality=quality)
    inventory=build_measured_sequence_campaign(campaign_id='measured-fixture',protocol_path='protocol.json',
        workloads=old['workloads'],runs=[dict(run_id='run0',manifest_path='sequence0.json',manifest=manifest,
            target_manifest_sha256=plan['target_manifest_sha256'],plan_path='plan.json',plan=plan)],
        worker_limits=old['worker_limits'],sources=sources)
    path=root/'measured-inventory.json';path.write_bytes(canonical_json(inventory))
    protocol['planned_inventory_sha256']=digest(path.read_bytes())
    (root/'protocol.json').write_bytes(canonical_json(protocol))
    manifest['protocol']['sha256']=digest(canonical_json(protocol))
    (root/'sequence0.json').write_bytes(canonical_json(manifest));(root/'plan.json').write_bytes(canonical_json(plan))
    return root/'plan.json',path,manifest


class MeasuredSequenceTests(unittest.TestCase):
    def test_inventory_exact_step_and_pause(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);plan,inventory,manifest=fixture(root,phase='confirmation')
            checked=validate_measured_sequence_campaign_files(inventory)
            self.assertEqual(len(checked['checked']),1)
            derived=derive_step_manifest(manifest,root/'sequence0.json',1)
            self.assertEqual(derived['deleted_ids'],['a','b'])
            self.assertEqual(derived['target']['original_token_count'],6)
            child=root/'step.json';child.write_bytes(canonical_json(derived))
            authorized=verify_measured_sequence_manifest(inventory,'run0',plan,child,1)
            self.assertEqual(authorized['execution_mode'],'clean')
            derived['deleted_ids']=['b'];child.write_bytes(canonical_json(derived))
            with self.assertRaisesRegex(ValueError,'frozen step'):
                verify_measured_sequence_manifest(inventory,'run0',plan,child,1)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);plan,inventory,_=fixture(root,phase='development',pause=True)
            with self.assertRaisesRegex(ValueError,'paused'):
                run_measured_sequence(plan,root/'out',inventory_path=inventory,inventory_run_id='run0')
            self.assertFalse((root/'out').exists())

    def test_lifetime_uses_distinct_preparations_and_no_oracle_cost(self):
        row=lambda n:dict(status='complete',complete_wall_time_ns=n)
        prep={'repair':row(100),'model_only_fresh':row(20)}
        steps=[{'status':'complete','methods':{'repair':row(3),'indexed_fresh':row(4),'model_only_fresh':row(9),'direct_fresh':row(999)}} for _ in range(3)]
        totals=_lifetime(prep,steps)
        self.assertEqual(totals['repair']['total_wall_ns'],109)
        self.assertEqual(totals['indexed_fresh']['total_wall_ns'],112)
        self.assertEqual(totals['model_only_fresh']['total_wall_ns'],47)
        steps[-1]['methods']['repair']={'status':'failed','complete_wall_time_ns':None}
        self.assertIsNone(_lifetime(prep,steps)['repair']['total_wall_ns'])

    def test_complete_all_delete_and_empty_after_all_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);plan,inventory,_=fixture(root,requests=[
                {'request_id':'first','deleted_ids':['a']},
                {'request_id':'all','deleted_ids':['b','c']},
                {'request_id':'empty','deleted_ids':[]}])
            result=run_measured_sequence(plan,root/'out',inventory_path=inventory,inventory_run_id='run0')
            self.assertEqual(result['outcome'],'complete',result.get('failure'))
            self.assertEqual([s['retained_ids'] for s in result['steps']],[['b','c'],[],[]])
            self.assertTrue(all(v['complete'] for v in result['lifetime'].values()))
            self.assertEqual(result['preparation']['repair']['common_model_sha256'],result['preparation']['model_only_fresh']['common_model_sha256'])
            for step in result['steps']:
                self.assertTrue(step['exact_model_equal']);self.assertTrue(step['exact_state_equal'])
            with patch('src.measured_comparison.invoke_role',side_effect=AssertionError('resume ran work')):
                saved=run_measured_sequence(plan,root/'out',inventory_path=inventory,inventory_run_id='run0')
            self.assertEqual(saved,result)
            with patch('src.measured_sequence.RunStore',side_effect=AssertionError('read-only archive constructed writer')):
                self.assertEqual(verify_measured_sequence_archive(root/'out'),result)
            copied=strict_json(canonical_json(result))
            copied['steps'][1]['methods']['repair']=copied['steps'][0]['methods']['repair']
            receipt=root/'out'/'result.json';original_receipt=receipt.read_bytes()
            receipt.write_bytes(canonical_json(copied))
            with self.assertRaises(ValueError):verify_measured_sequence_archive(root/'out')
            receipt.write_bytes(original_receipt)
            victim=Path(result['steps'][1]['methods']['repair']['state_reference']['path'])
            victim.write_bytes(victim.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'archive changed'):
                verify_measured_sequence_archive(root/'out')

    def test_interruption_after_sealed_role_reuses_original_observation(self):
        from src import measured_comparison as engine
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);plan,inventory,_=fixture(root,requests=[{'request_id':'one','deleted_ids':['a']}])
            original=engine.invoke_role;observed=[]
            def interrupt(*args,**kwargs):
                value=original(*args,**kwargs);observed.append(value)
                if len(observed)==1: raise KeyboardInterrupt('after sealed observer')
                return value
            with patch.object(engine,'invoke_role',side_effect=interrupt):
                with self.assertRaises(KeyboardInterrupt):
                    run_measured_sequence(plan,root/'out',inventory_path=inventory,inventory_run_id='run0')
            result=run_measured_sequence(plan,root/'out',inventory_path=inventory,inventory_run_id='run0')
            self.assertEqual(result['outcome'],'complete',result.get('failure'))
            prepkey='repair' if observed[0]['role']=='setup' else 'model_only_fresh'
            self.assertEqual(result['preparation'][prepkey]['complete_wall_time_ns'],observed[0]['complete_wall_time_ns'])


    def test_wrong_predecessor_fails_at_leaf_and_preserves_future_slots(self):
        from src import measured_comparison as engine
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);plan,inventory,_=fixture(root)
            original=engine.invoke_role;initial={}
            def substitute(checked,output,role,**kwargs):
                if role=='repair' and checked['manifest']['request_id']=='delete1':
                    kwargs['original_state']=initial['state']
                row=original(checked,output,role,**kwargs)
                if role=='setup':initial['state']=row['state_reference']
                return row
            with patch.object(engine,'invoke_role',side_effect=substitute):
                result=run_measured_sequence(plan,root/'out',inventory_path=inventory,inventory_run_id='run0')
            self.assertEqual(result['outcome'],'failed')
            self.assertEqual([s['status'] for s in result['steps']],['complete','failed','not_started'])
            row=result['steps'][1]['methods']['repair']
            self.assertEqual(row['status'],'failed')
            child=strict_json(Path(row['child_receipt_path']).read_bytes())
            self.assertIn('predecessor lineage',child['outcome']['failure']['message'])
            self.assertIsNone(result['lifetime']['repair']['total_wall_ns'])
            engine.verify_role(row)
            with self.assertRaisesRegex(ValueError,'predecessor'):
                verify_measured_sequence_archive(root/'out')
            victim=Path(row['child_receipt_path']).parent/child['attempt']/'request.json'
            victim.write_bytes(victim.read_bytes()+b' ')
            with self.assertRaises(ValueError):engine.verify_role(row)

    def test_lost_observer_receipt_never_becomes_short_success(self):
        from src import measured_comparison as engine
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);plan,inventory,_=fixture(root,requests=[{'request_id':'one','deleted_ids':['a']}])
            original=engine.invoke_role;observed=[]
            def interrupt(*args,**kwargs):
                row=original(*args,**kwargs);observed.append(row)
                raise KeyboardInterrupt('after first sealed child')
            with patch.object(engine,'invoke_role',side_effect=interrupt):
                with self.assertRaises(KeyboardInterrupt):
                    run_measured_sequence(plan,root/'out',inventory_path=inventory,inventory_run_id='run0')
            Path(observed[0]['timing_receipt_path']).unlink()
            result=run_measured_sequence(plan,root/'out',inventory_path=inventory,inventory_run_id='run0')
            self.assertEqual(result['outcome'],'failed')
            self.assertTrue(all(s['status']=='not_started' for s in result['steps']))
            key='repair' if observed[0]['role']=='setup' else 'model_only_fresh'
            self.assertIsNone(result['preparation'][key]['complete_wall_time_ns'])
            self.assertFalse(result['lifetime'][key]['all_attempt_costs_known'])

    def test_campaign_admission_failure_preserves_sequences_and_all_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);plan,inventory,manifest=fixture(root)
            protocol=strict_json((root/'protocol.json').read_bytes())
            protocol['resources']['phase_cpu_hour_caps']['software_test']=0.001
            (root/'protocol.json').write_bytes(canonical_json(protocol))
            manifest['protocol']['sha256']=digest(canonical_json(protocol))
            (root/'sequence0.json').write_bytes(canonical_json(manifest))
            with patch('src.worker_control.subprocess.Popen',side_effect=AssertionError('denied worker launched')):
                result=run_measured_sequence_campaign(inventory,root/'campaign')
            self.assertEqual(result['outcome'],'failed')
            self.assertEqual(len(result['runs']),1)
            child=verify_measured_sequence_archive(root/'campaign'/'runs'/'run0')
            self.assertEqual([s['status'] for s in child['steps']],['not_started']*3)
            self.assertTrue(all(v['total_wall_ns'] is None for v in child['lifetime'].values()))
            with patch('src.measured_comparison.invoke_role',side_effect=AssertionError('sealed campaign relaunched')):
                self.assertEqual(run_measured_sequence_campaign(inventory,root/'campaign'),result)

    def test_service_predecessor_does_not_require_research_or_timing_archives(self):
        import shutil
        from src.experiment_runner import _run_manifest
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);plan,inventory,_=fixture(root,requests=[
                {'request_id':'one','deleted_ids':['a']},{'request_id':'two','deleted_ids':['b']}])
            result=run_measured_sequence(plan,root/'out',inventory_path=inventory,inventory_run_id='run0')
            self.assertEqual(result['outcome'],'complete',result.get('failure'))
            work=root/'out'/'work'/'steps'
            request=strict_json((work/'step-0001'/'requests'/'repair.json').read_bytes())
            manifest=strict_json(Path(request['manifest_path']).read_bytes())
            prepared=_run_manifest(request['manifest_path'],root/'unused',prepare_only=True,skip_heldout=True)
            ref=request['original_state']
            old=prepared['service'].load_state(Path(ref['path']).read_bytes(),expected_digest=ref['sha256'])
            shutil.rmtree(work/'step-0000'/'transactions'/'direct_fresh')
            shutil.rmtree(work/'step-0000'/'transactions'/'model_only_fresh')
            shutil.rmtree(work/'step-0000'/'transactions'/'indexed_fresh')
            shutil.rmtree(work/'step-0000'/'observations')
            shutil.rmtree(work/'step-0000'/'verified-models')
            shutil.rmtree(root/'out'/'work'/'commits')
            with patch('src.measured_sequence.RunStore',side_effect=AssertionError('predecessor check constructed writer')):
                self.assertEqual(validate_sequence_context(request,manifest,prepared['records'],old),['b'])
            with self.assertRaisesRegex(ValueError,'archive changed'):
                verify_measured_sequence_archive(root/'out')

    def test_quality_is_separate_from_matched_lifetime(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);plan,inventory,_=fixture(root,requests=[{'request_id':'one','deleted_ids':['a']}],quality=True)
            result=run_measured_sequence(plan,root/'out',inventory_path=inventory,inventory_run_id='run0')
            self.assertEqual(result['outcome'],'complete',result.get('failure'))
            step=result['steps'][0]
            self.assertEqual(step['quality']['status'],'complete')
            self.assertEqual(step['quality']['output_contract'],'quality_evaluation')
            for name in ('repair','indexed_fresh','model_only_fresh'):
                prep='model_only_fresh' if name=='model_only_fresh' else 'repair'
                expected=result['preparation'][prep]['complete_wall_time_ns']+step['methods'][name]['complete_wall_time_ns']
                self.assertEqual(result['lifetime'][name]['total_wall_ns'],expected)
            verify_measured_sequence_archive(root/'out')

if __name__=='__main__':unittest.main()
