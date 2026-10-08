"""Prospective held-out selection and decision contracts; no model inference."""
import copy
import math
import tempfile
from pathlib import Path
import unittest

from scripts.run_heldout_quality_v30 import LABELS,POLICY,summarize,validate_selection
from scripts.prepare_heldout_quality_v30 import exposure_audit


def fixture():
    rows=[dict(id='wikitext2:validation:article-row-'+str(i),tokens=[i]*128) for i in range(60)]
    excluded=[row['id'] for row in rows[:20]]
    pools=dict(evaluation=rows,confirmation=[dict(id='reserved')])
    selection=dict(schema='heldout-quality-selection-v30',model_inference=False,records=copy.deepcopy(rows[20:]),
        prior_excluded_ids=excluded,prospective_all_excluded_ids=sorted(row['id'] for row in rows),
        exposure_audit=dict(remaining_id_collisions=[],observed_metadata_ids=sorted(excluded)))
    development=dict(excluded_from_future_confirmation_ids=excluded)
    quality={label:[dict(id=row['id'],predictions=127,nll_sum=254.) for row in rows[20:]] for label in LABELS}
    return selection,pools,development,quality


class HeldoutQualityTests(unittest.TestCase):
    def test_complete_unexposed_remainder_and_all_sixty_exclusions(self):
        selection,pools,development,_=fixture()
        self.assertEqual(len(validate_selection(selection,pools,development)),40)
        for variant in ('token','excluded','reserve','partial','exposure'):
            changed,pool2,dev2,_=copy.deepcopy(fixture())
            if variant=='token':changed['records'][0]['tokens'][0]=2
            elif variant=='excluded':changed['records'][0]=copy.deepcopy(pool2['evaluation'][0])
            elif variant=='reserve':pool2['confirmation'].append(dict(id=changed['records'][0]['id']))
            elif variant=='partial':changed['records'].pop()
            else:changed['exposure_audit']['remaining_id_collisions']=[{}]
            with self.assertRaises(ValueError):validate_selection(changed,pool2,dev2)

    def test_single_primary_bootstrap_and_secondary_scope(self):
        selection,_,_,quality=fixture()
        result=summarize(quality,selection['records'])
        self.assertTrue(result['bounded_pool_confirmation_gate_pass'])
        self.assertEqual(result['primary_bootstrap_upper_ratio'],1.)
        self.assertEqual(sum(row['primary'] for row in result['contrasts'].values()),1)
        self.assertEqual(result['totals']['fixed128']['predictions'],5080)

    def test_secondary_wins_cannot_rescue_failed_primary(self):
        selection,_,_,quality=fixture()
        for row in quality['sequential128']:row['nll_sum']-=127*math.log(1.10)
        for label in ('full_precision','nearest_rounding'):
            for row in quality[label]:row['nll_sum']+=127
        result=summarize(quality,selection['records'])
        self.assertFalse(result['bounded_pool_confirmation_gate_pass'])
        self.assertFalse(result['guards']['bootstrap_upper_pass'])
        self.assertLess(result['contrasts']['nearest_rounding']['perplexity_ratio'],1)

    def test_bad_article_blocks_otherwise_acceptable_aggregate(self):
        selection,_,_,quality=fixture()
        quality['fixed128'][0]['nll_sum']+=127*math.log(1.21)
        result=summarize(quality,selection['records'])
        self.assertTrue(result['guards']['aggregate_ratio_pass'])
        self.assertFalse(result['guards']['per_article_ratio_pass'])
        self.assertFalse(result['bounded_pool_confirmation_gate_pass'])

    def test_missing_model_or_duplicate_article_is_rejected(self):
        selection,_,_,quality=fixture()
        duplicate=copy.deepcopy(quality);duplicate['fixed128'][0]=copy.deepcopy(duplicate['fixed128'][1])
        for bad in (dict(quality,unexpected=[]),duplicate):
            with self.assertRaises(ValueError):summarize(bad,selection['records'])

    def test_exposure_audit_detects_new_metadata_outside_own_draft(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'pilots').mkdir();(root/'campaigns/draft').mkdir(parents=True)
            rid='wikitext2:validation:article-row-12'
            (root/'campaigns/draft/selection.json').write_text('{"id":"'+rid+'"}')
            self.assertFalse(exposure_audit(root,[rid],(root/'campaigns/draft',))['remaining_id_collisions'])
            (root/'pilots/exposed.json').write_text('{"id":"'+rid+'"}')
            self.assertEqual(len(exposure_audit(root,[rid],(root/'campaigns/draft',))['remaining_id_collisions']),1)


if __name__=='__main__':unittest.main()
