"""Generated files/seals and mocked registration environments; no cluster work."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import copy,unittest
from research_v69 import campaign as c,cost_accounting
from research_v69.test_cost_accounting import sealed_fixture
from src.run_store import canonical_json,digest


class CampaignTests(unittest.TestCase):
    def test_distinct_actual_cpu_and_cuda_runtime_shapes_bind_their_own_interpreters(self):
        p=dict(interpreters={'cpu':'/generated/venv/bin/python','cuda':'/generated/gpu/python3.10'},
            runtimes={'cpu':{'cpu-host':{'python':{'interpreter':{'sha256':'a'*64}}}},
                'cuda':{'gpu-host':{'executable':{'path':'/generated/gpu/python3.10'}}}})
        self.assertEqual(c.command(p,'parameters')[0],p['interpreters']['cpu'])
        self.assertEqual(c.command(p,'gpu_quality')[0],p['interpreters']['cuda'])
        p['interpreters']['cuda']='/different/python'
        with self.assertRaises(ValueError):c.command(p,'gpu_quality')

    def test_data_prerequisite_costs_need_all_actual_terminal_jobs_and_complete_process_clocks(self):
        from research_v68.data_runner import CAPS
        values={};lines=[]
        for i,(phase,cap) in enumerate(CAPS.items()):
            job=str(100+i);row=dict(job_id=job,status='complete',error=None,caps=cap,
                process_cpu_ns=2*10**9,waited_child_cpu_ns=10**9,combined_observed_cpu_ns=3*10**9,
                elapsed_ns=4*10**9,max_rss_kib=1000)
            values[phase]=canonical_json(row);lines.append(job+'|COMPLETED|0:0|5|00:03.500|1')
        raw='\n'.join(lines)
        self.assertEqual(c.v68_costs(values,raw)['status'],'verified_predecessor_costs')
        with self.assertRaises(ValueError):c.v68_costs(values,'\n'.join(lines[:-1]))
        with self.assertRaises(ValueError):c.v68_costs(values,raw.replace('COMPLETED','RUNNING'))
        bad=c.strict_json(values['data']);bad['combined_observed_cpu_ns']-=1
        with self.assertRaises(ValueError):c.v68_costs(dict(values,data=canonical_json(bad)),raw)

    def test_streamed_output_manifest_detects_mutation_and_symlink(self):
        with TemporaryDirectory() as tmp:
            d=Path(tmp).resolve();c.write(d/'completion.json',{'status':'complete'})
            c.write(d/'nested/model.bin',b'original',raw=True)
            before=c.output_census(d);self.assertEqual(set(before),{'completion.json','nested/model.bin'})
            (d/'nested/model.bin').write_bytes(b'changed')
            self.assertNotEqual(c.output_census(d),before)
            (d/'alias').symlink_to(d/'completion.json')
            with self.assertRaisesRegex(ValueError,'Symbolic'):c.output_census(d)

    def test_job_binding_cannot_rebind_phase_registration_or_submitted_running_state(self):
        with TemporaryDirectory() as tmp,patch.object(c,'RUN',Path(tmp).resolve()):
            p={'fixture':'generated'};d=c.RUN/'parameters';d.mkdir()
            b=dict(schema='quality-held-job-binding-v69',registration_sha256=digest(canonical_json(p)),
                phase='parameters',job_id='123',submission_state='held-before-release')
            path=d/'job-binding.json';path.write_bytes(canonical_json(b));self.assertEqual(c.job(p,'parameters'),b)
            for key,value in [('phase','gpu_quality'),('registration_sha256','0'*64),
                ('job_id','123;other'),('submission_state','already-running')]:
                path.write_bytes(canonical_json(dict(b,**{key:value})))
                with self.assertRaises(ValueError):c.job(p,'parameters')

    def test_only_verified_active_reservation_can_coexist_with_completed_predecessor(self):
        with TemporaryDirectory() as tmp:
            d,i,s=sealed_fixture(Path(tmp).resolve())
            s=copy.deepcopy(s);s['attempts']['live']=dict(state='reserved',phase='quality',
                reserved_cpu_seconds=602,charged_cpu_seconds=602,observed_cpu_ns=None)
            s['reserved_unknown_attempts']=1
            with self.assertRaisesRegex(ValueError,'separately admitted'):cost_accounting.worker(d,i,s)
            r=cost_accounting.worker(d,i,s,active_attempt_id='live')
            self.assertEqual(r['active_attempt_excluded_from_completion'],'live')
            with self.assertRaises(ValueError):cost_accounting.worker(d,i,s,active_attempt_id='other')
            s['attempts']['hidden']=s['attempts']['live'];s['reserved_unknown_attempts']=2
            with self.assertRaises(ValueError):cost_accounting.worker(d,i,s,active_attempt_id='live')

    def test_finished_reads_real_seal_debit_and_outputs_instead_of_completion_alone(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();phase='parameters';directory=root/phase;directory.mkdir()
            d,i,s=sealed_fixture(directory);p={'fixture':'generated'};registration=digest(canonical_json(p))
            result=dict(schema='quality-phase-worker-v69',phase=phase,registration_sha256=registration,
                job_id='123',status='complete',error=None,result={'generated':True})
            c.write(directory/'outputs/completion.json',result)
            e=dict(schema='quality-controller-entry-v69',phase=phase,registration_sha256=registration,
                job_id='123',status='complete',error=None,whole_process_cpu_clock=True,all_waited_children_included=True,
                affinity_cpus=[3],outputs=c.output_census(directory/'outputs'))
            c.write(directory/'entry.json',e)
            with patch.object(c,'RUN',root),patch.object(c,'job',return_value={'job_id':'123'}),\
                patch.object(c,'snapshot',return_value=s),patch.object(c,'worker_identity',return_value=i):
                self.assertEqual(c.finished(p,phase),result)
                (directory/'outputs/completion.json').write_bytes(canonical_json(dict(result,result={'fabricated':True})))
                with self.assertRaisesRegex(ValueError,'output bytes differ'):c.finished(p,phase)
                (directory/'outputs/completion.json').write_bytes(canonical_json(result))
                (d/'attempt-0001/stdout-summary.json').write_bytes(b'changed sealed artifact')
                with self.assertRaises(ValueError):c.finished(p,phase)

    def test_exact_previous_chain_includes_checks_parameters_and_both_constructors(self):
        seen=[]
        with patch.object(c,'finished',side_effect=lambda p,n,**kw:seen.append((n,kw)) or n):
            got=c.predecessors({},'gpu_quality',active_attempt_id='live')
        self.assertEqual(list(got),list(c.ORDER)[:6]);self.assertEqual(len(seen),6)
        self.assertTrue(all(kw=={'active_attempt_id':'live'} for n,kw in seen))
        with self.assertRaises(ValueError):c.predecessors({},'retry')


if __name__=='__main__':unittest.main()
