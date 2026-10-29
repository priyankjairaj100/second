"""Verify V63 metadata, actual-byte audit claims and descriptive size arithmetic.
Omitted numerical inputs/outputs and dependency binaries are NOT revalidated here.
"""
import argparse,hashlib,json
from pathlib import Path
REG='479f7861b06933994916f1d3a22d94caed104dffdcc807c58a73dbacee5ce9d6'
JOBS={'checks':'15244','measure':'15245','audit':'15246'}
def require(v,m):
    if not v:raise ValueError(m)
def info(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def safe(root,n):
    p=root/n;require(not Path(n).is_absolute() and '..' not in Path(n).parts and p.is_file() and not any(q.is_symlink() for q in (p,*p.parents)),'Unsafe local metadata path');return p
def check(root,repo):
    root=Path(root).resolve();repo=Path(repo).resolve()
    def raw(n):return safe(root,n).read_bytes()
    def read(n):return json.loads(raw(n))
    m=read('collection-manifest.json');p=read('registration.json')
    require(info(raw('registration.json'))['sha256']==REG and m['registration_sha256']==REG and m['schema']=='v63-terminal-metadata-capture','Capture/registration identity')
    require(m['numerical_binary_contents_read'] is False and m['frozen_sources_verified']==432,'Capture scope')
    require({str(q.relative_to(root)) for q in root.rglob('*') if q.is_file()}==set(m['files'])|{'collection-manifest.json'},'Metadata census')
    for n,e in m['files'].items():require(info(raw(n))==e,'Copied file differs: '+n)
    for n,e in p['new_sources'].items():require(info(raw(n))==info(safe(repo,n).read_bytes())==e,'Executed/local new source differs')
    for n,h in p['frozen_sources'].items():require(info(safe(repo,n).read_bytes())['sha256']==h,'Frozen numerical source changed')
    require(m['jobs']==read('jobs.json')==JOBS and m['scheduler']['successful'] is True and not m['scheduler']['queue'].strip(),'Scheduler gate')
    steps={}
    for line in m['scheduler']['accounting'].splitlines():
        f=line.split('|');require(f[0] not in steps,'Duplicate accounting row');steps[f[0]]=f
    receipts={}
    for trial,job in JOBS.items():
        require(job in steps and job+'.batch' in steps,'Missing allocation/batch row')
        for label in (job,job+'.batch'):
            f=steps[label];require(f[2:4]==['COMPLETED','0:0'] and f[4].isdigit() and 0<int(f[4])<=p['caps'][trial]['wall'],'Scheduler completion/cap')
        r=read(trial+'.json');receipts[trial]=r
        require(r['status']=='complete' and r['error'] is None and r['trial']==trial and r['slurm_job_id']==job and r['registration_sha256']==REG and r['caps']==p['caps'][trial] and r['original_inputs_mutated'] is False,'Bound complete receipt')
        require(0<r['process_cpu_ns']<=(p['caps'][trial]['cpu']+1)*10**9 and 0<r['elapsed_ns']<=p['caps'][trial]['wall']*10**9,'Process accounting cap')
        begin=read(trial+'-start.json');require(begin==dict(trial=trial,registration_sha256=REG,slurm_job_id=job,caps=p['caps'][trial],status='started'),'Exclusive start binding')
        submission=read(trial+'-submission.json');require(submission['job_id']==job and submission['registration_sha256']==REG,'Submission binding')
        args=submission['arguments'];require('--no-requeue' in args and '--mem=16G' in args and args[-3:]==[p['run_directory']+'/registration.json',REG,trial],'Submission options')
        if trial!='checks':require('--dependency=afterok:'+JOBS['checks' if trial=='measure' else 'measure'] in args and '--kill-on-invalid-dep=yes' in args,'Sequential dependency')
    gate=receipts['checks']['result'];measurement=receipts['measure']['result'];audit=receipts['audit']['result']
    require(gate['tests']==21 and gate['skipped']==0 and gate['empirical_inputs_opened'] is False,'21/0 Linux gate')
    require(measurement['codec_manifest']==gate['codec_manifest'] and measurement['codec_binding']==gate['codec_binding']==info(canonical(gate['codec_manifest']))['sha256'],'Same codec runtime')
    cm=gate['codec_manifest'];require(cm['native_sha256']==p['wheel']['extracted_files']['zstandard/backend_c.cpython-312-x86_64-linux-gnu.so']['sha256'] and cm['source_sha256']==p['new_sources']['research_v63/codec.py']['sha256'],'Actual codec implementation binding')
    require(audit['status']=='verified' and audit['measurement_receipt']==info(raw('measure.json')) and len(audit['comparisons'])==len(measurement['endpoints'])==3,'Read-only actual-artifact audit')
    require(measurement['neural_execution'] is False and measurement['calibration'] is False and measurement['quality_evaluation'] is False and measurement['deletion_latency_measured'] is False and measurement['independent_neural_oracle'] is False,'Scientific scope')
    deps=sum(e['bytes'] for e in p['wheel']['extracted_files'].values());sources=sum(e['bytes'] for e in p['new_sources'].values())
    require(measurement['added_dependency_bytes']==deps and measurement['added_control_source_bytes']==sources,'Added dependency byte census')
    require(raw('trust.json')==b'{}' and measurement['trust_sidecar']==info(b'{}'),'Literal trust sidecar')
    expected=dict(p['inputs']);summary=[]
    for i,(row,a) in enumerate(zip(measurement['endpoints'],audit['comparisons'])):
        require(row==read('endpoint-'+str(i)+'.json') and row['index']==a['endpoint']==i and row['retained_records']==p['retained_counts'][i]
            and row['retained_tokens']==128*p['retained_counts'][i] and row['source_count']==a['source_count']==p['factor_counts'][i],'Endpoint census/binding')
        require(row['artifact']==a['new_archive'] and row['reference_model']==p['inputs'][p['models'][i]],'Archive/model commitment')
        for k in ('actual_words_equal','actual_model_equal','actual_reference_state_restored'):require(a[k] is True,'Missing actual-byte audit comparison')
        require(a['actual_retained_transition_equal']==(None if i==0 else True),'Actual transition comparison')
        require(row['old_state_bytes']==p['inputs'][p['states'][i]]['bytes'] and row['new_archive_bytes']==row['artifact']['bytes'],'Literal full-state extents')
        require(row['old_live_bytes']==row['old_state_bytes']+2 and row['new_live_bytes']==row['new_archive_bytes']+2,'Trust-inclusive storage')
        require(row['old_checkpoint_inclusive_bytes']==row['old_live_bytes']+p['common_deployment_bytes'] and row['new_checkpoint_inclusive_bytes']==row['new_live_bytes']+p['common_deployment_bytes'] and row['new_checkpoint_plus_added_dependency_bytes']==row['new_checkpoint_inclusive_bytes']+deps+sources,'Dependency-inclusive byte arithmetic')
        rows=row['source_rows'];require(len(rows)==row['source_count'] and len({(r['stage_id'],r['record_id']) for r in rows})==len(rows),'Unique factor receipts')
        modes={str(k):0 for k in range(5)}
        for r in rows:
            require(r['actual_words_equal'] is True and r['new_mode'] in range(5),'Source equality/mode')
            candidates=r['candidate_encodes'];require([v['mode'] for v in candidates]==list(range(5)),'All fixed mode costs')
            require(r['new_mode']==min(candidates,key=lambda v:(v['payload_bytes']+len(str(v['payload_bytes'])),v['mode']))['mode'],'Deterministic size selection')
            require(all(type(v['encode_ns']) is int and v['encode_ns']>=0 for v in candidates) and sum(v['encode_ns'] for v in candidates)<=r['new_encode_serialize_ns'],'Nested encode clocks')
            for key in ('old_parse_and_decode_ns','new_encode_serialize_ns','new_canonical_parse_ns','new_decode_only_ns'):require(type(r[key]) is int and r[key]>=0,'Finite component clock')
            modes[str(r['new_mode'])]+=1
        expected[p['run_directory']+'/endpoint-'+str(i)+'.bin']=row['artifact']
        summary.append(dict(retained_records=row['retained_records'],old_live_bytes=row['old_live_bytes'],new_live_bytes=row['new_live_bytes'],new_live_saving=1-row['new_live_bytes']/row['old_live_bytes'],old_checkpoint_inclusive_bytes=row['old_checkpoint_inclusive_bytes'],new_checkpoint_inclusive_bytes=row['new_checkpoint_inclusive_bytes'],new_checkpoint_plus_added_dependency_bytes=row['new_checkpoint_plus_added_dependency_bytes'],new_dependency_inclusive_saving=1-row['new_checkpoint_plus_added_dependency_bytes']/row['old_checkpoint_inclusive_bytes'],mode_counts=modes,observed_total_endpoint_seconds=row['total_endpoint_ns']/1e9))
    require(m['omitted_inputs_outputs']==expected,'Complete omitted input/output inventory')
    for n,e in m['files'].items():require(info(raw(n))==e,'Final metadata changed')
    return dict(schema='v63-portable-metadata-check',status='verified_metadata_only',registration_sha256=REG,source_files_checked=432,new_source_files_checked=len(p['new_sources']),software_tests=21,software_skips=0,endpoint_comparison_claims_checked=3,numerical_binaries_locally_revalidated=False,dependency_binaries_locally_revalidated=False,deletion_latency_measured=False,quality_evaluation=False,confirmation=False,acl_ready=False,summary=summary,added_dependency_bytes=deps,added_control_source_bytes=sources,scheduler_accounting=m['scheduler']['accounting'],source_review='Root review; no independent reviewer',audit_receipt=info(raw('audit.json')))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--repo',required=True);p.add_argument('--output',required=True);a=p.parse_args();result=check(a.directory,a.repo)
    with Path(a.output).open('xb') as f:f.write(canonical(result))
    print(json.dumps(result,indent=2))
