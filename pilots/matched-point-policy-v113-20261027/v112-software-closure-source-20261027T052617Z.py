from pathlib import Path
import sys,json,subprocess,datetime
run=Path('/nfs_home/users/poonam/second-20261010/local_runs/matched-complete-recovery-v112-20261026-a');sys.path.insert(0,str(run))
from research_v112 import campaign,protocol
from research_v112.submit import FIELDS
from research_v112.closure import review
from research_v83.accounting import scheduler_rows
from research_v83.terminal import Inputs
sha='a73ca66d08b50feeccf9601d6d214b00ad21917ae900671cc35d373aef4f4381';job='16407'
raw=subprocess.check_output(['sacct','-nP','-j',job,FIELDS],text=True,timeout=20)
p=campaign.verify(prerequisite=False);assert campaign.sha(run/'program.json')==sha
protocol.allocation('checks',sha,job,require_release=True)
jobs={'checks':dict(job_id=job,name='second112-checks')};scheduled=scheduler_rows(raw,jobs);inputs=Inputs()
assert inputs.json(run/'program.json')==p and inputs.json(run/'registration.json')==dict(program_sha256=sha)
cost,worker=review('checks',p,sha,inputs,scheduled['checks']);assert worker is None
software=inputs.json(run/'software-results.json');inputs.unchanged()
print(json.dumps(dict(status='verified_actual_software_closure',program_sha256=sha,scheduler_raw=raw,cost=cost,inputs=inputs.files,software=software,captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),sort_keys=True))
