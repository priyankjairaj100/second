"""Unregistered one-use data-only Linux entry; no model/likelihood execution."""
import sys
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010');RUN=ROOT/'local_runs/quality-data-v68-20261016-a'
V65=ROOT/'local_runs/disjoint-data-v65-20261016-a';V67=ROOT/'local_runs/disjoint-service-v67-20261016-a'
if __name__=='__main__':sys.path[:0]=[str(RUN),str(V67),str(V65),str(ROOT)]
import os,resource,time,traceback,unittest,platform,datetime,signal
from research_v67.io import require,read,write,info,json_read
from research_v68 import quality_data as data
from research_v65.data import META_NAMES
from src.run_store import canonical_json,digest,strict_json
CAPS=dict(checks=dict(cpu=300,wall=600),data=dict(cpu=600,wall=1200),audit=dict(cpu=600,wall=900))
TESTS=22
SOURCE_NAMES={'__init__.py','quality_statistics.py','test_quality_statistics.py',
    'quality_data.py','test_quality_data.py','data_runner.py','test_data_runner.py','PROTOCOL.txt','README.txt'}
V67_PROGRAM='11e0db146e79330852f550a1cc3b2dd7568a66cdfe8006b004dca3840149cc30'
INPUTS={'v65_registration','v65_data','v65_audit','v65_selection','v65_prefix','v65_after',
    'v67_program','v67_primary','v67_supplemental','v67_primary_entry','v67_supplemental_entry',
    'quality_exclusions','tokenizer'}


def bound(e):return read(e['path'],{k:e[k] for k in ['bytes','sha256']},maximum=128*2**20)
def metadata(e):return strict_json(bound(e))


def history_inventory(root=ROOT,current=RUN):
    result={};total=0
    for folder in ['pilots','campaigns','local_runs']:
        for path in sorted((root/folder).rglob('*.json')):
            parts=path.relative_to(root).parts
            if path.name not in META_NAMES:continue
            if current in path.parents or {'worker','source'}&set(parts):continue
            raw=read(path,maximum=2*2**20);total+=len(raw)
            require(len(result)<5000 and total<=64*2**20,'Bounded historical inventory required')
            result[str(path.relative_to(root))]=info(raw)
    return result


def terminal_audits(values):
    """Admission from bound terminal receipts; this does not reparse model/state bytes."""
    primary,supplemental=[strict_json(values[k]) for k in ['v67_primary','v67_supplemental']]
    require(primary['status']==supplemental['status']=='verified'
        and primary['program_sha256']==supplemental['program_sha256']==V67_PROGRAM
        and len(primary['evidence']['comparisons'])==10
        and {(r['arm'],r['step']) for r in primary['evidence']['comparisons']}=={(a,s) for a in ['cached','cold','hybrid','compressed','modern'] for s in [1,2]}
        and all(r['actual_model_bytes_equal'] is True and r['actual_bytes_equal'] is True
            and r['code_count']==42_467_328 and r['stages']==24
            and r['source_membership_and_provenance_checked'] is True
            and r['independent_retained_traversal_witnessed'] is True for r in primary['evidence']['comparisons'])
        and supplemental['evidence']['ten_actual_model_pairs_equal'] is True
        and primary['costs']==supplemental['costs'] and primary['controllers']==supplemental['controllers']
        and supplemental['evidence']['primary_receipt_sha256']==digest(values['v67_primary']), 'Both actual-model V67 terminal audits required')
    for kind,job in [('primary','15274'),('supplemental','15275')]:
        entry=strict_json(values['v67_'+kind+'_entry'])
        require(entry['status']=='complete' and entry['error'] is None and entry['program_sha256']==V67_PROGRAM
            and entry['operation']==kind and entry['job_id']==job,'Successful V67 terminal entry required')


def prerequisites(p):
    require(set(p['inputs'])==INPUTS,'Complete immutable data/prerequisite census required')
    values={k:bound(e) for k,e in p['inputs'].items()}
    require(info(values['v67_program'])['sha256']==V67_PROGRAM
        and info(values['v65_registration'])['sha256']==data.V65_REG
        and info(values['v65_after'])['sha256']==data.AFTER_SHA
        and info(values['v65_prefix'])['sha256']==data.PREFIX_SHA
        and info(values['tokenizer'])['sha256']==data.TOKENIZER_SHA,'Frozen prerequisite identities differ')
    v65data,v65audit=[strict_json(values[k]) for k in ['v65_data','v65_audit']]
    require(v65data['status']==v65audit['status']=='complete'
        and v65data['registration_sha256']==v65audit['registration_sha256']==data.V65_REG
        and v65audit['result']['status']=='verified'
        and v65audit['result']['actual_saved_prefix_retokenized'] is True
        and v65audit['result']['actual_selected_records_equal'] is True
        and v65audit['result']['actual_exclusion_sets_equal'] is True,'Audited V65 inputs required')
    terminal_audits(values)
    require(len(strict_json(values['quality_exclusions'])['excluded_from_future_confirmation_ids'])==60,'Historical quality exclusion census differs')
    selection=strict_json(values['v65_selection'])
    require(selection['candidate_records']==2349 and all(selection['source'][k]==info(values['v65_prefix'])[k] for k in ['bytes','sha256']), 'Prior full-frame identity differs')
    return values


def verify(p,*,allow_pending_experiment=False):
    require(p['schema']=='untouched-quality-data-admission-v68' and p['directory']==str(RUN)
        and p['policy']==data.POLICY and p['caps']==CAPS and p['expected_tests']==TESTS
        and p['allowance_cpu_seconds']==1506 and p['automatic_retry'] is False
        and p['model_inference'] is False and p['quality_evaluation'] is False,'Prospective data-only registration differs')
    require(len(p['frozen_sources'])==469 and p['new_source_count']==len(SOURCE_NAMES)
        and set(p['new_sources'])=={str(RUN/'research_v68'/name) for name in SOURCE_NAMES},'Source census differs')
    for group in ['frozen_sources','new_sources','tokenizer_runtime_files','historical_ledgers']:
        for path,e in p[group].items():read(path,e,maximum=128*2**20,retain=False)
    from research_v61.campaign import runtime
    require(runtime()==p['base_runtime'],'Pinned numerical base runtime differs')
    require(history_inventory()==p['history'],'Prior metadata inventory changed')
    # No pending-experiment bypass is currently admitted, even for software.
    require(allow_pending_experiment is False,'Terminal experiment prerequisite cannot be bypassed')
    return prerequisites(p)


def protected(p,values,tokenizer):
    history=[strict_json(read(ROOT/n,e,maximum=2*2**20)) for n,e in p['history'].items()]
    e=data.protected_from_v65(values['v65_after'],values['v65_prefix'],history,tokenizer)
    ids=strict_json(values['quality_exclusions'])['excluded_from_future_confirmation_ids']
    require(len(set(ids))==60 and set(ids)<=e.ids,'All sixty quality exclusions must remain reserved')
    return e


def execute(expected,trial):
    require(sys.platform=='linux' and platform.node()=='csis.mn1' and Path(__file__).resolve()==RUN/'research_v68/data_runner.py'
        and os.environ.get('SLURM_JOB_ID','').isdigit(),'Pinned Linux Slurm entry required')
    require(trial in CAPS,'Unknown data-only trial')
    for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:require(os.environ.get(name)=='1','One thread required')
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});cap=CAPS[trial]
    def cpu_expired(signum,frame):raise TimeoutError('Registered process CPU ceiling reached')
    signal.signal(signal.SIGXCPU,cpu_expired)
    for k,v in [(resource.RLIMIT_CPU,(cap['cpu'],cap['cpu']+1)),(resource.RLIMIT_AS,(4*2**30,)*2),
        (resource.RLIMIT_FSIZE,(128*2**20,)*2),(resource.RLIMIT_CORE,(0,0))]:resource.setrlimit(k,v)
    p=json_read(RUN/'registration.json');require(digest(canonical_json(p))==expected,'Registration commitment differs')
    write(RUN/(trial+'-start.json'),dict(registration_sha256=expected,trial=trial,job_id=os.environ['SLURM_JOB_ID'],
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),affinity_cpus=sorted(os.sched_getaffinity(0))))
    tick=time.perf_counter_ns();result=None;error=None
    try:
        values=verify(p)
        if trial=='checks':
            suite=unittest.defaultTestLoader.loadTestsFromNames(['research_v68.test_quality_statistics','research_v68.test_quality_data','research_v68.test_data_runner'])
            tests=unittest.TextTestRunner(verbosity=2).run(suite)
            result=dict(tests=tests.testsRun,failures=len(tests.failures),errors=len(tests.errors),skips=len(tests.skipped),generated_fixtures_only=True)
            require(tests.wasSuccessful() and tests.testsRun==TESTS and not tests.skipped,'Exact-count software gate required')
        else:
            gate=json_read(RUN/'checks.json');require(gate['status']=='complete' and gate['registration_sha256']==expected
                and gate['result']['tests']==TESTS and not gate['result']['skips']
                and gate['result']['failures']==gate['result']['errors']==0,'Passed bound Linux software gate required')
            from tokenizers import Tokenizer
            import tokenizers
            require(tokenizers.__version__==p['tokenizers_version']=='0.23.2','Pinned tokenizer runtime required')
            tokenizer=Tokenizer.from_file(p['inputs']['tokenizer']['path']);require(tokenizer.get_vocab_size()==50257,'Tokenizer vocabulary differs')
            excluded=protected(p,values,tokenizer);out=RUN/'outputs'
            if trial=='data':
                out.mkdir(exist_ok=False);raw=data.acquire(out);result=data.materialize(out,raw,tokenizer,excluded)
            else:
                previous=json_read(RUN/'data.json');require(previous['status']=='complete' and previous['registration_sha256']==expected,'Complete one-use selection required')
                require(previous['result']==json_read(out/'selection.json'),'Selection receipt differs')
                result=data.audit_saved(out,tokenizer,excluded)
        verify(p)
    except BaseException as exc:
        error=dict(type=type(exc).__name__,message=str(exc));traceback.print_exc()
    now=resource.getrusage(resource.RUSAGE_CHILDREN);cc=round((now.ru_utime+now.ru_stime)*1e9);pc=time.process_time_ns()
    if pc+cc>(cap['cpu']+2)*10**9:error=dict(type='BudgetExceeded',message='Process plus child CPU exceeded its separate reservation')
    receipt=dict(status='complete' if error is None else 'failed',trial=trial,registration_sha256=expected,job_id=os.environ['SLURM_JOB_ID'],caps=cap,
        result=result,error=error,process_cpu_ns=pc,waited_child_cpu_ns=cc,combined_observed_cpu_ns=pc+cc,elapsed_ns=time.perf_counter_ns()-tick,
        max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,model_inference=False,quality_evaluation=False)
    receipt['cpu_clock_scope']='Whole Python process including imports plus all waited children; final receipt write and container startup require scheduler accounting'
    write(RUN/(trial+'.json'),receipt);require(error is None,'One-use data trial failed; preserve output and do not retry')

if __name__=='__main__':execute(*sys.argv[1:])
