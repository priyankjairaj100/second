"""Generated files and mocked host/runtime calls; never changes local limits."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy,tempfile,unittest
from research_v69 import execution_gate as g
from src.run_store import canonical_json,digest


class ExecutionGateTests(unittest.TestCase):
    def test_separate_cpu_cuda_qualification_and_complete_reserved_costs(self):
        d=g.design();self.assertEqual(len(d['phases']),8)
        self.assertEqual(d['worker_allowance_cpu_seconds'],39616)
        self.assertEqual(d['controller_allowance_cpu_seconds'],4808)
        self.assertFalse(d['registered'])
        for name in g.CAPS:
            limit=g.limits(name,7)
            self.assertEqual(limit.affinity_cpus,(7,));self.assertEqual(limit.threads,1)
            self.assertEqual(limit.address_space_bytes,g.GPU_AS if name in g.GPU_PHASES else g.MEMORY)
            self.assertEqual(limit.file_size_bytes,2*2**30)
        for name,cpu in [('foreign',0),('cpu_checks',True),('cpu_checks',-1)]:
            with self.assertRaises(ValueError):g.limits(name,cpu)

    def test_controller_admission_applies_recorded_limits_and_single_affinity(self):
        env={n:'1' for n in g.THREAD_VARIABLES};env.update(SLURM_JOB_ID='123',CUBLAS_WORKSPACE_CONFIG=':4096:8')
        values={};set_limit=lambda k,v:values.update({k:v})
        get_limit=lambda k:values.get(k,(g.resource.RLIM_INFINITY,)*2)
        with patch.object(g.sys,'platform','linux'),patch.object(g.sys,'dont_write_bytecode',True),\
            patch.object(g.platform,'node',return_value='admitted'),patch.dict(g.os.environ,env,clear=True),\
            patch.object(g.os,'sched_getaffinity',return_value={7,8},create=True),\
            patch.object(g.os,'sched_setaffinity',create=True) as affinity,\
            patch.object(g.resource,'setrlimit',side_effect=set_limit),\
            patch.object(g.resource,'getrlimit',side_effect=get_limit),patch.object(g.signal,'signal'):
            r=g.apply_controller_limits('gpu_quality',expected_job='123',expected_host='admitted')
        self.assertEqual(r['cpu_limits'],[600,14402]);self.assertEqual(r['address_space'],[g.GPU_AS]*2)
        affinity.assert_called_once_with(0,{7})
        self.assertTrue(r['physical_memory_requires_slurm_enforcement'])

    def test_wrong_host_loader_or_thread_environment_refuses_before_limits(self):
        env={n:'1' for n in g.THREAD_VARIABLES};env['SLURM_JOB_ID']='123'
        for changed in [{'SLURM_JOB_ID':'456'},{'LD_PRELOAD':'unbound.so'},{'OMP_NUM_THREADS':'2'}]:
            with patch.object(g.sys,'platform','linux'),patch.object(g.sys,'dont_write_bytecode',True),\
                patch.object(g.platform,'node',return_value='admitted'),\
                patch.dict(g.os.environ,dict(env,**changed),clear=True),patch.object(g.resource,'setrlimit') as apply:
                with self.assertRaises(ValueError):g.apply_controller_limits('parameters',expected_job='123',expected_host='admitted')
                apply.assert_not_called()

    def test_cpu_runtime_preserves_exact_inherited_identity(self):
        expected={'declared':'fixture'}
        with patch.object(g.sys,'platform','linux'),patch('research_v61.campaign.runtime',return_value=expected) as capture:
            self.assertEqual(g.runtime('parameters',expected,inherited_cpu_runtime=expected)['kind'],'cpu')
            with self.assertRaises(ValueError):g.runtime('parameters',expected,inherited_cpu_runtime={'other':1})
            self.assertEqual(capture.call_count,1)
            capture.return_value={'declared':'changed'}
            with self.assertRaises(ValueError):g.runtime('parameters',expected,inherited_cpu_runtime=expected)

    def test_cuda_runtime_admission_is_separate_and_before_device_initialization(self):
        expected={'gpu':'fixture'};cuda=SimpleNamespace(is_initialized=lambda:False)
        with patch.object(g.sys,'platform','linux'),patch('research_v47.campaign.runtime',return_value=expected),\
            patch.dict(g.sys.modules,{'torch':SimpleNamespace(cuda=cuda)}):
            self.assertTrue(g.runtime('gpu_quality',expected)['device_and_allocator_admission_still_required'])
            with self.assertRaises(ValueError):g.runtime('gpu_quality',expected,inherited_cpu_runtime=expected)
            cuda.is_initialized=lambda:True
            with self.assertRaises(ValueError):g.runtime('gpu_quality',expected)

    def test_source_union_includes_historical_gpu_files_and_rejects_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();old={};extras={};new={};data={};raw=b'fixture source\n'
            def file(relative):
                p=root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
                return str(p),g.info(raw)
            for i in range(469):name,e=file(f'cpu/file{i:03d}.py');old[name]=e
            for i in range(14):name,e=file(f'research_v47/extra{i:02d}.py');extras[name]=e
            for i in range(9):name,e=file(f'v68/file{i:02d}.py');data[name]=e
            name,e=file('v69/new.py');new[name]=e
            names=list(old);a=dict(directory=str(root/'local_runs/v67'),prior_sources={n:old[n] for n in names[:456]},
                new_sources={n:old[n] for n in names[456:]})
            b=dict(frozen_sources=old,new_sources=data,new_source_count=9)
            c=dict(sources={str(Path(n).relative_to(root)):e['sha256'] for n,e in
                list(old.items())[:290]+list(extras.items())})
            aa,bb,cc=map(canonical_json,[a,b,c])
            with patch.object(g,'V67_PROGRAM',digest(aa)),patch.object(g,'V47_PROGRAM',digest(cc)):
                union=g.sources(aa,bb,cc,v68_sha256=digest(bb),new_sources=new)
                self.assertEqual(len(union),493);self.assertTrue(set(extras)<=set(union))
                Path(next(iter(extras))).write_bytes(b'changed GPU source')
                with self.assertRaises(ValueError):g.sources(aa,bb,cc,v68_sha256=digest(bb),new_sources=new)

    def test_imported_project_modules_cannot_shadow_registered_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp).resolve()/'source.py';p.write_bytes(b'generated')
            registered={str(p):g.info(p.read_bytes())}
            modules={'src':SimpleNamespace(__path__=[]),'src.module':SimpleNamespace(__file__=str(p)),
                'ordinary_dependency':SimpleNamespace(__file__='/not/project.py')}
            self.assertEqual(set(g.imported_sources(registered,modules)),{'src.module'})
            modules['research_v69.shadow']=SimpleNamespace(__file__='/unbound/source.py')
            with self.assertRaises(ValueError):g.imported_sources(registered,modules)
            del modules['research_v69.shadow'];p.write_bytes(b'changed')
            with self.assertRaises(ValueError):g.imported_sources(registered,modules)


if __name__=='__main__':unittest.main()
