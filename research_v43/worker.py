"""Registered complete-model preparation, two deletions, or fresh state oracle."""
from dataclasses import asdict
import gc
import os
from pathlib import Path
import resource
import sys
import time
import traceback

from research_v43.campaign import ROOT, read, new, sha, verify, require
from research_v43.service import Service, REPRESENTATIONS, gram_stage, telemetry, trust_json, trust_read
from research_v43.state import GramTrust, validate_state
from research_v35.exact_gram import loads, dumps, subtract_gram
from research_v40.native_exact_gram import accumulate
from src.run_store import canonical_json, digest
from src.transaction_timing import verify_command_admission


def model_blob(codes):
    return b''.join(code.packed_indices for code in codes)


def main(plan_path):
    plan_path=Path(plan_path).absolute()
    plan=read(plan_path)
    program_path=Path(plan['program'])
    p=verify(program_path.parent)
    require(sha(program_path)==plan['program_sha256'],'Program binding changed')
    trial=plan['trial']
    # The durable controller reservation binds this exact argv to this program.
    verify_command_admission(plan['program_sha256'],'feasibility',
        [sys.executable,'-B','-m','research_v43.worker',str(plan_path)])
    out=Path(plan['output'])
    out.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter_ns()
    result=dict(schema='complete-service-worker-v43',status='running',trial=trial,
        program_sha256=plan['program_sha256'],slurm_job_id=plan['slurm_job_id'],artifacts={},
        steps=[],complete_model=False,confirmation=False,quality_evaluation=False,
        source_sha256=p['sources'],all_outputs_are_development=True)

    def artifact(name,blob):
        require(Path(name).name==name,'Artifact filename is unsafe')
        desc=new(out/name,blob,raw=True)
        result['artifacts'][name]=desc
        return desc

    def mark(phase,**details):
        # Full solver receipts live in the final result; compact progress only.
        details={k:v for k,v in details.items() if k not in ('admission','solver')}
        if 'elapsed_ns' in details:
            details['component_elapsed_ns']=details.pop('elapsed_ns')
        row=dict(phase=phase,elapsed_ns=time.perf_counter_ns()-start,**details)
        print(canonical_json(row).decode(),flush=True)
        new(out/f'progress-{mark.count:04d}.json',row)
        mark.count+=1
    mark.count=0

    def prepared(name):
        prep=Path(p['directory'])/'prepare/outputs'
        completion=read(prep/'completion.json')
        require(completion['status']=='complete','Preparation not complete')
        entry=completion['artifacts'][name]
        blob=(prep/name).read_bytes()
        require(len(blob)==entry['bytes'] and digest(blob)==entry['sha256'],'Prepared artifact changed')
        return blob

    try:
        service=Service(ROOT/'tmp/models/distilgpt2',p['normalization'],p['record_provenance'],mark)
        result.update(context_elapsed_ns=service.load_ns,execution_provenance_sha256=digest(service.provenance))
        artifact('execution-provenance.json',service.provenance)
        original=p['records']
        # Refuse all known requests, replay fallbacks and original solving before
        # touching calibration features. Native Gram product admission is also
        # checked by its factory before allocating products.
        admission=[]
        for retained in (3,2,1):
            rows=original[3-retained:]
            for representation in REPRESENTATIONS:
                admission.append(dict(retained=retained,representation=representation,
                    **service.admit(rows,representation)))
        artifact('admission.json',canonical_json(admission))

        if trial=='prepare':
            timing=telemetry()
            tick=time.perf_counter_ns()
            values=service.extract(original,timing)
            source_ns=time.perf_counter_ns()-tick
            # The canonical original model is common to all storage formats.
            tick=time.perf_counter_ns()
            codes,initial_admission=service.solve(original,'lossless',{}, {},{},timing,direct_values=values)
            model_ns=time.perf_counter_ns()-tick
            artifact('original-model.bin',model_blob(codes))
            reps={}
            for representation in REPRESENTATIONS:
                rep_timing=telemetry()
                tick=time.perf_counter_ns()
                payloads,grams,trust=service.prepare_payloads(original,values,representation,rep_timing)
                blob=service.serialize(original,codes,representation,payloads,grams,trust,rep_timing)
                entry=artifact(representation+'-original.bin',blob)
                trust_entry=artifact(representation+'-trust.json',canonical_json(trust_json(trust)))
                rep_ns=time.perf_counter_ns()-tick
                disposal=time.perf_counter_ns()
                del payloads,grams,trust,blob
                gc.collect()
                rep_timing['disposal_ns']=time.perf_counter_ns()-disposal
                reps[representation]=dict(timing=rep_timing,representation_elapsed_ns=rep_ns+rep_timing['disposal_ns'],
                    state_bytes=entry['bytes'],trust_bytes=trust_entry['bytes'],
                    complete_deployment_bytes=entry['bytes']+trust_entry['bytes']+p['shared_checkpoint_bytes'])
            count=sum(c.rows*c.columns for c in codes)
            disposal=time.perf_counter_ns()
            del values,codes
            gc.collect()
            result.update(preparation=dict(common_source_ns=source_ns,common_original_model_ns=model_ns,
                common_disposal_ns=time.perf_counter_ns()-disposal,
                common_timing=timing,representations=reps),complete_model=True,code_count=count)
        elif trial=='oracle':
            # No original state bytes or prepared descriptors are read here.
            for step,retained in enumerate((2,1),1):
                rows=original[3-retained:]
                tick=time.perf_counter_ns()
                timing=telemetry()
                values=service.extract(rows,timing)
                codes,_=service.solve(rows,'lossless',{}, {},{},timing,direct_values=values)
                artifact(f'step-{step}-model.bin',model_blob(codes))
                representations={}
                for representation in REPRESENTATIONS:
                    rep_timing=telemetry()
                    payloads,grams,trust=service.prepare_payloads(rows,values,representation,rep_timing)
                    blob=service.serialize(rows,codes,representation,payloads,grams,trust,rep_timing)
                    entry=artifact(f'step-{step}-{representation}.bin',blob)
                    trust_entry=artifact(f'step-{step}-{representation}-trust.json',canonical_json(trust_json(trust)))
                    representations[representation]=dict(state_bytes=entry['bytes'],trust_bytes=trust_entry['bytes'],timing=rep_timing)
                    del blob,payloads,grams,trust
                    gc.collect()
                result['steps'].append(dict(step=step,retained_ids=[r['id'] for r in rows],timing=timing,
                    representations=representations,oracle_elapsed_ns=time.perf_counter_ns()-tick,
                    independent_retained_token_traversal=True,prior_state_read=False))
                del values,codes
                gc.collect()
            result['complete_model']=True
        else:
            representation={'cached':'lossless','compressed':'compressed40','hybrid':'hybrid_gram','cold':'lossless'}[trial]
            previous_path=None
            previous_trust_path=None
            previous_rows=original
            for step,retained in enumerate((2,1),1):
                # Through predecessor load, source access, solving, complete
                # output write and obsolete in-process object disposal.
                tick=time.perf_counter_ns()
                timing=telemetry()
                rows=original[3-retained:]
                deleted=[r for r in previous_rows if r['id'] not in {x['id'] for x in rows}]
                old=None
                old_blob=None
                old_trust={}
                values=None
                if trial=='cold':
                    values=service.extract(rows,timing)
                    payloads,grams,trust=service.prepare_payloads(rows,values,representation,timing)
                else:
                    old_blob=prepared(representation+'-original.bin') if previous_path is None else previous_path.read_bytes()
                    old_trust=trust_read(__import__('json').loads(prepared(representation+'-trust.json')) if previous_trust_path is None else read(previous_trust_path))
                    old=validate_state(old_blob,expected_target=service.bound,expected_records=service.records(previous_rows),
                        gram_trust=old_trust,gram_budget=service.gram_budget)
                    kept={r['id'] for r in rows}
                    payloads={key:blob for key,blob in old.source_map().items() if key[1] in kept}
                    grams,trust={},{}
                    if trial=='hybrid':
                        removed=service.extract(deleted,timing)
                        for stage in service.target.stages:
                            if not gram_stage(stage,representation):
                                continue
                            sid=stage.stage_id
                            before=loads(old.gram_map()[sid],trusted_sha256=old_trust[sid].sha256,
                                expected_sources=old_trust[sid].sources,budget=service.gram_budget)
                            for row in deleted:
                                part=accumulate(removed[(sid,row['id'])].T.copy(),source_id=row['id'],
                                    normalization=service.normalization,budget=service.gram_budget)
                                updated=subtract_gram(before,part,budget=service.gram_budget)
                                del before,part
                                before=updated
                            grams[sid]=dumps(before,budget=service.gram_budget)
                            trust[sid]=GramTrust(digest(grams[sid]),before.sources)
                            del before,updated
                        del removed
                codes,stage_admission=service.solve(rows,representation,payloads,grams,trust,timing)
                blob=service.serialize(rows,codes,representation,payloads,grams,trust,timing)
                name=f'step-{step}-state.bin'
                entry=artifact(name,blob)
                trust_name=f'step-{step}-trust.json'
                trust_entry=artifact(trust_name,canonical_json(trust_json(trust)))
                artifact(f'step-{step}-model.bin',model_blob(codes))
                disposal=time.perf_counter_ns()
                del old,old_blob,old_trust,values,codes,blob,payloads,grams,trust
                gc.collect()
                timing['disposal_ns']=time.perf_counter_ns()-disposal
                step_ns=time.perf_counter_ns()-tick
                result['steps'].append(dict(step=step,representation=representation,
                    retained_ids=[r['id'] for r in rows],deleted_ids=[r['id'] for r in deleted],
                    request_elapsed_ns=step_ns,timing=timing,admission=stage_admission,
                    state_bytes=entry['bytes'],trust_bytes=trust_entry['bytes'],
                    complete_deployment_bytes=entry['bytes']+trust_entry['bytes']+p['shared_checkpoint_bytes'],
                    audit_history_physically_retained=True))
                previous_path=out/name
                previous_trust_path=out/trust_name
                previous_rows=rows
                mark('request_complete',step=step,request_elapsed_ns=step_ns)
            result['complete_model']=True
        result['status']='complete'
    except Exception as error:
        result.update(status='failed',error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc())
        raise
    finally:
        result.update(worker_elapsed_ns=time.perf_counter_ns()-start,
            max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            cpu_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
            request_clock_scope='Predecessor load/validation through source access, solver, complete state/model writes and in-process disposal. Context and all admission checks separately included in worker/transaction clocks.',
            worker_clock_scope='Context, all admission, all request/oracle work and artifacts; final completion JSON write and process shutdown are additionally included in controller transaction clock.',
            partial_artifacts_are_not_a_committed_complete_model=result['status']!='complete')
        new(out/'completion.json',result)


if __name__=='__main__':
    main(sys.argv[1])
