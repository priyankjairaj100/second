"""Common service operations for prospective V66 workers.

Unregistered preparation only. No campaign, empirical input or model is opened
by importing this module. Controllers, immutable input bindings, CPU accounting,
startup clocks and terminal audits remain separate launch prerequisites.
"""
import gc
import json
import time

from research_v61.service import Service, gram_stage, telemetry, trust_json, trust_read, require
from research_v61.state import GramTrust, validate_state
from research_v35.exact_gram import loads, dumps, subtract_gram
from research_v40.native_exact_gram import accumulate
from research_v63 import archive
from research_v64.service import ModernService, REPRESENTATION as MODERN
from src.run_store import canonical_json, digest

REPRESENTATIONS=('lossless','compressed48','hybrid_gram',MODERN)
ARM_REPRESENTATION=dict(cached='lossless',cold='lossless',compressed='compressed48',hybrid='hybrid_gram',modern=MODERN)


class AllRepresentationsService(ModernService):
    """Explicit routing over unchanged implementations, with one common context."""
    def admit(self,rows,representation):
        require(representation in REPRESENTATIONS,'Unknown representation')
        return Service.admit(self,rows,'lossless' if representation==MODERN else representation)

    def descriptor(self,stage,row,values,representation):
        implementation=ModernService if representation==MODERN else Service
        return implementation.descriptor(self,stage,row,values,representation)

    def prepare_payloads(self,rows,values,representation,timing):
        implementation=ModernService if representation==MODERN else Service
        return implementation.prepare_payloads(self,rows,values,representation,timing)

    def solve(self,rows,representation,payloads,grams,trust,timing,*,direct_values=None):
        implementation=ModernService if representation==MODERN else Service
        return implementation.solve(self,rows,representation,payloads,grams,trust,timing,direct_values=direct_values)

    def serialize(self,rows,codes,representation,payloads,grams,trust,timing):
        implementation=ModernService if representation==MODERN else Service
        return implementation.serialize(self,rows,codes,representation,payloads,grams,trust,timing)


def model_blob(codes):return b''.join(c.packed_indices for c in codes)


def ordered_rows(service,rows):
    require(type(rows) is list and rows and rows==sorted(rows,key=lambda r:r['id'])
            and len({r['id'] for r in rows})==len(rows),'Ordered distinct nonempty records required')
    service.records(rows)


def artifact(write,name,blob):
    """The writer must persist these exact bytes and return their commitment."""
    result=write(name,blob)
    require(result==dict(file=name,bytes=len(blob),sha256=digest(blob)),'Writer commitment differs')
    return result


def rebuild(service,rows,write):
    """Fresh original-token extraction and all four complete representations.

    No predecessor state argument exists. Reused for preparation and a separately
    executed retained-token oracle. Caller clocks include context and admission.
    """
    ordered_rows(service,rows)
    for representation in REPRESENTATIONS:service.admit(rows,representation)
    timing=telemetry();start=time.perf_counter_ns()
    values=service.extract(rows,timing)
    source_ns=time.perf_counter_ns()-start
    tick=time.perf_counter_ns()
    codes,admission=service.solve(rows,'lossless',{}, {}, {},timing,direct_values=values)
    model=artifact(write,'model.bin',model_blob(codes))
    model_ns=time.perf_counter_ns()-tick
    states={}
    for representation in REPRESENTATIONS:
        rep_timing=telemetry();tick=time.perf_counter_ns()
        payloads,grams,trust=service.prepare_payloads(rows,values,representation,rep_timing)
        blob=service.serialize(rows,codes,representation,payloads,grams,trust,rep_timing)
        state=artifact(write,representation+'-state.bin',blob)
        sidecar=artifact(write,representation+'-trust.json',canonical_json(trust_json(trust)))
        disposal=time.perf_counter_ns();del payloads,grams,trust,blob;gc.collect()
        rep_timing['disposal_ns']=time.perf_counter_ns()-disposal
        states[representation]=dict(timing=rep_timing,representation_elapsed_ns=time.perf_counter_ns()-tick,
            state=state,trust=sidecar,live_state_bytes=state['bytes']+sidecar['bytes'])
    count=sum(c.rows*c.columns for c in codes)
    disposal=time.perf_counter_ns();del values,codes;gc.collect()
    return dict(model=model,code_count=count,states=states,admission=admission,common_timing=timing,
        common_source_ns=source_ns,common_original_model_and_write_ns=model_ns,
        common_disposal_ns=time.perf_counter_ns()-disposal,
        independent_retained_token_traversal=True,prior_state_read=False)


def request(service,previous_rows,rows,arm,read_predecessor,write):
    """One actual deletion request; read and writes are inside the request clock.

    read_predecessor returns exact state and trust bytes. Cold never calls it.
    This clock excludes the caller's context load/admission/controller overhead,
    which a complete worker must record within its wider transaction clocks.
    """
    start=time.perf_counter_ns();timing=telemetry()
    require(arm in ARM_REPRESENTATION,'Unknown service arm')
    representation=ARM_REPRESENTATION[arm]
    ordered_rows(service,previous_rows);ordered_rows(service,rows)
    previous={r['id']:r for r in previous_rows};kept={r['id'] for r in rows}
    require(len(rows)<len(previous_rows) and all(previous.get(r['id'])==r for r in rows),'Proper unmodified retained subset required')
    deleted=[r for r in previous_rows if r['id'] not in kept]
    service.admit(previous_rows,representation);service.admit(rows,representation)
    old=old_blob=old_trust_blob=values=None;old_trust={}
    payloads={};grams={};trust={}
    if arm=='cold':
        values=service.extract(rows,timing)
        payloads,grams,trust=service.prepare_payloads(rows,values,representation,timing)
    else:
        old_blob,old_trust_blob=read_predecessor()
        require(type(old_blob) is bytes and type(old_trust_blob) is bytes,'Immutable predecessor bytes required')
        old_trust=trust_read(json.loads(old_trust_blob))
        require(canonical_json(trust_json(old_trust))==old_trust_blob,'Canonical trust sidecar required')
        tick=time.perf_counter_ns()
        if arm=='modern':
            require(not old_trust,'Modern state cannot contain Gram trust')
            old=archive.unpack(old_blob)
            require(old.target==service.bound and old.records==service.records(previous_rows),'Modern predecessor binding differs')
        else:
            old=validate_state(old_blob,expected_target=service.bound,
                expected_records=service.records(previous_rows),gram_trust=old_trust,gram_budget=service.gram_budget)
            require(old.representation==representation,'Predecessor representation differs')
        timing['predecessor_validation_ns']=time.perf_counter_ns()-tick
        payloads={key:value for key,value in old.source_map().items() if key[1] in kept}
        if arm=='hybrid':
            removed=service.extract(deleted,timing)
            for stage in service.target.stages:
                if not gram_stage(stage,representation):continue
                sid=stage.stage_id
                before=loads(old.gram_map()[sid],trusted_sha256=old_trust[sid].sha256,
                    expected_sources=old_trust[sid].sources,budget=service.gram_budget)
                for row in deleted:
                    part=accumulate(removed[(sid,row['id'])].T.copy(),source_id=row['id'],
                        normalization=service.normalization,budget=service.gram_budget)
                    updated=subtract_gram(before,part,budget=service.gram_budget)
                    del before,part;before=updated
                grams[sid]=dumps(before,budget=service.gram_budget)
                trust[sid]=GramTrust(digest(grams[sid]),before.sources)
                del before,updated
            del removed
    codes,admission=service.solve(rows,representation,payloads,grams,trust,timing)
    blob=service.serialize(rows,codes,representation,payloads,grams,trust,timing)
    state=artifact(write,'state.bin',blob)
    sidecar=artifact(write,'trust.json',canonical_json(trust_json(trust)))
    model=artifact(write,'model.bin',model_blob(codes))
    count=sum(c.rows*c.columns for c in codes)
    disposal=time.perf_counter_ns()
    del old,old_blob,old_trust_blob,old_trust,values,payloads,grams,trust,codes,blob
    gc.collect();timing['disposal_ns']=time.perf_counter_ns()-disposal
    return dict(arm=arm,representation=representation,retained_ids=[r['id'] for r in rows],
        deleted_ids=[r['id'] for r in deleted],request_elapsed_ns=time.perf_counter_ns()-start,
        timing=timing,admission=admission,state=state,trust=sidecar,model=model,code_count=count,
        live_state_bytes=state['bytes']+sidecar['bytes'],audit_history_physically_retained=True)
