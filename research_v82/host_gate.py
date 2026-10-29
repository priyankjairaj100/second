"""Host-side upstream terminal check, before container entry; never self-accounting."""
import datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
RUN=Path('/nfs_home/users/poonam/second-20261010/local_runs/matched-transfer-admission-v82-20261023-a')

def main(operation,expected):
    assert Path(__file__).resolve()==RUN/'research_v82/host_gate.py'
    assert operation in ('checks','fetch','distilgpt2','gpt2','close')
    assert hashlib.sha256((RUN/'program.json').read_bytes()).hexdigest()==expected
    report=dict(operation=operation,program_sha256=expected,job_id=os.environ['SLURM_JOB_ID'],checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),upstream_job='15917',status='checking')
    try:
        raw=subprocess.check_output(['sacct','-j','15917','-nP','--format=JobIDRaw,JobName%50,State,ExitCode,AllocCPUS,ReqMem,NodeList'],text=True,timeout=15)
        report['accounting']=raw
        rows=[r.split('|') for r in raw.splitlines() if r.split('|')[0]=='15917']
        assert len(rows)==1 and rows[0][1:]==['second81-software','COMPLETED','0:0','1','16G','csis.mn1'],'Upstream terminal identity/state differs'
        report['status']='complete'
    except BaseException as e:
        report.update(status='failed',error_type=type(e).__name__);raise
    finally:
        with (RUN/(operation+'-host-gate.json')).open('x') as f:json.dump(report,f,sort_keys=True,separators=(',',':'));f.flush();os.fsync(f.fileno())
if __name__=='__main__':main(*sys.argv[1:])
