"""Check a portable V65 metadata capture; this does not re-execute its data audit."""
from pathlib import Path
import hashlib,json,sys

REG='13d9ecb7ddb9ee37ba05498387af490a5e6f16879340c4ec301bbe2aaf5f08d2'
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def require(x,m):
    if not x:raise ValueError(m)
def check(directory,repo):
    d=Path(directory);repo=Path(repo)
    def raw(n):
        p=d/n
        require(p.is_file() and not p.is_symlink() and p.stat().st_size<2**20,'Unsafe metadata extent')
        return p.read_bytes()
    def read(n):return json.loads(raw(n))
    manifest=read('collection-manifest.json');p=read('registration.json')
    require(info(raw('registration.json'))['sha256']==REG and raw('registration.json')==(repo/'handoff/registration_v65.json').read_bytes(),'Registration binding')
    require(manifest['registration_sha256']==REG and manifest['actual_data_audit_verified'] is True
            and manifest['source_text_and_tokens_exported'] is False,'Capture scope')
    require({str(q.relative_to(d)) for q in d.rglob('*') if q.is_file()}==set(manifest['files'])|{'collection-manifest.json'},'Capture census')
    require(len(manifest['files'])==22,'Expected22 payload files')
    for n,e in manifest['files'].items():
        require(not Path(n).is_absolute() and '..' not in Path(n).parts and info(raw(n))==e,'Metadata commitment')
    for n,h in p['historical_sources'].items():require(info((repo/n).read_bytes())['sha256']==h,'Historical source changed')
    for group in ['v63_sources','v64_sources','new_sources']:
        for n,e in p[group].items():require(info((repo/n).read_bytes())==e,'Newer frozen source changed')
    for n,e in p['new_sources'].items():require(info(raw(n))==e,'Executed data source changed')
    jobs={'checks':'15255','data':'15256','audit':'15257'}
    require(read('jobs.json')==jobs,'Job identities')
    sched={f[0]:f for f in [line.split('|') for line in manifest['scheduler'].splitlines()]}
    observed=0;scheduler_cpu=0
    def seconds(value):
        fields=[float(x) for x in value.split(':')]
        require(len(fields) in [2,3],'Scheduler CPU syntax')
        return sum(v*60**i for i,v in enumerate(reversed(fields)))
    receipts={}
    for trial,job in jobs.items():
        r=read(trial+'.json');receipts[trial]=r
        require(r['status']=='complete' and r['error'] is None and r['job_id']==job
                and r['trial']==trial and r['registration_sha256']==REG,'Completion status/binding')
        require(r['caps']==p['caps'][trial] and r['process_cpu_ns']+r['waited_child_cpu_ns']==r['combined_observed_cpu_ns'],'Resource receipt')
        require(0<r['combined_observed_cpu_ns']<=(p['caps'][trial]['cpu']+2)*10**9
                and 0<r['elapsed_ns']<=p['caps'][trial]['wall']*10**9,'Trial cap')
        require(r['model_inference'] is False and r['quality_evaluation'] is False,'Data-only scope')
        require(all(sched[job+s][1:3]==['COMPLETED','0:0'] for s in ['','.batch']),'Scheduler terminal status')
        require(int(sched[job][3])<=p['caps'][trial]['wall'],'Scheduler wall cap')
        scheduler_cpu+=seconds(sched[job][4]);observed+=r['combined_observed_cpu_ns']
        require(read(trial+'-submission.json')['job_id']==job,'Submission binding')
    require(receipts['checks']['result']==dict(tests=9,skipped=0,failures=0,errors=0,corpus_parsed=False),'Nine passing Linux checks')
    require(observed<=1506*10**9 and scheduler_cpu<=1506,'Fresh phase allowance')
    data=receipts['data']['result'];audit=receipts['audit']['result'];selection=read('outputs/selection.json')
    require(data['selection']==audit['selection']==info(raw('outputs/selection.json')),'Selection commitment')
    omitted=manifest['omitted_files']
    require(set(omitted)=={'outputs/records.json','outputs/shard-2-prefix.gz.part','outputs/exclusions-before.json','outputs/exclusions-after.json'},'Explicit omitted data inventory')
    require(data['records']==audit['records']==selection['records']==omitted['outputs/records.json'],'Records commitment')
    require(selection['exclusions_before']==omitted['outputs/exclusions-before.json'],'Protected sets commitment')
    require(data['source_prefix']==selection['source'] and all(selection['source'][k]==v for k,v in omitted['outputs/shard-2-prefix.gz.part'].items()),'Source-prefix commitment')
    require(selection['policy']==p['policy'] and selection['source']['bytes']==2097152
            and selection['source']['content_range']=='bytes 0-2097151/319748667','Actual acquisition policy')
    require(audit['status']=='verified' and all(audit[k] is True for k in ['actual_saved_prefix_retokenized','actual_selected_records_equal','actual_exclusion_sets_equal']),'Saved-byte audit receipt')
    require(audit['independent_implementation'] is False and selection['semantic_deduplication'] is False,'Audit limitation')
    require(all(r['selected_records']==13 and r['calibration_tokens']==1664 and r['confirmation'] is False for r in [data,audit]),'Data scope')
    require(len(selection['selected_metadata'])==13 and len(set(selection['sampling_order_ids']))==13
            and set(selection['sampling_order_ids'])=={r['id'] for r in selection['selected_metadata']},'Selected identity census')
    require(selection['historical_files']==len(p['history'])==360 and selection['candidate_records']==2349
            and selection['historical_shard_one_records_excluded']==2318,'Exposure census')
    return dict(schema='v65-terminal-metadata-check',status='passed',registration_sha256=REG,
        tests=9,skipped=0,source_files_verified=450,historical_metadata_files=360,
        selected_records=13,calibration_tokens=1664,records=data['records'],selection=data['selection'],
        source_prefix=omitted['outputs/shard-2-prefix.gz.part'],protected_counts=selection['protected_counts'],
        combined_observed_cpu_seconds=observed/1e9,scheduler_allocation_cpu_seconds=round(scheduler_cpu,3),
        scheduler_batch_is_duplicate_not_added=True,scheduler=manifest['scheduler'],
        captured_at_utc=manifest['captured_at_utc'],cluster_actual_saved_byte_audit_receipt_verified=True,
        portable_check_reexecutes_data_audit=False,independent_implementation=False,
        model_inference=False,quality_evaluation=False,confirmation=False,
        reporting_helper_correction='Initial collector used8MiB bound but pinned tokenizer extension is11317624B; corrected reporting-only helper to registered128MiB bound. No empirical retry.')
if __name__=='__main__':print(json.dumps(check(*sys.argv[1:]),indent=2,sort_keys=True))
