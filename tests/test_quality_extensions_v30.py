"""Controller binding fixtures without research registration or worker runs."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import launch_quality_extensions_v30 as launcher
from scripts.launch_quality_extensions_v30 import checked_external, resolve_external_trials, verify_external_equalities


class QualityExtensionsV30Tests(unittest.TestCase):
    def test_external_model_and_completion_resolve_without_replacing_fields(self):
        parent = dict(attempt='/tmp/external-fixture',
            evidence={'outputs/completion.json':dict(bytes=10,sha256='a'*64)},
            verified_artifacts={'model':dict(file='model.bin',bytes=20,sha256='b'*64)})
        trial = dict(id='fixture',plan=dict(inputs={}),inputs_from_external=dict(
            new_completion=dict(external='parent',completion=True),new_model=dict(external='parent',artifact='model')))
        result = resolve_external_trials([trial],{'parent':parent})[0]['plan']['inputs']
        self.assertEqual(result['new_completion']['sha256'],'a'*64)
        self.assertEqual(result['new_model']['path'],'/tmp/external-fixture/outputs/model.bin')
        self.assertEqual(result['new_model']['bytes'],20)
        self.assertEqual(trial['plan']['inputs'],{})
        conflict = copy.deepcopy(trial);conflict['plan']['inputs']['new_model']={}
        with self.assertRaises(ValueError):
            resolve_external_trials([conflict],{'parent':parent})

    def test_unsafe_external_filename_fails(self):
        parent=dict(attempt='/tmp/external-fixture',verified_artifacts={'model':dict(file='../model.bin',bytes=1,sha256='a'*64)})
        trial=dict(plan=dict(inputs={}),inputs_from_external=dict(model=dict(external='parent',artifact='model')))
        with self.assertRaises(ValueError):
            resolve_external_trials([trial],{'parent':parent})

    def test_external_target_binding_preserves_explicit_plan_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'outputs').mkdir()
            (root/'outputs/completion.json').write_text(json.dumps(dict(base_target_sha256='a'*64)))
            parent=dict(attempt=str(root))
            trial=dict(plan=dict(inputs={}),plan_from_external=dict(expected_target=dict(external='parent',field='base_target_sha256')))
            self.assertEqual(resolve_external_trials([trial],{'parent':parent})[0]['plan']['expected_target'],'a'*64)
            trial['plan']['expected_target']='b'*64
            with self.assertRaises(ValueError):
                resolve_external_trials([trial],{'parent':parent})

    def test_external_evidence_freeze_detects_later_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            names=('plan.json','transaction.json','sealed-progress.json','outputs/completion.json',
                   'outputs/progress.json','worker/result.json')
            for name in names:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('{}')
            result=dict(status='complete',method='repair',artifacts={'model':dict(file='model.bin',bytes=1,sha256='a'*64)})
            spec={'parent':dict(attempt=str(root),equals=dict(status='complete',method='repair'))}
            with patch('src.service_terminal_evidence_v30.verify_completed',return_value=result):
                frozen=checked_external(spec)
                self.assertEqual(checked_external(frozen,require_bindings=True),frozen)
                (root/'plan.json').write_text('{"changed":true}')
                with self.assertRaises(ValueError):
                    checked_external(frozen,require_bindings=True)

    def test_external_gate_mismatch_fails(self):
        with patch('src.service_terminal_evidence_v30.verify_completed',return_value=dict(status='failed')):
            with self.assertRaises(ValueError):
                checked_external({'parent':dict(attempt='/tmp/external-fixture',equals=dict(status='complete'))})

    def test_original_and_retained_external_equality_is_recomputed(self):
        artifact = dict(file='model.bin', bytes=3, sha256='a'*64)
        external = {key:dict(verified_artifacts={'model':dict(artifact)}) for key in ('old', 'ordered')}
        pairs = [dict(left='old', right='ordered', artifacts=['model'])]
        self.assertTrue(verify_external_equalities(external, pairs)[0]['equal'])
        external['ordered']['verified_artifacts']['model']['bytes'] = 4
        with self.assertRaises(ValueError):
            verify_external_equalities(external, pairs)

    def test_completed_rejects_local_mismatch_without_or_with_true_sidecar(self):
        for saved in (None, dict(comparisons=[], all_equal=True)):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder); attempt = root/'attempts/new'; attempt.mkdir(parents=True)
                program = dict(external_attempts={}, trials=[dict(id='old'),
                    dict(id='new', compare_to=[dict(trial='old', artifacts=['model'])])])
                (root/'program.json').write_text(json.dumps(program))
                if saved is not None:
                    (attempt/'cross-method-agreement.json').write_text(json.dumps(saved))
                def completed(path):
                    code = 'a' if Path(path).name == 'old' else 'b'
                    return dict(artifacts={'model':dict(bytes=3, sha256=code*64)})
                with patch.object(launcher, 'C', root), \
                        patch('src.service_terminal_evidence_v30.verify_completed', side_effect=completed):
                    with self.assertRaisesRegex(ValueError, 'complete outputs disagree'):
                        launcher.completed('new')

    def test_completed_rechecks_external_comparison_on_dependency_read(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); attempt = root/'attempts/new'; attempt.mkdir(parents=True)
            program = dict(external_attempts={'parent':{}}, trials=[dict(id='new',
                compare_external=[dict(external='parent', artifacts=['model'])])])
            (root/'program.json').write_text(json.dumps(program))
            (attempt/'cross-method-agreement.json').write_text(json.dumps(dict(all_equal=True)))
            actual = dict(artifacts={'model':dict(bytes=3, sha256='a'*64)})
            external = {'parent':dict(verified_artifacts={'model':dict(bytes=3, sha256='b'*64)})}
            with patch.object(launcher, 'C', root), \
                    patch('src.service_terminal_evidence_v30.verify_completed', return_value=actual), \
                    patch.object(launcher, 'checked_external', return_value=external) as checked:
                with self.assertRaisesRegex(ValueError, 'complete outputs disagree'):
                    launcher.completed('new')
                checked.assert_called_once_with(program['external_attempts'], require_bindings=True)

    def test_equal_outputs_still_reject_forged_sidecar(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); attempt = root/'attempts/new'; attempt.mkdir(parents=True)
            (root/'program.json').write_text(json.dumps(dict(external_attempts={}, trials=[dict(id='old'),
                dict(id='new', compare_to=[dict(trial='old')])])))
            (attempt/'cross-method-agreement.json').write_text(json.dumps(dict(all_equal=True)))
            actual = dict(artifacts={'model':dict(bytes=3, sha256='a'*64)})
            with patch.object(launcher, 'C', root), \
                    patch('src.service_terminal_evidence_v30.verify_completed', return_value=actual):
                with self.assertRaisesRegex(ValueError, 'sidecar differs'):
                    launcher.completed('new')


if __name__=='__main__':unittest.main()
