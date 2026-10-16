"""Standard-library metadata boundary tests; no numerical or research imports."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE=Path(__file__).with_name('check_v61_terminal_metadata.py')
spec=importlib.util.spec_from_file_location('v61_portable_metadata_check',MODULE)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


def debit(cpu=1_000_000_001,reserved=10802):
    return dict(phase='feasibility',reserved_cpu_seconds=reserved,state='settled',
        observed_cpu_ns=cpu,charged_cpu_seconds=max(1,(cpu+999999999)//1000000000))


def ledger(sources):
    return dict(schema='phase-cpu-ledger-v1',binding=dict(identity=dict(protocol_sha256=c.PROGRAM_SHA,
        source_sha256=sources),phase_cpu_seconds={'feasibility':c.CAP},
        scope='trusted_worker_cpu_admission_not_process_tree_containment'),
        attempts={name:debit(reserved=limits[0]+2) for name,limits in c.TRIALS.items()})


def manifest(files):
    return dict(schema='second-terminal-v61-metadata-v1',files=files,repository_paths={},inputs_not_copied={},
        terminal=True,reported_success=True,capture_scope='terminal_success_receipts_metadata_only',
        portable_scientific_validation_performed=False,capture_issues=[],cluster_commit=c.SOURCE_COMMIT,
        program_sha256=c.PROGRAM_SHA,source_files_verified=432,final_metadata_bytes_rehashed=True,
        source_and_campaign_census_unchanged=True,excluded_binary_contents_rehashed=False,
        numerical_inference_or_calibration_executed=False,captured_metadata_bytes=sum(e['bytes'] for e in files.values()),
        quiescent=True,blocked_dependency_jobs={},scheduler_queue='')


class PortableMetadataTests(unittest.TestCase):
    def test_prelaunch_reservation_and_presettlement_receipts_bind_actual_attempt(self):
        identity=dict(limits={'cpu_seconds':10800},phase_budget={'binding_sha256':'2'*64})
        attempt='/p/worker/attempt-0001';aid=c.digest(c.canonical(dict(worker=identity,attempt=attempt)))
        reservation=dict(binding_sha256='2'*64,budget_attempt_id=aid,budget_debit=dict(
            phase='feasibility',reserved_cpu_seconds=10802,state='reserved',observed_cpu_ns=None,charged_cpu_seconds=10802))
        sealed=dict(budget_attempt_id=aid,outcome={'elapsed_wall_ns':10},resource_usage={'total_cpu_ns':9},
            timing_boundary=dict(start_ns=1,cleanup_start_ns=10,cleanup_end_ns=11,clock='time.perf_counter_ns_same_controller_process'))
        observation={key:sealed[key] for key in ('outcome','resource_usage','timing_boundary','budget_attempt_id')}
        observation['scope']='observed worker exit before CPU settlement and receipt sealing'
        c.validate_seal_observations(identity,sealed,reservation,observation,attempt)
        for edit in (lambda v:v.update(budget_attempt_id='0'*64),
                     lambda v:v['outcome'].update(elapsed_wall_ns=11),
                     lambda v:v['resource_usage'].update(total_cpu_ns=0)):
            changed=copy.deepcopy(observation);edit(changed)
            with self.assertRaises(ValueError):c.validate_seal_observations(identity,sealed,reservation,changed,attempt)
        changed=copy.deepcopy(reservation);changed['budget_debit']['reserved_cpu_seconds']=1
        with self.assertRaises(ValueError):c.validate_seal_observations(identity,sealed,changed,observation,attempt)

    def test_ledger_exact_schema_sources_six_settled_and_ceil_charge(self):
        sources={'src/f.py':'1'*64};value=ledger(sources)
        actual,snapshot=c.validate_ledger(c.canonical(value),sources)
        self.assertEqual(actual,value);self.assertEqual(snapshot['charged_cpu_seconds'],{'feasibility':12})
        self.assertEqual(snapshot['ledger_sha256'],c.digest(c.canonical(value)))
        for edit in (
            lambda v:v['binding']['identity']['source_sha256'].clear(),
            lambda v:v['binding'].update(scope='anything'),
            lambda v:v['attempts'].pop('oracle'),
            lambda v:v['attempts']['prepare'].update(state='reserved'),
            lambda v:v['attempts']['prepare'].update(observed_cpu_ns=True),
            lambda v:v['attempts']['prepare'].update(charged_cpu_seconds=2.0),
            lambda v:v['attempts']['prepare'].update(charged_cpu_seconds=1),
            lambda v:v['attempts']['prepare'].update(observed_cpu_ns=-1),
            lambda v:v['attempts']['prepare'].update(reserved_cpu_seconds=1)):
            changed=copy.deepcopy(value);edit(changed)
            with self.assertRaises(ValueError):c.validate_ledger(c.canonical(changed),sources)
        zero=debit(0);self.assertEqual(c.validate_debit(zero),1)
        with self.assertRaises(ValueError):c.validate_ledger(c.canonical(value)+b'\n',sources)

    def test_audit_inventory_rejects_missing_or_forged_entries_despite_new_collection_hash(self):
        expected={'/registered/program.json':c.info(b'program'),'/state.bin':c.info(b'not copied')}
        c.inventory_equal(copy.deepcopy(expected),expected,'audit')
        for changed in ({},dict(list(expected.items())[:1]),{**expected,'/extra.json':c.info(b'x')},
                        {**expected,'/state.bin':c.info(b'changed')}):
            # Updating an outer copy hash is irrelevant to the internal census.
            self.assertTrue(c.digest(c.canonical(changed)))
            with self.assertRaises(ValueError):c.inventory_equal(changed,expected,'audit')

    def test_collection_rejects_missing_extra_symlink_and_failure_captures(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'one.json').write_bytes(b'{}')
            value=manifest({'one.json':c.info(b'{}')})
            def save(v): (root/'collection-manifest.json').write_text(__import__('json').dumps(v,indent=2)+'\n')
            save(value);self.assertTrue(c.Check(root).collection()['terminal'])
            for changes in (dict(reported_success=False),dict(terminal=False),
                            dict(capture_scope='terminal_failure_or_incomplete_receipts_metadata_only'),
                            dict(capture_issues=[{'kind':'failure'}]),dict(excluded_binary_contents_rehashed=True),
                            dict(quiescent=False),dict(blocked_dependency_jobs={'13564':{'state':'PENDING'}}),
                            dict(scheduler_queue='13564|PENDING|DependencyNeverSatisfied\n')):
                save(dict(value,**changes))
                with self.assertRaises(ValueError):c.Check(root).collection()
            save(value);(root/'extra.json').write_bytes(b'{}')
            with self.assertRaises(ValueError):c.Check(root).collection()
            (root/'extra.json').unlink();(root/'one.json').unlink()
            with self.assertRaises(ValueError):c.Check(root).collection()
            (root/'real.json').write_bytes(b'{}');(root/'one.json').symlink_to(root/'real.json')
            with self.assertRaises(ValueError):c.Check(root).collection()

    def test_rehashed_forged_program_cannot_replace_pinned_registration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);folder=root/c.CAMPAIGN;folder.mkdir()
            raw=c.canonical({'pretended_registered_program':True});(folder/'program.json').write_bytes(raw)
            value=manifest({c.CAMPAIGN+'/program.json':c.info(raw)})
            (root/'collection-manifest.json').write_bytes(c.canonical(value))
            check=c.Check(root);check.collection()
            with self.assertRaisesRegex(ValueError,'Pinned registered'):
                check.registration()

    def test_absent_binary_is_explicit_but_metadata_cannot_be_omitted(self):
        with tempfile.TemporaryDirectory() as temporary:
            check=c.Check(temporary);remote=c.DIRECTORY+'/cached/outputs/step-1-state.bin';entry=c.info(b'contents')
            missing=dict(kind='numerical_binary',status='NOT revalidated',exists=True,observed_bytes=entry['bytes'],
                binary_contents_read=False,expected=entry)
            check.manifest=dict(repository_paths={},inputs_not_copied={remote:missing})
            self.assertIsNone(check.bind(remote,entry));self.assertEqual(check.missing[remote]['status'],'NOT revalidated')
            for key,value in (('exists',False),('observed_bytes',entry['bytes']+1),('binary_contents_read',True)):
                check.manifest['inputs_not_copied'][remote]=dict(missing,**{key:value})
                with self.assertRaises(ValueError):check.bind(remote,entry)
            meta=c.DIRECTORY+'/cached/outputs/completion.json'
            check.manifest['inputs_not_copied'][meta]=missing
            with self.assertRaises(ValueError):check.bind(meta,entry)

    def test_storage_math_requires_typed_complete_deployment_extent(self):
        state=c.info(b'abc');trust=c.info(b'{}')
        row=dict(state_bytes=3,trust_bytes=2,complete_deployment_bytes=105)
        self.assertEqual(c.storage(row,state,trust,100)['live_state_bytes'],5)
        for key,value in (('state_bytes',3.0),('trust_bytes',True),('complete_deployment_bytes',5)):
            with self.assertRaises(ValueError):c.storage(dict(row,**{key:value}),state,trust,100)

    def test_scheduler_checks_every_job_and_exact_raw_receipt(self):
        check=c.Check('.')
        lines=[];rows={}
        for label,jid in c.JOBS.items():
            fields=[jid,'second61-'+label,'COMPLETED','0:0','1','00:00:00.900','2026-10-14T00:00:00','2026-10-14T00:00:01']
            lines.append('|'.join(fields)+'|')
            rows[jid]=dict(job_name=fields[1],state=fields[2],raw_state=fields[2],exit_code=fields[3],
                elapsed_seconds=fields[4],total_cpu=fields[5],start=fields[6],end=fields[7])
        check.manifest=dict(scheduler='\n'.join(lines),scheduler_jobs=rows)
        check.scheduler();self.assertEqual(len(check.scheduler_rows),10)
        for changed in ('\n'.join(lines[:-1]),'\n'.join(lines).replace('COMPLETED','PENDING',1),
                        '\n'.join(lines).replace('|0:0|','|1:0|',1)):
            check.manifest['scheduler']=changed
            with self.assertRaises(ValueError):check.scheduler()

    def test_expected_artifacts_include_models_states_and_every_trust_sidecar(self):
        self.assertEqual(len(c.expected_artifacts('prepare')),9)
        self.assertEqual(len(c.expected_artifacts('oracle')),16)
        self.assertEqual(len(c.expected_artifacts('cached')),8)
        self.assertIn('step-2-hybrid_gram-trust.json',c.expected_artifacts('oracle'))
        self.assertIn('original-model.bin',c.expected_artifacts('prepare'))
        for name in ('../escape','/absolute','a/../b'):
            with self.assertRaises(ValueError):c.safe(Path('.'),name)


if __name__=='__main__':unittest.main()
