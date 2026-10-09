"""Recovery controller software checks; no model inference or registration."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import launch_independent_requests_v32 as s
from src.run_store import canonical_json


class RecoveryControllerTests(unittest.TestCase):
    def test_archived_gate_checks_without_binary_outputs(self):
        result=s.archive_evidence()
        self.assertEqual(result['metadata_files_checked'],279)
        self.assertFalse(result['historical_binary_outputs_reverified'])
        self.assertTrue(result['prior_gate']['all_passed'])

    def test_source_changes_are_rejected(self):
        with patch.object(s,'source_hashes',return_value={'changed': 'a'*64}):
            with self.assertRaisesRegex(ValueError,'numerical sources differ'):s.archive_evidence()

    def test_archive_binding_change_is_rejected(self):
        original=s.hashed
        def changed(path):return '0'*64 if str(path).endswith(s.BINDINGS) else original(path)
        with patch.object(s,'hashed',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'archive manifest changed'):s.archive_evidence()

    def test_metadata_mutation_cannot_be_hidden_by_missing_binary_scope(self):
        original=s.hashed
        target='compressed_service_v31/attempts/repair-128-48/transaction.json'
        def changed(path):return '0'*64 if str(path).endswith(target) else original(path)
        with patch.object(s,'hashed',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'historical metadata changed'):s.archive_evidence()

    def test_original_seven_trials_preserved(self):
        for corpus in ('wikitext','c4'):
            spec=s.build_spec(corpus)
            old=s.read_json(s.ROOT/('campaigns/independent_requests_v31_ready/'+corpus+'.spec.json'))
            self.assertEqual(spec['trials'],old['trials'])
            self.assertEqual(spec['execution_order'],old['execution_order'])
            self.assertEqual(sum(t['cpu_seconds']+2 for t in spec['trials']),1844)
            self.assertEqual(spec['phase_cpu_cap_seconds'],1900)
            s.validate_design(spec,inputs=False)
            self.assertEqual(len(s.resource_admission(spec)['reports']),6)

    def test_policy_source_or_comparator_retuning_is_rejected(self):
        changes=[]
        for field,value in [('codec_bits',40),('original_token_count',128),('use_candidates',True)]:
            spec=s.build_spec('wikitext');spec['trials'][-1]['plan'][field]=value;changes.append(spec)
        spec=s.build_spec('wikitext');spec['trials'][-1]['latency_gate']['trials']=['wikitext-root-prepare'];changes.append(spec)
        spec=s.build_spec('wikitext');spec['trials'][0]['plan']['record_ids'].reverse();changes.append(spec)
        for spec in changes:
            with self.assertRaisesRegex(ValueError,'recovery design differs'):s.validate_design(spec,inputs=False)

    def test_relocation_changes_paths_only(self):
        value={'path':'/old/a','ids':['x','/oldish/a'], 'hash':'abc', 'tokens':[10,20], 'text':'prefix /old/a'}
        self.assertEqual(s.relocate(value,'/old',Path('/new')),
            {'path':'/new/a','ids':['x','/oldish/a'],'hash':'abc','tokens':[10,20],'text':'prefix /old/a'})

    def test_new_checkout_build_is_portable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for corpus in ('wikitext','c4'):
                relative='campaigns/independent_requests_v31_ready/'+corpus+'.spec.json'
                dest=root/relative;dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes((s.ROOT/relative).read_bytes())
            with patch.object(s,'ROOT',root):
                for corpus in ('wikitext','c4'):
                    spec=s.build_spec(corpus)
                    self.assertEqual(spec['campaign'],str(root/('campaigns/independent_'+corpus+'_v32')))
                    for trial in spec['trials']:
                        for entry in trial['plan']['inputs'].values():
                            self.assertTrue(entry['path'].startswith(str(root)+'/'))

    def test_no_registration_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(s,'ROOT',root),patch.object(s,'archive_evidence',side_effect=AssertionError('no gate reads')):
                s.campaign('wikitext').mkdir(parents=True)
                with self.assertRaisesRegex(ValueError,'no overwrite'):s.register('wikitext')

    def test_absent_checkpoint_does_not_create_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);spec=s.build_spec('wikitext')
            with patch.object(s,'ROOT',root),patch.object(s,'build_spec',return_value=spec), \
                 patch.object(s,'archive_evidence',return_value={}), \
                 patch.object(s,'validate_design',side_effect=ValueError('missing checkpoint')):
                with self.assertRaisesRegex(ValueError,'missing checkpoint'):s.register('wikitext')
                self.assertFalse(s.campaign('wikitext').exists())

    def test_c4_requires_complete_settled_wikitext_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);spec=s.build_spec('c4')
            with patch.object(s,'ROOT',root),patch.object(s,'build_spec',return_value=spec), \
                 patch.object(s,'archive_evidence',return_value={}),patch.object(s,'validate_design'), \
                 patch.object(s,'registered_program',side_effect=ValueError('earlier root missing')):
                with self.assertRaisesRegex(ValueError,'earlier root missing'):s.register('c4')
                self.assertFalse(s.campaign('c4').exists())

    def test_balanced_preceding_trials_cannot_be_skipped(self):
        spec=s.build_spec('wikitext');root=s.campaign('wikitext')
        with patch.object(s,'check_registered',return_value=(root,spec,b'p',b'q',{})), \
             patch.object(s,'completed',side_effect=ValueError('previous missing')) as done, \
             patch.object(s,'PhaseBudget',side_effect=AssertionError('no reservation')):
            with self.assertRaisesRegex(ValueError,'previous missing'):s.run('wikitext',spec['execution_order'][-1])
            self.assertEqual(done.call_args.args[1],spec['execution_order'][0])

    def test_completed_scientific_loss_remains_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            trial=dict(id='compressed',compare_to=[dict(trial='cold',artifacts=['model'])],
                storage_gate=dict(trial='cold',artifact='state',strictly_smaller=True),
                latency_gate=dict(trials=['cold'],aggregation='minimum_recorded_controller_elapsed_ns',strictly_faster=True))
            (root/'program.json').write_bytes(canonical_json(dict(trials=[dict(id='cold'),trial])))
            for name,clock in [('cold',50),('compressed',60)]:
                path=root/'attempts'/name;path.mkdir(parents=True)
                (path/'transaction.json').write_bytes(canonical_json(dict(controller_elapsed_ns=clock)))
            def checked(current,trial_id,**kwargs):
                return dict(status='complete',artifacts=dict(model=dict(bytes=3,sha256='a'*64),
                    state=dict(bytes=2 if trial_id=='compressed' else 3,sha256='b'*64)))
            with patch.object(s,'verify_registered_attempt',side_effect=checked):
                result=s.completed(root,'compressed')
                self.assertEqual(result['status'],'complete')
                self.assertFalse(result['registered_scientific_gates']['all_passed'])
                (root/'attempts/compressed/scientific-gates.json').write_bytes(canonical_json(dict(all_passed=True)))
                with self.assertRaisesRegex(ValueError,'gate sidecar changed'):s.completed(root,'compressed')

    def test_unknown_attempt_status_blocks_automatic_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);spec=s.build_spec('wikitext');current=root/'campaigns/independent_wikitext_v32'
            (current/'attempts'/spec['execution_order'][0]).mkdir(parents=True)
            spec['source_sha256']={}
            with patch.object(s,'ROOT',root),patch.object(s,'check_registered',return_value=(current,spec,b'p',b'q',{})), \
                 patch.object(s,'completed',side_effect=ValueError('receipt missing')), \
                 patch.object(s,'read_budget_snapshot',return_value={'status':'missing'}):
                result=s.status('wikitext')
                self.assertIsNone(result['next_trial']);self.assertFalse(result['blocked']['automatic_retry'])

    def test_future_c4_ledger_does_not_invalidate_finished_wikitext(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(s,'ROOT',root):
                for corpus in ('wikitext','c4'):
                    path=s.campaign(corpus)/'phase-cpu-budget/ledger.json';path.parent.mkdir(parents=True)
                    path.write_text('{}')
                self.assertEqual(s.historical_ledgers(s.campaign('wikitext')), {})
                self.assertEqual(len(s.historical_ledgers(s.campaign('c4'))),1)

    def test_fresh_workspace_does_not_reuse_archived_registrations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(s,'ROOT',root),patch.object(s,'WORKSPACE','local_runs/replay-001'):
                self.assertEqual(s.validate_workspace('local_runs/replay-001'),'local_runs/replay-001')
                self.assertEqual(s.campaign('wikitext'),root/'local_runs/replay-001/independent_wikitext_v32')
                self.assertEqual(s.status('wikitext')['next_action'],'register')
                for bad in ('/tmp/x','../x','campaigns/x','local_runs','local_runs/../x'):
                    with self.assertRaises(ValueError):s.validate_workspace(bad)

    def test_historical_ledger_mutation_and_unapproved_addition_are_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(s,'ROOT',root):
                old=root/'campaigns/old/phase-cpu-budget/ledger.json';old.parent.mkdir(parents=True);old.write_text('{}')
                before=s.historical_ledgers(s.campaign('wikitext'))
                old.write_text('{"changed":true}')
                self.assertNotEqual(before,s.historical_ledgers(s.campaign('wikitext')))
                new=root/'local_runs/unapproved/phase-cpu-budget/ledger.json';new.parent.mkdir(parents=True);new.write_text('{}')
                self.assertEqual(len(s.historical_ledgers(s.campaign('wikitext'))),2)

    def test_failed_run_cli_exits_nonzero(self):
        from contextlib import nullcontext,redirect_stdout
        import io
        with patch.object(s.sys,'argv',['launcher','--corpus','wikitext','--run','example']), \
             patch.object(s,'research_worker_lock',return_value=nullcontext()), \
             patch.object(s,'run',return_value={'status':'failed'}),redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:s.main()
            self.assertEqual(raised.exception.code,1)


if __name__=='__main__':unittest.main()
