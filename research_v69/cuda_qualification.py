"""Fresh-process generated CUDA qualification, never empirical model quality.

No Slurm entry. A registered bounded cuda_checks worker must call this once.
The local tests only exercise fixture construction and pre-CUDA refusal.
"""
from pathlib import Path
import os,sys,time
import numpy as np
from research_v67.io import require,write
from research_v69 import model_backend
from research_v69.test_model_backend import make,construct
from src.worker_control import THREAD_VARIABLES


def fixture():
    reference,target,models=make()
    reference.config.max_sequence_length=128
    reference.positions=np.random.default_rng(69).normal(size=(128,reference.config.model_width))*.01
    reference.positions[0,0]=-0.
    reference.positions[0,1]=float.fromhex('0x0.0000000000001p-1022')
    reference.head_bias[0]=-0.
    result=construct(reference,target,models)
    records=[dict(id='generated-cuda-fixture-'+str(i),tokens=[(j+i)%reference.config.vocabulary_size for j in range(128)]) for i in range(4)]
    return result,records


def run(out,*,registration_sha256,allocator_bytes):
    require(sys.platform=='linux' and os.environ.get('SLURM_JOB_ID','').isdigit(),
        'Fresh admitted Linux Slurm qualification required')
    require(type(registration_sha256) is str and len(registration_sha256)==64
        and all(x in '0123456789abcdef' for x in registration_sha256),'Registration commitment required')
    require(all(os.environ.get(n)=='1' for n in THREAD_VARIABLES)
        and os.environ.get('CUBLAS_WORKSPACE_CONFIG')==':4096:8','Pinned deterministic thread environment required')
    out=Path(out).absolute();require(not any(p.is_symlink() for p in (out,*out.parents)),'Nonsymbolic exclusive output required')
    out.mkdir(exist_ok=False);tick=time.perf_counter_ns()
    report=dict(schema='generated-cuda-backend-qualification-v69',status='running',
        registration_sha256=registration_sha256,comparisons=[],error=None,gpu=None,
        actual_checkpoint_loaded=False,empirical_quality=False,generated_records=4,
        record_tokens=128,predictions_per_record=127,threshold=1e-8,
        signed_zero_and_subnormal_parameter_transfer_included=True)
    try:
        models,records=fixture();cpu={}
        for label in model_backend.MODELS:
            with models.cpu(label) as evaluator:
                cpu[label]=[evaluator.nll(r['tokens']) for r in records]
        # Importing the evaluator module and constructing NumPy references does
        # not initialize CUDA. The real factory enforces this before device use.
        with model_backend.cuda(models,allocator_bytes=allocator_bytes) as (factory,gpu):
            report['gpu']=gpu
            for label in model_backend.MODELS:
                with factory(label) as evaluator:
                    for i,r in enumerate(records):
                        value=evaluator.nll(r['tokens']);difference=abs(value-cpu[label][i])/127
                        row=dict(model=label,id=r['id'],cpu_sum_nll=cpu[label][i],cuda_sum_nll=value,
                            mean_nll_absolute_difference=difference,passed=difference<=1e-8)
                        report['comparisons'].append(row)
                        write(out/f'pair-{len(report["comparisons"])-1:02d}.json',row)
                        require(row['passed'],'Generated actual CUDA/CPU parity failed')
        require(len(report['comparisons'])==24,'All six generated models and four articles required')
        report['status']='complete'
    except BaseException as error:
        report.update(status='failed',error=dict(type=type(error).__name__,message=str(error)));raise
    finally:
        report['elapsed_ns']=time.perf_counter_ns()-tick
        write(out/'completion.json',report)
    return report
