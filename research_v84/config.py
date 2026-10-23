"""Prospective matched workload and finite CPU reservation; not registered."""
import hashlib
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/matched-complete-service-v84-20261023-a'
ADMISSION=ROOT/'local_runs/matched-transfer-admission-v82-20261023-a'
ADMISSION_SHA='5bead3425eb9bb4bec645ac12e681b45e62d87762cef0f15179aecdb427ae27b'
PROFILES=('distilgpt2','gpt2')
REBUILT_REPRESENTATIONS=('lossless','compressed48','hybrid_gram','modern_lossless')
CELLS=dict(reference_compressed='compressed',reference_modern='modern',optimized_compressed='compressed',optimized_modern='modern')
ARM_ORDER=sorted(CELLS,key=lambda k:hashlib.sha256(('second-matched-depth-service-v84:'+k).encode()).hexdigest())
LOCAL_ORDER=['prepare',*[a+'-1' for a in ARM_ORDER],*[a+'-2' for a in reversed(ARM_ORDER)],'oracle']
# A predetermined reverse model order at alternating operations limits gross
# time-order confounding; one observation remains descriptive.
ORDER=[profile+'/'+local for i,local in enumerate(LOCAL_ORDER) for profile in (PROFILES if i%2==0 else tuple(reversed(PROFILES)))]
TRIALS={}
for trial in ORDER:
    profile,local=trial.split('/');scale=1 if profile=='distilgpt2' else 2
    cpu=3600 if local=='prepare' else 4800 if local=='oracle' else 3000 if local.endswith('-1') else 1800
    TRIALS[trial]=dict(cpu_seconds=cpu*scale,wall_seconds=cpu*scale+1800)
CAP=sum(v['cpu_seconds']+2 for v in TRIALS.values())

def trial_parts(trial):
    if trial not in TRIALS:raise ValueError('Unknown matched profile/trial')
    return tuple(trial.split('/'))

def predecessor(trial):
    profile,local=trial_parts(trial)
    if local in ('prepare','oracle'):raise ValueError('Fresh reconstruction has no predecessor')
    cell,step=local.rsplit('-',1);rep='compressed48' if CELLS[cell]=='compressed' else 'modern_lossless'
    return (profile+'/prepare',rep+'-state.bin',rep+'-trust.json') if step=='1' else (profile+'/'+cell+'-1','state.bin','trust.json')

def expected_artifacts(trial):
    """Declare all outputs without importing the numerical worker."""
    _,local=trial_parts(trial)
    names={'execution-provenance.json','admission.json'}
    rebuilt={'model.bin'}|{r+'-'+suffix for r in REBUILT_REPRESENTATIONS for suffix in ('state.bin','trust.json')}
    if local=='prepare':names|=rebuilt
    elif local=='oracle':names|={f'step-{s}/'+name for s in (1,2) for name in rebuilt}
    else:names|={'model.bin','state.bin','trust.json'}
    return names

SOFTWARE_MODULES=['research_v63.test_control','research_v63.test_runner','research_v64.test_service','research_v64.test_linux','research_v66.test_operations','research_v66.test_linux',
    'research_v79.test_integration','research_v81.test_profile','research_v81.test_archive','research_v81.test_service','research_v80.test_implementation',
    'research_v84.test_config','research_v84.test_submit','research_v84.test_submit_flow','research_v84.test_worker','research_v84.test_receipts']

def design():
    return dict(schema='matched-complete-service-v84',software_modules=SOFTWARE_MODULES,expected_tests=88,profiles=list(PROFILES),cells=CELLS,trial_order=ORDER,trials=TRIALS,
        normalization=512,root_sources=4,retained_counts=[3,2],tokens_per_record=128,grid_allowance=1327104,
        phase_cpu_seconds=CAP,preserved_phase_ceiling=120624,controller_cpu_allowance_seconds=6040,preserved_controller_ceiling=7224,
        process_address_space_bytes=16*2**30,file_size_bytes=2*2**30,artifact_limit_bytes=2**30,resident_bytes=9*2**30,
        controller_cpu_soft_seconds=300,controller_cpu_hard_seconds=10202,controller_wall_overhead_seconds=600,
        primary_audit_caps=dict(cpu=7200,wall=9000),supplemental_audit_caps=dict(cpu=3600,wall=5400),
        software_caps=dict(cpu=300,aggregate=602,wall=600),threads=1,host='csis.mn1',automatic_retry=False,
        numerical_checkout='f900999fcb200509dfad4fc081ce9c87fd172a16',confirmation=False,quality_evaluation=False,
        development_data_previously_exposed=True,source_selection='frozen V82 four-of-thirteen hash selection',
        primary_timing='Complete controller transaction; separate worker/request clocks overlap',
        cache_policy='Fresh processes/contexts; OS cache uncontrolled; no flushing',stage_counts={'distilgpt2':24,'gpt2':48},
        code_counts={'distilgpt2':42467328,'gpt2':84934656},all_cells_and_failures_reported=True)
