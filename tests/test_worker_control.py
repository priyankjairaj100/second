"""Bounded process fixtures. These tests do not establish empirical speed."""
from dataclasses import replace
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import unittest

from src.run_store import strict_json
from src.worker_control import WorkerLimits, run_limited


@unittest.skipUnless(hasattr(os, 'sched_setaffinity'), 'Linux process limits required')
class WorkerControlTests(unittest.TestCase):
    def limits(self, **changes):
        return replace(WorkerLimits(wall_seconds=5, cpu_seconds=3,
            address_space_bytes=128*1024*1024, threads=1,
            affinity_cpus=(min(os.sched_getaffinity(0)),), termination_grace_seconds=0,
            file_size_bytes=4*1024*1024), **changes)

    def run_code(self, root, code, **changes):
        return run_limited([sys.executable, '-c', code], root, self.limits(**changes),
                           identity={'software_fixture':True})

    def test_applies_limits_and_seals_exactly_once(self):
        with tempfile.TemporaryDirectory() as folder:
            result=self.run_code(folder, "print('bounded software fixture')")
            self.assertEqual(result['outcome']['status'], 'complete')
            self.assertEqual(result['limits_applied']['address_space'],[128*1024*1024]*2)
            self.assertEqual(result['limits_applied']['cpu_seconds'],[3,4])
            self.assertEqual(result['limits_applied']['affinity_cpus'], list(self.limits().affinity_cpus))
            self.assertTrue(all(x=='1' for x in result['limits_applied']['thread_environment'].values()))
            repeated=self.run_code(folder, "print('bounded software fixture')")
            self.assertEqual(repeated,result)
            self.assertEqual(len(list(Path(folder).glob('attempt-*'))),1)
            with self.assertRaisesRegex(ValueError,'identity'):
                self.run_code(folder, "print('different fixture')")

    def test_wall_timeout_is_durable_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            result=self.run_code(folder, 'import time; time.sleep(8)', wall_seconds=1)
            self.assertEqual(result['outcome']['status'],'failed')
            self.assertEqual(result['outcome']['kind'],'wall_timeout')
            self.assertLess(result['outcome']['elapsed_wall_ns'],5_000_000_000)
            self.assertEqual(self.run_code(folder,'import time; time.sleep(8)', wall_seconds=1),result)

    def test_cpu_limit_is_distinct_from_wall_timeout(self):
        with tempfile.TemporaryDirectory() as folder:
            result=self.run_code(folder, 'while True: pass', cpu_seconds=1)
            self.assertEqual(result['outcome']['status'],'failed')
            self.assertEqual(result['outcome']['kind'],'cpu_limit')
            self.assertEqual(result['outcome']['signal'],signal.SIGXCPU)

    def test_address_space_limit_rejects_large_allocation(self):
        with tempfile.TemporaryDirectory() as folder:
            code="try:\n x=bytearray(256*1024*1024)\nexcept MemoryError:\n raise SystemExit(17)"
            result=self.run_code(folder,code)
            self.assertEqual(result['outcome']['status'],'failed')
            self.assertEqual(result['outcome']['returncode'],17)
            # A nonzero exit alone does not prove memory exhaustion in arbitrary programs.
            self.assertEqual(result['outcome']['kind'],'nonzero_exit')

    def test_cleanup_stops_descendants_after_leader_exit(self):
        with tempfile.TemporaryDirectory() as folder:
            marker=Path(folder)/'orphan-marker'
            child="import time; from pathlib import Path; time.sleep(1.2); Path("+repr(str(marker))+").write_text('leaked')"
            code="import subprocess,sys; subprocess.Popen([sys.executable,'-c',"+repr(child)+"])"
            result=self.run_code(Path(folder)/'worker',code)
            self.assertEqual(result['outcome']['status'],'complete')
            time.sleep(1.4)
            self.assertFalse(marker.exists())

    def test_invalid_limits_acknowledgment_seals_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            code = "from pathlib import Path; p=next(Path(" + repr(folder) + ").glob('attempt-*/limits-ack.pending.json')); p.write_text('{}')"
            result = self.run_code(folder, code)
            self.assertEqual(result['outcome']['status'], 'failed')
            self.assertEqual(result['outcome']['kind'], 'limits_ack_invalid')
            self.assertIn('limits_ack_failure', result)
            self.assertEqual(self.run_code(folder, code), result)

    def test_strict_configuration_and_changed_artifact_rejection(self):
        with self.assertRaises(ValueError): self.limits(threads=True)
        with self.assertRaises(ValueError): self.limits(affinity_cpus=(0,0))
        with self.assertRaises(ValueError): WorkerLimits.from_payload({})
        with tempfile.TemporaryDirectory() as folder:
            result=self.run_code(folder,'pass')
            artifact=Path(folder)/result['attempt']/'request.json'
            artifact.write_bytes(artifact.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                self.run_code(folder,'pass')

class CampaignControlTests(unittest.TestCase):
    def fixture(self, root, *, phase='software_test', paused=True):
        from tests.test_checkpoint_adapter import checkpoint_fixture, write_checkpoint
        from src.chart_construction import ChartRecipe
        from src.experiment_inventory import build_campaign, source_hashes
        from src.experiment_runner import run_manifest
        from src.request_workload import counterbalanced_orders
        from src.run_store import canonical_json, digest
        from src.target_manifest import TargetRecipe
        config,weights,_=checkpoint_fixture()
        checkpoint=root/'checkpoint';checkpoint.mkdir()
        write_checkpoint(checkpoint,config,weights)
        provenance={'dataset_id':'software','dataset_revision':'fixture-v1','split':'test','license':'test',
                    'tokenizer_id':'integer-fixture','tokenizer_revision':'v1'}
        data={'calibration':{'schema':'prepared-token-records-v1','provenance':provenance,
                            'records':[{'id':'a','tokens':[0,1]},{'id':'b','tokens':[1,0]}]},
              'heldout':{'schema':'prepared-token-records-v1','provenance':provenance,
                         'records':[{'id':'eval','tokens':[2,1]}]},
              'protocol':{'schema':'calibration-protocol-v1','status':'experiments_paused' if paused else 'development'}}
        refs={}
        for key,value in data.items():
            raw=canonical_json(value);(root/(key+'.json')).write_bytes(raw)
            refs[key]={'path':key+'.json','sha256':digest(raw)}
        manifest=dict(schema='calibration-run-v1',root_id='r',request_id='delete-one',configuration_id='fixture',
                      repeat_index=0,phase=phase,checkpoint={'path':'checkpoint','files_sha256':{
                          p.name:digest(p.read_bytes()) for p in checkpoint.iterdir()},'max_parameter_elements':1000},
                      deleted_ids=['a'],target=TargetRecipe(original_token_count=4).payload(),
                      chart=ChartRecipe(mode='none').payload(),
                      method_order=counterbalanced_orders(seed=1,root_id='r',request_id='delete-one',repeats=1)[0],**refs)
        run=root/'run.json';run.write_bytes(canonical_json(manifest))
        validation=run_manifest(run,root/'unused',validate_only=True)
        workload={'schema':'calibration-workload-v1','root_id':'r','seed':1,
                  'prepared_records_sha256':refs['calibration']['sha256'],'original_state_sha256':'0'*64,
                  'scores_sha256':'0'*64,'original_record_ids':['a','b'],
                  'requests':[{'request_id':'delete-one','deleted_ids':['a'],'blocked_reason':None,
                               'execution_requirement':'independent_reset','analysis_group':'primary'}]}
        limits=WorkerLimits(wall_seconds=20,cpu_seconds=15,address_space_bytes=256*1024*1024,
                            threads=1,affinity_cpus=(min(os.sched_getaffinity(0)),),
                            termination_grace_seconds=0,file_size_bytes=8*1024*1024)
        campaign=build_campaign(campaign_id='software',protocol_path='protocol.json',worker_limits=limits.payload(),
            manifests=[{'manifest_path':'run.json','manifest':manifest,
                        'target_manifest_sha256':digest(canonical_json(validation['target']))}],
            workloads=[workload],source_sha256=source_hashes(Path(__file__).resolve().parents[1]))
        raw=canonical_json(campaign);inventory=root/'campaign.json';inventory.write_bytes(raw)
        protocol=dict(data['protocol'],planned_inventory_sha256=digest(raw))
        protocol_raw=canonical_json(protocol);(root/'protocol.json').write_bytes(protocol_raw)
        manifest['protocol']['sha256']=digest(protocol_raw);run.write_bytes(canonical_json(manifest))
        return inventory,manifest

    def test_campaign_preserves_membership_execution_and_resume(self):
        from src.experiment_campaign import run_campaign
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);inventory,_=self.fixture(root)
            validation=run_campaign(inventory,root/'results',validate_only=True)
            self.assertEqual(validation['planned_runs'],1)
            self.assertFalse((root/'results').exists())
            result=run_campaign(inventory,root/'results')
            self.assertEqual(result['outcome'],'complete',result['runs'])
            self.assertEqual(result['completed_runs'],1)
            self.assertEqual(result['execution_mode'],'isolated_comparison_warm_arms_os_cache_uncontrolled')
            self.assertEqual(run_campaign(inventory,root/'results'),result)
            worker=Path(result['runs'][0]['worker_record_path'])
            worker_data=strict_json(worker.read_bytes())
            log=worker.parent/worker_data['attempt']/'stdout-summary.json'
            log.write_bytes(log.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                run_campaign(inventory,root/'results')

    def test_pause_blocks_dispatch_without_creating_outputs(self):
        from src.experiment_campaign import run_campaign
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);inventory,_=self.fixture(root,phase='development')
            with self.assertRaisesRegex(ValueError,'paused'):
                run_campaign(inventory,root/'results')
            self.assertFalse((root/'results').exists())

    def test_changed_membership_blocks_dispatch(self):
        from src.experiment_campaign import run_campaign
        from src.run_store import canonical_json
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);inventory,manifest=self.fixture(root)
            manifest['deleted_ids']=[]
            (root/'run.json').write_bytes(canonical_json(manifest))
            with self.assertRaisesRegex(ValueError,'frozen inventory'):
                run_campaign(inventory,root/'results')
            self.assertFalse((root/'results').exists())

    def test_confirmation_requires_the_complete_declared_product(self):
        from copy import deepcopy
        from src.experiment_campaign import _validate_confirmation_product
        protocol = {'status':'frozen_confirmation', 'confirmation_configuration_ids':['c1','c2'],
                    'stages':{'confirmation':{'independent_roots':2,'timing_repeats':2}},
                    'sampling':{'requests':['q1','q2']}}
        campaign = {'entries':[{'phase':'confirmation','analysis_group':'primary',
                               'configuration_id':c,'root_id':r,'request_id':q,'repeat_index':i}
                              for c in ('c1','c2') for r in ('r1','r2') for q in ('q1','q2') for i in (0,1)]}
        _validate_confirmation_product(campaign,protocol)
        partial=deepcopy(campaign);partial['entries'].pop()
        with self.assertRaisesRegex(ValueError,'complete declared'):
            _validate_confirmation_product(partial,protocol)
        partial=deepcopy(campaign);partial['entries']=[e for e in partial['entries'] if e['root_id']=='r1']
        with self.assertRaisesRegex(ValueError,'calibration roots'):
            _validate_confirmation_product(partial,protocol)
        undeclared=deepcopy(protocol);del undeclared['confirmation_configuration_ids']
        with self.assertRaisesRegex(ValueError,'confirmation_configuration_ids'):
            _validate_confirmation_product(campaign,undeclared)

    def test_missing_worker_result_is_a_failure(self):
        from src.experiment_campaign import _comparison_outcome
        with tempfile.TemporaryDirectory() as folder:
            result=_comparison_outcome(Path(folder),{},'0'*64,'1'*64)
            self.assertEqual(result['status'],'failed')
            self.assertEqual(result['failure']['kind'],'missing_worker_result')


if __name__ == "__main__": unittest.main()
