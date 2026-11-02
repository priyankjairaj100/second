"""Generated persisted RunStore seals and ledgers; no empirical worker runs."""
import copy,tempfile,unittest
from pathlib import Path
from research_v71 import cost_accounting as c
from research_v71.execution_gate import limits
from src.phase_budget import PhaseBudget,read_budget_snapshot
from src.run_store import RunStore,canonical_json,digest


def sealed_fixture(root,failed=False):
    policy={'quality':39616};bid={'fixture':'generated'}
    budget=PhaseBudget(root/'budget',identity=bid,phase_cpu_seconds=policy)
    limit=limits('parameters',3).payload()
    identity=dict(schema='limited-worker-identity-v1',identity={'phase':'parameters'},
        command=['/fixture/python','-B','/fixture/worker.py'],cwd=str(root),limits=limit,
        phase_budget=dict(binding_sha256=budget.identity_digest,phase='quality',directory=str(root/'budget')))
    directory=root/'worker'
    with RunStore(directory,identity) as store:
        debit_id='generated-debit';reservation=budget.reserve('quality',debit_id,602)
        request=dict(command=identity['command'],cwd=identity['cwd'],limits=limit,
            ack_path=str(store.attempt/'limits-ack.pending.json'))
        ack=dict(address_space=[limit['address_space_bytes']]*2,cpu_seconds=[600,601],
            file_size=[limit['file_size_bytes']]*2,affinity_cpus=[3],
            thread_environment={n:'1' for n in c.THREAD_VARIABLES},pid=11,process_group=11,
            request_sha256=digest(canonical_json(request)))
        for name,value in [('request.json',request),('limits-applied.json',ack),
            ('budget-reservation.json',dict(budget_attempt_id=debit_id,budget_debit=reservation,binding_sha256=budget.identity_digest)),
            ('stdout-summary.json',{'fixture':True}),('stderr-summary.json',{'fixture':True}),
            ('pre-settlement-observation.json',{'fixture':True})]:store.write_artifact(name,canonical_json(value))
        debit=budget.settle(debit_id,2100000000)
        store.finish(dict(schema='limited-worker-record-v1',status='complete',
            outcome=dict(status='failed' if failed else 'complete',returncode=1 if failed else 0),
            limits=limit,limits_applied=ack,budget_debit=debit,budget_attempt_id=debit_id,budget_reservation_overrun=False,
            resource_usage=dict(user_cpu_ns=2000000000,system_cpu_ns=100000000,total_cpu_ns=2100000000,max_rss_kib=2000)))
    snapshot=read_budget_snapshot(root/'budget',identity=bid,phase_cpu_seconds=policy)
    return directory,identity,snapshot


def entry_fixture(failed=False):
    return dict(schema='quality-controller-entry-v71',registration_sha256='a'*64,phase='parameters',job_id='123',
        status='failed' if failed else 'complete',error={'type':'FixtureFailure'} if failed else None,
        whole_process_cpu_clock=True,all_waited_children_included=True,process_cpu_ns=1500000000,
        waited_child_cpu_ns=2600000000,elapsed_ns=7000000000,maximum_rss_kib=1000)


def scheduler_fixture(failed=False):
    raw='123|'+('FAILED|1:0' if failed else 'COMPLETED|0:0')+'|8|00:04.800|1\n123.batch|COMPLETED|0:0|8|00:04.800|1\n'
    return c.scheduler_rows(raw,{'parameters':'123'})['parameters']


class CostAccountingTests(unittest.TestCase):
    def test_scheduler_clock_precision_days_and_no_step_double_count(self):
        self.assertEqual(c.cpu_time('1-02:03:04.123456'),(93784123456000,1000))
        self.assertEqual(c.cpu_time('00:02'),(2000000000,1000000000))
        self.assertEqual(scheduler_fixture()['total_cpu_ns'],4800000000)
        for text in ['nan','1:99','1-25:00:00','-1:00','1.5']:
            with self.subTest(text=text),self.assertRaises(ValueError):c.cpu_time(text)

    def test_scheduler_rejects_pending_missing_duplicate_or_extra_allocations(self):
        normal='123|COMPLETED|0:0|8|00:04.800|1\n'
        for raw in ['',normal+normal,normal+'999|COMPLETED|0:0|0|00:00|1',normal.replace('COMPLETED','RUNNING'),normal.replace('|1\n','|2\n')]:
            with self.assertRaises(ValueError):c.scheduler_rows(raw,{'parameters':'123'})

    def test_actual_saved_worker_seal_and_ledger_are_read_and_mutations_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory,identity,snapshot=sealed_fixture(Path(tmp).resolve())
            result=c.worker(directory,identity,snapshot)
            self.assertEqual(result['worker_cpu_ns'],2100000000);self.assertEqual(result['charged_cpu_seconds'],3)
            p=directory/'attempt-0001/stdout-summary.json';p.write_bytes(b'changed')
            with self.assertRaises(ValueError):c.worker(directory,identity,snapshot)

    def test_settled_worker_cpu_is_not_added_again_to_waited_children(self):
        with tempfile.TemporaryDirectory() as tmp:
            d,i,s=sealed_fixture(Path(tmp).resolve());worker=c.worker(d,i,s)
            row=c.reconcile('parameters',entry_fixture(),worker,scheduler_fixture(),registration_sha256='a'*64)
            self.assertEqual(row['observed_process_tree_cpu_ns'],4100000000)
            self.assertEqual(row['nonworker_waited_child_cpu_ns'],500000000)
            self.assertEqual(row['controller_charged_cpu_seconds'],2)
            self.assertEqual(row['scheduler_minus_observed_cpu_ns'],700000000)
            self.assertTrue(row['execution_successful'])

    def test_accounted_failed_worker_remains_failed_and_quality_flag_cannot_select_costs(self):
        with tempfile.TemporaryDirectory() as tmp:
            d,i,s=sealed_fixture(Path(tmp).resolve(),True);worker=c.worker(d,i,s)
            row=c.reconcile('parameters',entry_fixture(True),worker,scheduler_fixture(True),registration_sha256='a'*64)
            self.assertEqual(row['accounting_status'],'verified');self.assertFalse(row['execution_successful'])
            self.assertTrue(row['quality_gate_outcome_not_used_for_accounting'])

    def test_accounting_rejects_missing_children_over_budget_or_underreported_scheduler(self):
        with tempfile.TemporaryDirectory() as tmp:
            d,i,s=sealed_fixture(Path(tmp).resolve());worker=c.worker(d,i,s)
            for key,value in [('waited_child_cpu_ns',0),('process_cpu_ns',602*10**9),('whole_process_cpu_clock',False),('maximum_rss_kib',17*2**20)]:
                entry=entry_fixture();entry[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):c.reconcile('parameters',entry,worker,scheduler_fixture(),registration_sha256='a'*64)
            scheduler=scheduler_fixture();scheduler['total_cpu_ns']=1
            with self.assertRaises(ValueError):c.reconcile('parameters',entry_fixture(),worker,scheduler,registration_sha256='a'*64)
            s['reserved_unknown_attempts']=1
            with self.assertRaises(ValueError):c.worker(d,i,s)

    def test_complete_census_requires_all_eight_unique_actual_debits(self):
        rows={};attempts={}
        for i,phase in enumerate(c.CAPS):
            debit='debit-'+str(i)
            rows[phase]=dict(phase=phase,job_id=str(100+i),debit_id=debit,accounting_status='verified',
                execution_successful=phase!='gpu_quality',worker_cpu_ns=2*10**9,worker_charged_cpu_seconds=2,
                controller_charged_cpu_seconds=1,observed_process_tree_cpu_ns=3*10**9,scheduler_cpu_ns=4*10**9)
            attempts[debit]=dict(state='settled',observed_cpu_ns=2*10**9,charged_cpu_seconds=2,
                reserved_cpu_seconds=c.CAPS[phase]['cpu_seconds']+2)
        s=dict(status='verified',reserved_unknown_attempts=0,reservation_overrun_attempts=[],over_cap={'quality':False},attempts=attempts)
        result=c.complete(rows,s);self.assertFalse(result['execution_successful'])
        self.assertEqual(result['worker_charged_cpu_seconds'],16)
        with self.assertRaises(ValueError):c.complete({k:v for k,v in rows.items() if k!='terminal'},s)
        s['attempts']['hidden']=dict(next(iter(attempts.values())))
        with self.assertRaises(ValueError):c.complete(rows,s)

    def test_gpu_allocator_and_original_parameter_transfer_census(self):
        r=dict(dtype='float64',tf32=False,amp=False,deterministic_algorithms=True,
            allocator_limit_bytes=c.GPU_ALLOCATOR,peak_cuda_allocated_bytes=1000,
            peak_cuda_reserved_bytes=2000,copied_arrays_with_bitwise_roundtrip=318)
        self.assertTrue(c.gpu_memory(r)['allocator_is_not_total_device_memory'])
        for key,value in [('peak_cuda_reserved_bytes',c.GPU_ALLOCATOR+1),('copied_arrays_with_bitwise_roundtrip',77),('amp',True)]:
            with self.subTest(key=key),self.assertRaises(ValueError):c.gpu_memory(dict(r,**{key:value}))


if __name__=='__main__':unittest.main()
