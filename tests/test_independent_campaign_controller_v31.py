"""Controller contracts with no successful registration or empirical worker."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import launch_independent_requests_v31 as launcher
from scripts import prepare_independent_campaigns_v31 as prepare
from src.run_store import canonical_json


class IndependentControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs=prepare.build()

    def test_real_designs_validate_and_declared_order_cannot_change(self):
        original=launcher.check_file
        def cheap(entry):
            if entry['path'].endswith('model.safetensors'):return Path(entry['path'])
            return original(entry)
        with patch.object(launcher,'check_file',side_effect=cheap):
            for spec in self.specs.values():launcher.validate_design(spec)
            bad=copy.deepcopy(self.specs['wikitext']);bad['execution_order'][1:3]=reversed(bad['execution_order'][1:3])
            with self.assertRaisesRegex(ValueError,'execution order'):launcher.validate_design(bad)
            bad=copy.deepcopy(self.specs['wikitext']);bad['trials'][1]['plan']['record_ids']=bad['source_ids']
            with self.assertRaisesRegex(ValueError,'point plans'):launcher.validate_design(bad)
            bad=copy.deepcopy(self.specs['wikitext']);bad['trials'][-1]['cpu_seconds']+=1
            with self.assertRaisesRegex(ValueError,'1844'):launcher.validate_design(bad)

    def test_failed_pilot_gate_and_policy_retuning_are_rejected(self):
        spec=copy.deepcopy(self.specs['wikitext'])
        policy=copy.deepcopy(spec['trials'][-1]['plan'])
        program=dict(source_sha256={'src/fixture.py':'a'*64},controller_sha256={key:'f'*64 for key in launcher.prior_launcher.CONTROLLERS},
            trials=[dict(id='repair-128-48',plan=policy)])
        with patch.object(launcher,'check_file',return_value=Path('/software-fixture')), \
             patch.object(launcher,'hashed',return_value='f'*64), \
             patch.object(launcher,'registered_program',return_value=(program,b'program',b'protocol',{'runtime':{}})), \
             patch.object(launcher,'source_hashes',return_value=program['source_sha256']), \
             patch.object(launcher,'capture_runtime_contract',return_value={}), \
             patch.object(launcher.prior_launcher,'checked_external',return_value={}), \
             patch.object(launcher.prior_launcher,'verify_external_equalities',return_value=[]), \
             patch.object(launcher.prior_launcher,'completed') as checked:
            checked.return_value={'registered_scientific_gates':{'all_passed':False}}
            with self.assertRaisesRegex(ValueError,'scientific prerequisite failed'):
                launcher.prerequisites(spec)
            checked.return_value={'registered_scientific_gates':{'all_passed':True}}
            external,equalities,evidence=launcher.prerequisites(spec)
            self.assertEqual(evidence['policy']['max_certificate_workspace_bytes'],2**30)
            spec['trials'][-1]['plan']['sparse_budget']['max_rounds']=3
            with self.assertRaisesRegex(ValueError,'numerical policy differs'):
                launcher.prerequisites(spec)

    def test_fresh_conversion_and_all_scientific_prerequisites_cannot_be_weakened(self):
        original=launcher.check_file
        def cheap(entry):
            if entry['path'].endswith('model.safetensors'):return Path(entry['path'])
            return original(entry)
        cases=[]
        changed=copy.deepcopy(self.specs['wikitext'])
        changed['trials'][-2]['inputs_from_trial']['lossless_state']['trial']=changed['requests'][0]['repair_trial']
        cases.append(changed)
        changed=copy.deepcopy(self.specs['wikitext'])
        changed['trials'][-1]['storage_gate']['trial']=changed['trials'][0]['id']
        cases.append(changed)
        changed=copy.deepcopy(self.specs['wikitext'])
        changed['trials'][-1]['latency_gate']['trials']=[changed['trials'][0]['id']]
        cases.append(changed)
        changed=copy.deepcopy(self.specs['wikitext'])
        del changed['external_attempts']['matched-quality']['equals']['historical_control_parity_pass']
        cases.append(changed)
        changed=copy.deepcopy(self.specs['wikitext'])
        changed['prerequisite_scientific_gate']['trial']='convert-256-48'
        cases.append(changed)
        with patch.object(launcher,'check_file',side_effect=cheap):
            for index,spec in enumerate(cases):
                with self.subTest(index=index),self.assertRaisesRegex(ValueError,'prospective V31'):
                    launcher.validate_design(spec)

    def test_successful_pilot_does_not_admit_changed_numerical_sources_or_runtime(self):
        spec=copy.deepcopy(self.specs['wikitext'])
        program=dict(source_sha256={'src/fixture.py':'a'*64},
            controller_sha256={key:'f'*64 for key in launcher.prior_launcher.CONTROLLERS})
        with patch.object(launcher,'check_file',return_value=Path('/software-fixture')), \
             patch.object(launcher,'hashed',return_value='f'*64), \
             patch.object(launcher,'registered_program',return_value=(program,b'program',b'protocol',{'runtime':{'a':1}})), \
             patch.object(launcher.prior_launcher,'checked_external',return_value={}), \
             patch.object(launcher.prior_launcher,'verify_external_equalities',return_value=[]), \
             patch.object(launcher.prior_launcher,'completed',side_effect=AssertionError('reject drift first')):
            with patch.object(launcher,'source_hashes',return_value={'src/fixture.py':'b'*64}):
                with self.assertRaisesRegex(ValueError,'numerical sources differ'):
                    launcher.prerequisites(spec)
            with patch.object(launcher,'source_hashes',return_value=program['source_sha256']), \
                 patch.object(launcher,'capture_runtime_contract',return_value={'a':2}):
                with self.assertRaisesRegex(ValueError,'runtime differs'):
                    launcher.prerequisites(spec)

    def test_missing_prerequisite_creates_no_registration_or_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'spec.json';path.write_bytes(canonical_json(self.specs['wikitext']))
            with patch.object(launcher,'ROOT',root),patch.object(launcher,'validate_design'), \
                 patch.object(launcher,'prerequisites',side_effect=ValueError('pending scientific gate')), \
                 patch.object(launcher,'run_limited',side_effect=AssertionError('no worker')):
                with self.assertRaisesRegex(ValueError,'pending scientific gate'):
                    launcher.register(path,'wikitext')
            self.assertFalse((root/'campaigns/independent_wikitext_v31').exists())

    def test_cannot_skip_registered_preceding_transactions(self):
        spec=copy.deepcopy(self.specs['wikitext']);spec.update(source_sha256={'src/fixture.py':'a'*64},
            controller_sha256={key:'f'*64 for key in launcher.CONTROLLERS},historical_frozen_ledgers={})
        with patch.object(launcher,'registered_program',return_value=(spec,b'program',b'protocol',{'runtime':{}})), \
             patch.object(launcher,'hashed',return_value='f'*64),patch.object(launcher,'historical_ledgers',return_value={}), \
             patch.object(launcher,'capture_runtime_contract',return_value={}),patch.object(launcher,'prerequisites'), \
             patch.object(launcher,'validate_design'),patch.object(launcher,'completed',side_effect=ValueError('previous trial missing')) as checked, \
             patch.object(launcher,'PhaseBudget',side_effect=AssertionError('no reservation before order check')):
            with self.assertRaisesRegex(ValueError,'previous trial missing'):
                launcher.run('wikitext',spec['execution_order'][-1])
            self.assertEqual(checked.call_args.args[1],spec['execution_order'][0])

    def test_internal_model_and_scientific_checks_recompute_verified_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            trial=dict(id='compressed',compare_to=[dict(trial='cold',artifacts=['model'])],
                storage_gate=dict(trial='cold',artifact='state',strictly_smaller=True),
                latency_gate=dict(trials=['cold'],aggregation='minimum_recorded_controller_elapsed_ns',strictly_faster=True))
            (root/'program.json').write_bytes(canonical_json(dict(trials=[dict(id='cold'),trial])))
            for name,clock in (('cold',50),('compressed',60)):
                path=root/'attempts'/name;path.mkdir(parents=True)
                (path/'transaction.json').write_bytes(canonical_json(dict(controller_elapsed_ns=clock)))
            def verified(path):
                compressed=Path(path).name=='compressed'
                return dict(status='complete',artifacts=dict(model=dict(bytes=3,sha256='a'*64),
                    state=dict(bytes=2 if compressed else 3,sha256=('b' if compressed else 'c')*64)))
            with patch.object(launcher,'verify_completed',side_effect=verified):
                result=launcher.completed(root,'compressed')
                self.assertTrue(result['verified_comparisons']['all_equal'])
                self.assertTrue(result['registered_scientific_gates']['checks']['storage']['passed'])
                self.assertFalse(result['registered_scientific_gates']['all_passed'])
                self.assertEqual(result['status'],'complete')
                path=root/'attempts/compressed/scientific-gates.json'
                path.write_bytes(canonical_json(dict(all_passed=True)))
                with self.assertRaisesRegex(ValueError,'scientific gate sidecar changed'):
                    launcher.completed(root,'compressed')


if __name__=='__main__':unittest.main()
