"""Prospective pinned matched-depth service; not an empirical launcher."""
import json,time
from research_v79.implementation import IntegratedService
from research_v61.service import execution_provenance,require
from research_v61.target import BoundTarget,build_service_target
from research_v35.exact_gram import GramBudget
from research_v43 import dispatcher
from research_v81.profile import PROFILES,NORMALIZATION,CURRENT_GRID_CAP,PROPOSED_GRID_CAP,validate_geometry,validate_records
from research_v81 import archive
from src.checkpoint_adapter import load_gpt2_checkpoint
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
from src.dyadic_row_target import build_dyadic_row_target
from src.target_manifest import TargetRecipe
from src.run_store import canonical_json

class MatchedService(IntegratedService):
    def __init__(self,checkpoint,profile,record_provenance,mark=lambda *a,**k:None,*,allow_proposed_grid_cap=False):
        require(profile in PROFILES and len(record_provenance)==4,'Pinned profile and four original sources required')
        require(type(allow_proposed_grid_cap) is bool,'Explicit grid-policy choice required')
        grid_cap=PROPOSED_GRID_CAP if allow_proposed_grid_cap else CURRENT_GRID_CAP
        require(PROFILES[profile]['blocks']*sum((2304,768,3072,768))*16<=grid_cap,'Complete GPT2 target exceeds current grid guard; new allowance approval and registration required')
        tick=time.perf_counter_ns();self.mark=mark;self.normalization=NORMALIZATION
        self.profile=profile;self.record_provenance=record_provenance
        loaded=load_gpt2_checkpoint(checkpoint,identity_encoding='binary64_tree_v2')
        require(loaded.provenance['files_sha256']==PROFILES[profile]['checkpoint_files'],'Exact registered checkpoint bytes required')
        self.decoder=OrderedFiniteDecoder(loaded.decoder,primitive_backend='mpfr_enclosure')
        self.base=build_dyadic_row_target(self.decoder,TargetRecipe(original_token_count=NORMALIZATION,group_count=1,max_grid_entries=grid_cap))
        validate_geometry(self.base.payload(),profile)
        self.target=build_service_target(self.decoder,self.base)
        self.bound=BoundTarget(canonical_json(self.base.payload()),canonical_json(self.target.payload()))
        require(len(self.target.stages)==4*PROFILES[profile]['blocks'],'Complete decoder depth required')
        self.gram_budget=GramBudget(max_width=768,max_tokens=512,max_sources=4,
            max_product_terms=768*769//2*512,max_integer_bits=256,max_serialized_bytes=128*2**20,max_memory_bytes=2*2**30)
        self.policy=dispatcher.ResourcePolicy()
        self.provenance=execution_provenance(self.decoder,self.target,loaded.provenance)
        self.load_ns=time.perf_counter_ns()-tick
        self.mark('context_ready',elapsed_ns=self.load_ns,target_sha256=self.target.digest,profile=profile)

    def admit(self,rows,representation):
        validate_records(self.records(rows))
        validate_geometry(json.loads(self.bound.anchor_payload),self.profile)
        return super().admit(rows,representation)

    def serialize(self,rows,codes,representation,payloads,grams,trust,telemetry):
        if representation!='modern_lossless':
            return super().serialize(rows,codes,representation,payloads,grams,trust,telemetry)
        require(not grams and not trust,'Modern state cannot carry Gram state/trust')
        tick=time.perf_counter_ns()
        try:return archive.pack(self.bound,self.records(rows),codes,payloads)
        finally:telemetry['serialization_ns']+=time.perf_counter_ns()-tick

    def repair(self,*args,**kwargs):
        raise RuntimeError('Use separately registered V81 operations.request with full transaction/accounting')
