"""Independent direction checks for the two prospective six-model quality gates."""
import math
import unittest

from scripts.run_followup_quality_v30 import LABELS, summarize


def fixture():
    records = [dict(id='fixture-'+str(i), tokens=[1]*128) for i in range(8)]
    quality = {label:[dict(id=row['id'], predictions=127, nll_sum=254.) for row in records]
               for label in LABELS+('sequential128',)}
    return records, quality


class QualityExtensionGateDirectionTests(unittest.TestCase):
    def test_matched_failure_cannot_be_rescued_by_archived_safety_success(self):
        records, quality = fixture()
        for row in quality['sequential128']:
            row['nll_sum'] -= 127*math.log(1.10)
        result = summarize(quality, records, matched=True)
        self.assertFalse(result['matched_quality_gate_pass'])
        self.assertTrue(result['development_safety_gate_pass'])
        self.assertAlmostEqual(result['fixed128_comparisons']['sequential128']['perplexity_ratio'], 1.10)

    def test_matched_success_cannot_be_rescued_from_archived_safety_failure(self):
        records, quality = fixture()
        for row in quality['fixed16']:
            row['nll_sum'] -= 127*math.log(1.10)
        result = summarize(quality, records, matched=True)
        self.assertTrue(result['matched_quality_gate_pass'])
        self.assertFalse(result['development_safety_gate_pass'])

    def test_one_bad_article_blocks_a_small_aggregate_degradation(self):
        records, quality = fixture()
        quality['fixed128'][0]['nll_sum'] += 127*math.log(1.21)
        result = summarize(quality, records, matched=True)
        self.assertLess(result['fixed128_comparisons']['sequential128']['perplexity_ratio'], 1.05)
        self.assertFalse(result['matched_quality_gate_pass'])
        self.assertFalse(result['development_safety_gate_pass'])


if __name__ == '__main__':
    unittest.main()
