"""Independent statistical audit fixtures, without neural evaluation."""
import copy
import unittest
from scripts.run_heldout_quality_v30 import summarize
from scripts.analyze_heldout_quality_v30 import recompute
from tests.test_heldout_quality_v30 import fixture


class HeldoutQualityAnalyzerTests(unittest.TestCase):
    def make(self):
        selection,_,_,quality=fixture()
        for rows in quality.values():
            for row in rows:row['mean_nll']=row['nll_sum']/127
        summary=summarize(quality,selection['records'])
        return dict(quality=quality,summary=summary,bounded_pool_confirmation_gate_pass=True),selection['records']

    def test_independent_recomputation_matches_registered_recipe(self):
        result,records=self.make();audit=recompute(result,records)
        self.assertTrue(audit['bounded_pool_confirmation_gate_pass'])
        self.assertEqual(len(audit['per_article']),40)
        self.assertEqual(audit['primary_bootstrap_upper_ratio'],1.)

    def test_changed_upper_or_guard_is_rejected(self):
        result,records=self.make()
        for mutation in ('upper','guard','article'):
            changed=copy.deepcopy(result)
            if mutation=='upper':changed['summary']['primary_bootstrap_upper_ratio']=.99
            elif mutation=='guard':changed['summary']['guards']['bootstrap_upper_pass']=False
            else:changed['quality']['fixed128'][0]['nll_sum']+=1
            with self.assertRaises(ValueError):recompute(changed,records)


if __name__=='__main__':unittest.main()
