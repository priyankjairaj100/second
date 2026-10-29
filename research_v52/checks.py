"""Small software fixtures for the additive precision48 wrapper."""
import os
from pathlib import Path
import sys
import unittest
from research_v52.campaign import sources,runtime,new,require


def main(path):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform=='linux','Linux Slurm required')
    require(not Path(path).exists(),'Fresh software record required')
    suite=unittest.defaultTestLoader.loadTestsFromName('research_v52.test_precision')
    r=unittest.TextTestRunner(verbosity=2).run(suite);ok=r.wasSuccessful() and not r.skipped
    new(Path(path),dict(status='passed' if ok else 'failed',tests=r.testsRun,skipped=len(r.skipped),
        sources=sources(),runtime=runtime(),slurm_job_id=os.environ['SLURM_JOB_ID'],real_model_inference=False))
    return 0 if ok else 1


if __name__=='__main__':sys.exit(main(sys.argv[1]))
