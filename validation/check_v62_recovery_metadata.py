"""Check original V61 failure plus separately captured V62 recovery metadata.
Actual numerical bytes remain remote; this never rewrites failed scheduler rows
or pretends the original 30-minute audit passed. Reuses the unchanged V61 worker,
progress, comparison and cost checks with explicit new audit paths and job IDs.
"""
from check_v61_terminal_metadata import *
import check_v61_terminal_metadata as base

RECOVERY = REMOTE+'/local_runs/audit-recovery-v62-20261015-a'
RECOVERY_JOBS = dict(primary='15150',postrun='15151')
REGISTRATION_SHA = '531d530feb42feca040dab0f5f288136152f80463611a391d8404dfd82b8192b'
FAILURE_MANIFEST_SHA = '65c1cd2da06dddb28be13e2403c4d8f76292626499d2f33949a44739dc21e841'
BASE_CHECKER_SHA = 'd6c6e4dd27ddb86f285ecd1be35ac37b413d115c931c6aa0175832a52d2ab3bd'


def original_rows(m):
    rows={}
    for line in m['scheduler'].splitlines():
        if not line.strip():continue
        f=line.split('|');f=f[:-1] if f[-1]=='' else f
        require(len(f)==8 and f[0] in JOBS.values() and f[0] not in rows,'Original scheduler census')
        expected='TIMEOUT' if f[0]=='13569' else 'CANCELLED' if f[0]=='13570' else 'COMPLETED'
        require(f[2]==expected and f[3]=='0:0' and f[4].isdigit(),'Original failure/completion history changed')
        rows[f[0]]=dict(job_name=f[1],state=f[2],raw_state=f[2],exit_code=f[3],elapsed_seconds=f[4],total_cpu=f[5],start=f[6],end=f[7])
    require(set(rows)==set(JOBS.values()),'All ten original scheduler rows required')
    equal(rows,m['scheduler_jobs'],'Raw original scheduler bindings')
    return rows


def recovery_rows(m):
    rows={}
    for line in m['scheduler'].splitlines():
        if not line.strip():continue
        f=line.split('|');f=f[:-1] if f[-1]=='' else f
        require(len(f)==8 and f[0] in RECOVERY_JOBS.values() and f[0] not in rows,'Recovery scheduler census')
        require(f[2]=='COMPLETED' and f[3]=='0:0' and f[4].isdigit() and 0<int(f[4])<=3900,'Recovery job failed or exceeded wall cap')
        rows[f[0]]=dict(job_name=f[1],state=f[2],exit_code=f[3],elapsed_seconds=int(f[4]),total_cpu=f[5],start=f[6],end=f[7])
    require(set(rows)==set(RECOVERY_JOBS.values()),'Two complete recovery jobs required')
    require(not m['scheduler_queue'].strip(),'Recovery jobs still active')
    return rows


class RecoveryCheck(base.Check):
    def __init__(self,original,recovery,repo):
        super().__init__(original,repo);self.recovery_root=Path(recovery).resolve()
        self.recovery_manifest=None
    def recovery_local(self,n):return safe(self.recovery_root,n)
    def recovery_json(self,n):return read_json(self.recovery_local(n))

    def collection(self):
        raw=read_bytes(self.local('collection-manifest.json'));m=strict(raw);self.manifest=m
        require(digest(raw)==FAILURE_MANIFEST_SHA,'Exact original failure capture required')
        require(m['schema']=='second-terminal-v61-metadata-v1' and m['reported_success'] is False
            and m['capture_scope']=='terminal_failure_or_incomplete_receipts_metadata_only'
            and m['terminal'] is True and m['quiescent'] is True,'Original audit failure must remain explicit')
        for n,e in m['files'].items():equal(info(read_bytes(self.local(n))),commitment(e),'Original copied metadata '+n)
        require({str(p.relative_to(self.root)) for p in self.root.rglob('*') if p.is_file()}==set(m['files'])|{'collection-manifest.json'},'Original copied census')
        require(m['source_files_verified']==432 and m['cluster_commit']==SOURCE_COMMIT and m['program_sha256']==PROGRAM_SHA
            and m['excluded_binary_contents_rehashed'] is False and m['final_metadata_bytes_rehashed'] is True,'Original capture scope')
        original_rows(m)
        rraw=read_bytes(self.recovery_local('collection-manifest.json'));r=strict(rraw);self.recovery_manifest=r
        require(r['schema']=='second-audit-recovery-capture-v62' and r['registered_program_sha256']==REGISTRATION_SHA
            and r['old_failure_manifest_sha256']==FAILURE_MANIFEST_SHA and r['old_campaign_unmodified'] is True
            and r['binary_contents_read'] is False and r['terminal_success'] is True,'Recovery capture identity/scope')
        for n,e in r['files'].items():equal(info(read_bytes(self.recovery_local(n))),commitment(e),'Recovery copied metadata '+n)
        require({str(p.relative_to(self.recovery_root)) for p in self.recovery_root.rglob('*') if p.is_file()}==set(r['files'])|{'collection-manifest.json'},'Recovery copied census')
        self.recovery_scheduler=recovery_rows(r)
        p=self.recovery_json('registration.json');self.recovery_plan=p
        require(digest(canonical(p))==REGISTRATION_SHA and p['program_sha256']==PROGRAM_SHA,'Pinned recovery registration')
        equal(p['original_outcomes'],{'13569':'TIMEOUT','13570':'CANCELLED'},'Preserved original outcomes')
        equal(p['metadata_inputs'],{n:m['files'][rel] for n,rel in m['repository_paths'].items()},'All original metadata pinned')
        equal(p['binary_inputs'],{n:e['expected'] for n,e in m['inputs_not_copied'].items() if e['kind']=='numerical_binary'},'All original binary commitments pinned')
        for n,e in p['wrapper_sources'].items():
            equal(info(read_bytes(self.recovery_local(n))),e,'Executed recovery source')
            equal(info(read_bytes(self.repo/'research_v62'/n)),e,'Local recovery source')
        equal(info(read_bytes(self.repo/'cluster_setup/run_cpu.sbatch')),p['slurm_wrapper'],'Pinned launch wrapper')
        require(digest(read_bytes(self.repo/'validation/check_v61_terminal_metadata.py'))==BASE_CHECKER_SHA,'Base metadata checker changed')
        equal(self.recovery_json('jobs.json'),RECOVERY_JOBS,'Recovery submitted IDs')
        software=self.recovery_json('software.json')
        equal(software,dict(status='passed',tests=8,skipped=0,registration_sha256=REGISTRATION_SHA,slurm_job_id=RECOVERY_JOBS['primary'],scope='Wrapper boundary fixtures, not numerical evidence'),'Linux wrapper fixtures')
        for trial,job in RECOVERY_JOBS.items():
            submitted=self.recovery_json(trial+'-submission.json')
            args=['sbatch','--parsable','--no-requeue','--nodelist=csis.mn1','--mem=16G','--time=01:05:00','--job-name=second62-'+trial,'--output='+RECOVERY+'/'+trial+'-%j.log']
            if trial=='postrun':args+=['--dependency=afterok:15150','--kill-on-invalid-dep=yes']
            args+=['cluster_setup/run_cpu.sbatch','local_runs/cluster-setup-20261010/container-13155.sha256',RECOVERY+'/audit_recovery.py',RECOVERY+'/registration.json',REGISTRATION_SHA,trial]
            equal(submitted,dict(job_id=job,arguments=args,registration_sha256=REGISTRATION_SHA),'Exact recovery submission and dependency')
            begin=self.recovery_json(trial+'-start.json');done=self.recovery_json(trial+'-wrapper.json')
            require(begin['status']=='started' and done['status']=='complete' and done['error'] is None,'Exclusive recovery attempt complete')
            for row in (begin,done):
                require(row['trial']==trial and row['slurm_job_id']==job and row['registration_sha256']==REGISTRATION_SHA,'Recovery wrapper binding')
                equal(row['limits'],p['limits'],'Recovery applied limits')
                require(len(row['affinity'])==1 and type(row['affinity'][0]) is int and row['affinity'][0]>=0,'Recovery affinity')
                equal(row['thread_environment'],{k:'1' for k in ('MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS')},'Complete recovery thread environment')
            require(done['original_audit_failure_preserved'] is True and done['old_campaign_mutated'] is False
                and done['numerical_execution'] is False and 0<done['process_cpu_ns']<=3601*10**9
                and 0<done['elapsed_ns']<=3900*10**9,'Recovery runtime/scope')
            equal(info(read_bytes(self.recovery_local(trial+'.json'))),done['audit_output'],'Actual audit output hash')
            require(self.recovery_json(trial+'.json')['slurm_job_id']==job,'Output job binding')
        return m

    def scheduler(self):self.scheduler_rows=original_rows(self.manifest)

    def registration(self):
        self.p=self.copied('program.json');p=self.p
        require(digest(canonical(p))==digest(read_bytes(self.local(CAMPAIGN+'/program.json')))==PROGRAM_SHA,
            'Pinned registered V61 program changed')
        equal(self.copied('registration.json'),dict(program_sha256=PROGRAM_SHA),'Registration binding')
        require(p['directory']==DIRECTORY and p['registered_source_commit']==SOURCE_COMMIT,'Program path/source commit')
        require(read_bytes(self.local(LAUNCH+'/source-commit.txt')).decode().strip()==SOURCE_COMMIT,'Launch commit')
        jobs=[line.split('\t') for line in read_bytes(self.local(LAUNCH+'/jobs.tsv')).decode().splitlines()]
        require([x[0] for x in jobs]==['register',*ORDER,'audit','postrun'] and all(len(x)==2 and x[1].isdigit() for x in jobs),'Nine-stage launch census/order')
        self.jobs=dict(jobs);require(len(set(self.jobs.values()))==9,'Duplicate job ID')
        require(p['registration_job']==self.jobs['register'],'Registration job')
        require(len(p['sources'])==432,'Exactly432 frozen sources required')
        for name,expected in p['sources'].items():
            local=info(read_bytes(safe(self.repo,name)))
            require(local['sha256']==expected,'Local registered source changed: '+name)
            self.bind(REMOTE+'/'+name,local)
        for entry in p['inputs'].values(): self.bind(entry['path'],entry)
        old=self.input('v59_program')
        require(len(old['sources'])==412 and all(p['sources'].get(k)==v for k,v in old['sources'].items()),'V59 frozen source preservation')
        extra={str(path.relative_to(self.repo)) for path in (self.repo/'research_v61').iterdir()
               if path.is_file() and (path.suffix=='.py' or path.name=='PROTOCOL.txt')}
        extra.add('cluster_setup/v61_pipeline.sh')
        require(set(p['sources'])==set(old['sources'])|extra,'Exact source census including all V61 implementation')
        check=self.input('software_checks')
        require(p['inputs']['software_checks']['sha256']==SOFTWARE_SHA,'Pinned software receipt')
        modules=literal_assignment(self.repo/'research_v61/checks.py','MODULES')
        require(check['status']=='passed' and type(check['tests']) is int and check['tests']==205
            and type(check['skipped']) is int and check['skipped']==0 and check['modules']==list(modules)
            and check['real_model_inference'] is False and check['source_and_runtime_unchanged'] is True,'Complete205/0 software gate')
        equal(check['sources'],p['sources'],'Software sources');equal(check['runtime'],p['runtime'],'Software runtime')
        self.jobs['checks']=check['slurm_job_id']
        require(len(set(self.jobs.values()))==10,'Ten distinct software/launch jobs required')
        equal(self.jobs,JOBS,'Frozen launch job IDs')
        logs=[LAUNCH+'/'+label+'-'+jid+'.log' for label,jid in self.jobs.items() if label not in ('checks','postrun')]
        logs.append('continuation-v61-software-20261014-a/checks-'+self.jobs['checks']+'.log')
        require(all(name in self.manifest['files'] for name in logs),'All nine executed original jobs must have logs')
        require(LAUNCH+'/postrun-13570.log' not in self.manifest['files'],'Cancelled original postrun unexpectedly executed')
        self.scheduler()
        histories=self.manifest['historical_ledger_bindings']
        require(set(histories)=={REMOTE+'/'+name for name in p['historical_ledgers']},'Historical ledger census')
        for name,expected in p['historical_ledgers'].items():
            remote=REMOTE+'/'+name;data=read_bytes(self.path(remote));entry=histories[remote]
            require(digest(data)==expected and entry['expected_sha256']==expected and entry['verified'] is True
                and entry['observed_bytes']==len(data) and entry['archive_file']==self.manifest['repository_paths'][remote],
                'Historical ledger unchanged binding: '+name)
        self.prior()
        paths=sorted((self.repo/'src').glob('*.py'))+sorted((self.repo/'scripts').glob('run_*.py'))
        sources={str(path.relative_to(self.repo)):digest(read_bytes(path)) for path in paths}
        require(len(sources)==158 and all(p['sources'].get(k)==v for k,v in sources.items()),'Complete158 ledger source subset')
        raw=read_bytes(self.local(CAMPAIGN+'/budget/ledger.json'))
        self.ledger,self.snapshot=validate_ledger(raw,sources)
        self.bind(DIRECTORY+'/budget/ledger.json',info(raw))


    def audits(self):
        a=self.recovery_json('primary.json');b=self.recovery_json('postrun.json')
        primary_expected=copy.deepcopy(self.expected)
        inventory_equal(a['inputs'],primary_expected,'Complete primary audit Inputs')
        post_expected=dict(primary_expected)
        post_expected[RECOVERY+'/primary.json']=info(read_bytes(self.recovery_local('primary.json')))
        inventory_equal(b['inputs'],post_expected,'Complete postrun audit Inputs')
        for label,value,schema,job in (
            ('primary',a,'complete-full-precision-service-artifact-audit-v61','audit'),
            ('postrun',b,'complete-full-precision-service-additive-artifact-audit-v61','postrun')):
            require(value['schema']==schema and value['status']=='verified' and value['campaign']==DIRECTORY
                and value['program_sha256']==PROGRAM_SHA and value['slurm_job_id']==RECOVERY_JOBS[label]
                and value['analysis_outside_empirical_worker_ledger'] is True,label+' audit identity/accounting scope')
            integer(value['analysis_cpu_ns'],label+' audit CPU');integer(value['analysis_elapsed_ns'],label+' audit wall',1)
        require(a['all_declared_artifacts_rehashed'] is True and b['frozen_sources_changed'] is False,'Audit completeness/source flag')
        require(b['frozen_audit_path']==RECOVERY+'/primary.json'
            and b['frozen_audit_sha256']==post_expected[RECOVERY+'/primary.json']['sha256'],'Supplemental primary-byte link')
        equal(a['source_sha256'],self.p['sources'],'Primary source inventory');equal(a['runtime'],self.p['runtime'],'Primary runtime')
        equal(a['budget'],self.snapshot,'Primary exact settled budget');equal(b['ledger_snapshot'],self.snapshot,'Postrun exact settled budget')
        require(a['fresh_campaign_cpu_seconds']==self.snapshot['charged_cpu_seconds']['feasibility']
            and a['allowance_scope']==self.p['allowance_scope'],'Fresh CPU accounting')
        implementation={path.name:info(read_bytes(path)) for path in sorted((self.repo/'research_v61').glob('*.py'))}
        inventory_equal(b['implementation'],implementation,'Postrun implementation census')
        for key,value in dict(complete_model=True,successive_deletions=2,original_tokens=1664,retained_tokens=[1536,768],
                quality_evaluation=False,confirmation=False,population_claims=False,acl_ready=False,
                all_final_six_models_equal_actual_v59_candidate=True,calibration_target_sha256=V59_TARGET,
                v59_final_model_sha256=V59_MODEL,shared_checkpoint_bytes=self.p['shared_checkpoint_bytes']).items():
            equal(a[key],value,'Primary result scope '+key)
        evidence=b['evidence']
        target_hash=self.completions['prepare']['service_target_sha256']
        for key,value in dict(anchor_target_sha256=digest(canonical(self.base)),fixed_target_sha256=target_hash,
                calibration_target_sha256=V59_TARGET,v59_final_model_sha256=V59_MODEL,
                all_final_six_models_equal_actual_v59_candidate=True,checkpoint_bytes=self.p['shared_checkpoint_bytes'],
                original_model_sha256=self.artifact('prepare','original-model.bin')['sha256']).items():
            equal(evidence[key],value,'Postrun target/model commitment '+key)
        self.check_service_manifest(target_hash)
        self.comparison_claims(a,evidence)
        self.timings(a,evidence)
        self.audit_records=dict(primary=info(read_bytes(self.recovery_local('primary.json'))),
            postrun=info(read_bytes(self.recovery_local('postrun.json'))))
        # The collector repeats each complete inventory to make omissions visible.
        declarations=self.recovery_manifest['audit_input_inventories']
        require(set(declarations)=={'primary','postrun'},'Both collector audit inventories required')
        for key,receipt in (('primary',a),('postrun',b)):
            inventory_equal(declarations[key]['inputs'],receipt['inputs'],'Collector '+key+' input inventory')
        inventory_equal(self.recovery_manifest['expected_input_commitments'],post_expected,'Collector complete expected inputs')
        for remote,entry in self.manifest['inputs_not_copied'].items():
            if remote in self.missing: continue
            if remote in (DIRECTORY+'/artifact-audit.json',DIRECTORY+'/postrun-audit.json'):
                equal(entry,dict(exists=False,kind='missing',status='NOT revalidated'),'Original audit absence preserved')
                continue
            require(remote.startswith(DIRECTORY+'/') and Path(remote).suffix=='.lock'
                and entry.get('kind')=='unselected_file' and entry.get('status')=='NOT revalidated'
                and entry.get('binary_contents_read') is False and entry.get('exists') is True and 'expected' not in entry,
                'Unexpected omitted metadata or numerical binary: '+remote)
        require(set(self.missing)=={remote for remote in post_expected if Path(remote).suffix in BINARY_SUFFIXES},
            'Exact absent numerical binary census')
        self.primary,self.postrun=a,b


    def run(self):
        result=super().run()
        for n,e in self.recovery_manifest['files'].items():equal(info(read_bytes(self.recovery_local(n))),e,'Final recovery rehash')
        result.update(schema='portable-v61-with-separate-v62-audit-recovery-check',
            original_terminal_gate_passed=False,original_audit_timeout_preserved=True,
            recovery_metadata_status='verified_metadata_only',recovery_registration_sha256=REGISTRATION_SHA,
            recovery_jobs=self.recovery_scheduler,recovery_audit_paths={k:RECOVERY+'/'+k+'.json' for k in RECOVERY_JOBS},
            recovered_validation_does_not_change_original_timing_cap=True)
        return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('original');p.add_argument('recovery');p.add_argument('--repo',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();result=RecoveryCheck(a.original,a.recovery,a.repo).run()
    with Path(a.output).open('xb') as f:f.write(canonical(result))
    print(canonical(dict(status=result['status'],original_terminal_gate_passed=False,comparison_claims_checked=8,output=a.output)).decode())


if __name__=='__main__':main()
