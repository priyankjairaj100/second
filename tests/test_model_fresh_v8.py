"""Model-output control tests. These fixtures are not empirical observations."""
from dataclasses import replace
from fractions import Fraction as Q
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch

from src.chart_construction import ChartRecipe, build_chart, make_service, make_identity_service
from src.certified_transformer import CertifiedDecoder
from src.model_fresh import fresh_model, run_model_fresh, target_model_bytes
from src.repair_service import Record, StageSpec, JobSpec
from src.run_store import canonical_json, digest, strict_json
from src.service_telemetry import ServiceTelemetry
from src.target_manifest import TargetRecipe, build_target
from tests.test_checkpoint_adapter import checkpoint_fixture
from tests import test_isolated_comparison_v7 as fixtures


class ModelFreshTests(unittest.TestCase):
    def setup_target(self):
        _, _, base = checkpoint_fixture()
        decoder = CertifiedDecoder(base)
        target = build_target(decoder, TargetRecipe(4, group_count=1))
        records = tuple(Record(str(i), decoder.record_payload(tokens))
                        for i, tokens in enumerate(((0, 1), (1, 0))))
        return decoder, target, records

    def test_same_target_model_across_index_families(self):
        decoder, target, records = self.setup_target()
        for tier in ('linear', 'quadratic'):
            service = make_service(decoder, target, build_chart(decoder, target,
                         ChartRecipe(mode='none', response_tier=tier)))
            actual = fresh_model(service.job, service.evaluator, records, target_digest=target.digest)
            expected = service.fresh(records)
            self.assertEqual(actual.output.canonical_bytes(), target_model_bytes(target.digest, expected.state.model))
            self.assertFalse(any('extractor' in k for k in actual.ledger.as_mapping()))
        identity = make_identity_service(decoder, target)
        expected = identity.fresh(records).state
        self.assertEqual(actual.output.canonical_bytes(), target_model_bytes(target.digest, expected.model))

    def test_dependency_closure_and_empty_target(self):
        stages = tuple(StageSpec(name, dependencies, ((Q(3, 4),),), ((Q(0), Q(1)),), Q(1), Q(4))
                       for name, dependencies in (('a', ()), ('b', ('a',)), ('c', ('b',))))
        job = JobSpec(stages, 'fixture', 'none')
        seen = []
        def evaluator(record, stage, prefix):
            seen.append((stage.stage_id, tuple(prefix.as_mapping())))
            return ((Q(len(prefix.outputs)+1),),)
        records = (Record('one', b'fixture'),)
        result = fresh_model(job, evaluator, records, target_digest='a'*64)
        self.assertEqual(seen, [('a', ()), ('b', ('a',)), ('c', ('a', 'b'))])
        empty = fresh_model(job, lambda *args: self.fail('empty target read data'), (), target_digest='a'*64)
        self.assertEqual(result.output.model, empty.output.model)
        with self.assertRaises(ValueError):
            fresh_model(job, evaluator, records+records, target_digest='a'*64)

    def test_telemetry_preserves_bytes_and_evaluator_failure_aborts(self):
        decoder, target, records = self.setup_target()
        service = make_identity_service(decoder, target)
        plain = fresh_model(service.job, service.evaluator, records, target_digest=target.digest)
        telemetry = ServiceTelemetry()
        traced = fresh_model(service.job, service.evaluator, records, target_digest=target.digest, telemetry=telemetry)
        self.assertEqual(plain.output.canonical_bytes(), traced.output.canonical_bytes())
        self.assertIn('factor_rounding', telemetry.payload()['timings'])
        with self.assertRaisesRegex(ArithmeticError, 'unavailable'):
            fresh_model(service.job, lambda *args: (_ for _ in ()).throw(ArithmeticError('unavailable')),
                        records, target_digest=target.digest)

    def test_manifest_skips_response_construction_and_heldout_loading(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, manifest = fixtures.IsolatedComparisonTests().fixture(root)
            manifest['heldout'] = {'path': 'not-needed.json', 'sha256': 'a'*64}
            path = root/'run.json'; path.write_bytes(canonical_json(manifest))
            with patch('src.chart_construction.build_chart', side_effect=AssertionError('chart created')), \
                 patch('src.chart_construction.make_service', side_effect=AssertionError('service created')):
                result = run_model_fresh(path, root/'model')
                self.assertEqual(result['outcome']['status'], 'complete', result)
                self.assertEqual(result['output_contract'], 'model_only')
                self.assertEqual(set(result['artifacts']), {'manifest.json', 'model.json'})
                self.assertFalse(result['canonical_deletion_state_returned'])
                self.assertEqual(run_model_fresh(path, root/'model'), result)
            artifact = root/'model'/result['attempt']/'model.json'
            artifact.write_bytes(artifact.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError, 'artifact hash mismatch'):
                run_model_fresh(path, root/'model')

    def test_pause_and_standalone_confirmation_block_before_output(self):
        for phase in ('development', 'confirmation'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                _, manifest = fixtures.IsolatedComparisonTests().fixture(root)
                manifest['phase'] = phase
                (root/'run.json').write_bytes(canonical_json(manifest))
                with self.assertRaisesRegex(ValueError, 'paused|frozen inventory'):
                    run_model_fresh(root/'run.json', root/'model')
                self.assertFalse((root/'model').exists())

    def test_complete_deletion_produces_ridge_only_model(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            _, manifest=fixtures.IsolatedComparisonTests().fixture(root)
            records=strict_json((root/manifest['calibration']['path']).read_bytes())
            manifest['deleted_ids']=[r['id'] for r in records['records']]
            path=root/'run.json';path.write_bytes(canonical_json(manifest))
            result=run_model_fresh(path,root/'model')
            self.assertEqual(result['outcome']['status'],'complete',result)
            self.assertEqual(result['retained_records'],0)
            self.assertEqual(result['ledger'].get('fresh_target_evaluator_calls',0),0)

    def test_measured_feasibility_requires_and_charges_live_admission(self):
        from src.transaction_timing import measure_command, transaction_source_hashes
        from src.worker_control import WorkerLimits
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, manifest = fixtures.IsolatedComparisonTests().fixture(root)
            protocol_path = root/'protocol.json'
            protocol = strict_json(protocol_path.read_bytes())
            protocol.update(status='software_fixture_open', resources={'phase_cpu_hour_caps': {'feasibility': 1}})
            protocol_raw = canonical_json(protocol); protocol_path.write_bytes(protocol_raw)
            manifest['phase'] = 'feasibility'
            manifest['protocol']['sha256'] = digest(protocol_raw)
            manifest_path = root/'run.json'; manifest_path.write_bytes(canonical_json(manifest))
            output = root/'model'
            with self.assertRaisesRegex(ValueError, 'active phase CPU admission'):
                run_model_fresh(manifest_path, output)
            self.assertFalse(output.exists())
            plan = strict_json((root/'isolated.json').read_bytes())
            limits = WorkerLimits.from_payload(plan['worker_limits'])
            repository = Path(__file__).resolve().parents[1]
            command = [sys.executable, str(repository/'scripts/run_model_fresh.py'),
                       str(manifest_path), '--output', str(output)]
            observed = measure_command(command, output, root/'observer', limits,
                identity={'software_fixture': True}, source_sha256=transaction_source_hashes(),
                output_contract='model_only', budget_config={'protocol_path': str(protocol_path),
                    'protocol_sha256': digest(protocol_raw), 'phase': 'feasibility'})
            receipt = observed['receipt']
            self.assertEqual(receipt['outcome']['status'], 'complete', receipt)
            self.assertTrue(observed['new_latency_observation'])
            self.assertEqual(receipt['budget_debit']['phase'], 'feasibility')
            self.assertEqual(receipt['budget_debit']['state'], 'settled')


if __name__=='__main__':
    unittest.main()
