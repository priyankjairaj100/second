"""Bounded software fixtures followed by a one-use read-only prefix audit."""
import os
from pathlib import Path
import sys
import time
import unittest
from research_v54.campaign import new,require,runtime,sha
from research_v57.prefix_audit import audit


def main(directory,output):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform=='linux','Linux Slurm required')
    out=Path(output).resolve();require(not out.exists(),'Fresh audit directory required');out.mkdir(parents=True)
    tick=time.process_time_ns()
    suite=unittest.defaultTestLoader.loadTestsFromName('research_v57.test_prefix')
    r=unittest.TextTestRunner(verbosity=2).run(suite)
    ok=r.wasSuccessful() and not r.skipped and r.testsRun==5
    new(out/'checks.json',dict(status='passed' if ok else 'failed',tests=r.testsRun,skipped=len(r.skipped),
        software_cpu_ns=time.process_time_ns()-tick,real_model_inference=False,
        sources={p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},runtime=runtime(),slurm_job_id=os.environ['SLURM_JOB_ID']))
    if not ok:return 1
    audit(directory,out/'prefix-audit.json');return 0


if __name__=='__main__':sys.exit(main(*sys.argv[1:]))
