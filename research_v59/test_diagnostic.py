"""Small software fixtures: no checkpoint load, real-model inference or cluster work."""
import copy
import math
import unittest

from research_v59 import diagnostic as d
from src.compact_state import StageCodes
from src.run_store import digest


def quality(delta=0.):
    rows = {label: [dict(id=rid, predictions=127, nll_sum=508., mean_nll=4., elapsed_ns=1)
        for rid in d.ARTICLE_IDS] for label in d.LABELS}
    for row in rows[d.CANDIDATE_LABEL]:
        row['nll_sum'] += 127*delta
        row['mean_nll'] = row['nll_sum']/127
    return rows


def previous():
    return dict(status='complete', quality={label: rows for label, rows in quality().items() if label in d.CONTROL_LABELS})


def codes():
    return tuple(StageCodes('stage-'+str(i), 1, 2, 'dyadic_row', 4, (), b'\x87', (1.,)) for i in range(24))


def result(delta=0.):
    q, old = quality(delta), previous()
    report, summary = d.parity(q, old), d.summarize(q)
    return dict(status='complete', valid_diagnostic=True, quality=q, historical_parity=report,
        summary=summary, development_guards_pass=summary['development_guards_pass']), old, report


def progress(quality_rows, stage_rows, first, guards=True):
    events = []
    def mark(phase, **details):
        events.append(dict(phase=phase, worker_elapsed_ns=len(events), **details))
    mark('targets_and_actual_models_validated')
    for label in d.CONTROL_LABELS:
        for row in quality_rows[label]:
            mark('quality_article', model=label, record_id=row['id'], nll_sum=row['nll_sum'])
    mark('all_historical_controls_passed', checked_losses=32)
    mark('candidate_construction_started')
    for row in stage_rows:
        mark('candidate_stage', stage_id=row['stage_id'], elapsed_ns=row['elapsed_ns'], output_code_sha256=row['output_code_sha256'])
    mark('candidate_model_validated', first_stage_packed_sha256=first['packed_sha256'])
    for row in quality_rows[d.CANDIDATE_LABEL]:
        mark('quality_article', model=d.CANDIDATE_LABEL, record_id=row['id'], nll_sum=row['nll_sum'])
    mark('diagnostic_complete', development_guards_pass=guards)
    return events


class DiagnosticTests(unittest.TestCase):
    def test_all_thirty_two_controls_are_required_and_checked(self):
        q, old = quality(), previous()
        report = d.parity({label: q[label] for label in d.CONTROL_LABELS}, old)
        self.assertTrue(report['passed'])
        self.assertEqual(report['checked_losses'], 32)
        self.assertEqual({r['model'] for r in report['checks']}, set(d.CONTROL_LABELS))
        for label in d.CONTROL_LABELS:
            bad = copy.deepcopy(q)
            bad[label][0]['nll_sum'] += 127*2e-8
            bad[label][0]['mean_nll'] = bad[label][0]['nll_sum']/127
            self.assertFalse(d.parity(bad, old)['passed'])

    def test_parity_uses_mean_nll_tolerance_and_ignores_candidate_improvement(self):
        q, old = quality(-1.), previous()
        q['sequential'][0]['nll_sum'] += 127*0.5e-8
        q['sequential'][0]['mean_nll'] = q['sequential'][0]['nll_sum']/127
        self.assertTrue(d.parity(q, old)['passed'])
        q['sequential'][0]['nll_sum'] += 127*2e-8
        q['sequential'][0]['mean_nll'] = q['sequential'][0]['nll_sum']/127
        self.assertFalse(d.parity(q, old)['passed'])

    def test_loss_extent_duplicates_nonfinite_and_mean_tampering_are_rejected(self):
        variants = []
        q = quality(); q['fixed_feature'].pop(); variants.append(q)
        q = quality(); q['sequential'][1] = copy.deepcopy(q['sequential'][0]); variants.append(q)
        q = quality(); q['sequential'][0]['predictions'] = 126; variants.append(q)
        q = quality(); q['full_precision'][0]['nll_sum'] = math.inf; variants.append(q)
        q = quality(); q['nearest_rounding'][0]['mean_nll'] = 0.; variants.append(q)
        q = quality(); q['unknown_model'] = []; variants.append(q)
        for q in variants:
            with self.assertRaises(ValueError): d.summarize(q)
        bad = previous(); bad['quality']['sequential'].reverse()
        with self.assertRaises(ValueError): d.parity(quality(), bad)

    def test_pooled_and_every_article_guards_are_unchanged_and_distinct(self):
        pooled = d.summarize(quality(math.log(1.06)))
        self.assertFalse(pooled['guards']['pooled_pass'])
        self.assertTrue(pooled['guards']['every_article_pass'])
        q = quality()
        q[d.CANDIDATE_LABEL][0]['nll_sum'] += 127*math.log(1.21)
        q[d.CANDIDATE_LABEL][0]['mean_nll'] = q[d.CANDIDATE_LABEL][0]['nll_sum']/127
        article = d.summarize(q)
        self.assertTrue(article['guards']['pooled_pass'])
        self.assertFalse(article['guards']['every_article_pass'])
        self.assertAlmostEqual(article['candidate_comparisons']['sequential']['pooled_perplexity_ratio'], 1.21**(1/8))
        self.assertEqual(article['thresholds'], dict(max_pooled_candidate_over_sequential=1.05, max_article_candidate_over_sequential=1.2))

    def test_all_forty_losses_and_overflowing_adverse_result_are_preserved(self):
        for delta, expected in ((0., True), (math.log(1.3), False), (1000., False)):
            c, old, report = result(delta)
            summary = d.check_result(c, old, report)
            self.assertEqual(summary['development_guards_pass'], expected)
            self.assertEqual(len(summary['totals']), 5)
            self.assertTrue(all(v['predictions'] == 1016 for v in summary['totals'].values()))
            self.assertIsNone(summary['inferential_interval'])
            self.assertFalse(summary['confirmation'])
            self.assertFalse(summary['acl_ready'])
        self.assertIsNone(summary['candidate_comparisons']['sequential']['pooled_perplexity_ratio'])

    def test_report_and_guard_tampering_do_not_pass(self):
        c, old, report = result()
        for key in ('historical_parity', 'summary'):
            bad = copy.deepcopy(c); bad[key] = {}
            with self.assertRaises(ValueError): d.check_result(bad, old, report)
        bad = copy.deepcopy(c); bad['development_guards_pass'] = False
        with self.assertRaises(ValueError): d.check_result(bad, old, report)
        bad = copy.deepcopy(c); bad['status'] = 'failed'
        with self.assertRaises(ValueError): d.check_result(bad, old, report)

    def test_candidate_reconstruction_checks_actual_packing_target_and_every_grid(self):
        model = codes(); blob = b''.join(s.packed_indices for s in model)
        meta = dict(target_sha256='candidate', stages=[s.metadata() for s in model])
        self.assertEqual(d.reconstruct_candidate(blob, meta, target_sha256='candidate', controls=model), model)
        variants = [(blob+b'x', meta), (blob[:-1], meta), (b'\x88'+blob[1:], meta)]
        bad = copy.deepcopy(meta); bad['target_sha256'] = 'nearest'; variants.append((blob, bad))
        bad = copy.deepcopy(meta); bad['stages'][20]['scale_values_hex'] = [float(2).hex()]; variants.append((blob, bad))
        bad = copy.deepcopy(meta); bad['stages'].pop(); variants.append((blob, bad))
        for data, metadata in variants:
            with self.assertRaises(ValueError): d.reconstruct_candidate(data, metadata, target_sha256='candidate', controls=model)

    def test_first_stage_requires_actual_frozen_bytes_and_complete_matched_grids(self):
        model = codes(); frozen = digest(model[0].packed_indices)
        report = d.first_stage_invariant(model, model, model, expected_sha256=frozen)
        self.assertTrue(report['actual_packed_bytes_equal'])
        changed = (StageCodes('stage-0', 1, 2, 'dyadic_row', 4, (), b'\x88', (1.,)), *model[1:])
        for candidate, fixed, sequential, sha in ((changed, model, model, frozen), (model, model, model, 'wrong'),
                (model[:-1], model, model, frozen)):
            with self.assertRaises(ValueError): d.first_stage_invariant(candidate, fixed, sequential, expected_sha256=sha)

    def test_progress_requires_parity_before_all_candidate_work(self):
        model = codes(); q = quality()
        stages = [dict(stage_id=s.stage_id, elapsed_ns=1, output_code_sha256=digest(s.packed_indices)) for s in model]
        first = d.first_stage_invariant(model, model, model, expected_sha256=digest(model[0].packed_indices))
        events = progress(q, stages, first)
        report = d.check_progress(events, q, stages, first, True)
        self.assertEqual(report['events'], 69)
        self.assertTrue(report['parity_before_candidate'])
        variants = []
        bad = copy.deepcopy(events); bad[33], bad[34] = bad[34], bad[33]; variants.append(bad)
        bad = copy.deepcopy(events); bad.pop(2); variants.append(bad)
        bad = copy.deepcopy(events); bad[35]['output_code_sha256'] = 'wrong'; variants.append(bad)
        bad = copy.deepcopy(events); bad[3]['nll_sum'] += 1; variants.append(bad)
        bad = copy.deepcopy(events); bad[-1]['development_guards_pass'] = False; variants.append(bad)
        bad = copy.deepcopy(events); bad[-1]['worker_elapsed_ns'] = 0; variants.append(bad)
        for changed in variants:
            with self.assertRaises(ValueError): d.check_progress(changed, q, stages, first, True)


if __name__ == '__main__':
    unittest.main()
