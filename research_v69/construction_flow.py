"""One-use matched sequential endpoint construction and saved-code audit.

No standalone launch. The caller must admit actual source/checkpoint/runtime,
original target normalization, production geometry, resource limits and ledger.
"""
from pathlib import Path
import time
from research_v43.dispatcher import ResourcePolicy
from research_v67.io import read,write,info,require,json_read
from research_v69 import model_gate as gate
from src.run_store import canonical_json,digest,strict_json


def membership(records,endpoint,expected_root_sha256):
    require(type(endpoint) is int and endpoint in [12,6],'Exactly the two registered retained endpoints required')
    require(type(records) is list and len(records)==13 and all(type(r) is dict and set(r)=={'id','tokens'}
        and type(r['id']) is str and r['id'] and type(r['tokens']) is list and len(r['tokens'])==128
        and all(type(t) is int and 0<=t<50257 for t in r['tokens']) for r in records),'Actual13x128 root required')
    require([r['id'] for r in records]==sorted({r['id'] for r in records})
        and digest(canonical_json(dict(records=records)))==expected_root_sha256,'Exact canonical root token commitment required')
    retained=records[-endpoint:]
    return retained,digest(canonical_json(dict(records=retained)))


def construct(endpoint,decoder,base,records,candidate_blob,out,*,expected_root_sha256,
              expected_candidate,expected_target_sha256,registration_sha256,policy=ResourcePolicy()):
    retained,rhash=membership(records,endpoint,expected_root_sha256)
    require(type(registration_sha256) is str and len(registration_sha256)==64
        and all(c in '0123456789abcdef' for c in registration_sha256),'Registration commitment required')
    codes=gate.restore(candidate_blob,base,expected_blob=expected_candidate,expected_target_sha256=expected_target_sha256)
    out=Path(out).absolute();require(not any(p.is_symlink() for p in (out,*out.parents)),'Nonsymbolic output required')
    out.mkdir(exist_ok=False);start=time.perf_counter_ns();events=[]
    result=dict(schema='matched-sequential-construction-v69',status='running',endpoint=endpoint,
        registration_sha256=registration_sha256,root_records_sha256=expected_root_sha256,
        retained_records_sha256=rhash,retained_ids=[r['id'] for r in retained],
        base_target_sha256=expected_target_sha256,candidate=expected_candidate,
        artifacts={},error=None,constructor_diagnostics=None,
        actual_source_runtime_resource_and_checkpoint_admission_required_of_caller=True,
        numerical_constructor_independently_reexecuted=False,quality_evaluation=False)
    def mark(row):
        event=dict(stage=row,elapsed_ns=time.perf_counter_ns()-start)
        write(out/f'progress-{len(events):04d}.json',event);events.append(event)
    try:
        sequential,receipt=gate.construct_sequential(decoder,base,retained,codes,
            expected_target_sha256=expected_target_sha256,expected_records_sha256=rhash,policy=policy,progress=mark)
        require(len(events)==len(sequential) and [e['stage'] for e in events]==receipt['diagnostics']['stages'],
            'Complete actual constructor progress required')
        blob=b''.join(s.packed_indices for s in sequential)
        result['artifacts']['model.bin']=write(out/'model.bin',blob,raw=True)
        result['artifacts']['codes.json']=write(out/'codes.json',dict(stages=[s.metadata() for s in sequential]))
        result['artifacts']['construction.json']=write(out/'construction.json',receipt)
        result.update(status='complete',constructor_diagnostics=receipt['diagnostics'])
    except BaseException as exc:
        result.update(status='failed',error=dict(type=type(exc).__name__,message=str(exc)),
            constructor_diagnostics=getattr(exc,'service_diagnostics',result['constructor_diagnostics']));raise
    finally:
        result.update(progress_events=len(events),elapsed_ns=time.perf_counter_ns()-start,
            partial_artifacts_retained=result['status']!='complete')
        write(out/'completion.json',result)
    return result


def audit(directory,base,records,candidate_blob,*,endpoint,expected_root_sha256,
          expected_candidate,expected_target_sha256,registration_sha256):
    """Reparse actual saved codes; does not independently repeat calibration."""
    directory=Path(directory);retained,rhash=membership(records,endpoint,expected_root_sha256)
    candidate=gate.restore(candidate_blob,base,expected_blob=expected_candidate,expected_target_sha256=expected_target_sha256)
    raw=read(directory/'completion.json');c=strict_json(raw);completion_info=info(raw)
    require(type(c) is dict and canonical_json(c)==raw,'Canonical construction completion required')
    require(c['schema']=='matched-sequential-construction-v69' and c['status']=='complete' and c['error'] is None
        and c['endpoint']==endpoint and c['registration_sha256']==registration_sha256
        and c['root_records_sha256']==expected_root_sha256 and c['retained_records_sha256']==rhash
        and c['retained_ids']==[r['id'] for r in retained] and c['base_target_sha256']==expected_target_sha256
        and c['candidate']==expected_candidate and c['partial_artifacts_retained'] is False,
        'Complete bound sequential construction required')
    require(set(c['artifacts'])=={'model.bin','codes.json','construction.json'},'Exact construction output census required')
    artifacts={};objects={}
    for name,e in c['artifacts'].items():
        require(set(e)=={'file','bytes','sha256'} and e['file']==name,'Artifact name binding differs')
        expected={k:e[k] for k in ['bytes','sha256']};artifacts[name]=expected
        objects[name]=read(directory/name,expected,maximum=64*2**20)
    sequential=gate.restore(objects['model.bin'],base,expected_blob=artifacts['model.bin'],expected_target_sha256=expected_target_sha256)
    require(json_read(directory/'codes.json',artifacts['codes.json'])==dict(stages=[s.metadata() for s in sequential]),
        'Actual saved codes and declared grids differ')
    r=json_read(directory/'construction.json',artifacts['construction.json']);d=r['diagnostics']
    require(candidate[0].packed_indices==sequential[0].packed_indices and r['first_stage_equal'] is True
        and r['complete_model']==artifacts['model.bin'] and r['retained_records_sha256']==rhash
        and r['sequential_target_sha256']==expected_target_sha256 and r['stages']==len(sequential)
        and r['code_count']==sum(s.rows*s.columns for s in sequential),'Complete actual sequential model differs')
    require(d==c['constructor_diagnostics'] and d['target_sha256']==expected_target_sha256
        and d['records']==endpoint and d['retained_tokens']==endpoint*128
        and d['neural_stage_record_pairs']==endpoint*len(sequential)
        and d['prior_model_access'] is False and d['prior_factor_access'] is False
        and [row['stage_id'] for row in d['stages']]==[s.stage_id for s in sequential],
        'Complete sequential constructor traversal differs')
    require(type(c['elapsed_ns']) is int and c['elapsed_ns']>=0 and type(c['progress_events']) is int
        and c['progress_events']==len(sequential),'Exact progress extent and bounded clock required')
    names=set(c['artifacts'])|{'completion.json'};previous=0
    for i,row in enumerate(d['stages']):
        name=f'progress-{i:04d}.json';raw=read(directory/name);event=strict_json(raw);artifacts[name]=info(raw)
        require(type(event) is dict and canonical_json(event)==raw,'Canonical actual progress required')
        require(set(event)=={'stage','elapsed_ns'} and event['stage']==row and type(event['elapsed_ns']) is int
            and previous<=event['elapsed_ns']<=c['elapsed_ns'],'Actual ordered progress differs')
        previous=event['elapsed_ns'];names.add(name)
    require({p.name for p in directory.iterdir()}==names,'Unrecognized or missing actual construction output')
    artifacts['completion.json']=completion_info
    for name,e in artifacts.items():read(directory/name,e,maximum=64*2**20,retain=False)
    return dict(status='verified',endpoint=endpoint,actual_model_codes_compared=sum(s.rows*s.columns for s in sequential),
        stages=len(sequential),first_stage_equal=True,artifacts=artifacts,
        numerical_constructor_independently_reexecuted=False,actual_source_runtime_resource_and_checkpoint_audit_still_required=True)
