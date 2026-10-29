"""One-use controller, immutable program verification and disjoint-root bindings."""
import os,sys,time
from pathlib import Path
from research_v89.config import ROOT,RUN,STAGED,ORDER,TRIALS,CAP,design,RECORDS_SHA,SELECTION_SHA,V65_REG,V66_REG,CALIBRATION_TARGET,BASE_TARGET
from research_v80.io import require,read,json_read,write,info
from research_v89.resource_review import review
from research_v61.campaign import runtime
from research_v38.bootstrap_target import CHECKPOINT_HASHES
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget
from src.worker_control import WorkerLimits,run_limited
from src.run_store import canonical_json,digest

INPUT_KEYS={'checkpoint_config','checkpoint_weights','base_target','calibration_target',
    'data_registration','data_receipt','data_audit','data_selection','data_records',
    'exclusions_before','exclusions_after','source_prefix','quality_exclusions',
    'v66_registration','v66_completion','v79_completion'}

def bound(e,retain=True):return read(e['path'],{k:e[k] for k in ['bytes','sha256']},retain=retain)
def sha(path):return read(path,retain=False)['sha256']
def entry_json(e):
    from src.run_store import strict_json
    raw=bound(e);x=strict_json(raw);require(type(x) is dict and canonical_json(x)==raw,'Canonical bound metadata required');return x

def load_records(p):
    require(p['inputs']['data_records']['sha256']==RECORDS_SHA and p['inputs']['data_selection']['sha256']==SELECTION_SHA,'Fixed V65 root required')
    records=entry_json(p['inputs']['data_records'])['records'];selection=entry_json(p['inputs']['data_selection'])
    require(type(records) is list and len(records)==13 and records==sorted(records,key=lambda r:r['id'])
        and len({r['id'] for r in records})==13 and all(set(r)=={'id','tokens'} and type(r['tokens']) is list
        and len(r['tokens'])==128 and all(type(t) is int and 0<=t<50257 for t in r['tokens']) for r in records),'Root extent/order/vocabulary differs')
    metadata={r['id']:r for r in selection['selected_metadata']}
    require(set(metadata)=={r['id'] for r in records} and len(selection['selected_metadata'])==13,'Selected identity census')
    from research_v45.data import TOKENIZER_SHA
    provenance={r['id']:dict(dataset_id='allenai/c4',dataset_revision=selection['policy']['revision'],
        split='train-shard2-prefix',source_file_sha256=selection['source']['sha256'],tokenizer_sha256=TOKENIZER_SHA,
        body_sha256=metadata[r['id']]['body_sha256'],normalized_text_sha256=metadata[r['id']]['normalized_text_sha256'],
        selection_sha256=SELECTION_SHA) for r in records}
    return records,provenance

def verify_inputs(p):
    require(set(p['inputs'])==INPUT_KEYS,'Complete V80 input census required')
    for e in p['inputs'].values():bound(e,retain=False)
    for key in ['checkpoint_config','checkpoint_weights']:
        e=p['inputs'][key];path=Path(e['path'])
        require(path.parent==ROOT/'tmp/models/distilgpt2' and e['sha256']==CHECKPOINT_HASHES[path.name],'Checkpoint binding differs')
    require({Path(p['inputs'][k]['path']).name for k in ['checkpoint_config','checkpoint_weights']}==set(CHECKPOINT_HASHES),'Complete checkpoint files required')
    require(p['shared_checkpoint_bytes']==sum(p['inputs'][k]['bytes'] for k in ['checkpoint_config','checkpoint_weights']),'Common checkpoint extent')
    require(p['inputs']['calibration_target']['sha256']==CALIBRATION_TARGET and p['inputs']['base_target']['sha256']==BASE_TARGET,'Frozen numerical target differs')
    require(p['inputs']['data_registration']['sha256']==V65_REG and p['inputs']['v66_registration']['sha256']==V66_REG,'Preceding registration identities differ')
    d,a,c=[entry_json(p['inputs'][k]) for k in ['data_receipt','data_audit','v66_completion']]
    require(d['status']==a['status']=='complete' and d['registration_sha256']==a['registration_sha256']==V65_REG
        and a['result']['status']=='verified' and all(a['result'][k] for k in ['actual_saved_prefix_retokenized','actual_selected_records_equal','actual_exclusion_sets_equal']),'Successful data admission/audit required')
    require(c['status']=='complete' and c['registration_sha256']==V66_REG and c['result']['tests']==44 and c['result']['skipped']==0,'Passed V66 qualification required')
    q=__import__('json').loads(bound(p['inputs']['v79_completion']))
    require(q['status']=='complete' and q['error'] is None and q['job_id']=='15903' and q['program_sha256']=='a0d71ade247d410150a3178cc385613b3c6dc9e347eaaaca0b20524f64f6770a','Successful V79 integration prerequisite required')
    exclusions=entry_json(p['inputs']['quality_exclusions'])['excluded_from_future_confirmation_ids']
    require(len(exclusions)==len(set(exclusions))==60,'Historical quality exclusions differ')
    selection=entry_json(p['inputs']['data_selection'])
    require(selection['records']=={k:p['inputs']['data_records'][k] for k in ['bytes','sha256']}
        and all(selection['source'][k]==p['inputs']['source_prefix'][k] for k in ['bytes','sha256'])
        and selection['exclusions_before']=={k:p['inputs']['exclusions_before'][k] for k in ['bytes','sha256']},'Data provenance commitments differ')
    data_manifest=entry_json(p['inputs']['data_registration'])
    require(selection['policy']==data_manifest['policy'] and selection['confirmation'] is False,'Data policy differs')
    # These actual saved sets bind the exposure exclusions used by future phases.
    before=entry_json(p['inputs']['exclusions_before']);after=entry_json(p['inputs']['exclusions_after'])
    require(set(before)==set(after)=={'ids','content','chunks'} and all(set(before[k])<=set(after[k]) for k in before),'Protected exclusions were removed')
    records,provenance=load_records(p)
    require({r['id'] for r in records}<=set(after['ids']),'Admitted root missing from successor exclusions')
    return records,provenance

def verify_bindings(p):
    require(len(p['prior_sources'])==456 and len(p['new_sources'])==p['new_source_count'],'Source inventory census differs')
    for group in ['prior_sources','new_sources','dependency_files','historical_ledgers']:
        for path,e in p[group].items():read(path,e,retain=False)
    require(runtime()==p['runtime'],'Pinned base runtime changed')

def verify(program=RUN/'program.json',*,software=True):
    program=Path(program).absolute();require(program==RUN/'program.json','One fixed program path required')
    p=json_read(program);require(all(p.get(k)==v for k,v in design().items()),'Frozen design differs')
    require(json_read(RUN/'registration.json')==dict(program_sha256=sha(program)),'Program registration differs')
    verify_bindings(p);verify_inputs(p)
    from research_v89.recovery import verify_failure_bindings
    verify_failure_bindings(p)
    require(p['resource_admission']==review(bound(p['inputs']['base_target'])),'Complete structural admission changed')
    if software:
        c=json_read(RUN/'software-completion.json')
        require(c['status']=='complete' and c['program_sha256']==sha(program) and c['tests']==p['expected_tests']
            and c['skipped']==0 and c['failures']==0 and c['errors']==0 and c['empirical_execution'] is False,'Passed exact-source Linux qualification required')
    return p

def budget(p):
    return PhaseBudget(RUN/'budget',identity=dict(protocol_sha256=sha(RUN/'program.json'),source_sha256=source_hashes(ROOT)),phase_cpu_seconds={'feasibility':CAP})

def command(plan):return [sys.executable,'-B',str(RUN/'research_v89/worker.py'),str(plan)]

def run(trial):
    require(sys.platform=='linux' and os.environ.get('SLURM_JOB_ID','').isdigit(),'Pinned Slurm controller required')
    tick=time.perf_counter_ns();cpu=time.process_time_ns();p=verify();require(trial in TRIALS,'Unknown trial')
    for previous in ORDER[:ORDER.index(trial)]:
        require(json_read(RUN/previous/'transaction.json')['worker_outcome']['status']=='complete'
            and json_read(RUN/previous/'outputs/completion.json')['status']=='complete','Earlier one-use trial failed or missing')
    attempt=RUN/trial;require(not attempt.exists(),'One-use attempt exists; retry forbidden');attempt.mkdir()
    plan=dict(trial=trial,program=str(RUN/'program.json'),program_sha256=sha(RUN/'program.json'),
        output=str(attempt/'outputs'),slurm_job_id=os.environ['SLURM_JOB_ID'])
    write(attempt/'plan.json',plan)
    receipt=run_limited(command(attempt/'plan.json'),attempt/'worker',
        WorkerLimits(**TRIALS[trial],address_space_bytes=p['process_address_space_bytes'],threads=1,
            affinity_cpus=(min(os.sched_getaffinity(0)),),file_size_bytes=p['file_size_bytes']),
        identity=dict(campaign_sha256=plan['program_sha256'],trial=trial),cwd=ROOT,phase_budget=budget(p),phase='feasibility')
    snapshot=budget(p).snapshot()
    write(attempt/'transaction.json',dict(worker_outcome=receipt['outcome'],elapsed_ns=time.perf_counter_ns()-tick,
        controller_process_cpu_ns=time.process_time_ns()-cpu,budget=snapshot,slurm_job_id=plan['slurm_job_id'],
        clock_scope='Controller verification and setup through worker exit, sealing and ledger snapshot; final transaction JSON write and controller shutdown additionally appear in scheduler accounting'))
    require(receipt['outcome']['status']=='complete','One-use worker failed; preserve all partial outputs')
