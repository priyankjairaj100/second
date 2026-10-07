"""Exact factor-cache service, distinct from aggregate response repair.

Every committed factor belongs to the current exact ancestor code prefix.
The service replays changed prefixes. It makes no transport-avoidance claim.
All four methods share the same finite kernels and certified token solver.
"""
from dataclasses import dataclass
import hashlib
import json
import time
import numpy as np

from .compact_state import CompactState, StageCodes, RecordFactor, prefix_digest, serialize, parse, token_digest
from .ordered_finite import FiniteWeights
from .sequential_finite import sequential_features
from .low_rank_certified import certified_token_codes
from .row_scaled_quantizer import quantize_row_scaled

METHODS = ('model_only_fresh', 'repair', 'indexed_fresh', 'direct_fresh')



@dataclass(frozen=True)
class CompactResult:
    stages: tuple
    state: object
    diagnostics: dict


def _records(decoder, records):
    rows=[]
    for record in records:
        if set(record) != {'id','tokens'} or type(record['id']) is not str or not record['id']:
            raise ValueError('records require exactly a nonempty ID and tokens')
        tokens=decoder.base._tokens(record['tokens'])
        rows.append((record['id'], tokens))
    rows.sort(key=lambda row:row[0])
    if len({row[0] for row in rows}) != len(rows):raise ValueError('duplicate record ID')
    return tuple(rows)


def _grid(target,index):
    stage=target.stages[index]
    if hasattr(stage,'bits') and hasattr(stage,'scale_exponents'):
        return 'row',stage.bits,stage.scale_exponents
    return 'column',target.recipe.bits,target.scale_exponents[index]


class CompactIdentityService:
    """Trusted canonical cache with strict membership and prefix binding.

    State hashes detect corruption. They do not authenticate hostile suppliers
    or prove that supplied factor values were originally extracted correctly.
    Fresh construction and repair assume trusted state provenance.
    """
    def __init__(self,decoder,target,*,progress=None):
        if tuple(s.stage_id for s in target.stages)!=tuple(decoder.stage_ids):
            raise ValueError('complete target and decoder stage order differ')
        for i,s in enumerate(target.stages):
            if set(s.dependencies)!=set(decoder.stage_ids[:i]):
                raise ValueError('service requires the complete sequential dependency prefix')
        self.decoder=decoder;self.target=target;self.progress=progress

    def _validate_prior(self,prior):
        if not isinstance(prior,CompactState) or prior.target_sha256!=self.target.digest:
            raise ValueError('prior state target mismatch')
        if len(prior.stages)!=len(self.target.stages):raise ValueError('incomplete prior model')
        for i,(codes,stage) in enumerate(zip(prior.stages,self.target.stages)):
            axis,bits,exponents=_grid(self.target,i)
            if (codes.stage_id!=stage.stage_id or codes.grid_axis!=axis or codes.bits!=bits
                or tuple(codes.scale_exponents)!=tuple(exponents)
                or tuple(codes.array().shape)!=(len(stage.weights),stage.width)):
                raise ValueError('prior model grid or dimensions differ')
        # The state constructor/parser validates complete factors and prefix hashes.

    def run(self,records,*,method='direct_fresh',prior=None,deleted_ids=()):
        if method not in METHODS:raise ValueError('unknown comparison method')
        rows=_records(self.decoder,records)
        deleted=tuple(deleted_ids)
        if any(type(x) is not str for x in deleted) or len(set(deleted))!=len(deleted):
            raise ValueError('deletions must be unique record IDs')
        indexed=method in ('repair','indexed_fresh')
        if indexed:
            self._validate_prior(prior)
            previous={factor.record_id for factor in prior.factors}
            retained={rid for rid,_ in rows}
            if not set(deleted)<=previous or retained!=previous-set(deleted):
                raise ValueError('retained membership differs from the declared deletion')
            old_factors={(f.stage_id,f.record_id):f for f in prior.factors}
            for rid,tokens in rows:
                if any(old_factors[(stage.stage_id,rid)].token_sha256!=token_digest(tokens)
                       for stage in self.target.stages):
                    raise ValueError('retained record contents changed')
        else:
            if prior is not None or deleted:raise ValueError('fresh methods accept only retained records')
            old_factors={}
        metrics=dict(schema='factor-identity-service-v13',method=method,
            target_sha256=self.target.digest,records=len(rows),stages=[],
            cached_factor_reads=0,neural_stage_record_pairs=0,
            changed_ancestor_factor_pairs=0,changed_ancestor_pairs_avoided=0,
            retained_source_token_reads=sum(len(t) for _,t in rows),
            interval_decisions=0,exact_decisions=0,
            state_family='factor_identity_v1',transport_certificate=False)
        streams={};positions={};current={};outputs=[];factors=[];installed=[]
        def evaluate(rid,tokens,index):
            if rid not in streams:
                stream=sequential_features(self.decoder,tokens)
                streams[rid]=stream;current[rid]=next(stream);positions[rid]=0
                metrics['neural_stage_record_pairs']+=1
            while positions[rid]<index:
                j=positions[rid]
                current[rid]=streams[rid].send(installed[j]);positions[rid]+=1
                metrics['neural_stage_record_pairs']+=1
            sid,values=current[rid]
            if sid!=self.target.stages[index].stage_id:raise ArithmeticError('stage traversal mismatch')
            return np.asarray(values,dtype=np.float64)
        for i,stage in enumerate(self.target.stages):
            started=time.perf_counter_ns();prefix=prefix_digest(self.target.digest,tuple(outputs))
            block_factors=[];cache_hits=0
            for rid,tokens in rows:
                old=old_factors.get((stage.stage_id,rid))
                if old is not None and old.prefix_sha256==prefix:
                    values=old.array();cache_hits+=1;metrics['cached_factor_reads']+=1
                else:
                    if old is not None:metrics['changed_ancestor_factor_pairs']+=1
                    values=evaluate(rid,tokens,i)
                block_factors.append(values)
                if method!='model_only_fresh':
                    factors.append(RecordFactor.from_array(stage.stage_id,rid,values,
                        prefix_sha256=prefix,token_sha256=token_digest(tokens)))
            features=(np.concatenate(block_factors,axis=0).T.copy() if rows
                      else np.empty((stage.width,0),dtype=np.float64))
            weights=FiniteWeights(stage.weights).array()
            axis,bits,exponents=_grid(self.target,i)
            options=dict(ridge=stage.ridge,normalization=stage.normalization,
                max_exact_rank=64,max_exact_coordinates=16,max_refinement_coordinates=64)
            if axis=='row':
                quantized=quantize_row_scaled(weights,features,exponents,bits=bits,**options)
            else:quantized=certified_token_codes(weights,features,stage.grids,**options)
            codes=StageCodes.from_array(stage.stage_id,quantized.codes,grid_axis=axis,
                bits=bits,scale_exponents=exponents)
            outputs.append(codes);installed.append(quantized.codes)
            metrics['interval_decisions']+=quantized.interval_decisions
            metrics['exact_decisions']+=quantized.exact_decisions
            stage_metrics=dict(stage_id=stage.stage_id,elapsed_ns=time.perf_counter_ns()-started,
                cached_factor_reads=cache_hits,record_count=len(rows),
                interval_decisions=quantized.interval_decisions,exact_decisions=quantized.exact_decisions)
            metrics['stages'].append(stage_metrics)
            if self.progress:self.progress(stage_metrics)
        state=None if method=='model_only_fresh' else CompactState(self.target.digest,tuple(outputs),tuple(factors))
        return CompactResult(tuple(outputs),state,metrics)


def model_digest(stages):
    """Canonical model-only bytes use the same packing and an empty factor set."""
    # Caller binds the numerical target separately.
    h=hashlib.sha256()
    for stage in stages:
        encoded=stage.array().astype('<f8',copy=False).tobytes()
        sid=stage.stage_id.encode('utf8');h.update(len(sid).to_bytes(8,'little'));h.update(sid)
        h.update(len(encoded).to_bytes(8,'little'));h.update(encoded)
    return h.hexdigest()
