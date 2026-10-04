"""Frozen measured dispatch correctness fixtures, never research evidence."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from src.measured_comparison import build_measured_plan, measured_source_hashes
from src.measured_inventory import (METHODS, build_measured_campaign, measured_counterbalanced_orders,
    measured_analysis_plan, run_measured_campaign, validate_measured_campaign_files,
    validate_measured_inventory, verify_model_manifest)
from src.model_fresh import model_fresh_command, run_model_fresh
from src.run_store import canonical_json, digest, strict_json
from tests import test_worker_control as fixtures


def fixture(root, *, phase='software_test', paused=False, quality=False, bad_target=False, explicit_caps=True):
    old_path, manifest = fixtures.CampaignControlTests().fixture(root)
    old = strict_json(old_path.read_bytes())
    manifest['phase'] = phase
    protocol = {'schema': 'calibration-protocol-v1', 'status': 'experiments_paused' if paused else
                'frozen_confirmation' if phase == 'confirmation' else 'software_fixture_open',
                'blocked_fields': [], 'confirmation_configuration_ids': ['fixture'],
                'stages': {'confirmation': {'independent_roots': 1, 'timing_repeats': 1}},
                'sampling': {'requests': ['delete-one']},
                'resources': {'phase_cpu_hour_caps': {phase: 1} if explicit_caps else {}}}
    sources = measured_source_hashes()
    order = measured_counterbalanced_orders(seed=1, root_id='r', request_id='delete-one', repeats=1)[0]
    plan = build_measured_plan(manifest_path='run.json', manifest=manifest,
        target_manifest_sha256='f'*64 if bad_target else old['entries'][0]['target_manifest_sha256'],
        worker_limits=old['worker_limits'], sources=sources, method_order=order, quality=quality)
    inventory = build_measured_campaign(campaign_id='fixture', protocol_path='protocol.json',
        worker_limits=old['worker_limits'], plans=[{'plan_path': 'plan.json', 'plan': plan}],
        workloads=old['workloads'], sources=sources)
    path = root/'measured-campaign.json'; path.write_bytes(canonical_json(inventory))
    protocol['planned_inventory_sha256'] = digest(path.read_bytes())
    protocol_raw = canonical_json(protocol); (root/'protocol.json').write_bytes(protocol_raw)
    manifest['protocol']['sha256'] = digest(protocol_raw)
    (root/'run.json').write_bytes(canonical_json(manifest)); (root/'plan.json').write_bytes(canonical_json(plan))
    return path, inventory


@unittest.skipUnless(hasattr(os, 'wait4') and hasattr(os, 'sched_setaffinity'), 'Linux workers required')
class MeasuredCampaignTests(unittest.TestCase):
    def test_counterbalance_all_four_positions_and_plan_schema(self):
        orders = measured_counterbalanced_orders(seed=71, root_id='r', request_id='q', repeats=8)
        for block in (orders[:4], orders[4:]):
            for position in range(4):
                self.assertEqual(Counter(row[position] for row in block), Counter(METHODS))
        with tempfile.TemporaryDirectory() as folder:
            path, inventory = fixture(Path(folder), explicit_caps=False)
            checked = validate_measured_campaign_files(path)
            self.assertEqual(checked['phase_cpu_seconds']['software_test'], 5*(15+2))
            analysis = measured_analysis_plan(inventory, protocol_sha256=checked['protocol_sha256'])
            self.assertEqual(set(analysis['planned_runs'][0]['planned_methods']), set(METHODS))
            changed = deepcopy(inventory)
            changed['entries'][0]['measured_plan_payload']['method_order'].reverse()
            with self.assertRaisesRegex(ValueError, 'counterbalance'):
                validate_measured_inventory(changed)

    def test_normalized_cycle_and_actual_membership(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); path,inventory=fixture(root, phase='confirmation')
            run_id=inventory['entries'][0]['run_id']
            authorization=verify_model_manifest(path,run_id,root/'plan.json',root/'run.json')
            self.assertEqual(authorization['inventory_sha256'],digest(path.read_bytes()))
            self.assertEqual(authorization['manifest_sha256'],digest((root/'run.json').read_bytes()))
            self.assertEqual(authorization['execution_mode'],'clean')
            self.assertIsNone(inventory['entries'][0]['manifest_payload']['protocol']['sha256'])
            with self.assertRaisesRegex(ValueError,'absent'):
                verify_model_manifest(path,'forged',root/'plan.json',root/'run.json')
            with self.assertRaisesRegex(ValueError,'sequence step'):
                verify_model_manifest(path,run_id,root/'plan.json',root/'run.json',sequence_step=0)
            with patch('src.experiment_runner._run_manifest',side_effect=AssertionError('loaded')):
                with self.assertRaisesRegex(ValueError,'frozen inventory'):
                    run_model_fresh(root/'run.json',root/'standalone')
                with self.assertRaisesRegex(ValueError,'active phase CPU admission'):
                    run_model_fresh(root/'run.json',root/'unadmitted',inventory_path=path,
                        inventory_run_id=run_id,plan_path=root/'plan.json',execution_mode='clean')
            command=model_fresh_command(root/'run.json',root/'unadmitted',inventory_path=path,
                        inventory_run_id=run_id,plan_path=root/'plan.json',execution_mode='clean')
            self.assertEqual(command[-2:],['--execution-mode','clean'])
            self.assertIn('--inventory-run-id',command)

    def test_pause_complete_product_changed_runtime_and_mode_rejected(self):
        for phase in ('development','feasibility'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as folder:
                root=Path(folder);path,_=fixture(root,phase=phase,paused=True)
                with self.assertRaisesRegex(ValueError,'paused'):
                    run_measured_campaign(path,root/'out')
                self.assertFalse((root/'out').exists())
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path,_=fixture(root,phase='confirmation')
            protocol=strict_json((root/'protocol.json').read_bytes())
            protocol['confirmation_configuration_ids'].append('omitted')
            (root/'protocol.json').write_bytes(canonical_json(protocol))
            with self.assertRaisesRegex(ValueError,'complete declared comparison product'):
                validate_measured_campaign_files(path)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path,inventory=fixture(root)
            inventory['runtime_contract']['kernel']+='-different'
            path.write_bytes(canonical_json(inventory))
            with self.assertRaisesRegex(ValueError,'runtime'):
                validate_measured_campaign_files(path)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path,inventory=fixture(root)
            with patch('src.experiment_runner._run_manifest',side_effect=AssertionError('loaded')):
                with self.assertRaisesRegex(ValueError,'instrumentation differs'):
                    run_model_fresh(root/'run.json',root/'out',inventory_path=path,
                        inventory_run_id=inventory['entries'][0]['run_id'],plan_path=root/'plan.json',execution_mode='diagnostic')

    def test_complete_campaign_resume_and_mutation_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path,inventory=fixture(root,phase='confirmation')
            validation=run_measured_campaign(path,root/'out',validate_only=True)
            self.assertFalse(validation['checkpoint_parameters_loaded'])
            result=run_measured_campaign(path,root/'out')
            self.assertEqual(result['outcome'],'complete',result['runs'])
            self.assertEqual(set(result['runs'][0]['analysis']['methods']),set(METHODS))
            self.assertEqual(len(result['phase_cpu_budget_at_completion']['attempts']),5)
            with patch('src.measured_inventory.run_measured_comparison',side_effect=AssertionError('new work')):
                self.assertEqual(run_measured_campaign(path,root/'out'),result)
            row=result['runs'][0]
            victim=root/'out'/'runs'/row['run_id']/'added.txt';victim.write_text('changed')
            with self.assertRaisesRegex(ValueError,'archive changed'):
                run_measured_campaign(path,root/'out')

    def test_dispatch_failure_preserves_four_denominators_and_partial_tree(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path,inventory=fixture(root)
            def fail(plan, output, **kwargs):
                output.mkdir(parents=True);(output/'partial.json').write_text('{}')
                raise ValueError('injected before observer')
            with patch('src.measured_inventory.run_measured_comparison',side_effect=fail):
                result=run_measured_campaign(path,root/'out')
            self.assertEqual(result['outcome'],'failed')
            row=result['runs'][0]
            self.assertEqual(set(row['analysis']['methods']),set(METHODS))
            self.assertEqual(run_measured_campaign(path,root/'out'),result)
            victim=root/'out'/'runs'/row['run_id']/'partial.json';victim.write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError,'archive changed'):
                run_measured_campaign(path,root/'out')


if __name__=='__main__':unittest.main()
