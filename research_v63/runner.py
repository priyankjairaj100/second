"""One-attempt Linux qualification and artifact-only lossless control."""
from pathlib import Path
import hashlib
import json
import os
import resource
import sys
import time
import traceback

ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/lossless-control-v63-20261016-a'
TESTS=21
CAPS={'checks':dict(cpu=300,wall=600),'measure':dict(cpu=3600,wall=3900),'audit':dict(cpu=1800,wall=2100)}


def require(v,m):
    if not v:raise ValueError(m)


def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def info(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def strict(raw):
    def pairs(rows):
        d={}
        for k,v in rows:require(k not in d,'Duplicate JSON key');d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def bound(path,e,maximum=1024*2**20):
    path=Path(path);require(path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)),'Unsafe input')
    a=path.stat();require(a.st_size==e['bytes'] and a.st_size<=maximum,'Input extent exceeds bound')
    raw=path.read_bytes();b=path.stat()
    require((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns),'Input changed during read')
    require(info(raw)==e,'Input commitment differs: '+str(path));return raw


def new(path,value,raw=False):
    data=value if raw else canonical(value)
    with Path(path).open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    return info(data)


def validate_plan(p,expected):
    require(info(canonical(p))['sha256']==expected and p['schema']=='source-local-lossless-artifact-control-v63','Registration differs')
    require(p['run_directory']==str(RUN) and p['trials']==['checks','measure','audit'] and p['caps']==CAPS,'Scope/caps changed')
    require(p['neural_execution'] is False and p['calibration'] is False and p['quality_evaluation'] is False
        and p['automatic_retry'] is False and p['expected_tests']==TESTS,'Execution scope changed')
    require(len(p['frozen_sources'])==432 and len(p['states'])==3 and len(p['models'])==3,'Input census differs')
    require(p['retained_counts']==[13,12,6] and p['factor_counts']==[312,288,144],'Fixed endpoint census differs')
    for key in ('frozen_sources','new_sources'):
        for n in p[key]:require(not Path(n).is_absolute() and '..' not in Path(n).parts,'Unsafe source path')
    for n in p['inputs']:require(Path(n).is_absolute() and ROOT in Path(n).parents,'Foreign empirical input')
    return p


def bindings(p):
    for n,h in p['frozen_sources'].items():require(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,'Frozen source changed')
    for n,e in p['new_sources'].items():bound(RUN/n,e,2**20)
    for n,e in p['wheel']['extracted_files'].items():bound(RUN/'deps'/n,e,128*2**20)
    bound(RUN/p['wheel']['filename'],dict(bytes=p['wheel']['bytes'],sha256=p['wheel']['sha256']),16*2**20)
    from research_v61.campaign import runtime
    require(runtime()==p['base_runtime'],'Frozen base runtime changed')


def checks(p):
    import unittest
    from research_v63 import codec
    suite=unittest.defaultTestLoader.loadTestsFromNames(['research_v63.test_control','research_v63.test_runner'])
    r=unittest.TextTestRunner(verbosity=2).run(suite)
    require(r.wasSuccessful() and r.testsRun==TESTS and not r.skipped,'Linux software gate failed')
    return dict(tests=r.testsRun,skipped=0,codec_manifest=codec.codec_manifest(),codec_binding=codec.codec_binding(),empirical_inputs_opened=False)


def measure(p):
    from research_v61 import state as old
    from src import fixed_lossless_codec_v29 as prior
    from research_v63 import codec,archive
    import gc
    report=dict(schema='source-local-lossless-artifact-measurement-v63',endpoints=[],neural_execution=False,
        calibration=False,quality_evaluation=False,deletion_latency_measured=False,independent_neural_oracle=False)
    report['added_dependency_bytes']=sum(e['bytes'] for e in p['wheel']['extracted_files'].values())
    report['added_control_source_bytes']=sum(e['bytes'] for e in p['new_sources'].values())
    report['trust_sidecar']=new(RUN/'trust.json',{})
    previous=None;target=None
    for index,(state_path,model_path) in enumerate(zip(p['states'],p['models'])):
        begin=time.perf_counter_ns();raw=bound(state_path,p['inputs'][state_path]);v=old.validate_state(raw)
        model=bound(model_path,p['inputs'][model_path]);require(b''.join(c.packed_indices for c in v.stage_codes)==model,'Actual reference model differs')
        require(v.representation=='lossless' and len(v.records)==p['retained_counts'][index]
            and len(v.source_payloads)==p['factor_counts'][index],'Actual endpoint shape differs')
        require(old.sha(v.target.fixed_payload)==p['service_target_sha256'],'Reference service identity differs')
        require(target is None or target==v.target,'Endpoint target changed');target=v.target
        migration_ns=time.perf_counter_ns()-begin;new_sources={};rows=[]
        for sid,rid,blob in v.source_payloads:
            start=time.perf_counter_ns();d=prior.parse(blob);words=d.binary64();old_decode_ns=time.perf_counter_ns()-start
            measurements=[];start=time.perf_counter_ns()
            encoded=codec.encode_factor(codec.np.frombuffer(words,dtype="<f8").reshape(d.shape),target_sha256=d.target_sha256,anchor_target_sha256=d.anchor_target_sha256,
                record_id=rid,token_sha256=d.token_sha256,stage_id=sid,measurements=measurements)
            newblob=codec.serialize(encoded);encode_ns=time.perf_counter_ns()-start
            start=time.perf_counter_ns();parsed=codec.parse(newblob);validate_ns=time.perf_counter_ns()-start
            start=time.perf_counter_ns();decoded=parsed.binary64();decode_ns=time.perf_counter_ns()-start
            require(decoded==words,'Actual binary64 words changed')
            new_sources[sid,rid]=newblob
            rows.append(dict(stage_id=sid,record_id=rid,raw_bytes=len(words),old_descriptor_bytes=len(blob),
                new_descriptor_bytes=len(newblob),new_mode=encoded.mode,candidate_encodes=measurements,
                old_parse_and_decode_ns=old_decode_ns,new_encode_serialize_ns=encode_ns,
                new_canonical_parse_ns=validate_ns,new_decode_only_ns=decode_ns,actual_words_equal=True))
        start=time.perf_counter_ns();packed=archive.pack(v.target,v.records,v.stage_codes,new_sources);pack_ns=time.perf_counter_ns()-start
        start=time.perf_counter_ns();fresh=archive.unpack(packed);unpack_ns=time.perf_counter_ns()-start
        require(b''.join(c.packed_indices for c in fresh.stage_codes)==model,'Actual archived model codes changed')
        start=time.perf_counter_ns();restored=archive.restore(fresh);restore_ns=time.perf_counter_ns()-start
        require(restored==raw,'Full original state byte restoration differs')
        transition_ns=None
        if previous is not None:
            start=time.perf_counter_ns();transitioned=archive.transition(previous,v.records,v.stage_codes);transition_ns=time.perf_counter_ns()-start
            require(transitioned==packed,'Retained descriptor transition differs from fresh artifact repack')
            del transitioned
        artifact=new(RUN/('endpoint-'+str(index)+'.bin'),packed,True)
        require(bound(RUN/('endpoint-'+str(index)+'.bin'),artifact)==packed,'Stored archive bytes differ')
        row=dict(index=index,retained_records=len(v.records),retained_tokens=sum(len(r.tokens) for r in v.records),
            old_state_bytes=len(raw),new_archive_bytes=len(packed),trust_bytes=2,
            old_live_bytes=len(raw)+2,new_live_bytes=len(packed)+2,
            old_checkpoint_inclusive_bytes=len(raw)+2+p['common_deployment_bytes'],
            new_checkpoint_inclusive_bytes=len(packed)+2+p['common_deployment_bytes'],
            new_checkpoint_plus_added_dependency_bytes=len(packed)+2+p['common_deployment_bytes']+report['added_dependency_bytes']+report['added_control_source_bytes'],
            reference_model=info(model),artifact=artifact,source_count=len(rows),source_rows=rows,
            input_read_validate_model_ns=migration_ns,pack_validate_ns=pack_ns,unpack_validate_ns=unpack_ns,
            restore_old_format_ns=restore_ns,transition_with_supplied_codes_ns=transition_ns,
            actual_source_words_equal=True,actual_model_bytes_equal=True,actual_old_state_restoration_equal=True,
            actual_transition_equals_fresh_repack=None if index==0 else True,
            total_endpoint_ns=time.perf_counter_ns()-begin)
        report['endpoints'].append(row);new(RUN/('endpoint-'+str(index)+'.json'),row)
        previous=fresh
        del raw,restored,v,model,new_sources,packed,blob,d,words,encoded,newblob,parsed,decoded
        gc.collect();print(json.dumps(dict(endpoint=index,retained=row['retained_records'],archive_bytes=row['new_archive_bytes'],status='verified_artifact_only')),flush=True)
    report['codec_manifest']=codec.codec_manifest();report['codec_binding']=codec.codec_binding()
    return report


def audit(p,expected):
    from research_v63 import archive,codec
    from research_v61 import state as old
    from src import fixed_lossless_codec_v29 as prior
    receipt=strict((RUN/'measure.json').read_bytes())
    require(receipt['status']=='complete' and receipt['registration_sha256']==expected,'Complete bound measurement required')
    measured=receipt['result'];require(len(measured['endpoints'])==3,'Complete measurement census required')
    require(bound(RUN/'trust.json',measured['trust_sidecar'])==b'{}','Actual empty trust sidecar differs')
    results=[];previous=None
    for i,row in enumerate(measured['endpoints']):
        require(row['index']==i and row['source_count']==p['factor_counts'][i] and len(row['source_rows'])==row['source_count'],'Endpoint/source census')
        original=bound(p['states'][i],p['inputs'][p['states'][i]])
        ov=old.validate_state(original)
        data=bound(RUN/('endpoint-'+str(i)+'.bin'),row['artifact']);view=archive.unpack(data)
        require(view.target==ov.target and view.records==ov.records and view.stage_codes==ov.stage_codes,'Target, membership or code bytes differ')
        require(archive.restore(view)==original,'Stored archive does not restore actual reference state')
        model=bound(p['models'][i],p['inputs'][p['models'][i]])
        require(b''.join(c.packed_indices for c in view.stage_codes)==model,'Stored model differs')
        originals=ov.source_map();mapped=view.source_map()
        require(set(mapped)==set(originals),'Actual factor census differs')
        rows={(r['stage_id'],r['record_id']):r for r in row['source_rows']}
        require(len(rows)==len(row['source_rows']) and set(rows)==set(mapped),'Factor receipt census differs')
        for key,blob in mapped.items():
            d=codec.parse(blob);words=d.binary64();oldblob=originals[key];reference=prior.parse(oldblob)
            require(words==reference.binary64(),'Actual decoded words differ')
            r=rows[key]
            require(r['raw_bytes']==len(words) and r['old_descriptor_bytes']==len(oldblob) and r['new_descriptor_bytes']==len(blob) and r['new_mode']==d.mode and r['actual_words_equal'] is True,'Factor receipt sizes/mode differ')
            encodes=r['candidate_encodes'];require([x['mode'] for x in encodes]==list(codec.MODES),'All candidate costs required')
            require(all(type(x['encode_ns']) is int and x['encode_ns']>=0 and type(x['payload_bytes']) is int and x['payload_bytes']>=0 for x in encodes),'Invalid candidate cost')
            require(sum(x['encode_ns'] for x in encodes)<=r['new_encode_serialize_ns'],'Nested candidate clocks exceed encode clock')
        if previous is not None:require(archive.transition(previous,ov.records,ov.stage_codes)==data,'Stored successor differs from retained descriptor transition')
        require(row['old_state_bytes']==len(original) and row['new_archive_bytes']==len(data)
            and row['old_live_bytes']==len(original)+2 and row['new_live_bytes']==len(data)+2,'Complete state accounting differs')
        require(row['old_checkpoint_inclusive_bytes']==len(original)+2+p['common_deployment_bytes']
            and row['new_checkpoint_inclusive_bytes']==len(data)+2+p['common_deployment_bytes']
            and row['new_checkpoint_plus_added_dependency_bytes']==len(data)+2+p['common_deployment_bytes']+sum(x['bytes'] for x in p['wheel']['extracted_files'].values())+sum(x['bytes'] for x in p['new_sources'].values()),'Dependency-inclusive accounting differs')
        results.append(dict(endpoint=i,actual_words_equal=True,actual_model_equal=True,actual_reference_state_restored=True,
            actual_retained_transition_equal=None if i==0 else True,new_archive=row['artifact'],source_count=len(mapped)))
        previous=view
    return dict(schema='source-local-lossless-artifact-audit-v63',status='verified',comparisons=results,
        measurement_receipt=info((RUN/'measure.json').read_bytes()),neural_execution=False,deletion_latency_measured=False,
        independent_numerical_implementation=False)


def execute(path,expected,trial):
    require(trial in CAPS and Path(path)==RUN/'registration.json' and sys.platform=='linux' and os.environ.get('SLURM_JOB_ID','').isdigit(),'Linux Slurm and bound plan required')
    require(Path(__file__).resolve()==RUN/'research_v63/runner.py','Wrong source location')
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):require(os.environ.get(k)=='1','Single thread required')
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});cap=CAPS[trial]
    resource.setrlimit(resource.RLIMIT_CPU,(cap['cpu'],cap['cpu']+1));resource.setrlimit(resource.RLIMIT_AS,(16*2**30,)*2)
    resource.setrlimit(resource.RLIMIT_FSIZE,(1024*2**20,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    raw=Path(path).read_bytes();p=strict(raw);require(raw==canonical(p),'Noncanonical plan');validate_plan(p,expected)
    require(not (RUN/(trial+'.json')).exists(),'Existing trial result')
    start=time.perf_counter_ns();cpu=time.process_time_ns()
    base=dict(trial=trial,registration_sha256=expected,slurm_job_id=os.environ['SLURM_JOB_ID'],caps=cap)
    new(RUN/(trial+'-start.json'),dict(base,status='started'))
    error=None;result=None
    try:
        bindings(p)
        if trial=='checks':result=checks(p)
        else:
            gate=strict((RUN/'checks.json').read_bytes())
            require(gate['status']=='complete' and gate['registration_sha256']==expected and gate['result']['tests']==TESTS and gate['result']['skipped']==0,'Passing same-registration Linux gate required')
            from research_v63 import codec
            require(gate['result']['codec_manifest']==codec.codec_manifest(),'Gate codec runtime changed')
            for n,e in p['inputs'].items():
                if n not in p['states'] and n not in p['models']:bound(n,e,2**20)
            result=measure(p) if trial=='measure' else audit(p,expected)
            # Rehash every registered input after measurement; no old artifact can be rewritten.
            for n,e in p['inputs'].items():bound(n,e)
        bindings(p)
    except Exception as exc:
        error=dict(type=type(exc).__name__,message=str(exc));traceback.print_exc()
    new(RUN/(trial+'.json'),dict(base,status='complete' if error is None else 'failed',error=error,result=result,
        elapsed_ns=time.perf_counter_ns()-start,process_cpu_ns=time.process_time_ns()-cpu,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        original_inputs_mutated=False if error is None else None))
    require(error is None,'Trial failed; preserve evidence, no retry')


if __name__=='__main__':
    sys.path[:0]=[str(RUN/'deps'),str(RUN),str(ROOT)]
    require(len(sys.argv)==4,'Expected registration, digest and trial')
    execute(*sys.argv[1:])
