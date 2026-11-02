"""Six-model evaluator factories from actual parameter words and packed codes.

No launch entry. An admitted caller must bind checkpoint provenance, complete
V67/V68 audits, sequential construction, runtime and resource limits first.
"""
from contextlib import contextmanager
from types import SimpleNamespace
import gc,os
import numpy as np
from research_v43.dispatcher import _weight_digest
from research_v46.evaluator import TorchQualityDecoder
from research_v61.target import BoundTarget
from research_v67.io import require,info
from research_v68.quality_statistics import MODELS
from research_v71.parameter_audit import fields
from scripts.run_quality_v30 import nearest_prefix,nll_from_logits
from src.compact_state import StageCodes
from src.run_store import canonical_json,strict_json,digest


def parameter_words(reference):
    return dict(config=vars(reference.config).copy(),arrays={name:dict(shape=list(a.shape),
        dtype='<f8',word_sha256=digest(a.astype('<f8',copy=False).tobytes(order='C')))
        for name,a in sorted(fields(reference).items())})


class ModelSet:
    def __init__(self,reference,bound,models,*,expected_base,expected_service):
        require(type(bound) is BoundTarget and info(bound.anchor_payload)==expected_base
            and info(bound.fixed_payload)==expected_service,'Actual bound V61 target bytes required')
        self.reference=reference;self.bound=bound;self.words=parameter_words(reference)
        entries=strict_json(bound.anchor_payload)['stages'];self.stages=[]
        names=[f'block.{i:04d}.{n}' for i in range(reference.config.block_count)
            for n in ['qkv','attn_out','mlp_up','mlp_down']]
        require([e['stage_id'] for e in entries]==names and set(reference.weights)==set(names),
            'Complete ordered decoder stages required')
        for e in entries:
            actual=reference.weights[e['stage_id']]
            require(list(actual.shape)==e['shape'] and _weight_digest(actual)==e['weights_sha256'],
                'Actual checkpoint matrix differs from frozen target')
            self.stages.append(SimpleNamespace(stage_id=e['stage_id'],rows=e['shape'][0],width=e['shape'][1],
                bits=4,scale_values=tuple(float.fromhex(v) for v in e['row_scale_hex'])))
        require(type(models) is dict and set(models)==set(MODELS[2:]),'Exactly four endpoint models required')
        self.codes={};self.bindings={}
        common=dict(schema='actual-quality-model-words-v71',parameters=info(canonical_json(self.words)),
            base_target=expected_base,service_target=expected_service,
            checkpoint_and_retained_source_provenance_required_of_caller=True)
        for label in MODELS:
            binding=dict(common,model=label)
            if label in models:
                m=models[label]
                require(set(m)=={'blob','expected','retained_records_sha256'} and type(m['blob']) is bytes
                    and info(m['blob'])==m['expected'],'Actual endpoint packed bytes required')
                h=m['retained_records_sha256']
                require(type(h) is str and len(h)==64 and all(c in '0123456789abcdef' for c in h),
                    'Retained-token commitment required')
                offset=0;codes=[]
                for s in self.stages:
                    size=(s.rows*s.width*4+7)//8
                    codes.append(StageCodes(s.stage_id,s.rows,s.width,'dyadic_row',4,(),
                        m['blob'][offset:offset+size],s.scale_values));offset+=size
                require(offset==len(m['blob']),'Exact full packed-model extent required')
                self.codes[label]=tuple(codes)
                binding.update(packed_model=m['expected'],retained_records_sha256=h)
            prefix=self.arrays(label)
            binding['installed_prefix_words']=None if prefix is None else {
                k:dict(shape=list(v.shape),sha256=digest(v.astype('<f8',copy=False).tobytes(order='C')))
                for k,v in sorted(prefix.items())}
            self.bindings[label]=binding
            del prefix
        for endpoint in [12,6]:
            a,b=('candidate_'+str(endpoint),'sequential_'+str(endpoint))
            require(self.bindings[a]['retained_records_sha256']==self.bindings[b]['retained_records_sha256'],
                'Candidate/sequential retained membership differs')
            require(self.codes[a][0].packed_indices==self.codes[b][0].packed_indices,
                'Matched first-stage invariant differs')
        self._binding_bytes=canonical_json(self.bindings)

    def arrays(self,label):
        require(label in MODELS,'Unknown model label')
        if label=='original':return None
        if label=='nearest':
            return nearest_prefix(SimpleNamespace(_float_weights=self.reference.weights),self.stages)
        return {s.stage_id:s.array() for s in self.codes[label]}

    def before_model(self,label):
        require(canonical_json(self.bindings)==self._binding_bytes,'Model provenance bindings changed')
        require(parameter_words(self.reference)==self.words,'Reference parameter words changed before inference')
        arrays=self.arrays(label)
        actual=None if arrays is None else {k:dict(shape=list(v.shape),sha256=digest(v.astype('<f8',copy=False).tobytes(order='C')))
            for k,v in sorted(arrays.items())}
        require(actual==self.bindings[label]['installed_prefix_words'],'Installed model words changed')
        return arrays

    @contextmanager
    def cpu(self,label):
        arrays=self.before_model(label)
        yield SimpleNamespace(binding=self.bindings[label],nll=lambda tokens:
            nll_from_logits(self.reference.logits(tokens,arrays),tokens))


@contextmanager
def cuda(models,*,allocator_bytes):
    """One actual CUDA context, one model prefix at a time, no CPU fallback."""
    require(type(models) is ModelSet and type(allocator_bytes) is int and allocator_bytes>0,
        'Actual model set and prospectively bounded allocator required')
    require(os.environ.get('CUBLAS_WORKSPACE_CONFIG')==':4096:8',
        'Pinned deterministic cuBLAS workspace must be set before CUDA initialization')
    import torch
    require(not torch.cuda.is_initialized(),'Fresh CUDA process required')
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True)
    require(torch.cuda.is_available() and torch.cuda.device_count()==1,'Exactly one CUDA device required')
    total=torch.cuda.get_device_properties(0).total_memory
    require(allocator_bytes<=total,'GPU allocation cap exceeds device memory')
    torch.cuda.set_per_process_memory_fraction(allocator_bytes/total,0);torch.cuda.reset_peak_memory_stats()
    require(parameter_words(models.reference)==models.words,'Actual reference changed before device copy')
    evaluator=TorchQualityDecoder(models.reference)
    report=dict(dtype='float64',tf32=False,amp=False,deterministic_algorithms=True,
        device=torch.cuda.get_device_name(0),torch=torch.__version__,allocator_limit_bytes=allocator_bytes,
        runtime_admission_required_of_caller=True)
    @contextmanager
    def factory(label):
        arrays=models.before_model(label);prefix=None
        try:
            prefix=None if arrays is None else evaluator.prefix(arrays)
            def nll(tokens):
                torch.cuda.synchronize()
                with torch.inference_mode():value=evaluator.nll(tokens,prefix)
                torch.cuda.synchronize();return value
            yield SimpleNamespace(binding=models.bindings[label],nll=nll)
        finally:
            del prefix,arrays;gc.collect();torch.cuda.empty_cache()
    try:yield factory,report
    finally:
        report.update(copied_arrays_with_bitwise_roundtrip=evaluator.copied_arrays,
            peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),
            peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved())
        require(report['peak_cuda_reserved_bytes']<=allocator_bytes,'Actual CUDA allocator cap exceeded')
        del evaluator;gc.collect();torch.cuda.empty_cache()
