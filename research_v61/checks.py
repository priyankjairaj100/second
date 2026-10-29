"""Source/runtime-bound Linux fixtures; no empirical corpus or real model run."""
import os
from pathlib import Path
import sys
import unittest

from research_v61.campaign import sources, runtime, new, require

MODULES = (
    'research_v53.test_state', 'research_v53.test_service',
    'research_v53.test_worker', 'research_v53.test_postrun', 'research_v53.test_precision',
    'research_v43.test_state', 'research_v50.test_neighbors', 'research_v54.test_archive',
    'research_v55.test_diagnostic', 'research_v55.test_sequential', 'research_v55.test_audit',
    'research_v59.test_anchor', 'research_v59.test_diagnostic', 'research_v59.test_audit',
    'research_v59.test_campaign',
    'research_v61.test_target', 'research_v61.test_state',
    'research_v61.test_features', 'research_v61.test_service',
    'research_v61.test_campaign', 'research_v61.test_worker', 'research_v61.test_postrun',
)
# Reviewed static census: historical76+49, new27+18+8+4+23.
EXPECTED_TESTS = 205


def main(path):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform == 'linux',
        'Pinned Linux Slurm required')
    require(not Path(path).exists(), 'Fresh software receipt required')
    before, environment = sources(), runtime()
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in MODULES)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = sources()
    ok = (result.wasSuccessful() and not result.skipped and
        result.testsRun == EXPECTED_TESTS and before == after and environment == runtime())
    new(Path(path), dict(status='passed' if ok else 'failed', tests=result.testsRun,
        skipped=len(result.skipped), modules=list(MODULES), sources=after, runtime=environment,
        source_and_runtime_unchanged=before == after and environment == runtime(),
        slurm_job_id=os.environ['SLURM_JOB_ID'], real_model_inference=False))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
