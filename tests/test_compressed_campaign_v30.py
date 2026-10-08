"""Unregistered controller fixtures; no empirical worker or registration."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import launch_compressed_service_v30 as launcher
from src.run_store import canonical_json, digest
from tests.test_compressed_service_worker_v30 import policy, records


class CompressedCampaignTests(unittest.TestCase):
    def test_resolved_external_inputs_match_worker_exact_descriptor_contract(self):
        parent = dict(attempt='/tmp/fixture',evidence={'outputs/completion.json':dict(bytes=10,sha256='a'*64)},
            verified_artifacts={'model':dict(file='model.bin',bytes=20,sha256='b'*64)})
        trial = dict(plan=dict(inputs={}),inputs_from_external=dict(
            lossless_completion=dict(external='parent',completion=True),
            lossless_model=dict(external='parent',artifact='model')))
        resolved = launcher.resolve_external_trials([trial],{'parent':parent})[0]['plan']['inputs']
        self.assertTrue(all(set(value) == {'path','sha256'} for value in resolved.values()))
        self.assertEqual(parent['verified_artifacts']['model']['bytes'],20)
        self.assertEqual(trial['plan']['inputs'],{})
        conflict = copy.deepcopy(trial); conflict['plan']['inputs']['lossless_model'] = {}
        with self.assertRaises(ValueError):launcher.resolve_external_trials([conflict],{'parent':parent})

    def trial(self):
        plan = dict(policy(),decoder_backend='ordered',max_certificate_workspace_bytes=2**30)
        plan['inputs'] = {key:{} for key in ('records','config','weights','reference_completion')}
        return dict(id='repair',script='run_compressed_service_v30.py',plan=plan,
            inputs_from_trial=dict(prior_state=dict(trial='convert',artifact='state'),
                compressed_preparation_completion=dict(trial='convert',completion=True)))

    def test_late_bindings_are_complete_and_cannot_replace_inputs(self):
        trial = self.trial(); launcher.validate_trial_access(trial)
        bad = copy.deepcopy(trial);bad['plan']['inputs']['prior_state'] = {}
        with self.assertRaisesRegex(ValueError,'replace'):launcher.validate_trial_access(bad)
        bad = copy.deepcopy(trial);del bad['inputs_from_trial']['prior_state']
        with self.assertRaisesRegex(ValueError,'capability'):launcher.validate_trial_access(bad)
        bad = copy.deepcopy(trial);bad['script'] = 'run_other.py'
        with self.assertRaisesRegex(ValueError,'reviewed worker'):launcher.validate_trial_access(bad)

    def test_shape_admission_checks_every_stage_without_decoder_construction(self):
        import numpy as np
        from src.compact_state import CompactState, StageCodes, serialize
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'outputs').mkdir()
            stages=tuple(StageCodes.from_array('s'+str(i),np.zeros((2,3)),grid_axis='row',bits=4,
                scale_exponents=(0,0)) for i in range(24))
            raw=serialize(CompactState('a'*64,stages,()));(root/'outputs/model.bin').write_bytes(raw)
            source=root/'records.json';source.write_bytes(canonical_json(records()))
            trial=self.trial();trial['plan']['inputs']['records']={'path':str(source),'sha256':digest(source.read_bytes())}
            external={'original':dict(attempt=str(root),verified_artifacts={'model':dict(file='model.bin',sha256=digest(raw))})}
            with patch('src.checkpoint_adapter.load_gpt2_checkpoint',side_effect=AssertionError('no checkpoint loading')):
                report=launcher.assess_pilot_resources([trial],external)
                self.assertEqual(len(report['reports'][0]['certificates']),24)
                self.assertTrue(report['reports'][0]['all_certificate_stages_admitted'])
                self.assertFalse(report['reports'][0]['neural_execution'])
                trial['plan']['max_certificate_workspace_bytes']=1
                with self.assertRaisesRegex(ValueError,'known certificate admission refusal'):
                    launcher.assess_pilot_resources([trial],external)

    def test_failed_or_wrong_model_quality_gate_stops_external_binding(self):
        equals={'status':'complete','development_safety_gate_pass':True,
                'matched_quality_gate_pass':True,'historical_control_parity_pass':True,
                'provenance.new_model_sha256':'a'*64}
        passed=dict(status='complete',development_safety_gate_pass=True,matched_quality_gate_pass=True,
                    historical_control_parity_pass=True,provenance={'new_model_sha256':'a'*64})
        for result in (dict(passed,development_safety_gate_pass=False),
                       dict(passed,matched_quality_gate_pass=False),
                       dict(passed,historical_control_parity_pass=False),
                       dict(passed,provenance={'new_model_sha256':'b'*64})):
            with patch('src.service_terminal_evidence_v30.verify_completed',return_value=result):
                with self.assertRaisesRegex(ValueError,'prerequisite differs'):
                    launcher.checked_external({'quality':dict(attempt='/tmp/software-fixture',equals=equals)})

    def test_storage_and_latency_gates_preserve_completed_losing_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);raw=canonical_json(dict(controller_elapsed_ns=100));(root/'transaction.json').write_bytes(raw)
            external={'reference':dict(attempt=str(root),evidence={'transaction.json':dict(sha256=digest(raw))},
                verified_artifacts={'state':dict(bytes=30,sha256='a'*64)})}
            for name,elapsed in (('second',80),('third',120)):
                path=root/name;path.mkdir();payload=canonical_json(dict(controller_elapsed_ns=elapsed))
                (path/'transaction.json').write_bytes(payload)
                external[name]=dict(attempt=str(path),evidence={'transaction.json':dict(sha256=digest(payload))})
            trial=dict(storage_gate=dict(external='reference',artifact='state',strictly_smaller=True),
                latency_gate=dict(externals=['reference','second','third'],strictly_faster=True,
                    aggregation='minimum_recorded_controller_elapsed_ns'))
            result=dict(status='complete',artifacts={'state':dict(bytes=20,sha256='b'*64)})
            gates=launcher.scientific_gates(trial,result,external,dict(controller_elapsed_ns=70))
            self.assertTrue(gates['all_passed'])
            self.assertEqual(gates['checks']['latency']['reference_ns'],80)
            self.assertEqual([row['controller_elapsed_ns'] for row in gates['checks']['latency']['references']], [100,80,120])
            # Beating the first reference alone is insufficient.
            gates=launcher.scientific_gates(trial,result,external,dict(controller_elapsed_ns=90))
            self.assertFalse(gates['all_passed']);self.assertFalse(gates['checks']['latency']['passed'])
            gates=launcher.scientific_gates(trial,result,external,dict(controller_elapsed_ns=80))
            self.assertFalse(gates['checks']['latency']['passed'])
            invalid=copy.deepcopy(trial);invalid['latency_gate']['externals']=['reference','reference']
            with self.assertRaisesRegex(ValueError,'unique references'):
                launcher.scientific_gates(invalid,result,external,dict(controller_elapsed_ns=70))
            result['artifacts']['state']['bytes']=30
            gates=launcher.scientific_gates(trial,result,external,dict(controller_elapsed_ns=70))
            self.assertFalse(gates['checks']['storage']['passed'])
            self.assertEqual(result['status'],'complete')
            (root/'transaction.json').write_bytes(canonical_json(dict(controller_elapsed_ns=200)))
            with self.assertRaisesRegex(ValueError,'latency evidence changed'):
                launcher.scientific_gates(trial,result,external,dict(controller_elapsed_ns=90))

    def test_completed_recomputes_scientific_gates_and_rejects_forged_sidecar(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);attempt=root/'attempts/repair';attempt.mkdir(parents=True)
            trial=dict(id='repair',storage_gate=dict(external='reference',artifact='state',strictly_smaller=True))
            (root/'program.json').write_bytes(canonical_json(dict(trials=[trial],external_attempts={'reference':{}})))
            (attempt/'transaction.json').write_bytes(canonical_json(dict(controller_elapsed_ns=100)))
            actual=dict(status='complete',artifacts={'state':dict(bytes=40,sha256='a'*64)})
            external={'reference':dict(verified_artifacts={'state':dict(bytes=30,sha256='b'*64)})}
            with patch.object(launcher,'C',root),patch.object(launcher,'checked_external',return_value=external), \
                 patch('src.service_terminal_evidence_v30.verify_completed',return_value=actual):
                result=launcher.completed('repair')
                self.assertEqual(result['status'],'complete')
                self.assertFalse(result['registered_scientific_gates']['all_passed'])
                (attempt/'scientific-gates.json').write_bytes(canonical_json(dict(all_passed=True,checks={})))
                with self.assertRaisesRegex(ValueError,'scientific gates differ'):
                    launcher.completed('repair')


if __name__=='__main__':unittest.main()
