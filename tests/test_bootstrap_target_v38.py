"""Software fixtures only. No empirical checkpoint or calibration data is loaded."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from research_v38 import bootstrap_target as target


class BootstrapProtocolFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=target.ROOT / 'tmp')
        self.root = Path(self.temp.name)
        self.stack = contextlib.ExitStack()
        self.stack.enter_context(patch.object(target, 'ROOT', self.root))
        helper = self.root / 'research_v38/bootstrap_target.py'
        helper.parent.mkdir()
        helper.write_text('# Explicit software fixture. No empirical program.\n')
        self.stack.enter_context(patch.object(target, '__file__', str(helper)))
        self.stack.enter_context(patch.object(target, 'source_hashes', return_value={'src/fixture.py': '1' * 64}))
        self.stack.enter_context(patch.object(target, 'capture_runtime_contract', return_value={'software_fixture': True}))
        model = self.root / 'tmp/models/distilgpt2'
        model.mkdir(parents=True)
        (model / 'config.json').write_bytes(b'{}')
        (model / 'model.safetensors').write_bytes(b'explicit-software-fixture-only')
        hashes = {name: target.hashed(model / name) for name in target.CHECKPOINT_HASHES}
        self.stack.enter_context(patch.object(target, 'CHECKPOINT_HASHES', hashes))
        self.directory = self.root / 'campaigns/bootstrap-fixture'

    def tearDown(self):
        self.stack.close()
        self.temp.cleanup()

    def test_registration_never_constructs_target_or_runs_worker(self):
        with patch.object(target, '_construct_static', side_effect=AssertionError('must not load')), \
             patch.object(target, 'run_limited', side_effect=AssertionError('must not run')):
            audit = target.register_bootstrap(self.directory)
        protocol, plan, limits = target.registration(self.directory)
        self.assertFalse(audit['numerical_execution'])
        self.assertEqual(audit['phase_cpu_cap_seconds'], limits.cpu_seconds + 2)
        self.assertEqual(plan['original_token_count'], 256)
        self.assertFalse((self.directory / 'outputs').exists())
        self.assertFalse((self.directory / 'phase-cpu-budget').exists())

    def test_registration_refuses_overwrite(self):
        target.register_bootstrap(self.directory)
        old = (self.directory / 'protocol.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            target.register_bootstrap(self.directory)
        self.assertEqual((self.directory / 'protocol.json').read_bytes(), old)

    def test_changed_checkpoint_refuses_before_model_load(self):
        target.register_bootstrap(self.directory)
        (self.root / 'tmp/models/distilgpt2/model.safetensors').write_bytes(b'changed')
        with patch.object(target, '_construct_static', side_effect=AssertionError('must not load')):
            with self.assertRaisesRegex(ValueError, 'Checkpoint hash differs'):
                target.launch_bootstrap(self.directory)
        self.assertFalse((self.directory / 'worker').exists())

    def test_changed_policy_refuses(self):
        target.register_bootstrap(self.directory)
        plan_path = self.directory / 'plan.json'
        plan = target.read(plan_path)
        plan['original_token_count'] = 128
        plan_path.write_bytes(target.canonical_json(plan))
        with self.assertRaisesRegex(ValueError, 'fixed policy'):
            target.registration(self.directory)

    def test_changed_source_refuses(self):
        target.register_bootstrap(self.directory)
        with patch.object(target, 'source_hashes', return_value={'src/fixture.py': '2' * 64}):
            with self.assertRaisesRegex(ValueError, 'source files changed'):
                target.registration(self.directory)

    def test_existing_attempt_refuses_retry(self):
        target.register_bootstrap(self.directory)
        (self.directory / 'worker').mkdir()
        with patch.object(target, 'run_limited', side_effect=AssertionError('must not retry')):
            with self.assertRaisesRegex(ValueError, 'already exists'):
                target.launch_bootstrap(self.directory)

    def test_missing_admission_prevents_target_load(self):
        target.register_bootstrap(self.directory)
        with patch.object(target, 'verify_command_admission', side_effect=ValueError('no admission')):
            with patch.object(target, '_construct_static', side_effect=AssertionError('must not load')):
                with self.assertRaisesRegex(ValueError, 'no admission'):
                    target.worker(self.directory / 'plan.json')
        self.assertFalse((self.directory / 'outputs').exists())

    def test_constructor_failure_seals_failure_without_target(self):
        target.register_bootstrap(self.directory)
        text = io.StringIO()
        with patch.object(target, 'verify_command_admission', return_value={}), \
             patch.object(target, '_construct_static', side_effect=FileNotFoundError('/proc/self/maps')), \
             contextlib.redirect_stdout(text):
            code = target.worker(self.directory / 'plan.json')
        self.assertEqual(code, 1)
        result = target.read(self.directory / 'outputs/completion.json')
        seal = target.read(self.directory / 'outputs/terminal.json')
        stdout = json.loads(text.getvalue())
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error']['type'], 'FileNotFoundError')
        self.assertEqual(seal['completion_sha256'], target.hashed(self.directory / 'outputs/completion.json'))
        self.assertEqual(stdout['terminal_sha256'], target.hashed(self.directory / 'outputs/terminal.json'))
        self.assertFalse((self.directory / 'outputs/fixed-target.json').exists())

    def test_noncanonical_and_symbolic_inputs_refuse(self):
        path = self.root / 'bad.json'
        path.write_text('{"a": 1}')
        with self.assertRaisesRegex(ValueError, 'not canonical'):
            target.read(path)
        linked = self.root / 'link.json'
        linked.symlink_to(path)
        with self.assertRaisesRegex(ValueError, 'Symbolic'):
            target.read(linked)


@unittest.skipUnless(Path('/proc/self/maps').is_file() and Path('/proc/cpuinfo').is_file(),
                     'The unchanged decoder requires actual procfs; no runtime facts are fabricated')
class StaticConstructorFixture(unittest.TestCase):
    def test_tiny_decoded_fixture_produces_manifest_without_neural_work(self):
        from tests.test_transformer_backend import decoder_fixture
        from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
        fixture = decoder_fixture(block_count=6)
        expected = {'config.json': '1' * 64, 'model.safetensors': '2' * 64}
        loaded = SimpleNamespace(decoder=fixture, provenance={'files_sha256': expected})
        with patch('src.checkpoint_adapter.load_gpt2_checkpoint', return_value=loaded) as load, \
             patch.object(OrderedFiniteDecoder, '_eval', side_effect=AssertionError('neural evaluation forbidden')):
            payloads, facts = target._construct_static(Path('software-fixture-only'), expected)
        load.assert_called_once_with(Path('software-fixture-only'), identity_encoding='binary64_tree_v2')
        self.assertEqual(len(facts['stage_ids']), 24)
        self.assertEqual(set(payloads), set(target.FILES))
        self.assertEqual(facts['fixed_target_sha256'], target.digest(target.canonical_json(payloads['fixed-target.json'])))
        self.assertNotEqual(facts['base_target_sha256'], facts['fixed_target_sha256'])
        self.assertEqual(payloads['recipe.json']['ridge'], [1, 100])


if __name__ == '__main__':
    unittest.main()
