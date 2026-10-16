"""Unregistered process/source/runtime gates. No job submission or entry point.

CPU and GPU qualification are separate phases. All execution still requires a
future immutable campaign registration, one-use controller and terminal audit.
"""
from pathlib import Path
import os,platform,resource,signal,sys
from research_v67.io import read,require,info
from src.run_store import canonical_json,digest,strict_json
from src.worker_control import WorkerLimits,THREAD_VARIABLES

V67_PROGRAM='11e0db146e79330852f550a1cc3b2dd7568a66cdfe8006b004dca3840149cc30'
V47_PROGRAM='620076c67ae79ee56de784ecd4c6e49ef3b4b22f45742f72956821b1e416cf54'
CAPS={name:dict(cpu_seconds=cpu,wall_seconds=wall) for name,cpu,wall in [
    ('cpu_checks',600,900),('cuda_checks',600,900),('parameters',600,900),
    ('sequential_12',14400,18000),('sequential_6',14400,18000),
    ('cpu_parity',1800,2400),('gpu_quality',5400,7200),('terminal',1800,2400)]}
GPU_PHASES={'cuda_checks','gpu_quality'}
MEMORY=16*2**30;GPU_AS=128*2**40;FILE=2*2**30;GPU_ALLOCATOR=8*2**30
CONTROLLER_CPU=600


def kind(phase):
    require(phase in CAPS,'Unknown admitted phase')
    return 'cuda' if phase in GPU_PHASES else 'cpu'


def limits(phase,cpu):
    require(type(cpu) is int and cpu>=0,'One actual affinity CPU required')
    k=kind(phase)
    return WorkerLimits(**CAPS[phase],address_space_bytes=GPU_AS if k=='cuda' else MEMORY,
        threads=1,affinity_cpus=(cpu,),file_size_bytes=FILE)


def design():
    return dict(schema='quality-execution-resource-design-v69',phases=CAPS,
        worker_allowance_cpu_seconds=sum(x['cpu_seconds']+2 for x in CAPS.values()),
        controller_cpu_soft_seconds=CONTROLLER_CPU,
        controller_cpu_hard_seconds=max(x['cpu_seconds'] for x in CAPS.values())+2,
        controller_allowance_cpu_seconds=len(CAPS)*(CONTROLLER_CPU+1),
        slurm_wall_overhead_seconds=600,host_memory_bytes=MEMORY,cpu_address_space_bytes=MEMORY,
        cuda_address_space_bytes=GPU_AS,gpu_allocator_bytes=GPU_ALLOCATOR,file_size_bytes=FILE,
        threads=1,automatic_retry=False,no_concurrent_second_empirical_work=True,
        final_scheduler_and_closure_accounting_required=True,registered=False)


def apply_controller_limits(phase,*,expected_job,expected_host):
    """Only an admitted entry may call this, before any numerical imports."""
    k=kind(phase)
    require(sys.platform=='linux' and type(expected_job) is str and expected_job.isdigit()
        and os.environ.get('SLURM_JOB_ID')==expected_job and platform.node()==expected_host,
        'Actual prospectively admitted Linux Slurm job/host required')
    require(sys.flags.optimize==0 and sys.dont_write_bytecode is True,'Unoptimized -B process required')
    require(not os.environ.get('LD_PRELOAD') and not os.environ.get('LD_AUDIT'),
        'Loader interposition is outside the admitted runtime')
    require(all(os.environ.get(n)=='1' for n in THREAD_VARIABLES),'All admitted library thread requests must be one')
    if k=='cuda':require(os.environ.get('CUBLAS_WORKSPACE_CONFIG')==':4096:8','Fresh deterministic cuBLAS environment required')
    available=os.sched_getaffinity(0);require(bool(available),'Actual CPU affinity required')
    cpu=min(available);os.sched_setaffinity(0,{cpu})
    def exceeded(*unused):raise TimeoutError('Registered controller CPU ceiling reached')
    signal.signal(signal.SIGXCPU,exceeded)
    requested={resource.RLIMIT_CPU:(CONTROLLER_CPU,design()['controller_cpu_hard_seconds']),
        resource.RLIMIT_AS:(GPU_AS if k=='cuda' else MEMORY,)*2,
        resource.RLIMIT_FSIZE:(FILE,FILE),resource.RLIMIT_CORE:(0,0)}
    for key,pair in requested.items():
        inherited=resource.getrlimit(key)[1]
        require(inherited==resource.RLIM_INFINITY or pair[1]<=inherited,'Admitted limit exceeds inherited ceiling')
        resource.setrlimit(key,pair)
    return dict(job_id=expected_job,hostname=expected_host,phase=phase,affinity_cpus=[cpu],
        cpu_limits=list(resource.getrlimit(resource.RLIMIT_CPU)),
        address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
        file_size=list(resource.getrlimit(resource.RLIMIT_FSIZE)),
        thread_environment={n:os.environ[n] for n in THREAD_VARIABLES},
        physical_memory_requires_slurm_enforcement=True)


def runtime(phase,expected,*,inherited_cpu_runtime=None):
    require(sys.platform=='linux','Numerical runtime qualification requires Linux')
    if kind(phase)=='cpu':
        require(inherited_cpu_runtime is not None and expected==inherited_cpu_runtime,
            'CPU execution must preserve the frozen V67 numerical runtime')
        from research_v61.campaign import runtime as capture
    else:
        require(inherited_cpu_runtime is None,'CUDA runtime is separately registered')
        from research_v47.campaign import runtime as capture
    observed=capture()
    require(canonical_json(observed)==canonical_json(expected),'Actual numerical runtime differs from registration')
    if kind(phase)=='cuda':
        import torch
        require(not torch.cuda.is_initialized(),'Runtime admission must precede CUDA initialization')
    return dict(kind=kind(phase),runtime_sha256=digest(canonical_json(observed)),
        actual_declared_runtime_checked=True,device_and_allocator_admission_still_required=kind(phase)=='cuda')


def sources(v67_bytes,v68_bytes,v47_bytes,*,v68_sha256,new_sources):
    require(type(v67_bytes) is bytes and type(v68_bytes) is bytes and type(v47_bytes) is bytes
        and digest(v67_bytes)==V67_PROGRAM and digest(v68_bytes)==v68_sha256,
        'Actual frozen predecessor registrations required')
    require(digest(v47_bytes)==V47_PROGRAM,'Actual historical GPU registration required')
    a,b,c=strict_json(v67_bytes),strict_json(v68_bytes),strict_json(v47_bytes)
    require(canonical_json(a)==v67_bytes and canonical_json(b)==v68_bytes and canonical_json(c)==v47_bytes,
        'Canonical predecessor registrations required')
    old=dict(a['prior_sources']);require(not set(old)&set(a['new_sources']),'Duplicate frozen source path')
    old.update(a['new_sources'])
    require(len(a['prior_sources'])==456 and len(a['new_sources'])==13 and len(old)==469
        and b['frozen_sources']==old and len(b['new_sources'])==b['new_source_count']==9,
        'All469 frozen and nine admitted V68 source bindings required')
    require(type(new_sources) is dict and bool(new_sources),'Registered V69 source census required')
    # The CPU V67 inventory never included the14 V46/V47 GPU/export files.
    # Restore them from their actual historical registration, never from an
    # unbound current checkout or an invented extension to the frozen V67 set.
    root=Path(a['directory']).parents[1];extra={}
    require(len(c['sources'])==304,'Historical GPU source census differs')
    for relative,sha in c['sources'].items():
        rel=Path(relative);require(not rel.is_absolute() and '..' not in rel.parts,'Canonical historical GPU source required')
        path=str(root/rel)
        actual=read(path,maximum=128*2**20,retain=False)
        require(actual['sha256']==sha,'Historical GPU source changed')
        if path in old:require(actual==old[path],'Historical CPU/GPU source versions conflict')
        else:
            require(rel.parts[0] in {'research_v46','research_v47'},'Unexpected inherited GPU source')
            extra[path]=actual
    require(len(extra)==14,'All fourteen historical GPU/export sources required')
    groups=[old,extra,b['new_sources'],new_sources];combined={}
    for group in groups:
        require(not set(combined)&set(group),'Source inventories overlap')
        for name,e in group.items():
            p=Path(name)
            require(p.is_absolute() and '..' not in p.parts and set(e)=={'bytes','sha256'},
                'Absolute canonical source binding required')
            read(p,e,maximum=128*2**20,retain=False)
        combined.update(group)
    return combined


def imported_sources(registered,modules=None):
    """Reject an imported project module from an unregistered/shadow location."""
    modules=sys.modules if modules is None else modules;checked={}
    for name,module in list(modules.items()):
        top=name.split('.')[0]
        if not (top in {'src','scripts','tests'} or top.startswith('research_v')):continue
        origin=getattr(module,'__file__',None)
        # Empty namespace packages contain no executable source. All actual
        # project code, including package initializers, must be registered.
        if origin is None:
            require(getattr(module,'__path__',None) is not None,'Unbound project module origin')
            continue
        p=Path(origin).absolute()
        require(p.suffix=='.py' and str(p) in registered,'Imported project source outside registration: '+name)
        checked[name]=dict(path=str(p),**read(p,registered[str(p)],maximum=128*2**20,retain=False))
    return checked
