"""Bound Linux software fixtures, no real-data model execution."""
import os
from pathlib import Path
import sys
import unittest
from research_v53.campaign import sources,runtime,new,require

MODULES = ('research_v53.test_state','research_v53.test_service',
    'research_v53.test_worker','research_v53.test_postrun','research_v53.test_precision',
    'research_v43.test_state','research_v50.test_neighbors')


def main(path):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform=='linux','Linux Slurm required')
    require(not Path(path).exists(),'Fresh software receipt required')
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in MODULES)
    r=unittest.TextTestRunner(verbosity=2).run(suite)
    ok=r.wasSuccessful() and not r.skipped
    new(Path(path),dict(status='passed' if ok else 'failed',tests=r.testsRun,skipped=len(r.skipped),
        sources=sources(),runtime=runtime(),slurm_job_id=os.environ['SLURM_JOB_ID'],real_model_inference=False))
    return 0 if ok else 1


if __name__=='__main__':sys.exit(main(sys.argv[1]))
