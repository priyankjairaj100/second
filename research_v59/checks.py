"""Pinned Linux software gate; no real checkpoint, corpus, or quality evaluation."""
import os
from pathlib import Path
import sys
import unittest
from research_v59.campaign import sources, runtime, new, require

MODULES=('research_v55.test_diagnostic','research_v55.test_sequential','research_v55.test_audit',
    'research_v59.test_anchor','research_v59.test_diagnostic','research_v59.test_audit','research_v59.test_campaign')
# Fixed after reviewing the complete suite; execution must match with no skips.
EXPECTED_TESTS = 49


def main(path):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform=='linux','Pinned Linux Slurm required')
    require(not Path(path).exists(),'Fresh software receipt required')
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in MODULES)
    before=sources()
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    after=sources()
    ok=result.wasSuccessful() and not result.skipped and result.testsRun==EXPECTED_TESTS and before==after
    new(Path(path),dict(status='passed' if ok else 'failed',tests=result.testsRun,skipped=len(result.skipped),
        modules=list(MODULES),sources=after,runtime=runtime(),slurm_job_id=os.environ['SLURM_JOB_ID'],
        real_model_inference=False))
    return 0 if ok else 1


if __name__=='__main__':sys.exit(main(sys.argv[1]))
