"""Linux-only software admission, without real checkpoint or dataset inference."""
import os
from pathlib import Path
import sys
import time
import unittest
from research_v51.campaign import sources, runtime, new, require


def main(output):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform=='linux','Linux Slurm required')
    require(not Path(output).exists(),'Fresh check output required')
    start=time.perf_counter_ns()
    suite=unittest.defaultTestLoader.loadTestsFromNames([
        'research_v51.test_stage','research_v50.test_neighbors'])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    passed=result.wasSuccessful() and not result.skipped
    new(Path(output),dict(schema='wide-stage-software-checks-v51',status='passed' if passed else 'failed',
        tests=result.testsRun,skipped=len(result.skipped),failures=len(result.failures),errors=len(result.errors),
        sources=sources(),runtime=runtime(),slurm_job_id=os.environ['SLURM_JOB_ID'],
        elapsed_ns=time.perf_counter_ns()-start,real_model_inference=False))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(main(sys.argv[1]))
