"""Prospective V69 registration and actual predecessor admission.

No submission command. A separate launcher must bind held Slurm job IDs before
release. This module refuses absent registration, incomplete predecessors and
unsealed outputs; it never discovers substitute inputs or retries a phase.
"""
from pathlib import Path
import os,platform,sys
from research_v67.io import read,write,json_read,require,info
from research_v69 import execution_gate as gate
from src.run_store import canonical_json,digest,strict_json,read_completed
from src.phase_budget import PhaseBudget,read_budget_snapshot
from src.experiment_inventory import source_hashes

ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/untouched-quality-v69-20261016-a'
ORDER=tuple(gate.CAPS)
GROUPS={'service','candidates','quality','prefix','checkpoint','targets','snapshot','gpu_registration','v68_scheduler'}
SNAPSHOT_MANIFEST='8e4c3e790b7c1747f6fe114899240c6f14c10b8111f9d7df9f2a41d64e6f5d9d'
SNAPSHOT_ARCHIVE='c5cc19cde2e526bb3098efaec5c7709ac3714bd781f8753c1c5b77f6c4a67f2b'


def commitment(e):
    require(type(e) is dict and set(e)=={'path','bytes','sha256'},'Exact actual-file input binding required')
    p=Path(e['path']);require(p.is_absolute() and '..' not in p.parts,'Absolute canonical input path required')
    return {k:e[k] for k in ['bytes','sha256']}


def bound(e,*,maximum=64*2**20,retain=True):
    return read(e['path'],commitment(e),maximum=maximum,retain=retain)


def schema(p):
    require(set(p)=={'schema','directory','resources','inputs','new_sources','dependency_files',
        'historical_ledgers','runtimes','hosts','interpreters','software_modules','expected_tests','v68_sha256',
        'automatic_retry','registered','submission_policy','launch'},'Exact campaign field census required')
    require(p['schema']=='untouched-quality-campaign-v69' and p['directory']==str(RUN)
        and p['resources']==gate.design() and p['automatic_retry'] is False and p['registered'] is True
        and p['submission_policy']=='hold-bind-release-once-sequential-afterok',
        'Prospective once-only quality registration required')
    require(set(p['inputs'])==GROUPS and set(p['runtimes'])==set(p['hosts'])==set(p['interpreters'])=={'cpu','cuda'},
        'Complete input and separate runtime groups required')
    for kind in ['cpu','cuda']:
        interpreter=Path(p['interpreters'][kind])
        require(interpreter.is_absolute() and '..' not in interpreter.parts,'Absolute interpreter command required')
        hosts=p['hosts'][kind]
        require(type(hosts) is list and hosts==sorted(set(hosts)) and hosts
            and set(p['runtimes'][kind])==set(hosts),'Actual admitted host/runtime inventory required')
    require(p['hosts']['cpu']==['csis.mn1'],'Inherited CPU host required')
    require(type(p['software_modules']) is list and p['software_modules']==sorted(set(p['software_modules']))
        and 'research_v55.test_sequential' in p['software_modules']
        and all(n=='research_v55.test_sequential' or n.startswith('research_v69.test_') for n in p['software_modules'])
        and type(p['expected_tests']) is int and p['expected_tests']>=70,'Complete Linux checks, including V55, required')
    source_dir=RUN/'research_v69'
    require(type(p['new_sources']) is dict and p['new_sources']
        and all(Path(n).parent==source_dir and (Path(n).suffix=='.py' or Path(n).name in {'PROTOCOL.txt','README.txt','run_cpu.sbatch','run_gpu.sbatch'})
            for n in p['new_sources']),'Only staged V69 sources admitted as new')
    tests=sorted('research_v69.'+Path(n).stem for n in p['new_sources'] if Path(n).name.startswith('test_') and Path(n).suffix=='.py')
    require(p['software_modules']==sorted(['research_v55.test_sequential',*tests]),'Every staged V69 fixture must be registered')
    require({str(q) for q in source_dir.iterdir() if q.is_file()}==set(p['new_sources']),
        'Exact staged source file census required')
    from research_v69.submission import policy
    policy(p)
    return p


def load(expected):
    p=json_read(RUN/'program.json')
    require(digest(canonical_json(p))==expected and json_read(RUN/'registration.json')==
        dict(program_sha256=expected),'Actual immutable registration differs')
    return schema(p)


def inputs(p):
    from research_v69 import input_gate,production_gate
    entries=p['inputs']
    require(set(entries['service'])==input_gate.SERVICE_KEYS and set(entries['quality'])==input_gate.QUALITY_KEYS
        and set(entries['candidates'])=={'candidate_12','candidate_6'}
        and set(entries['targets'])=={'base','calibration'} and set(entries['snapshot'])=={'manifest','archive'},
        'Complete actual input census required')
    service={k:bound(e) for k,e in entries['service'].items()}
    candidates={k:bound(e,maximum=21233664) for k,e in entries['candidates'].items()}
    quality={k:bound(e) for k,e in entries['quality'].items()}
    prefix=bound(entries['prefix'],maximum=8*2**20)
    service_report=input_gate.service(service,candidates)
    quality_report=input_gate.quality(quality,prefix,registration_sha256=p['v68_sha256'])
    quality_costs=v68_costs(quality,bound(entries['v68_scheduler'],maximum=128*2**10).decode('ascii'))
    # Never rerun V68's live historical glob here: later quality metadata extends
    # that namespace. Bind its actually completed audit and selected bytes instead.
    checkpoint=production_gate.checkpoint(entries['checkpoint'])
    base,calibration=[bound(entries['targets'][k],maximum=8*2**20) for k in ['base','calibration']]
    target=production_gate.targets(base,calibration)
    require(entries['snapshot']['manifest']['sha256']==SNAPSHOT_MANIFEST
        and entries['snapshot']['archive']['sha256']==SNAPSHOT_ARCHIVE,
        'Original historical export identities required before fresh reference audit')
    manifest=bound(entries['snapshot']['manifest'],maximum=2*2**20)
    bound(entries['snapshot']['archive'],maximum=2*2**30,retain=False)
    production_gate.configuration(strict_json(manifest)['config'])
    old=strict_json(service['v67_program'])
    require(entries['checkpoint']=={Path(old['inputs'][k]['path']).name:old['inputs'][k]
        for k in ['checkpoint_config','checkpoint_weights']},'Inherited checkpoint paths/bytes differ')
    return dict(service=service,quality=quality,candidates=candidates,base=base,calibration=calibration,
        bound=target,root=strict_json(service['root_records'])['records'],
        records=strict_json(quality['records'])['records'],service_report=service_report,
        quality_report=quality_report,quality_costs=quality_costs,checkpoint=checkpoint)


def v68_costs(values,scheduler_text):
    from research_v69.cost_accounting import scheduler_rows
    from research_v68.data_runner import CAPS
    rows={k:strict_json(values[k]) for k in CAPS};jobs={k:v['job_id'] for k,v in rows.items()}
    scheduler=scheduler_rows(scheduler_text,jobs);result={}
    for phase,row in rows.items():
        cap=CAPS[phase];job=scheduler[phase]
        require(row['status']=='complete' and row['error'] is None and row['caps']==cap
            and job['state']=='COMPLETED' and job['exit_code']=='0:0','Complete V68 process and scheduler evidence required')
        clocks=[row[k] for k in ['process_cpu_ns','waited_child_cpu_ns','combined_observed_cpu_ns','elapsed_ns','max_rss_kib']]
        require(all(type(v) is int and v>=0 for v in clocks),'Integral nonnegative predecessor clocks required')
        own,child,total,elapsed,rss=clocks
        require(total==own+child and total<=(cap['cpu']+2)*10**9
            and job['total_cpu_ns']+job['reporting_quantum_ns']>=total
            and job['total_cpu_ns']<=(cap['cpu']+2)*10**9
            and elapsed<=(job['elapsed_seconds']+1)*10**9 and rss*1024<=4*2**30,
            'Actual V68 costs exceed admission or scheduler cannot contain them')
        result[phase]=dict(observed_process_tree_cpu_ns=total,scheduler=job,
            charged_cpu_seconds=max(1,(total+999999999)//10**9))
    require(sum(r['charged_cpu_seconds'] for r in result.values())<=1506,'V68 complete cost cap exceeded')
    return dict(status='verified_predecessor_costs',phases=result,
        scope='The three registered V68 processes and their scheduler allocations, not global project costs')


def verify(p,phase):
    schema(p);kind=gate.kind(phase);host=platform.node()
    require(sys.platform=='linux' and host in p['hosts'][kind]
        and sys.executable==p['interpreters'][kind],'Admitted Linux host and actual interpreter command required')
    x=inputs(p);entries=p['inputs']
    sources=gate.sources(x['service']['v67_program'],x['quality']['registration'],
        bound(entries['gpu_registration']),v68_sha256=p['v68_sha256'],new_sources=p['new_sources'])
    for group in ['dependency_files','historical_ledgers']:
        require(type(p[group]) is dict and bool(p[group]),'Bound inherited dependency/ledger census required')
        for path,e in p[group].items():read(path,e,maximum=128*2**20,retain=False)
    old=strict_json(x['service']['v67_program'])
    data=strict_json(x['quality']['registration']);dependencies=dict(old['dependency_files'])
    for path,e in data['tokenizer_runtime_files'].items():
        require(path not in dependencies or dependencies[path]==e,'Conflicting inherited dependencies')
        dependencies[path]=e
    require(p['dependency_files']==dependencies and data['base_runtime']==old['runtime']
        and p['historical_ledgers']==data['historical_ledgers'],
        'Complete frozen V67/V68 dependency, runtime and historical-ledger inventories required')
    runtime=gate.runtime(phase,p['runtimes'][kind][host],
        inherited_cpu_runtime=old['runtime'] if kind=='cpu' else None)
    return dict(x,registered_sources=sources,runtime=runtime)


def job(p,phase):
    require(phase in (*ORDER,'closure'),'Registered phase required')
    binding=json_read(RUN/phase/'job-binding.json')
    require(set(binding)=={'schema','registration_sha256','phase','job_id','submission_state'}
        and binding['schema']=='quality-held-job-binding-v69' and binding['phase']==phase
        and binding['registration_sha256']==digest(canonical_json(p))
        and type(binding['job_id']) is str and binding['job_id'].isdigit()
        and binding['submission_state']=='held-before-release',
        'Exclusive held-job identity must exist before release')
    return binding


def command(p,phase):
    require(phase in ORDER,'Registered phase required')
    # The inherited CPU runtime records the interpreter byte identity, not a
    # top-level executable path. CUDA records both. Preserve both schemas.
    kind=gate.kind(phase);executable=p['interpreters'][kind]
    require(Path(executable).is_absolute(),'Absolute interpreter required')
    if kind=='cuda':
        require(all(r['executable']['path']==executable for r in p['runtimes']['cuda'].values()),
            'CUDA interpreter command differs from bound runtime')
    return [executable,'-B',str(RUN/'research_v69/worker.py'),phase,digest(canonical_json(p))]


def budget_arguments(p):
    return dict(identity=dict(protocol_sha256=digest(canonical_json(p)),source_sha256=source_hashes(ROOT)),
        phase_cpu_seconds={'quality':gate.design()['worker_allowance_cpu_seconds']})


def budget(p):return PhaseBudget(RUN/'budget',**budget_arguments(p))
def snapshot(p):return read_budget_snapshot(RUN/'budget',**budget_arguments(p),max_attempts=8)


def worker_identity(p,phase,cpu,ledger):
    return dict(schema='limited-worker-identity-v1',identity=dict(registration_sha256=digest(canonical_json(p)),phase=phase),
        command=command(p,phase),cwd=str(ROOT),limits=gate.limits(phase,cpu).payload(),
        phase_budget=dict(binding_sha256=ledger['binding_sha256'],phase='quality',directory=str(RUN/'budget')))


def output_census(directory):
    """Stream all declared actual outputs; bound count and aggregate bytes."""
    directory=Path(directory);result={};total=0
    require(directory.is_dir() and not directory.is_symlink(),'Actual nonsymbolic output directory required')
    for path in sorted(directory.rglob('*')):
        require(not path.is_symlink(),'Symbolic output forbidden')
        if path.is_dir():continue
        require(len(result)<5000,'Output count exceeds fixed bound')
        e=read(path,maximum=64*2**20,retain=False);total+=e['bytes']
        require(total<=256*2**20,'Total output extent exceeds fixed bound')
        result[str(path.relative_to(directory))]=e
    require('completion.json' in result,'Actual phase completion required')
    return result


def finished(p,phase,*,active_attempt_id=None):
    """Bind actual outputs through completed controller, seal and settled debit.

    Scheduler final costs are deliberately deferred until post-exit closure.
    A self-asserted outputs/completion.json is never sufficient for admission.
    """
    from research_v69 import cost_accounting
    j=job(p,phase);e=json_read(RUN/phase/'entry.json');ledger=snapshot(p)
    require(e['schema']=='quality-controller-entry-v69' and e['phase']==phase
        and e['registration_sha256']==digest(canonical_json(p)) and e['job_id']==j['job_id']
        and e['status']=='complete' and e['error'] is None and e['whole_process_cpu_clock'] is True
        and e['all_waited_children_included'] is True,'Complete bound predecessor controller required')
    require(type(e['affinity_cpus']) is list and len(e['affinity_cpus'])==1,'One actually recorded CPU required')
    identity=worker_identity(p,phase,e['affinity_cpus'][0],ledger)
    checked=cost_accounting.worker(RUN/phase/'worker',identity,ledger,active_attempt_id=active_attempt_id)
    require(checked['worker_outcome'].get('status')=='complete' and checked['worker_outcome'].get('returncode')==0,
        'Successful actual predecessor worker required')
    actual=output_census(RUN/phase/'outputs')
    require(actual==e['outputs'],'Actual predecessor output bytes differ from completed controller')
    complete=json_read(RUN/phase/'outputs/completion.json',actual['completion.json'])
    require(complete['schema']=='quality-phase-worker-v69' and complete['phase']==phase
        and complete['registration_sha256']==digest(canonical_json(p))
        and complete['job_id']==j['job_id'] and complete['status']=='complete' and complete['error'] is None,
        'Complete actual predecessor phase required')
    return complete


def predecessors(p,phase,*,active_attempt_id=None):
    require(phase in ORDER,'Registered phase required')
    return {name:finished(p,name,active_attempt_id=active_attempt_id) for name in ORDER[:ORDER.index(phase)]}
