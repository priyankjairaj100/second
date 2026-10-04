"""Profiled arithmetic observations cannot become clean latency evidence."""
import sys
import unittest
from unittest.mock import patch

from src.experiment_runner import measure
from src.result_analysis import analyze_runs, AnalysisError
from tests.test_result_analysis import record


class ProfiledAnalysisTests(unittest.TestCase):
    def test_arm_and_run_profile_labels_exclude_ratios(self):
        for top in (False, True):
            with self.subTest(top=top):
                row = record()
                if top:
                    row['profiler_active'] = True
                else:
                    for arm in row['methods'].values():
                        arm['profiler_active'] = True
                result = analyze_runs([row])['strata'][0]
                self.assertIsNone(result['conditional_ratio']['estimate'])
                self.assertEqual(result['methods']['repair']['outcomes'], {'diagnostic_timing': 1})
                self.assertTrue(row['methods']['repair']['exact_model_equal'])

    def test_profiler_flag_requires_boolean_and_keeps_mismatch_priority(self):
        row = record(); row['profiler_active'] = 'false'
        with self.assertRaises(AnalysisError):
            analyze_runs([row])
        row['profiler_active'] = True
        row['methods']['repair']['exact_model_equal'] = False
        result = analyze_runs([row])['strata'][0]
        self.assertEqual(result['methods']['repair']['outcomes'], {'mismatch': 1})

    def test_measure_marks_success_and_failure_when_profiled(self):
        with patch.object(sys, 'getprofile', return_value=object()):
            _, result = measure(lambda: 1)
            self.assertIs(result['profiler_active'], True)
            with self.assertRaises(ArithmeticError) as caught:
                measure(lambda: (_ for _ in ()).throw(ArithmeticError('fixture')))
            self.assertIs(caught.exception.runner_metrics['profiler_active'], True)
        _, ordinary = measure(lambda: 1)
        self.assertNotIn('profiler_active', ordinary)


if __name__ == '__main__':
    unittest.main()
