"""Article-statistic audit fixtures, without model evaluation."""
import copy
import unittest

from scripts.analyze_quality_extensions_v30 import LABELS, recompute
from scripts.run_followup_quality_v30 import OLD_LABELS, policy_for_mode, summarize


def fixture():
    records=[dict(id='article'+str(i),tokens=[1]*128) for i in range(8)]
    quality={label:[dict(id=row['id'],predictions=127,nll_sum=254.+i,mean_nll=(254.+i)/127)
        for i,row in enumerate(records)] for label in LABELS}
    summary=summarize(quality,records,matched=True)
    first=dict(quality={old:copy.deepcopy(quality[new]) for new,old in OLD_LABELS.items()})
    result=dict(policy=policy_for_mode(True),quality=quality,summary=summary,
        parity=[dict(model=label,id=row['id'],mean_nll_deviation=0.) for label in OLD_LABELS for row in records],
        matched_quality_gate_pass=True,development_safety_gate_pass=True,historical_control_parity_pass=True,
        primary_comparison_control='sequential128',primary_observed_win=False)
    return result,dict(records=records),first


class QualityExtensionAnalyzerTests(unittest.TestCase):
    def test_recomputes_all_six_models_and_five_contrasts(self):
        report=recompute(*fixture())
        self.assertTrue(report['all_three_gates_pass'])
        self.assertEqual(len(report['totals']),6)
        self.assertEqual(len(report['comparisons']),5)
        self.assertEqual(report['comparisons']['sequential128']['article_ties'],8)

    def test_rejects_parity_and_gate_tampering(self):
        result,reg,first=fixture()
        for mutation in ('parity','gate','summary'):
            changed=copy.deepcopy(result)
            if mutation=='parity':changed['parity'][0]['mean_nll_deviation']=1e-9
            elif mutation=='gate':changed['matched_quality_gate_pass']=False
            else:changed['summary']['totals']['fixed128']['perplexity']+=1
            with self.assertRaises(ValueError):recompute(changed,reg,first)

    def test_rejects_missing_article_or_duplicate_model_row(self):
        for duplicate in (False,True):
            result,reg,first=fixture()
            if duplicate:result['quality']['fixed128'][1]=copy.deepcopy(result['quality']['fixed128'][0])
            else:result['quality']['fixed128'].pop()
            with self.assertRaises(ValueError):recompute(result,reg,first)


if __name__=='__main__':unittest.main()
