"""Generated scheduler/filesystem fixtures; never call Slurm or create a job."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import copy,json,subprocess,unittest
from research_v69 import submission as s,execution_gate


def program():
    partitions={}
    for kind,name,wall,mem,cpus in [('cpu','cpu-short','12:00:00','128000','64'),
        ('cuda','gpu-short','08:00:00','96000','48')]:
        partitions[kind]=dict(PartitionName=name,AllowGroups='ALL',AllowAccounts='ALL',AllowQos='ALL',
            Nodes='csis.cn[1-4],csis.mn1',State='UP',MaxTime=wall,MaxMemPerNode=mem,MaxCPUsPerNode=cpus)
    return dict(schema='untouched-quality-campaign-v69',directory=str(s.RUN),registered=True,
        automatic_retry=False,submission_policy='hold-bind-release-once-sequential-afterok',
        resources=s.resources(),interpreters=dict(cpu=str(s.CPU),cuda=str(s.CUDA)),
        hosts=dict(cpu=['csis.mn1'],cuda=['csis.cn1','csis.cn3']),new_sources={},
        launch=dict(schema='held-slurm-launch-policy-v69',partitions=partitions,
            partition_hosts={k:sorted(s.NODES) for k in ['cpu','cuda']},qos_max_wall='12:00:00',
            account='faculty',qos='cpu-short'))


class Scheduler:
    def __init__(self,p):self.p=p;self.calls=[];self.jobs={};self.released=[];self.mutate=None;self.fail=None
    def __call__(self,args):
        self.calls.append(args[:]);out='';code=0
        if self.fail:
            special=self.fail(args)
            if special is not None:return special
        if args[0]=='sbatch':
            job=str(17001+len(self.jobs));o=dict(x[2:].split('=',1) for x in args if x.startswith('--') and '=' in x)
            self.jobs[job]=(args[-2],o,args[-3]);out=job+'\n'
        elif args[:3]==['scontrol','show','job']:
            job=args[3];phase,o,wrapper=self.jobs[job];gpu=phase in s.GPU
            f=dict(JobId=job,JobName=o['job-name'],UserId='poonam(1007)',JobState='PENDING',Reason='JobHeldUser',
                Priority='0',Account=o['account'],QOS=o['qos'],Partition=o['partition'],Requeue='0',Restarts='0',
                NumCPUs=o['cpus-per-task'],NumNodes=o['nodes'],NumTasks=o['ntasks'],BatchFlag='1',
                WorkDir=o['chdir'],Command=wrapper,StdIn='/dev/null',StdOut=o['output'].replace('%j',job),
                StdErr=o['error'].replace('%j',job),KillOInInvalidDependent='Yes',Comment=o['comment'],
                TimeLimit=o['time'],MinMemoryNode=o['mem'],Dependency=o['dependency']+'(unfulfilled)' if 'dependency' in o else '(null)',
                ReqNodeList=o.get('nodelist','(null)'),ExcNodeList=o.get('exclude','(null)'),
                ReqTRES='cpu=1,mem='+o['mem']+',node=1,billing=1'+(',gres/gpu=1,gres/gpu:a100-80gb=1' if gpu else ''))
            f['CPUs/Task']='1'
            if gpu:f['TresPerNode']='gres/gpu:a100-80gb:1'
            if self.mutate:self.mutate(phase,f)
            out=' '.join(k+'='+v for k,v in f.items())
        elif args[:3]==['scontrol','show','partition']:
            kind='cpu' if args[3]=='cpu-short' else 'cuda'
            out=' '.join(k+'='+v for k,v in self.p['launch']['partitions'][kind].items())
        elif args[:3]==['scontrol','show','hostnames']:
            out='\n'.join(sorted(s.NODES) if args[3]=='csis.cn[1-4],csis.mn1' else args[3].split(','))
        elif args[0]=='sacctmgr':out='cpu-short|12:00:00\n'
        elif args[0]=='squeue':out='\n'.join(j+'|second69-'+v[0]+'|PENDING' for j,v in self.jobs.items())
        elif args[:2]==['scontrol','release']:self.released.append(args[2])
        elif args==['git','rev-parse','HEAD']:out=s.CHECKOUT
        elif args==['git','status','--porcelain']:out=''
        else:raise AssertionError(args)
        return dict(arguments=args,returncode=code,stdout=out,stderr='')


def save_program():
    p=program();source=s.RUN/'research_v69/generated.txt';source.parent.mkdir();source.write_bytes(b'generated-only')
    p['new_sources'][str(source)]=s.info(source.read_bytes())
    expected=s.sha(s.canonical(p));s.write(s.RUN/'program.json',p)
    s.write(s.RUN/'registration.json',dict(program_sha256=expected))
    return p,expected


class SubmissionTests(unittest.TestCase):
    def test_full_resource_copy_matches_worker_and_each_cap_change_refuses(self):
        self.assertEqual(s.resources(),execution_gate.design())
        p=program();s.policy(p)
        for phase in s.ORDER[:-1]:
            q=copy.deepcopy(p);q['resources']['phases'][phase]['cpu_seconds']+=1
            with self.assertRaisesRegex(ValueError,'caps'):s.policy(q)
        q=copy.deepcopy(p);q['resources']['threads']=2
        with self.assertRaises(ValueError):s.policy(q)

    def test_node_pool_is_one_gpu_with_exclusions_and_cpu_closure_has_own_cap(self):
        p=program();a=s.arguments(p,'cuda_checks','17001')
        self.assertIn('--nodes=1',a);self.assertIn('--gres=gpu:a100-80gb:1',a)
        self.assertIn('--exclude=csis.cn2,csis.cn4,csis.mn1',a)
        self.assertFalse(any(x.startswith('--nodelist=') for x in a))
        b=s.arguments(p,'closure','17008');self.assertIn('--mem=4G',b);self.assertIn('--time=00:15:00',b)
        for a in [a,b]:
            for flag in ['--hold','--no-requeue','--kill-on-invalid-dep=yes','--ntasks=1','--cpus-per-task=1']:
                self.assertIn(flag,a)

    def test_insufficient_partition_or_changed_live_policy_refuses(self):
        p=program();q=copy.deepcopy(p);q['launch']['partitions']['cpu']['MaxTime']='01:00:00'
        with self.assertRaises(ValueError):s.policy(q)
        fake=Scheduler(p);q=copy.deepcopy(p);q['launch']['qos_max_wall']='13:00:00'
        with self.assertRaisesRegex(ValueError,'QoS'):s.live_policy(q,fake)

    def test_active_second_queue_refuses_before_any_source_read_or_submission(self):
        p=program();fake=Scheduler(p);fake.jobs['15263']=('hybrid',{},'')
        with self.assertRaisesRegex(ValueError,'Existing Second'):
            s.preflight(p,fake)
        self.assertFalse(any(a[0]=='sbatch' for a in fake.calls))

    def test_all_nine_bindings_exist_and_rechecked_before_first_release(self):
        with TemporaryDirectory() as tmp,patch.object(s,'RUN',Path(tmp).resolve()),patch.object(s,'preflight',return_value={'generated':True}):
            p,expected=save_program();fake=Scheduler(p)
            def check_release(args):
                if args[:2]==['scontrol','release']:
                    self.assertTrue((s.RUN/'chain-ready.json').exists())
                    for n in s.ORDER:
                        self.assertEqual(s.obj(s.RUN/n/'job-binding.json')['submission_state'],'held-before-release')
            fake.fail=check_release;jobs=s.launch(expected,fake)
            self.assertEqual(len(jobs),9);self.assertEqual(fake.released,[str(j) for j in range(17009,17000,-1)])
            self.assertEqual(sum(a[:3]==['scontrol','show','job'] for a in fake.calls),18)
            self.assertEqual(s.obj(s.RUN/'launch-completion.json')['status'],'complete')
            count=len(fake.calls)
            with self.assertRaisesRegex(ValueError,'One-use'):s.launch(expected,fake)
            self.assertEqual(len(fake.calls),count)

    def test_uncertain_second_submission_keeps_first_held_and_never_retries(self):
        for mode in ['timeout','cluster_suffix','nonzero']:
            with self.subTest(mode=mode),TemporaryDirectory() as tmp,patch.object(s,'RUN',Path(tmp).resolve()),\
                patch.object(s,'preflight',return_value={'generated':True}):
                p,expected=save_program();fake=Scheduler(p)
                def fail(args):
                    if args[0]=='sbatch' and len(fake.jobs)==1:
                        if mode=='timeout':raise subprocess.TimeoutExpired(args,30)
                        return dict(arguments=args,returncode=1 if mode=='nonzero' else 0,stdout='17002;cluster\n',stderr='generated uncertainty')
                fake.fail=fail
                with self.assertRaises((ValueError,subprocess.TimeoutExpired)):s.launch(expected,fake)
                completion=s.obj(s.RUN/'launch-completion.json')
                self.assertEqual(completion['status'],'failed');self.assertEqual(len(completion['jobs']),1)
                self.assertEqual(fake.released,[]);self.assertEqual(sum(a[0]=='sbatch' for a in fake.calls),2)
                self.assertTrue((s.RUN/'cuda_checks/submission-intent.json').exists())
                with self.assertRaisesRegex(ValueError,'One-use'):s.launch(expected,fake)

    def test_changed_held_identity_resources_dependency_or_pool_prevents_release(self):
        mutations=[('cpu_checks','Requeue','1'),('cpu_checks','NumCPUs','2'),
            ('cuda_checks','Dependency','afterany:17001(unfulfilled)'),('cuda_checks','ExcNodeList','csis.mn1'),
            ('cuda_checks','TresPerNode','gres/gpu:a100-80gb:2'),('cuda_checks','Comment','other'),
            ('cpu_checks','ReqTRES','cpu=2,cpu=1,mem=16G,node=1')]
        for target,key,value in mutations:
            with self.subTest(key=key),TemporaryDirectory() as tmp,patch.object(s,'RUN',Path(tmp).resolve()),\
                patch.object(s,'preflight',return_value={'generated':True}):
                p,expected=save_program();fake=Scheduler(p)
                fake.mutate=lambda n,f:f.update({key:value}) if n==target else None
                with self.assertRaises(ValueError):s.launch(expected,fake)
                self.assertEqual(fake.released,[]);self.assertEqual(s.obj(s.RUN/'launch-completion.json')['status'],'failed')

    def test_source_changed_during_binding_prevents_all_releases(self):
        with TemporaryDirectory() as tmp,patch.object(s,'RUN',Path(tmp).resolve()),patch.object(s,'preflight',return_value={'generated':True}):
            p,expected=save_program();fake=Scheduler(p)
            def corrupt(n,f):
                if n=='closure':(s.RUN/'research_v69/generated.txt').write_bytes(b'changed')
            fake.mutate=corrupt
            with self.assertRaisesRegex(ValueError,'commitment'):s.launch(expected,fake)
            self.assertEqual(len(fake.jobs),9);self.assertEqual(fake.released,[])

    def test_partial_release_failure_keeps_successful_history_and_first_job_held(self):
        with TemporaryDirectory() as tmp,patch.object(s,'RUN',Path(tmp).resolve()),patch.object(s,'preflight',return_value={'generated':True}):
            p,expected=save_program();fake=Scheduler(p)
            def fail(args):
                if args==['scontrol','release','17008']:
                    return dict(arguments=args,returncode=1,stdout='',stderr='generated release failure')
            fake.fail=fail
            with self.assertRaisesRegex(ValueError,'release'):s.launch(expected,fake)
            self.assertEqual(fake.released,['17009']);self.assertEqual(len(fake.jobs),9)
            self.assertTrue((s.RUN/'terminal/release-response.json').exists())
            self.assertFalse((s.RUN/'cpu_checks/release-intent.json').exists())

    def test_symbolic_inputs_exclusive_outputs_and_noncanonical_json_refuse(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();s.write(root/'x',{'a':1});(root/'link').symlink_to(root/'x')
            with self.assertRaises(ValueError):s.obj(root/'link')
            with self.assertRaises(FileExistsError):s.write(root/'x',{'a':2})
            (root/'x').write_text('{"a": 1}')
            with self.assertRaises(ValueError):s.obj(root/'x')
        with self.assertRaises(ValueError):s.fields('Name=a Name=b')

    def test_cpu_and_gpu_wrapper_syntax_and_all_thread_variables(self):
        for name in ['run_cpu.sbatch','run_gpu.sbatch']:
            path=Path(__file__).with_name(name)
            result=subprocess.run(['bash','-n',str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            text=path.read_text()
            for key in execution_gate.THREAD_VARIABLES:self.assertIn(key+'=1',text)
            self.assertIn('PYTHONHASHSEED=0',text);self.assertIn('-B',text)
        self.assertIn('--cleanenv',Path(__file__).with_name('run_cpu.sbatch').read_text())
        self.assertIn('CUBLAS_WORKSPACE_CONFIG=:4096:8',Path(__file__).with_name('run_gpu.sbatch').read_text())


if __name__=='__main__':unittest.main()
