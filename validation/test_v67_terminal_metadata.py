"""Generated reporting/gating fixtures; no numerical experiment or Slurm call."""
import copy
import json
from decimal import Decimal
import unittest
from validation import check_v67_terminal_metadata as m


def summary():
    return dict(jobs={str(i):dict(state='COMPLETED',exit_code='0:0') for i in range(15261,15276)},
        terminal_receipts_present=True,queue='',archive={},captured_at_utc='fixture')


def receipt_names():
    return {n:b'fixture, deliberately unparsed' for n in
        ['primary-audit.json','supplemental-audit.json','primary-entry.json','supplemental-entry.json']}


def toy_costs():
    prep=dict(common_source_ns=10,common_original_model_and_write_ns=20,common_disposal_ns=30,
        states={r:dict(representation_elapsed_ns=5) for r in m.REPS})
    c={'prepare':dict(preparation=prep,context_elapsed_ns=40,worker_elapsed_ns=150)}
    t={'prepare':dict(elapsed_ns=180),'oracle':dict(elapsed_ns=250)}
    for arm in m.ARMS:
        for step in (1,2):
            n=arm+'-'+str(step)
            c[n]=dict(context_elapsed_ns=7,worker_elapsed_ns=90,max_rss_kib=2,
                request=dict(request_elapsed_ns=80,timing=dict(neural_stage_record_pairs=3,
                    stages=[dict(stage_id='tiny',fallback=(arm=='compressed'))])))
            t[n]=dict(elapsed_ns=100,controller_process_cpu_ns=4)
    return c,t


class TerminalReporting(unittest.TestCase):
    def test_pending_ignores_terminal_looking_receipts(self):
        s=summary();s['jobs']['15265']['state']='RUNNING'
        r=m.reconcile(receipt_names(),s)
        self.assertEqual(r['status'],'pending_terminal')
        self.assertFalse(r['cluster_terminal_audit_claims_reconciled'])
        self.assertNotIn('comparison_rows',r)

    def test_failure_is_not_pending_or_promoted(self):
        s=summary();s['jobs']['15265']['state']='TIMEOUT';s['jobs']['15266']['state']='PENDING'
        r=m.reconcile(receipt_names(),s)
        self.assertEqual(r['status'],'terminal_failure_preserved')
        self.assertEqual(r['failed_jobs'],{'15265':'TIMEOUT'})

    def test_nonzero_exit_is_a_failure(self):
        s=summary();s['jobs']['15274']['exit_code']='1:0'
        self.assertEqual(m.terminal_gate(s,receipt_names())['status'],'terminal_failure_preserved')

    def test_missing_terminal_receipt_is_incomplete(self):
        files=receipt_names();del files['supplemental-entry.json']
        self.assertEqual(m.terminal_gate(summary(),files)['status'],'terminal_capture_incomplete')

    def test_terminal_queue_contradiction_refused(self):
        s=summary();s['queue']='15275|running'
        with self.assertRaisesRegex(ValueError,'queue'):m.terminal_gate(s,receipt_names())

    def test_registered_job_census_required(self):
        s=summary();del s['jobs']['15273']
        with self.assertRaisesRegex(ValueError,'census'):m.terminal_gate(s,receipt_names())

    def test_ready_is_only_ready_for_reconciliation(self):
        self.assertEqual(m.terminal_gate(summary(),receipt_names()),{'status':'ready_for_receipt_reconciliation'})

    def test_duration_fraction_and_days(self):
        self.assertEqual(m.elapsed_seconds('01:22:10'),Decimal(4930))
        self.assertEqual(m.elapsed_seconds('00:09.977'),Decimal('9.977'))
        self.assertEqual(m.elapsed_seconds('2-01:00:00'),Decimal(176400))

    def test_duration_unknown_and_invalid_refused(self):
        for value in ['Unknown','N/A','NaN','-1','01:70:00','1-24:00:00','1:2:3:4']:
            with self.subTest(value=value),self.assertRaises(ValueError):m.elapsed_seconds(value)

    def test_common_preparation_is_attributed_once(self):
        c,t=toy_costs();r=m.recompute_costs({},c,t)
        for arm in m.ARMS:
            self.assertEqual(r['timings'][arm]['attributed_preparation_ns'],105)
            self.assertEqual(r['timings'][arm]['attributed_two_request_total_ns'],305)
        self.assertEqual(r['preparation_transaction_elapsed_ns'],180)
        self.assertEqual(r['oracle_transaction_elapsed_ns'],250)

    def test_fallback_and_nested_clocks_preserved(self):
        c,t=toy_costs();r=m.recompute_costs({},c,t)['timings']['compressed']['requests'][0]
        self.assertEqual(r['fallback_stages'],['tiny'])
        self.assertEqual([r[k] for k in ['request_elapsed_ns','worker_elapsed_ns','transaction_elapsed_ns']],[80,90,100])

    def test_invalid_clock_refused(self):
        c,t=toy_costs();c['modern-2']['request']['request_elapsed_ns']=101
        with self.assertRaisesRegex(ValueError,'containment'):m.recompute_costs({},c,t)

    def test_four_representations_not_five_arms(self):
        c,t=toy_costs();self.assertEqual(len(c['prepare']['preparation']['states']),4)
        c['prepare']['preparation']['states']['cold']=dict(representation_elapsed_ns=5)
        with self.assertRaisesRegex(ValueError,'Four'):m.recompute_costs({},c,t)


class GeneratedCompleteReceiptPath(unittest.TestCase):
    """Synthetic metadata only: no real model bytes, scheduler or audit execution."""
    def setUp(self):
        from validation.v67_terminal_fixture import make
        self.files,self.summary=make()

    def mutate(self,name,change):
        value=json.loads(self.files[name]);change(value);self.files[name]=m.canonical(value)

    def test_complete_synthetic_path_retains_scope_and_adverse_rows(self):
        r=m.reconcile(self.files,self.summary)
        self.assertEqual(r['status'],'verified_terminal_receipt_metadata')
        self.assertEqual(len(r['comparison_rows']),10)
        self.assertFalse(r['actual_model_state_bytes_checked_locally'])
        self.assertFalse(r['confirmation']);self.assertFalse(r['quality_evaluation'])
        self.assertTrue(r['snapshot']['synthetic_fixture_only'])
        self.assertEqual(r['numerical_worker_charged_cpu_seconds'],24)
        self.assertEqual(sum(x['numerical_solver_fallback_rows'] for x in r['comparison_rows']),2)

    def test_nested_scheduler_cpu_is_not_added_twice(self):
        self.assertEqual(m.reconcile(self.files,self.summary)['scheduler_allocation_cpu_seconds'],'15.000')

    def test_changed_audit_cost_refused(self):
        self.mutate('primary-audit.json',lambda x:x['costs']['timings']['modern'].__setitem__('attributed_two_request_total_ns',1))
        with self.assertRaisesRegex(ValueError,'Audit clocks'):m.reconcile(self.files,self.summary)

    def test_missing_audit_input_refused(self):
        self.mutate('primary-audit.json',lambda x:x['inputs'].pop(next(iter(x['inputs']))))
        with self.assertRaisesRegex(ValueError,'Complete audit input'):m.reconcile(self.files,self.summary)

    def test_missing_final_entry_refused_before_reconciliation(self):
        del self.files['supplemental-entry.json']
        self.assertEqual(m.reconcile(self.files,self.summary)['status'],'terminal_capture_incomplete')

    def test_failed_audit_entry_cannot_hide_behind_passing_audit(self):
        self.mutate('primary-entry.json',lambda x:x.__setitem__('status','failed'))
        with self.assertRaisesRegex(ValueError,'Audit entry'):m.reconcile(self.files,self.summary)

    def test_applied_limit_mutation_refused(self):
        self.mutate('hybrid-1/worker/attempt-fixture/limits-applied.json',lambda x:x.__setitem__('cpu_seconds',[999999,999999]))
        with self.assertRaisesRegex(ValueError,'Sealed artifact'):m.reconcile(self.files,self.summary)

    def test_changed_copied_model_commitment_refused(self):
        self.mutate('cached-2/outputs/completion.json',lambda x:x['artifacts']['model.bin'].__setitem__('sha256','0'*64))
        with self.assertRaisesRegex(ValueError,'Complete audit input'):m.reconcile(self.files,self.summary)

    def test_unsettled_ledger_refused(self):
        self.mutate('budget/ledger.json',lambda x:x['attempts']['generated-cold-2'].__setitem__('state','reserved'))
        with self.assertRaisesRegex(ValueError,'copied ledger'):m.reconcile(self.files,self.summary)

    def test_duplicate_scheduler_row_refused(self):
        self.mutate('collection.json',lambda x:x.__setitem__('accounting',x['accounting']+'\n'+x['accounting'].splitlines()[0]))
        with self.assertRaisesRegex(ValueError,'Duplicate scheduler'):m.reconcile(self.files,self.summary)

    def test_missing_batch_row_refused(self):
        self.mutate('collection.json',lambda x:x.__setitem__('accounting','\n'.join(l for l in x['accounting'].splitlines() if not l.startswith('15275.batch|'))))
        with self.assertRaisesRegex(ValueError,'allocation/batch'):m.reconcile(self.files,self.summary)

    def test_scheduler_wall_overshoot_refused(self):
        self.mutate('collection.json',lambda x:x.__setitem__('accounting',x['accounting'].replace('00:00:30','02:00:00')))
        with self.assertRaisesRegex(ValueError,'wall exceeds'):m.reconcile(self.files,self.summary)


if __name__=='__main__':unittest.main()
