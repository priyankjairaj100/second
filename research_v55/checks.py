"""Bound Linux software-only checks, no checkpoint load or empirical inference."""
import os
from pathlib import Path
import sys
import unittest
from research_v55.campaign import sources,runtime,new,require

MODULES=('research_v55.test_diagnostic','research_v55.test_sequential','research_v55.test_audit')


def main(path):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform=='linux','Linux Slurm required')
    require(not Path(path).exists(),'Fresh software receipt required')
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in MODULES)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    ok=result.wasSuccessful() and not result.skipped
    new(Path(path),dict(status='passed' if ok else 'failed',tests=result.testsRun,skipped=len(result.skipped),
        sources=sources(),runtime=runtime(),slurm_job_id=os.environ['SLURM_JOB_ID'],real_model_inference=False))
    return 0 if ok else 1


if __name__=='__main__':sys.exit(main(sys.argv[1]))
