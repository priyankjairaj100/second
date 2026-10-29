"""Generated numerical fixtures only; never empirical quality observations."""
import math,unittest
from research_v68.quality_statistics import MODELS,summarize


def fixture(n=4,differences=None):
    diffs=differences or [0.0]*n
    rows=[]
    for i in range(n):
        losses={m:dict(sum_nll=127*(4+diffs[i] if m.startswith('candidate_') else 4),mean_nll=4+diffs[i] if m.startswith('candidate_') else 4) for m in MODELS}
        rows.append(dict(id=f'article-{i:04d}',predictions=127,losses=losses))
    return rows


def evaluate(rows):return summarize(rows,expected_articles=4,draws=100)

class QualityStatisticsTests(unittest.TestCase):
    def test_equal_models_give_exact_unit_ratio_and_both_pass(self):
        result=evaluate(fixture())
        self.assertTrue(result['all_endpoint_gates_pass'])
        for r in result['endpoints'].values():
            self.assertEqual(r['pooled_ratio'],1);self.assertEqual(r['two_sided_95_percentile_interval'],[1,1])
        self.assertFalse(result['actual_loss_artifact_validation_performed'])

    def test_constant_adverse_loss_cannot_pass_uncertainty(self):
        result=evaluate(fixture(differences=[math.log(1.06)]*4))
        self.assertFalse(result['all_endpoint_gates_pass'])
        for r in result['endpoints'].values():self.assertFalse(r['observed_pooled_guard_pass']);self.assertFalse(r['uncertainty_guard_pass'])

    def test_small_pooled_loss_does_not_hide_tail_failure(self):
        result=evaluate(fixture(differences=[-.2,-.2,-.2,.3]))
        for r in result['endpoints'].values():
            self.assertTrue(r['observed_pooled_guard_pass']);self.assertFalse(r['observed_maximum_guard_pass']);self.assertFalse(r['gate_pass'])

    def test_paired_endpoints_share_draws_and_repeat_exactly(self):
        rows=fixture(differences=[-.02,.01,.02,-.01]);a=evaluate(rows);b=evaluate(rows)
        self.assertEqual(a,b)
        self.assertEqual(a['endpoints']['12'],a['endpoints']['6'])
        for row in rows:
            row['losses']['candidate_6']=dict(sum_nll=127*4.1,mean_nll=4.1)
        c=evaluate(rows);self.assertTrue(c['endpoints']['12']['gate_pass']);self.assertFalse(c['endpoints']['6']['gate_pass'])

    def test_pooled_ratio_uses_nll_difference_not_mean_ratio(self):
        r=evaluate(fixture(differences=[-.2,.2,-.2,.2]))['endpoints']['12']
        self.assertAlmostEqual(r['pooled_ratio'],1.0)
        self.assertNotAlmostEqual(r['pooled_ratio'],(math.exp(.2)+math.exp(-.2))/2)

    def test_missing_duplicate_nonfinite_and_inconsistent_losses_refuse(self):
        variants=[];x=fixture();x[1]['id']=x[0]['id'];variants.append(x)
        x=fixture();del x[0]['losses']['original'];variants.append(x)
        x=fixture();x[0]['losses']['original']['sum_nll']=float('nan');variants.append(x)
        x=fixture();x[0]['losses']['original']['mean_nll']=9;variants.append(x)
        x=fixture();x[0]['predictions']=126;variants.append(x)
        variants.extend([fixture()[:3],list(reversed(fixture()))])
        for rows in variants:
            with self.subTest(rows=str(rows)[:60]):
                with self.assertRaises(ValueError):evaluate(rows)

    def test_large_adverse_log_loss_is_preserved_without_exp_overflow(self):
        r=evaluate(fixture(differences=[800]*4))
        self.assertFalse(r['all_endpoint_gates_pass'])
        self.assertIsNone(r['endpoints']['12']['pooled_ratio'])
        self.assertAlmostEqual(r['endpoints']['12']['log_pooled_ratio'],800)
        self.assertIsNone(r['models']['candidate_12']['perplexity'])

    def test_production_article_count_cannot_silently_shrink(self):
        with self.assertRaises(ValueError):summarize(fixture(),draws=20)

if __name__=='__main__':unittest.main()
