"""Frozen bulk-sequence correctness fixtures; no empirical datasets or timings."""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from src.chart_construction import ChartRecipe
from src.checkpoint_adapter import load_gpt2_checkpoint
from src.certified_transformer import CertifiedDecoder
from src.experiment_inventory import source_hashes
from src.request_workload import counterbalanced_orders
from src.run_store import canonical_json,digest,strict_json
from src.sequence_campaign import (build_sequence_campaign,run_sequence_campaign,
    validate_sequence_campaign,validate_sequence_campaign_files)
from src.sequence_runner import verify_sequence_archive
from src.target_manifest import TargetRecipe,build_target
from src.worker_control import WorkerLimits
from tests.test_checkpoint_adapter import checkpoint_fixture,write_checkpoint


def fixture(root, *, phase='software_test', repeats=1, bad_target=False, budget_hours=1, pause=False):
    config,weights,_=checkpoint_fixture()
    checkpoint=root/'checkpoint';checkpoint.mkdir()
    write_checkpoint(checkpoint,config,weights)
    provenance={'dataset_id':'software','dataset_revision':'fixture-v1','split':'test','license':'test',
                'tokenizer_id':'integer-fixture','tokenizer_revision':'v1'}
    calibration={'schema':'prepared-token-records-v1','provenance':provenance,
                 'records':[{'id':'a','tokens':[0,1]},{'id':'b','tokens':[1,0]},{'id':'c','tokens':[0,2]}]}
    heldout=dict(calibration,records=[{'id':'eval','tokens':[2,1]}])
    refs={}
    for name,data in [('calibration',calibration),('heldout',heldout)]:
        raw=canonical_json(data);(root/(name+'.json')).write_bytes(raw)
        refs[name]={'path':name+'.json','sha256':digest(raw)}
    workload={'schema':'calibration-workload-v1','root_id':'root0','seed':71,'original_record_ids':['a','b','c'],
              'prepared_records_sha256':refs['calibration']['sha256'],'original_state_sha256':'1'*64,
              'scores_sha256':'2'*64,'requests':[]}
    removed=[]
    for i,rid in enumerate(['a','b','c']):
        previous=list(removed);removed.append(rid)
        workload['requests'].append({'request_id':f'delete{i}','deleted_ids':[rid],
            'starting_state':'original' if i==0 else f'delete{i-1}',
            'execution_requirement':'previous_committed_state','blocked_reason':None,
            'previously_deleted_ids':previous,'cumulative_deleted_ids':list(removed),
            'analysis_group':'sequential'})
    recipe=TargetRecipe(original_token_count=6)
    decoder=CertifiedDecoder(load_gpt2_checkpoint(checkpoint,max_parameter_elements=1000).decoder)
    target=build_target(decoder,recipe).digest
    limits=WorkerLimits(wall_seconds=90,cpu_seconds=60,address_space_bytes=512*1024*1024,threads=1,
        affinity_cpus=(min(os.sched_getaffinity(0)),),termination_grace_seconds=0,file_size_bytes=32*1024*1024)
    runs=[]
    for repeat in range(repeats):
        manifest=dict(schema='calibration-sequence-v1',sequence_id='three',root_id='root0',configuration_id='software',
            repeat_index=repeat,phase=phase,checkpoint={'path':'checkpoint','files_sha256':{
                p.name:digest(p.read_bytes()) for p in checkpoint.iterdir()},'max_parameter_elements':1000},
            requests=[{'request_id':r['request_id'],'deleted_ids':r['deleted_ids']} for r in workload['requests']],
            target=recipe.payload(),chart=ChartRecipe(mode='none').payload(),
            method_order=counterbalanced_orders(seed=71,root_id='root0',request_id='three',repeats=repeat+1)[-1],
            protocol={'path':'protocol.json','sha256':None},**refs)
        runs.append({'run_id':f'run{repeat}','manifest_path':f'sequence{repeat}.json','manifest':manifest,
                     'target_manifest_sha256':'0'*64 if bad_target else target})
    campaign=build_sequence_campaign(campaign_id='software-sequences',protocol_path='protocol.json',
        workloads=[workload],runs=runs,worker_limits=limits.payload(),sources=source_hashes(Path(__file__).resolve().parents[1]))
    inventory=root/'inventory.json';inventory.write_bytes(canonical_json(campaign))
    protocol={'schema':'calibration-protocol-v1','status':'experiments_paused' if pause else 'software_fixture',
              'planned_inventory_sha256':digest(inventory.read_bytes()),'blocked_fields':[],
              'resources':{'phase_cpu_hour_caps':{phase:budget_hours}}}
    if phase=='confirmation':
        protocol.update(status='frozen_confirmation',sequence_confirmation={'configuration_ids':['software'],
            'root_ids':['root0'],'sequence_ids':['three'],'timing_repeats':repeats})
    (root/'protocol.json').write_bytes(canonical_json(protocol))
    for run in runs:
        run['manifest']['protocol']['sha256']=digest(canonical_json(protocol))
        (root/run['manifest_path']).write_bytes(canonical_json(run['manifest']))
    return inventory,campaign,protocol


@unittest.skipUnless(hasattr(os,'sched_setaffinity'),'Linux workers required')
class SequenceCampaignTests(unittest.TestCase):
    def test_inventory_cycle_order_and_confirmation_product(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,campaign,protocol=fixture(root,phase='confirmation',repeats=2)
            checked=validate_sequence_campaign_files(path)
            self.assertEqual(len(checked['checked']),2)
            self.assertTrue(all(e['manifest_payload']['protocol']['sha256'] is None for e in campaign['entries']))
            changed=strict_json(canonical_json(campaign))
            changed['entries'][0]['request_provenance'].reverse()
            with self.assertRaisesRegex(ValueError,'provenance'):
                validate_sequence_campaign(changed)
            protocol['sequence_confirmation']['root_ids'].append('missing-root')
            raw=canonical_json(protocol);(root/'protocol.json').write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'exact declared product'):
                validate_sequence_campaign_files(path)

    def test_pause_and_source_change_before_worker_or_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,campaign,_=fixture(root,phase='development',pause=True)
            valid=run_sequence_campaign(path,root/'out',validate_only=True)
            self.assertEqual(valid['status'],'validated')
            with self.assertRaisesRegex(ValueError,'paused'):
                run_sequence_campaign(path,root/'out')
            self.assertFalse((root/'out').exists())
            campaign['source_sha256']['src/sequence_campaign.py']='0'*64
            path.write_bytes(canonical_json(campaign))
            with self.assertRaisesRegex(ValueError,'source hashes'):
                validate_sequence_campaign_files(path)

    def test_feasibility_phase_requires_cap_and_obeys_pause(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,campaign,protocol=fixture(root,phase='feasibility',pause=True,budget_hours=3)
            self.assertEqual(validate_sequence_campaign_files(path)['phase_cpu_seconds']['feasibility'],10800)
            with self.assertRaisesRegex(ValueError,'paused'):
                run_sequence_campaign(path,root/'out')
            self.assertFalse((root/'out').exists())
            protocol['resources']['phase_cpu_hour_caps']={}
            raw=canonical_json(protocol);(root/'protocol.json').write_bytes(raw)
            manifest=strict_json((root/'sequence0.json').read_bytes())
            manifest['protocol']['sha256']=digest(raw)
            (root/'sequence0.json').write_bytes(canonical_json(manifest))
            with self.assertRaisesRegex(ValueError,'explicit CPU-hour cap'):
                validate_sequence_campaign_files(path)

    def test_bulk_success_original_once_and_verified_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,_,_=fixture(root,repeats=2)
            result=run_sequence_campaign(path,root/'out')
            errors=[]
            for row in result['runs']:
                if row['status']!='complete':
                    worker=root/'out'/'workers'/row['run_id']
                    record=strict_json((worker/'result.json').read_bytes())
                    errors.append(strict_json((worker/record['attempt']/'stderr-summary.json').read_bytes())['tail_utf8'])
            self.assertEqual(result['outcome'],'complete',errors)
            self.assertEqual(result['completed_sequences'],2)
            for row in result['runs']:
                sequence=root/'out'/'sequences'/row['run_id']
                verified=verify_sequence_archive(sequence)
                self.assertEqual(verified['result']['final_retained_ids'],[])
                self.assertEqual(len(list((sequence/'initial').glob('attempt-*'))),1)
                self.assertEqual([s['status'] for s in row['steps']],['complete']*3)
            budget_before=result['phase_cpu_budget_at_completion']
            with patch('src.sequence_campaign.run_limited',side_effect=AssertionError('resume launched worker')):
                resumed=run_sequence_campaign(path,root/'out')
            self.assertEqual(resumed,result)
            self.assertEqual(resumed['phase_cpu_budget_at_completion'],budget_before)

    def test_budget_denial_preserves_every_planned_step(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,_,_=fixture(root,repeats=2,budget_hours=0.001)
            with patch('src.worker_control.subprocess.Popen') as launch:
                result=run_sequence_campaign(path,root/'out')
            launch.assert_not_called()
            self.assertEqual(result['outcome'],'failed')
            self.assertEqual(len(result['runs']),2)
            self.assertTrue(all(r['failure']['kind']=='phase_cpu_budget_exhausted' for r in result['runs']))
            self.assertTrue(all(len(r['steps'])==3 for r in result['runs']))
            self.assertEqual(result['phase_cpu_budget_at_completion']['attempts'],{})

    def test_failed_scientific_outcome_archives_are_checked_on_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,_,_=fixture(root,bad_target=True)
            result=run_sequence_campaign(path,root/'out')
            self.assertEqual(result['outcome'],'failed')
            self.assertTrue(result['runs'][0]['archive_snapshot'])
            sequence=root/'out'/'sequences'/'run0'
            failure=next(sequence.glob('preflight-failure-*.json'))
            failure.write_bytes(failure.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'archive changed'):
                run_sequence_campaign(path,root/'out')

    def test_controller_interruption_reuses_sealed_worker_and_original_timing(self):
        from src import sequence_campaign as module
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,_,_=fixture(root)
            observe=module._observe_sequence
            with patch.object(module,'_observe_sequence',side_effect=KeyboardInterrupt('fixture parent interruption')):
                with self.assertRaises(KeyboardInterrupt):
                    run_sequence_campaign(path,root/'out')
            worker=(root/'out'/'workers'/'run0'/'result.json').read_bytes()
            with patch('src.worker_control.subprocess.Popen',side_effect=AssertionError('sealed worker restarted')):
                result=run_sequence_campaign(path,root/'out')
            self.assertEqual(result['outcome'],'complete',result['runs'])
            self.assertEqual(worker,(root/'out'/'workers'/'run0'/'result.json').read_bytes())


if __name__=='__main__': unittest.main()
