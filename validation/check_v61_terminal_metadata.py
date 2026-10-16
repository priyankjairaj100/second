"""Portable, read-only V61 terminal METADATA check; Python standard library only.

No model, decoder, solver, numerical library, runtime binary, or state parser is
loaded. Cluster binary-equality findings are checked as mutually bound receipt
claims, never promoted to a local numerical verification or physical erasure.
The fixed program and original software receipt are trust anchors; coherent
hostile rewriting of later unsigned receipts is outside this check's scope.
"""
import argparse
import ast
import copy
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re

# A repository argument is mandatory at the CLI. The class default supports
# metadata-only helper fixtures and normal placement under repo/validation.
REPO = Path(__file__).resolve().parents[1]
REMOTE = '/nfs_home/users/poonam/second-20261010'
CAMPAIGN = 'full-precision-service-v61-20261014-a'
LAUNCH = 'continuation-v61-20261014-a'
DIRECTORY = REMOTE+'/local_runs/'+CAMPAIGN
PROGRAM_SHA = '6632712f7b79b49734790fa6fc173ec7e5ee70f542fe8f8a0c3ef3ff2171ea2d'
SOURCE_COMMIT = 'f900999fcb200509dfad4fc081ce9c87fd172a16'
SOFTWARE_SHA = '71c1f573e977a66f244e85bf2229744d3077bd1d3ccf860c266cc9d94d629ae7'
V59_PROGRAM = '4a22292c903b4817629bd43449dcf6f22c827f7c31c9e525fcb3fdcca448e835'
V59_COMPLETION = '2c80712913d314aa88d5abede08f324e8a773b9ffb847b58a9b721e7301c731c'
V59_AUDIT = '286a2c74b676e55ff4d463d31545ca8138eb7dce36e515112fb697575a89f6e6'
V59_TARGET = '3853008973e0a89db5c80d73d30cb4304bc5d9c89fafa80e6f7f15de232a1245'
V59_MODEL = '904d2dc59a22b28d74db20b388bc1acc5d7566150441d65a7318a5d896271192'
ORDER = ('prepare','cached','cold','hybrid','compressed','oracle')
TRIALS = dict(prepare=(10800,14400),cached=(10800,14400),cold=(12600,16200),
              hybrid=(14400,18000),compressed=(18000,21600),oracle=(14400,18000))
ARMS = dict(cached='lossless',compressed='compressed48',hybrid='hybrid_gram',cold='lossless')
REPS = ('lossless','compressed48','hybrid_gram')
CAP = 81012
JOBS = dict(checks='13561',register='13562',prepare='13563',cached='13564',cold='13565',
    hybrid='13566',compressed='13567',oracle='13568',audit='13569',postrun='13570')
THREADS = ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS',
           'VECLIB_MAXIMUM_THREADS','BLIS_NUM_THREADS','RAYON_NUM_THREADS')
BINARY_SUFFIXES = {'.bin','.npz','.safetensors'}


def require(value, message):
    if not value: raise ValueError(message)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')


def strict(raw):
    def pairs(items):
        result = {}
        for key,value in items:
            require(key not in result,'Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def equal(a,b,message):
    require(canonical(a)==canonical(b),message)


def digest(raw): return hashlib.sha256(raw).hexdigest()
def info(raw): return dict(bytes=len(raw),sha256=digest(raw))


def commitment(entry):
    require(type(entry) is dict,'Expected file commitment')
    result={key:entry[key] for key in ('bytes','sha256')}
    require(type(result['bytes']) is int and result['bytes'] >= 0 and
        type(result['sha256']) is str and re.fullmatch('[0-9a-f]{64}',result['sha256']), 'Invalid file commitment')
    return result


def integer(value,label,minimum=0):
    require(type(value) is int and value >= minimum,label+' must be an integer >= '+str(minimum))
    return value


def safe(root,name):
    require(type(name) is str and name,'Empty path')
    relative=PurePosixPath(name)
    require(not relative.is_absolute() and '..' not in relative.parts and str(relative)==name,'Unsafe relative path')
    path=Path(root).joinpath(*relative.parts)
    require(not any(p.is_symlink() for p in (path,*path.parents)),'Symbolic input refused')
    return path


def read_bytes(path):
    require(path.is_file() and not path.is_symlink(),'Missing regular metadata: '+str(path))
    require(path.stat().st_size <= 64*2**20,'Metadata exceeds bound')
    return path.read_bytes()


def read_json(path):
    raw=read_bytes(path); value=strict(raw)
    require(canonical(value)==raw,'Noncanonical JSON: '+str(path))
    return value


def inventory_equal(actual,expected,label):
    require(type(actual) is dict and set(actual)==set(expected),label+' census differs')
    for name,entry in expected.items(): equal(actual[name],entry,label+' commitment differs: '+name)


def literal_assignment(path,name):
    """Read a literal source constant without importing any module."""
    for node in ast.parse(read_bytes(path),filename=str(path)).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('Missing literal source constant '+name)


def validate_debit(row,reserved=None):
    require(type(row) is dict and set(row)=={'phase','reserved_cpu_seconds','state','charged_cpu_seconds','observed_cpu_ns'},'Debit fields')
    require(row['phase']=='feasibility' and row['state']=='settled','Unsettled or foreign phase debit')
    used=integer(row['observed_cpu_ns'],'Observed CPU')
    charge=integer(row['charged_cpu_seconds'],'Charged CPU',1)
    allowance=integer(row['reserved_cpu_seconds'],'CPU reservation',1)
    require(charge==max(1,(used+999999999)//1000000000) and charge <= allowance,'CPU rounding or reservation overrun')
    if reserved is not None: require(allowance==reserved,'Worker CPU reservation differs')
    return charge


def validate_ledger(raw,sources):
    ledger=strict(raw); require(canonical(ledger)==raw,'Ledger noncanonical')
    binding=dict(identity=dict(protocol_sha256=PROGRAM_SHA,source_sha256=sources),
        phase_cpu_seconds={'feasibility':CAP},scope='trusted_worker_cpu_admission_not_process_tree_containment')
    require(set(ledger)=={'schema','binding','attempts'} and ledger['schema']=='phase-cpu-ledger-v1','Ledger schema')
    equal(ledger['binding'],binding,'Complete ledger source/scope binding')
    require(type(ledger['attempts']) is dict and len(ledger['attempts'])==6,'Exactly six worker debits required')
    used=0
    for key,row in ledger['attempts'].items():
        require(type(key) is str and 0<len(key)<=1024,'Invalid debit ID')
        used += validate_debit(row)
    require(used<=CAP,'V61 phase cap exceeded')
    snapshot=dict(schema='phase-cpu-read-snapshot-v1',path=DIRECTORY+'/budget/ledger.json',binding=binding,
        binding_sha256=digest(canonical(binding)),phase_cpu_seconds={'feasibility':CAP},
        scope='complete trusted protocol ledger at read time; not project/global/hostile completeness',
        read_only=True,status='verified',ledger_sha256=digest(raw),ledger_bytes=len(raw),attempts=ledger['attempts'],
        charged_cpu_seconds={'feasibility':used},reserved_unknown_attempts=0,reservation_overrun_attempts=[],over_cap={'feasibility':False})
    return ledger,snapshot


def validate_seal_observations(identity,sealed,reservation,observation,attempt_path):
    expected_id=digest(canonical(dict(worker=identity,attempt=attempt_path)))
    require(sealed['budget_attempt_id']==expected_id,'Derived one-use budget attempt identity')
    allowance=identity['limits']['cpu_seconds']+2
    expected=dict(binding_sha256=identity['phase_budget']['binding_sha256'],budget_attempt_id=expected_id,
        budget_debit=dict(phase='feasibility',reserved_cpu_seconds=allowance,state='reserved',
            observed_cpu_ns=None,charged_cpu_seconds=allowance))
    equal(reservation,expected,'Prelaunch full CPU reservation')
    equal(observation,dict(outcome=sealed['outcome'],timing_boundary=sealed['timing_boundary'],
        resource_usage=sealed['resource_usage'],budget_attempt_id=expected_id,
        scope='observed worker exit before CPU settlement and receipt sealing'),'Pre-settlement observations')
    timing=sealed['timing_boundary']
    for key in ('start_ns','cleanup_start_ns','cleanup_end_ns'): integer(timing[key],'Controller '+key)
    require(timing['clock']=='time.perf_counter_ns_same_controller_process'
        and timing['start_ns']<=timing['cleanup_start_ns']<=timing['cleanup_end_ns']
        and timing['cleanup_end_ns']-timing['start_ns']==sealed['outcome']['elapsed_wall_ns'],
        'Controller clock arithmetic')


def expected_artifacts(trial):
    names={'execution-provenance.json','admission.json'}
    if trial=='prepare':
        names.add('original-model.bin')
        for rep in REPS: names.update((rep+'-original.bin',rep+'-trust.json'))
    elif trial=='oracle':
        for step in (1,2):
            names.add(f'step-{step}-model.bin')
            for rep in REPS: names.update((f'step-{step}-{rep}.bin',f'step-{step}-{rep}-trust.json'))
    else:
        for step in (1,2): names.update(f'step-{step}-{suffix}' for suffix in ('model.bin','state.bin','trust.json'))
    return names


def storage(row,state_entry,trust_entry,checkpoint):
    expected=dict(state_bytes=state_entry['bytes'],trust_bytes=trust_entry['bytes'],
        complete_deployment_bytes=state_entry['bytes']+trust_entry['bytes']+checkpoint)
    for key,value in expected.items(): equal(row[key],value,'Storage arithmetic '+key)
    return dict(expected,live_state_bytes=state_entry['bytes']+trust_entry['bytes'])


class Check:
    def __init__(self,root,repo=REPO):
        self.root,self.repo=Path(root).resolve(),Path(repo).resolve()
        self.manifest=None;self.p=None;self.jobs={};self.expected={};self.missing={}
        self.completions={};self.transactions={};self.seals={};self.progress={};self.verified={}

    def local(self,name): return safe(self.root,name)
    def json(self,name): return read_json(self.local(name))
    def path(self,remote):
        require(remote.startswith(REMOTE+'/'),'Remote path outside pinned checkout')
        if remote.startswith(REMOTE+'/local_runs/'+CAMPAIGN+'/'):
            return self.local(CAMPAIGN+'/'+remote[len(DIRECTORY)+1:])
        mapping=self.manifest['repository_paths']
        require(remote in mapping,'Required captured metadata path not mapped: '+remote)
        return self.local(mapping[remote])

    def bind(self,remote,entry):
        entry=commitment(entry)
        require(remote not in self.expected or self.expected[remote]==entry,'Conflicting audit commitment')
        self.expected[remote]=entry
        if Path(remote).suffix in BINARY_SUFFIXES:
            missing=self.manifest['inputs_not_copied'].get(remote)
            require(type(missing) is dict and missing.get('status')=='NOT revalidated','Absent binary must be explicit: '+remote)
            equal(commitment(missing.get('expected',missing)),entry,'Absent binary commitment')
            require(missing.get('exists') is True and missing.get('observed_bytes')==entry['bytes']
                and missing.get('binary_contents_read') is False and missing.get('kind')=='numerical_binary',
                'Captured binary extent/scope differs: '+remote)
            self.missing[remote]=dict(expected=entry,status='NOT revalidated',kind='numerical binary')
            return None
        raw=read_bytes(self.path(remote))
        equal(info(raw),entry,'Captured metadata commitment: '+remote)
        self.verified[remote]=entry
        return raw

    def input(self,key):
        entry=self.p['inputs'][key]
        return strict(self.bind(entry['path'],entry))

    def copied(self,relative):
        remote=DIRECTORY+'/'+relative
        raw=read_bytes(self.local(CAMPAIGN+'/'+relative))
        self.bind(remote,info(raw))
        return strict(raw) if relative.endswith('.json') else raw

    def collection(self):
        m=strict(read_bytes(self.local('collection-manifest.json')));self.manifest=m
        require(m['schema']=='second-terminal-v61-metadata-v1','Terminal collection schema required')
        require(type(m['files']) is dict and m['files'],'Complete copied file inventory required')
        for name,entry in m['files'].items(): equal(info(read_bytes(self.local(name))),commitment(entry),'Copied file '+name)
        actual={str(p.relative_to(self.root)) for p in self.root.rglob('*') if p.is_file()}
        require(actual==set(m['files'])|{'collection-manifest.json'},'Copied inventory missing/extra files')
        require(type(m['repository_paths']) is dict and type(m['inputs_not_copied']) is dict,'Collection path/missing inventories required')
        for remote,name in m['repository_paths'].items():
            require(remote.startswith(REMOTE+'/') and name in m['files'],'Invalid remote metadata mapping')
            self.local(name)
        # Exact terminal-success discriminator is checked against the collector's
        # stable schema below; no partial or failed capture is accepted.
        require(m.get('terminal') is True,'Only a terminal capture is accepted')
        require(m.get('reported_success') is True and m.get('capture_scope')=='terminal_success_receipts_metadata_only',
            'Only a successful terminal capture is accepted')
        require(m.get('portable_scientific_validation_performed') is False and m.get('capture_issues')==[]
            and m.get('cluster_commit')==SOURCE_COMMIT and m.get('program_sha256')==PROGRAM_SHA
            and m.get('source_files_verified')==432 and m.get('final_metadata_bytes_rehashed') is True
            and m.get('source_and_campaign_census_unchanged') is True
            and m.get('excluded_binary_contents_rehashed') is False
            and m.get('numerical_inference_or_calibration_executed') is False,'Capture identity/scope')
        require(m.get('quiescent') is True and m.get('blocked_dependency_jobs')=={}
            and type(m.get('scheduler_queue')) is str and not m['scheduler_queue'].strip(),
            'Successful capture cannot contain queued or blocked jobs')
        require(m.get('captured_metadata_bytes')==sum(entry['bytes'] for entry in m['files'].values()),'Capture byte total')
        return m

    def registration(self):
        self.p=self.copied('program.json');p=self.p
        require(digest(canonical(p))==digest(read_bytes(self.local(CAMPAIGN+'/program.json')))==PROGRAM_SHA,
            'Pinned registered V61 program changed')
        equal(self.copied('registration.json'),dict(program_sha256=PROGRAM_SHA),'Registration binding')
        require(p['directory']==DIRECTORY and p['registered_source_commit']==SOURCE_COMMIT,'Program path/source commit')
        require(read_bytes(self.local(LAUNCH+'/source-commit.txt')).decode().strip()==SOURCE_COMMIT,'Launch commit')
        jobs=[line.split('\t') for line in read_bytes(self.local(LAUNCH+'/jobs.tsv')).decode().splitlines()]
        require([x[0] for x in jobs]==['register',*ORDER,'audit','postrun'] and all(len(x)==2 and x[1].isdigit() for x in jobs),'Nine-stage launch census/order')
        self.jobs=dict(jobs);require(len(set(self.jobs.values()))==9,'Duplicate job ID')
        require(p['registration_job']==self.jobs['register'],'Registration job')
        require(len(p['sources'])==432,'Exactly432 frozen sources required')
        for name,expected in p['sources'].items():
            local=info(read_bytes(safe(self.repo,name)))
            require(local['sha256']==expected,'Local registered source changed: '+name)
            self.bind(REMOTE+'/'+name,local)
        for entry in p['inputs'].values(): self.bind(entry['path'],entry)
        old=self.input('v59_program')
        require(len(old['sources'])==412 and all(p['sources'].get(k)==v for k,v in old['sources'].items()),'V59 frozen source preservation')
        extra={str(path.relative_to(self.repo)) for path in (self.repo/'research_v61').iterdir()
               if path.is_file() and (path.suffix=='.py' or path.name=='PROTOCOL.txt')}
        extra.add('cluster_setup/v61_pipeline.sh')
        require(set(p['sources'])==set(old['sources'])|extra,'Exact source census including all V61 implementation')
        check=self.input('software_checks')
        require(p['inputs']['software_checks']['sha256']==SOFTWARE_SHA,'Pinned software receipt')
        modules=literal_assignment(self.repo/'research_v61/checks.py','MODULES')
        require(check['status']=='passed' and type(check['tests']) is int and check['tests']==205
            and type(check['skipped']) is int and check['skipped']==0 and check['modules']==list(modules)
            and check['real_model_inference'] is False and check['source_and_runtime_unchanged'] is True,'Complete205/0 software gate')
        equal(check['sources'],p['sources'],'Software sources');equal(check['runtime'],p['runtime'],'Software runtime')
        self.jobs['checks']=check['slurm_job_id']
        require(len(set(self.jobs.values()))==10,'Ten distinct software/launch jobs required')
        equal(self.jobs,JOBS,'Frozen launch job IDs')
        logs=[LAUNCH+'/'+label+'-'+jid+'.log' for label,jid in self.jobs.items() if label!='checks']
        logs.append('continuation-v61-software-20261014-a/checks-'+self.jobs['checks']+'.log')
        require(all(name in self.manifest['files'] for name in logs),'All ten scheduler logs must be copied')
        self.scheduler()
        histories=self.manifest['historical_ledger_bindings']
        require(set(histories)=={REMOTE+'/'+name for name in p['historical_ledgers']},'Historical ledger census')
        for name,expected in p['historical_ledgers'].items():
            remote=REMOTE+'/'+name;data=read_bytes(self.path(remote));entry=histories[remote]
            require(digest(data)==expected and entry['expected_sha256']==expected and entry['verified'] is True
                and entry['observed_bytes']==len(data) and entry['archive_file']==self.manifest['repository_paths'][remote],
                'Historical ledger unchanged binding: '+name)
        self.prior()
        paths=sorted((self.repo/'src').glob('*.py'))+sorted((self.repo/'scripts').glob('run_*.py'))
        sources={str(path.relative_to(self.repo)):digest(read_bytes(path)) for path in paths}
        require(len(sources)==158 and all(p['sources'].get(k)==v for k,v in sources.items()),'Complete158 ledger source subset')
        raw=read_bytes(self.local(CAMPAIGN+'/budget/ledger.json'))
        self.ledger,self.snapshot=validate_ledger(raw,sources)
        self.bind(DIRECTORY+'/budget/ledger.json',info(raw))

    def prior(self):
        p=self.p
        for key,wanted in (('v59_program',V59_PROGRAM),('v59_completion',V59_COMPLETION),('v59_audit',V59_AUDIT),
                           ('v59_candidate_target',V59_TARGET),('v59_candidate_model',V59_MODEL)):
            require(p['inputs'][key]['sha256']==wanted,'Frozen V59 identity: '+key)
        old,c,a=(self.input(k) for k in ('v59_program','v59_completion','v59_audit'))
        equal(self.input('v59_registration'),dict(program_sha256=V59_PROGRAM),'V59 registration')
        require(c['status']=='complete' and c['valid_diagnostic'] is True and c['development_guards_pass'] is True
            and a['status']=='verified' and a['development_guards_pass'] is True and a['checked_losses']==40
            and a['complete_stages']==24 and a['actual_candidate_model_sha256']==V59_MODEL
            and a['candidate_target_sha256']==V59_TARGET,'Frozen passed V59 audit/quality extent')
        equal(a['summary'],c['summary'],'V59 quality summary');equal(old['runtime'],p['runtime'],'Inherited runtime')
        # Recompute the already exposed V59 candidate/sequential point ratio.
        losses=c['quality']; totals={label:math.fsum(r['nll_sum'] for r in rows) for label,rows in losses.items()}
        for label,rows in losses.items():
            require(len(rows)==8 and all(r['predictions']==127 and math.isfinite(r['nll_sum']) for r in rows),'Frozen exposed loss extent')
            require(math.isclose(c['summary']['totals'][label]['nll_sum'],totals[label],rel_tol=1e-14),'Frozen raw loss arithmetic')
        candidate='full_precision_anchor';seq='sequential'
        pooled=(totals[candidate]-totals[seq])/1016
        maximum=max((r['nll_sum']-s['nll_sum'])/127 for r,s in zip(losses[candidate],losses[seq]))
        require(pooled<=math.log(1.05) and maximum<=math.log(1.20),'Frozen V59 guards')
        v54=self.input('v54_program')
        for key in ('records','record_provenance','deletion_order'): equal(p[key],v54[key],'Frozen C4 root '+key)
        equal(old['retained_records'],p['records'][-6:],'V59 exact final-six membership')
        self.base=self.input('v59_base_target');self.calibration=self.input('v59_candidate_target')
        require(self.base['recipe']['original_token_count']==1664 and len(self.base['stages'])==24,'Base target extent')
        exclusions=self.input('historical_exclusions')['excluded_from_future_confirmation_ids']
        require(len(set(exclusions))==60,'Sixty preserved quality exclusions')
        equal(exclusions,c['excluded_from_future_confirmation_ids'],'V59 exclusions')
        self.v59_summary=c['summary']

    def worker(self,trial,prefix):
        root=trial+'/';p=self.p
        tx=self.copied(root+'transaction.json');plan=self.copied(root+'plan.json');identity=self.copied(root+'worker/identity.json')
        command=[REMOTE+'/.venv-container/bin/python','-B','-m','research_v61.worker',DIRECTORY+'/'+root+'plan.json']
        equal(plan,dict(trial=trial,program=DIRECTORY+'/program.json',program_sha256=PROGRAM_SHA,
            output=DIRECTORY+'/'+root+'outputs',slurm_job_id=self.jobs[trial]),'Literal worker plan')
        require(tx['slurm_job_id']==self.jobs[trial],'Transaction job');integer(tx['elapsed_ns'],'Transaction time',1)
        equal(identity['identity'],dict(campaign_sha256=PROGRAM_SHA,trial=trial),'Worker protocol identity')
        require(set(identity)=={'schema','identity','command','cwd','limits','phase_budget'}
            and identity['schema']=='limited-worker-identity-v1','Worker identity schema')
        equal(identity['command'],command,'Worker literal argv');require(identity['cwd']==REMOTE,'Worker cwd')
        equal(identity['phase_budget'],dict(binding_sha256=self.snapshot['binding_sha256'],phase='feasibility',directory=DIRECTORY+'/budget'),'Worker phase binding')
        cpu,wall=TRIALS[trial];limits=identity['limits']
        affinity=limits['affinity_cpus'];require(type(affinity) is list and len(affinity)==1,'Single CPU affinity')
        integer(affinity[0],'Affinity CPU')
        equal(limits,dict(cpu_seconds=cpu,wall_seconds=wall,address_space_bytes=16*2**30,file_size_bytes=2*2**30,
            threads=1,termination_grace_seconds=1,affinity_cpus=affinity),'Worker limits')
        sealed=self.copied(root+'worker/result.json')
        require(sealed['schema']=='limited-worker-record-v1' and sealed['status']=='complete'
            and sealed['no_shell'] is True and sealed['identity_sha256']==digest(canonical(identity))
            and sealed['attempt']=='attempt-0001','One-use sealed attempt')
        equal(sealed,self.copied(root+'worker/attempt-0001/status.json'),'Terminal seal/status')
        equal(sealed['limits'],limits,'Sealed limits');equal(sealed['worker_identity'],identity['identity'],'Sealed identity')
        equal(sealed['outcome'],tx['worker_outcome'],'Transaction/seal outcome')
        require(sealed['outcome']['status']=='complete' and type(sealed['outcome']['returncode']) is int
            and sealed['outcome']['returncode']==0,'Worker did not complete')
        integer(sealed['outcome']['elapsed_wall_ns'],'Worker wall elapsed',1)
        require(type(sealed['artifacts']) is dict and set(sealed['artifacts'])=={'budget-reservation.json','limits-applied.json',
            'pre-settlement-observation.json','request.json','stderr-summary.json','stdout-summary.json'},'Complete sealed artifact census')
        for name,entry in sealed['artifacts'].items(): self.bind(DIRECTORY+'/'+root+'worker/attempt-0001/'+name,entry)
        request=self.copied(root+'worker/attempt-0001/request.json');ack=self.copied(root+'worker/attempt-0001/limits-applied.json')
        require(set(request)=={'command','cwd','limits','ack_path'} and
            request['ack_path']==DIRECTORY+'/'+root+'worker/attempt-0001/limits-ack.pending.json','Worker acknowledgment path')
        equal(request['command'],command,'Executed argv');equal(request['limits'],limits,'Executed limits');require(request['cwd']==REMOTE,'Executed cwd')
        equal(ack,sealed['limits_applied'],'Applied limits seal');require(ack['request_sha256']==digest(canonical(request)),'Request acknowledgment')
        for key,value in dict(cpu_seconds=[cpu,cpu+1],address_space=[16*2**30]*2,file_size=[2*2**30]*2,
                affinity_cpus=affinity,thread_environment={name:'1' for name in THREADS}).items(): equal(ack[key],value,'Applied '+key)
        integer(sealed['worker_pid'],'Worker PID',1)
        equal(ack['pid'],sealed['worker_pid'],'Acknowledged PID');equal(ack['process_group'],sealed['worker_pid'],'Acknowledged process group')
        validate_seal_observations(identity,sealed,self.copied(root+'worker/attempt-0001/budget-reservation.json'),
            self.copied(root+'worker/attempt-0001/pre-settlement-observation.json'),DIRECTORY+'/'+root+'worker/attempt-0001')
        usage=sealed['resource_usage']
        for key in ('user_cpu_ns','system_cpu_ns','total_cpu_ns'): integer(usage[key],key)
        require(usage['total_cpu_ns']==usage['user_cpu_ns']+usage['system_cpu_ns'],'CPU sum')
        debit=sealed['budget_debit'];validate_debit(debit,cpu+2)
        require(debit['observed_cpu_ns']==usage['total_cpu_ns'] and sealed['budget_reservation_overrun'] is False,'Observed debit')
        key=sealed['budget_attempt_id'];require(key not in prefix,'Duplicate attempt debit')
        equal(self.ledger['attempts'].get(key),debit,'Ledger/seal debit')
        prefix[key]=debit
        snapshot=dict(binding_sha256=self.snapshot['binding_sha256'],phase_cpu_seconds={'feasibility':CAP},
            charged_cpu_seconds={'feasibility':sum(v['charged_cpu_seconds'] for v in prefix.values())},attempts=copy.deepcopy(prefix),over_cap={'feasibility':False})
        equal(tx['budget'],snapshot,'Transaction exact prefix ledger')
        c=self.copied(root+'outputs/completion.json')
        require(c['schema']=='complete-full-precision-service-worker-v61' and c['trial']==trial and c['status']=='complete'
            and c['complete_model'] is True and c['program_sha256']==PROGRAM_SHA and c['slurm_job_id']==self.jobs[trial]
            and c['confirmation'] is False and c['quality_evaluation'] is False
            and c['partial_artifacts_are_not_a_committed_complete_model'] is False
            and c['v59_final_model_actual_bytes_equal'] is (None if trial=='prepare' else True),'Complete worker binding/scope')
        equal(c['source_sha256'],p['sources'],'Worker frozen sources')
        require(set(c['artifacts'])==expected_artifacts(trial),'Complete worker output artifact census')
        for name,entry in c['artifacts'].items():
            require(entry['file']==name and set(entry)=={'file','bytes','sha256'},'Output artifact metadata')
            self.bind(DIRECTORY+'/'+root+'outputs/'+name,entry)
        require(c['calibration_target_sha256']==V59_TARGET and c['base_target_sha256']==digest(canonical(self.base)),'Worker target link')
        integer(c['worker_elapsed_ns'],'Worker completion time',1);integer(c['context_elapsed_ns'],'Context time',1)
        require(c['context_elapsed_ns']<=c['worker_elapsed_ns']<=tx['elapsed_ns'],'Worker/context/transaction clocks')
        self.completions[trial],self.transactions[trial],self.seals[trial]=c,tx,sealed
        self.execution(trial)
        self.admissions(trial)
        self.progress[trial]=self.check_progress(trial)

    def execution(self,trial):
        c=self.completions[trial];execution=self.copied(trial+'/outputs/execution-provenance.json')
        require(digest(canonical(execution))==c['execution_provenance_sha256'],'Execution sidecar commitment')
        require(execution['schema']=='full-precision-source-execution-binding-v61'
            and execution['target_sha256']==c['service_target_sha256']
            and execution['anchor_target_sha256']==c['base_target_sha256']
            and execution['calibration_target_sha256']==V59_TARGET
            and execution['provider_sha256']==self.p['sources']['research_v61/features.py'],'Original teacher provenance')
        equal(execution['teacher_stages'],self.calibration['teacher_stages'],'Immutable teacher stages')
        require(digest(canonical(execution['decoder']))==self.calibration['decoder_sha256']
            and digest(canonical(execution['implementation']))==self.calibration['implementation_manifest_sha256'],'Finite decoder identity')
        expected_files={Path(self.p['inputs'][key]['path']).name:self.p['inputs'][key]['sha256'] for key in ('checkpoint_config','checkpoint_weights')}
        equal(execution['checkpoint']['files_sha256'],expected_files,'Checkpoint provenance')
        if trial=='prepare': self.execution_value=execution
        else: equal(execution,self.execution_value,'Common execution context across all six workers')
        kernel=c['shared_primal_kernel'];require(kernel['backend']=='normal_neighbor_primal_v50'
            and kernel['wrapper_sha256']==self.p['sources']['research_v50/neighbors.py'],'Shared frozen primal backend')
        if trial=='prepare': self.kernel=kernel
        else:
            for key in ('backend','source_sha256','original_c_source_sha256','wrapper_sha256','flags'):
                equal(kernel[key],self.kernel[key],'Common kernel '+key)

    def expected_admission(self,tokens,rep,target):
        request=next(r for r in self.p['shape_admission']['requests'] if r['tokens']==tokens and r['representation']==rep)
        stages=copy.deepcopy(request['stages'])
        for row in stages: row.pop('reserved_fallback',None);row['target_sha256']=target
        return dict(stages=stages,reserved_work_units=request['work_units_including_fallback'],replay_all_ancestors_reserved=True,
            maximum_fallback_neural_stage_record_pairs=24*(tokens//128) if rep=='compressed48' else 0,
            resident_reservation_bytes=4*2**30,process_address_space_cap=16*2**30)

    def admissions(self,trial):
        target=self.completions[trial]['service_target_sha256']
        actual=self.copied(trial+'/outputs/admission.json')
        expected=[dict(retained=n,representation=rep,**self.expected_admission(n*128,rep,target)) for n in (13,12,6) for rep in REPS]
        equal(actual,expected,'Complete nine-request admission before feature work')
        if trial in ARMS:
            for step,n in zip(self.completions[trial]['steps'],(12,6)):
                equal(step['admission'],self.expected_admission(n*128,ARMS[trial],target),'Recorded request admission')

    def check_progress(self,trial):
        c=self.completions[trial];rows=self.p['records'];expected=[]
        def event(phase,**fields): expected.append(dict(phase=phase,**fields))
        event('context_ready',component_elapsed_ns=c['context_elapsed_ns'],target_sha256=c['service_target_sha256'])
        def sources(records):
            for row in records: event('source_replayed',record_id=row['id'])
        def stages(timing,retained=None):
            data=timing['stages'];require(len(data)==24,'Complete24 stage telemetry')
            replay=False
            for item,base in zip(data,self.base['stages']):
                require(item['stage_id']==base['stage_id'],'Stage telemetry order')
                integer(item['elapsed_ns'],'Stage time',1)
                commitment(dict(bytes=1,sha256=item['code_sha256']))
                require(type(item['fallback']) is bool,'Fallback must be boolean')
                if item['fallback'] and not replay:
                    require(trial=='compressed' and retained is not None,'Undeclared fallback')
                    sources(retained);replay=True
                fields={k:v for k,v in item.items() if k not in ('admission','solver','elapsed_ns')}
                event('stage_certified',component_elapsed_ns=item['elapsed_ns'],**fields)
            return replay
        def payloads():
            for rep in REPS:
                for base in self.base['stages']: event('payload_stage',stage_id=base['stage_id'],representation=rep)
        if trial=='prepare':
            require(c['steps']==[] and c['code_count']==42467328,'Preparation extent')
            sources(rows);stages(c['preparation']['common_timing']);payloads()
            require(c['preparation']['common_timing']['neural_stage_record_pairs']==312,'Preparation source traversal extent')
        else:
            require(len(c['steps'])==2,'Two actual successions required')
            for index,(step,n) in enumerate(zip(c['steps'],(12,6)),1):
                retained=rows[-n:];deleted=rows[:1] if index==1 else rows[1:7]
                equal(step['retained_ids'],[r['id'] for r in retained],'Retained IDs')
                require(step['step']==index,'Step ordinal')
                if trial in ('oracle','cold'): sources(retained)
                elif trial=='hybrid': sources(deleted)
                if trial=='cold':
                    for base in self.base['stages']: event('payload_stage',stage_id=base['stage_id'],representation='lossless')
                replay=stages(step['timing'],retained)
                expected_pairs=24*(n if trial in ('oracle','cold') or replay else len(deleted) if trial=='hybrid' else 0)
                require(step['timing']['neural_stage_record_pairs']==expected_pairs,'Source access/replay count')
                if trial=='oracle':
                    require(step['prior_state_read'] is False and step['independent_retained_token_traversal'] is True,'Independent oracle route')
                    payloads()
                else:
                    equal(step['deleted_ids'],[r['id'] for r in deleted],'Deletion IDs')
                    require(step['representation']==ARMS[trial] and step['audit_history_physically_retained'] is True,'Representation/history scope')
                    integer(step['request_elapsed_ns'],'Request time',1)
                    event('request_complete',step=index,request_elapsed_ns=step['request_elapsed_ns'])
        names=sorted(name for name in self.manifest['files'] if name.startswith(CAMPAIGN+'/'+trial+'/outputs/progress-') and name.endswith('.json'))
        wanted=[CAMPAIGN+'/'+trial+f'/outputs/progress-{i:04d}.json' for i in range(len(expected))]
        require(names==wanted,'Exact progress file census: '+trial)
        previous=-1
        for name,fields in zip(names,expected):
            actual=self.json(name);clock=actual.pop('elapsed_ns')
            integer(clock,'Progress clock');require(previous<=clock<=c['worker_elapsed_ns'],'Progress clock order/extent');previous=clock
            equal(actual,fields,'Progress contents/order: '+name)
        return len(expected)

    def audits(self):
        a=self.json(CAMPAIGN+'/artifact-audit.json');b=self.json(CAMPAIGN+'/postrun-audit.json')
        primary_expected=copy.deepcopy(self.expected)
        inventory_equal(a['inputs'],primary_expected,'Complete primary audit Inputs')
        post_expected=dict(primary_expected)
        post_expected[DIRECTORY+'/artifact-audit.json']=info(read_bytes(self.local(CAMPAIGN+'/artifact-audit.json')))
        inventory_equal(b['inputs'],post_expected,'Complete postrun audit Inputs')
        for label,value,schema,job in (
            ('primary',a,'complete-full-precision-service-artifact-audit-v61','audit'),
            ('postrun',b,'complete-full-precision-service-additive-artifact-audit-v61','postrun')):
            require(value['schema']==schema and value['status']=='verified' and value['campaign']==DIRECTORY
                and value['program_sha256']==PROGRAM_SHA and value['slurm_job_id']==self.jobs[job]
                and value['analysis_outside_empirical_worker_ledger'] is True,label+' audit identity/accounting scope')
            integer(value['analysis_cpu_ns'],label+' audit CPU');integer(value['analysis_elapsed_ns'],label+' audit wall',1)
        require(a['all_declared_artifacts_rehashed'] is True and b['frozen_sources_changed'] is False,'Audit completeness/source flag')
        require(b['frozen_audit_path']==DIRECTORY+'/artifact-audit.json'
            and b['frozen_audit_sha256']==post_expected[DIRECTORY+'/artifact-audit.json']['sha256'],'Supplemental primary-byte link')
        equal(a['source_sha256'],self.p['sources'],'Primary source inventory');equal(a['runtime'],self.p['runtime'],'Primary runtime')
        equal(a['budget'],self.snapshot,'Primary exact settled budget');equal(b['ledger_snapshot'],self.snapshot,'Postrun exact settled budget')
        require(a['fresh_campaign_cpu_seconds']==self.snapshot['charged_cpu_seconds']['feasibility']
            and a['allowance_scope']==self.p['allowance_scope'],'Fresh CPU accounting')
        implementation={path.name:info(read_bytes(path)) for path in sorted((self.repo/'research_v61').glob('*.py'))}
        inventory_equal(b['implementation'],implementation,'Postrun implementation census')
        for key,value in dict(complete_model=True,successive_deletions=2,original_tokens=1664,retained_tokens=[1536,768],
                quality_evaluation=False,confirmation=False,population_claims=False,acl_ready=False,
                all_final_six_models_equal_actual_v59_candidate=True,calibration_target_sha256=V59_TARGET,
                v59_final_model_sha256=V59_MODEL,shared_checkpoint_bytes=self.p['shared_checkpoint_bytes']).items():
            equal(a[key],value,'Primary result scope '+key)
        evidence=b['evidence']
        target_hash=self.completions['prepare']['service_target_sha256']
        for key,value in dict(anchor_target_sha256=digest(canonical(self.base)),fixed_target_sha256=target_hash,
                calibration_target_sha256=V59_TARGET,v59_final_model_sha256=V59_MODEL,
                all_final_six_models_equal_actual_v59_candidate=True,checkpoint_bytes=self.p['shared_checkpoint_bytes'],
                original_model_sha256=self.artifact('prepare','original-model.bin')['sha256']).items():
            equal(evidence[key],value,'Postrun target/model commitment '+key)
        self.check_service_manifest(target_hash)
        self.comparison_claims(a,evidence)
        self.timings(a,evidence)
        self.audit_records=dict(primary=info(read_bytes(self.local(CAMPAIGN+'/artifact-audit.json'))),
            postrun=info(read_bytes(self.local(CAMPAIGN+'/postrun-audit.json'))))
        # The collector repeats each complete inventory to make omissions visible.
        declarations=self.manifest['audit_input_inventories']
        require(set(declarations)=={'primary','postrun'},'Both collector audit inventories required')
        for key,receipt in (('primary',a),('postrun',b)):
            inventory_equal(declarations[key]['inputs'],receipt['inputs'],'Collector '+key+' input inventory')
        inventory_equal(self.manifest['expected_input_commitments'],post_expected,'Collector complete expected inputs')
        for remote,entry in self.manifest['inputs_not_copied'].items():
            if remote in self.missing: continue
            require(remote.startswith(DIRECTORY+'/') and Path(remote).suffix=='.lock'
                and entry.get('kind')=='unselected_file' and entry.get('status')=='NOT revalidated'
                and entry.get('binary_contents_read') is False and entry.get('exists') is True and 'expected' not in entry,
                'Unexpected omitted metadata or numerical binary: '+remote)
        require(set(self.missing)=={remote for remote in post_expected if Path(remote).suffix in BINARY_SUFFIXES},
            'Exact absent numerical binary census')
        self.primary,self.postrun=a,b

    def scheduler(self):
        rows={}
        for line in self.manifest['scheduler'].splitlines():
            if not line.strip(): continue
            fields=line.split('|')
            if fields[-1]=='': fields.pop()
            require(len(fields)==8 and fields[0] in JOBS.values() and fields[0] not in rows,'Scheduler census/columns')
            state=fields[2].split()[0].rstrip('+')
            require(state=='COMPLETED' and fields[3]=='0:0','Every V61 job must complete successfully')
            require(fields[4].isdigit(),'Scheduler elapsed integer')
            rows[fields[0]]=dict(job_name=fields[1],state=state,raw_state=fields[2],exit_code=fields[3],
                elapsed_seconds=fields[4],total_cpu=fields[5],start=fields[6],end=fields[7])
        equal(rows,self.manifest['scheduler_jobs'],'Raw scheduler receipt/parsed records')
        require(set(rows)==set(JOBS.values()),'All ten scheduler jobs required')
        self.scheduler_rows=rows

    def artifact(self,trial,name): return commitment(self.completions[trial]['artifacts'][name])

    def check_service_manifest(self,target_hash):
        # Evaluate only literal top-level contract constants; no module imports.
        env={}
        for node in ast.parse(read_bytes(self.repo/'research_v61/target.py')).body:
            if not isinstance(node,ast.Assign) or len(node.targets)!=1 or not isinstance(node.targets[0],ast.Name): continue
            name=node.targets[0].id
            if name not in ('SCHEMA','FAMILY','STATE_SCHEMA','FEATURE_RULE','ANCHOR_RULE','SERVICE_CONTRACT'): continue
            if name!='SERVICE_CONTRACT': env[name]=ast.literal_eval(node.value)
            else:
                require(isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name)
                    and node.value.func.id=='dict' and not node.value.args,'Static service contract form')
                env[name]={kw.arg:(env[kw.value.id] if isinstance(kw.value,ast.Name) else ast.literal_eval(kw.value))
                           for kw in node.value.keywords}
        service=dict(env['SERVICE_CONTRACT'],anchor_target_sha256=digest(canonical(self.base)),
            calibration_target=self.calibration,calibration_target_sha256=V59_TARGET,
            decoder_sha256=self.calibration['decoder_sha256'],implementation_manifest_sha256=self.calibration['implementation_manifest_sha256'],
            provider_sha256=self.p['sources']['research_v61/features.py'],constructor_source_sha256=self.p['sources']['research_v61/target.py'])
        require(digest(canonical(service))==target_hash and target_hash!=V59_TARGET,'Distinct source-bound V61 service target')

    def comparison_claims(self,a,evidence):
        def indexed(rows):
            require(type(rows) is list and len(rows)==8,'Eight comparisons required')
            result={(r['trial'],r['step']):r for r in rows}
            require(len(result)==8 and set(result)=={(trial,step) for trial in ARMS for step in (1,2)},'Exact comparison pair census')
            return result
        primary,post=indexed(a['comparisons']),indexed(evidence['comparisons'])
        v59meta=self.input('v59_candidate_metadata')
        for trial,rep in ARMS.items():
            for step,n,deleted in ((1,12,1),(2,6,6)):
                state=self.artifact(trial,f'step-{step}-state.bin');model=self.artifact(trial,f'step-{step}-model.bin')
                trust=self.artifact(trial,f'step-{step}-trust.json')
                equal(state,self.artifact('oracle',f'step-{step}-{rep}.bin'),'State equality receipt commitments')
                equal(trust,self.artifact('oracle',f'step-{step}-{rep}-trust.json'),'Trust sidecar equality')
                equal(model,self.artifact('oracle',f'step-{step}-model.bin'),'Model equality receipt commitments')
                require(model['bytes']==21233664,'Complete packed-model extent')
                if step==2: require(model['sha256']==V59_MODEL,'Final-six V59 model commitment')
                expected=dict(trial=trial,step=step,representation=rep,state_sha256=state['sha256'],state_bytes=state['bytes'],
                    complete_model_sha256=model['sha256'],code_count=42467328,stages=24,retained_records=n,retained_tokens=n*128,
                    deleted_count=deleted,actual_bytes_equal=True,actual_model_bytes_equal=True,exact_retained_membership_verified=True,
                    v59_quality_anchor_actual_bytes_equal=True if step==2 else None)
                for key,value in expected.items():
                    equal(primary[trial,step][key],value,'Primary comparison '+key)
                    equal(post[trial,step][key],value,'Postrun comparison '+key)
                require(primary[trial,step]['independently_regenerated_features_verified_here'] is False
                    and primary[trial,step]['independent_fresh_source_execution_witnessed'] is True,'Oracle evidence boundary')
                for key in ('model_export_matches_state_codes','cross_representation_target_and_model_verified','registered_record_binding_verified'):
                    require(post[trial,step][key] is True,'Postrun binary audit claim '+key)
                row=self.completions[trial]['steps'][step-1]
                actual_storage=storage(row,state,trust,self.p['shared_checkpoint_bytes'])
                equal(post[trial,step]['storage'],actual_storage,'Postrun storage arithmetic')
                oracle_row=self.completions['oracle']['steps'][step-1]
                for key in ('state_bytes','trust_bytes'): equal(oracle_row['representations'][rep][key],actual_storage[key],'Oracle storage')
                stage_rows=row['timing']['stages'];oracle_stages=oracle_row['timing']['stages']
                equal([r['code_sha256'] for r in stage_rows],[r['code_sha256'] for r in oracle_stages],'Complete ordered stage-code commitments')
                if step==2: equal([r['code_sha256'] for r in stage_rows],[r['sha256'] for r in v59meta['stages']],'V59 ordered stage-code commitments')
        prep=self.completions['prepare']['preparation']
        require(set(prep['representations'])==set(REPS) and set(evidence['original_storage'])==set(REPS),'Original representation census')
        for rep in REPS:
            actual=storage(prep['representations'][rep],self.artifact('prepare',rep+'-original.bin'),
                self.artifact('prepare',rep+'-trust.json'),self.p['shared_checkpoint_bytes'])
            equal(evidence['original_storage'][rep],actual,'Original storage arithmetic')

    def timings(self,a,evidence):
        prep=self.completions['prepare'];preparation=prep['preparation']
        equal(a['preparation'],preparation,'Preparation receipt')
        common=prep['context_elapsed_ns']+sum(integer(preparation[key],key) for key in ('common_source_ns','common_original_model_ns','common_disposal_ns'))
        expected={}
        for trial,rep in ARMS.items():
            c=self.completions[trial];requests=[s['request_elapsed_ns'] for s in c['steps']]
            own=integer(preparation['representations'][rep]['representation_elapsed_ns'],'Representation preparation')
            require(sum(requests)<=c['worker_elapsed_ns'],'Request clock containment')
            expected[trial]=dict(representation=rep,context_elapsed_ns=c['context_elapsed_ns'],request_elapsed_ns=requests,
                worker_elapsed_ns=c['worker_elapsed_ns'],transaction_elapsed_ns=self.transactions[trial]['elapsed_ns'],
                worker_outside_request_ns=c['worker_elapsed_ns']-sum(requests),attributed_preparation_ns=common+own,
                attributed_two_deletion_lifetime_ns=common+own+self.transactions[trial]['elapsed_ns'],
                live_state_bytes=[s['state_bytes']+s['trust_bytes'] for s in c['steps']],
                complete_deployment_bytes=[s['complete_deployment_bytes'] for s in c['steps']],max_rss_kib=c['max_rss_kib'],
                replay_neural_stage_record_pairs=[s['timing']['neural_stage_record_pairs'] for s in c['steps']],
                fallback_stages=[[r['stage_id'] for r in s['timing']['stages'] if r['fallback']] for s in c['steps']])
            for key,value in expected[trial].items(): equal(a['timings'][trial][key],value,'Timing/storage receipt '+trial+'/'+key)
        require(set(a['timings'])==set(ARMS) and set(a['ratios'])=={'cached','hybrid','cold'},'Timing/control census')
        for control in ('cached','hybrid','cold'):
            compressed,other=expected['compressed'],expected[control]
            ratios=dict(compressed_over_control_request_time=[x/y for x,y in zip(compressed['request_elapsed_ns'],other['request_elapsed_ns'])],
                compressed_live_state_saving=[1-x/y for x,y in zip(compressed['live_state_bytes'],other['live_state_bytes'])],
                compressed_deployment_saving=[1-x/y for x,y in zip(compressed['complete_deployment_bytes'],other['complete_deployment_bytes'])],
                compressed_over_control_observed_lifetime=compressed['attributed_two_deletion_lifetime_ns']/other['attributed_two_deletion_lifetime_ns'])
            equal(a['ratios'][control],ratios,'Observed ratio arithmetic '+control)
        for key,value in dict(preparation_worker_ns=prep['worker_elapsed_ns'],preparation_transaction_ns=self.transactions['prepare']['elapsed_ns'],
                oracle_worker_ns=self.completions['oracle']['worker_elapsed_ns']).items(): equal(a[key],value,'Clock '+key)

    def run(self):
        self.collection();self.registration()
        prefix={}
        for trial in ORDER: self.worker(trial,prefix)
        equal(prefix,self.ledger['attempts'],'No missing or extra worker debit')
        self.audits()
        # A local file changing after the initial census cannot be silently
        # accepted as the same copied evidence bundle.
        for name,entry in self.manifest['files'].items():
            equal(info(read_bytes(self.local(name))),commitment(entry),'Final copied metadata rehash: '+name)
        return dict(schema='portable-full-precision-service-terminal-metadata-check-v61',status='verified_metadata_only',
            program_sha256=PROGRAM_SHA,registered_numerical_commit=SOURCE_COMMIT,source_files_checked=432,
            software_tests=205,software_skips=0,worker_receipts=6,comparison_claims_checked=8,
            audit_receipts=self.audit_records,charged_worker_cpu_seconds=self.snapshot['charged_cpu_seconds']['feasibility'],
            phase_cap_cpu_seconds=CAP,observed_worker_cpu_ns=sum(s['resource_usage']['total_cpu_ns'] for s in self.seals.values()),
            source_local_progress_events=self.progress,all_required_metadata_present=True,missing_metadata=[],
            scheduler_jobs=self.scheduler_rows,historical_ledgers_verified=len(self.p['historical_ledgers']),
            required_inputs_checked=len(self.verified),numerical_binaries_not_revalidated=self.missing,
            metadata_claims_link_final_six_models_to_v59=True,calibration_target_sha256=V59_TARGET,v59_model_sha256=V59_MODEL,
            local_actual_model_or_state_equality_verified=False,local_neural_reconstruction=False,
            local_runtime_binaries_verified=False,quality_evaluation=False,confirmation=False,acl_ready=False,
            timings=self.primary['timings'],ratios=self.primary['ratios'],
            caveats=['Actual numerical binaries remain on the cluster; this is receipt/metadata consistency only.',
                'Unsigned receipt hashes assume controlled trusted execution/storage; not hostile-storage authentication.',
                'One adaptive root and one fixed-order observation per request; no population or timing confidence claim.',
                'V59 exposed quality is inherited only through recorded actual-byte-equality audits; no new quality evaluation.',
                'Common preparation attribution is the frozen reporting convention, not a new standalone lifecycle measurement.',
                'Audit CPU is outside the six-worker ledger; scheduler charges must be reported separately.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=Check(args.directory,args.repo).run()
    raw=canonical(result)
    if args.output:
        with args.output.open('xb') as stream: stream.write(raw)
    print(raw.decode())


if __name__=='__main__': main()
