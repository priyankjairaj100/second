from pathlib import Path
import sys,json,hashlib,io,contextlib
run=Path('/nfs_home/users/poonam/second-20261010/local_runs/matched-complete-recovery-v112-20261026-a')
sys.path.insert(0,str(run))
from research_v112.prepare import main
out=io.StringIO()
with contextlib.redirect_stdout(out):main('633aa917d4ab03de4e7be45e53a3b0ed5af821266be6db38c3437dcfd0de7505','051c490a449120fabd7ddd839afb1287b5ea8ceef15a39fcd86a8823258ac2bd')
raw=(run/'program.json').read_bytes()
print(json.dumps(dict(status='prepared_not_registered',program=json.loads(raw),program_sha256=hashlib.sha256(raw).hexdigest(),program_bytes=len(raw),preparation_stdout=out.getvalue()),sort_keys=True))
