"""Selection and schedule contracts on software fixtures, without model execution."""
import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_independent_requests_v30 import (
    c4_eligible, check_prefix, choose_root, history_exclusions, point_trials,
)
from src.run_store import canonical_json, digest


def rows():
    return [dict(id='row'+str(i), tokens=[i]*128, normalized_text_sha256=str(i)*64) for i in range(6)]


class IndependentRequestDraftTests(unittest.TestCase):
    def test_selection_is_order_invariant_and_excludes_previous_sources(self):
        candidates = rows()
        first = choose_root(candidates, 'wiki', {'row0'})
        self.assertEqual(first, choose_root(list(reversed(candidates)), 'wiki', {'row0'}))
        self.assertNotIn('row0', [row['id'] for row in first])

    def test_selection_excludes_protected_chunks_and_documents(self):
        candidates = rows()
        selected = choose_root(candidates, 'wiki', set(),
            [digest(canonical_json(candidates[0]['tokens']))], [candidates[1]['normalized_text_sha256']])
        self.assertFalse({'row0','row1'} & {row['id'] for row in selected})
        with self.assertRaises(ValueError):
            choose_root(candidates[:2], 'wiki', {'row0'})

    def test_duplicate_selected_urls_are_rejected(self):
        candidates = rows()[:2]
        for row in candidates:
            row['url_sha256'] = 'same'
        with self.assertRaises(ValueError):
            choose_root(candidates, 'c4', set())

    def test_c4_reproduces_normalized_document_deduplication(self):
        corpus = [dict(text='one two',url='url1'), dict(text='one  two',url='url2'),
                  dict(text='short',url='url3'), dict(text='three',url='url4')]
        eligible = c4_eligible(corpus, lambda text: [2]*3 if text == 'short' else [1]*128)
        self.assertEqual({row['id'] for row in eligible}, {'c4:en:shard0:line0', 'c4:en:shard0:line3'})
        with self.assertRaises(ValueError):
            c4_eligible(corpus, lambda text: [50257]*128)

    def test_cached_prefix_requires_exact_records_and_acquisition_hash(self):
        corpus = [dict(text='fixture',url='x')]
        raw = gzip.compress(json.dumps(corpus[0]).encode()+b'\n')
        acquisition = dict(prefix_bytes=len(raw),prefix_sha256=digest(raw),complete_records=1)
        check_prefix(raw, corpus, acquisition)
        with self.assertRaises(ValueError):
            check_prefix(raw, [], acquisition)
        with self.assertRaises(ValueError):
            check_prefix(raw, corpus, dict(acquisition,prefix_sha256='0'*64))

    def test_history_exclusion_reads_plans_and_skips_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('pilots/a', 'pilots/b/outputs', 'campaigns/c/source'):
                (root/name).mkdir(parents=True)
            (root/'pilots/a/plan.json').write_text('{"id":"c4:en:shard0:line10"}')
            (root/'pilots/b/outputs/plan.json').write_text('{"id":"c4:en:shard0:line20"}')
            (root/'campaigns/c/source/plan.json').write_text('{"id":"c4:en:shard0:line30"}')
            ids, paths = history_exclusions(root)
            self.assertEqual(ids, {'c4:en:shard0:line10'})
            self.assertEqual(list(paths), ['pilots/a/plan.json'])

    def test_both_deletions_are_paired_and_order_is_balanced(self):
        common = dict(inputs={'config':{},'weights':{}},expected_target='a'*64)
        records = dict(path='/fixture/records.json',sha256='b'*64)
        schedules = []
        for corpus in ('wikitext','c4'):
            trials, requests = point_trials(corpus, rows()[:2], common, records)
            self.assertEqual(len(trials), 5)
            self.assertEqual(len(requests), 2)
            self.assertEqual({tuple(row['deleted_ids']) for row in requests}, {('row0',),('row1',)})
            for trial in trials:
                self.assertEqual(trial['plan']['original_token_count'], 256)
                if trial['plan']['method'] == 'model_only_fresh':
                    self.assertNotIn('inputs_from_trial', trial)
                    self.assertEqual(set(trial['plan']['inputs']), {'records','config','weights'})
                elif trial['plan']['method'] == 'repair':
                    self.assertEqual(set(trial['inputs_from_trial']), {'prior_state','preparation_completion'})
            schedules.extend(request['method_order'] for request in requests)
        self.assertEqual(schedules.count(['repair','cold']), 2)
        self.assertEqual(schedules.count(['cold','repair']), 2)
        self.assertEqual(common, dict(inputs={'config':{},'weights':{}},expected_target='a'*64))


if __name__ == '__main__':
    unittest.main()
