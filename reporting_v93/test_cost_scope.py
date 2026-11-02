"""Generated clock fixtures, not measured research observations."""
import copy
import unittest
from reporting_v93.cost_scope import phase_partition, comparisons, CELLS


def request(fallback=False):
    return dict(arm='compressed', request_elapsed_ns=100, timing=dict(
        predecessor_validation_ns=10, source_extraction_ns=20 if fallback else 0,
        neural_stage_record_pairs=6 if fallback else 0, encoding_and_gram_ns=0,
        serialization_ns=15, disposal_ns=5,
        stages=[dict(stage_id='a', elapsed_ns=30, fallback=fallback),
                dict(stage_id='b', elapsed_ns=20, fallback=False)]))


class Scope(unittest.TestCase):
    def test_fallback_traversal_is_not_added_twice(self):
        r = phase_partition(140, request(True), 2)
        self.assertEqual(sum(r['disjoint_host_partition_ns'].values()), 140)
        self.assertEqual(r['disjoint_host_partition_ns']['unattributed_request_time'], 20)
        self.assertEqual(r['nested_source_extraction_ns'], 20)
        self.assertFalse(r['decoder_only_duration_available'])

    def test_no_fallback_partition_covers_host_without_named_residual(self):
        r = phase_partition(140, request(), 2)
        self.assertEqual(r['disjoint_host_partition_ns']['outside_request'], 40)
        self.assertTrue(r['remainder_is_not_a_named_operation'])
        self.assertEqual(r['fallback_stages'], [])

    def test_rejects_unexplained_or_impossible_source_clocks(self):
        for arm, fallback, duration in [('modern', True, 20), ('compressed', False, 20), ('compressed', True, 40)]:
            r=request(fallback);r['arm']=arm;r['timing']['source_extraction_ns']=duration
            with self.subTest(arm=arm,fallback=fallback,duration=duration), self.assertRaises(ValueError):
                phase_partition(140,r,2)

    def test_rejects_incomplete_stages_and_overlapping_phase_sum(self):
        for change in ('duplicate','missing','sum','host'):
            r=request();host=140
            if change=='duplicate':r['timing']['stages'][1]['stage_id']='a'
            elif change=='missing':r['timing']['stages'].pop()
            elif change=='sum':r['timing']['serialization_ns']=100
            else:host=90
            with self.subTest(change=change), self.assertRaises(ValueError):phase_partition(host,r,2)

    def test_every_endpoint_retained_even_when_speed_directions_differ(self):
        rows={(cell,step):dict(host_elapsed_ns=100,live_state_bytes=1000,checkpoint_inclusive_bytes=1500)
              for cell in CELLS for step in (1,2)}
        rows['optimized_compressed',1]['host_elapsed_ns']=80
        rows['optimized_compressed',2]['host_elapsed_ns']=120
        rows['optimized_compressed',1]['transaction_elapsed_ns']=1  # Deliberately excluded inner clock.
        got=comparisons(rows)
        self.assertEqual([x['step'] for x in got],[1,2])
        self.assertEqual(got[0]['optimized_compressed_to_modern']['host_elapsed_ns'],dict(numerator=4,denominator=5))
        self.assertEqual(got[1]['optimized_compressed_to_modern']['host_elapsed_ns'],dict(numerator=6,denominator=5))
        self.assertEqual(got[0]['combined_optimization_speedup']['compressed'],dict(numerator=5,denominator=4))

    def test_missing_cell_zero_duration_and_boolean_time_refused(self):
        original={(cell,step):dict(host_elapsed_ns=100,live_state_bytes=1000,checkpoint_inclusive_bytes=1500)
                  for cell in CELLS for step in (1,2)}
        for change in ('missing',0,True):
            rows=copy.deepcopy(original)
            if change=='missing':rows.pop(('reference_modern',2))
            else:rows['optimized_compressed',1]['host_elapsed_ns']=change
            with self.subTest(change=change), self.assertRaises(ValueError):comparisons(rows)

if __name__=='__main__':unittest.main()
