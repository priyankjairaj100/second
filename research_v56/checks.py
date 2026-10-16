"""Twelve bound CUDA software checks without actual-checkpoint inference."""
import os
from pathlib import Path
import sys
import unittest
from research_v56.campaign import sources,runtime,new,require
MODULES=('research_v46.test_evaluator.MatchedLosses',
    'research_v46.test_evaluator.DecoderParity.test_complete_batch_and_replacement_prefix',
    'research_v46.test_evaluator.DecoderParity.test_future_tokens_cannot_change_past_logits',
    'research_v46.test_evaluator.DecoderParity.test_bitwise_copy_and_dtype_guard',
    'research_v47.test_snapshot.SnapshotTests.test_every_word_and_likelihood_preserved',
    'research_v47.test_snapshot.SnapshotTests.test_tampered_word_commitment_refused',
    'research_v56.test_gate')


def main(path):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform=='linux','Linux Slurm GPU required')
    require(not Path(path).exists(),'Fresh software receipt required')
    os.environ['V46_TEST_DEVICE']='cuda'
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in MODULES)
    r=unittest.TextTestRunner(verbosity=2).run(suite);ok=r.wasSuccessful() and not r.skipped
    new(Path(path),dict(status='passed' if ok else 'failed',tests=r.testsRun,skipped=len(r.skipped),
        sources=sources(),runtime=runtime(),slurm_job_id=os.environ['SLURM_JOB_ID'],real_model_inference=False))
    return 0 if ok else 1


if __name__=='__main__':sys.exit(main(sys.argv[1]))
