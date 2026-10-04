"""Exclusive timing arithmetic and tiny software fixtures, not benchmarks."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from src.diagnostic_breakdown import decompose_records,diagnostic_report,REQUIRED_CATEGORIES
from src.service_telemetry import ServiceTelemetry
from src.transaction_timing import accounting_partition,detailed_accounting_partition
from tests import test_measured_comparison_v9 as fixtures


def window(a,b,clock=False):
    value={'start_ns':a,'end_ns':b,'wall_ns':b-a}
    if clock:value['clock']='time.perf_counter_ns_system_monotonic'
    return value


def evidence():
    spans=[]
    for name,a,b in [('observer_preflight',0,10),('worker_preparation',10,20),
        ('worker_execution_until_cleanup',20,900),('ordinary_process_cleanup',900,920),
        ('worker_finalization_and_commit',920,950),('observer_postflight',950,1000)]:
        spans.append({'name':name,'start_offset_ns':a,'end_offset_ns':b,'wall_ns':b-a})
    observer={'observer_clock':window(0,1000,True),'observed_wall_ns':1000,'timing_detail_spans':spans,
              'adopted_cleanup_windows':[window(932,940),window(970,975)],'outcome':{'status':'complete'}}
    child={'execution_mode':'diagnostic','output_contract':'canonical_state','outcome':{'status':'complete'},
        'preflight':{'loading_measurement':{'wall_time_ns':100,'timing_window':window(40,140,True)},
                     'chart_construction_measurement':{'wall_time_ns':30,'timing_window':window(150,180,True)}},
        'service_telemetry':{'instrumented':True,'timing_clock':'time.perf_counter_ns_system_monotonic',
            'timing_windows':[window(200,300),window(400,600)],'timing_windows_omitted':0,
            'total_exclusive_ns':300,'timings':{name:{'exclusive_ns':value,'calls':1} for name,value in
                [('extraction',50),('proof_verification',40),('replay_feature_evaluation',100),
                 ('factor_rounding',50),('serialization',20),('durable_output',30),('validation_metadata',10)]}}}
    return observer,child


class DiagnosticBreakdownTests(unittest.TestCase):
    def test_exact_disjoint_decomposition_with_explicit_residual(self):
        observer,child=evidence(); value=decompose_records(observer,child)
        self.assertEqual(value['status'],'attributed')
        self.assertFalse(value['verified_artifacts'])
        self.assertFalse(value['named_attribution_complete'])
        self.assertEqual(value['accounting_sum_ns'],1000)
        observer['outcome']['status']='incomplete'
        self.assertEqual(decompose_records(observer,child)['status'],'partial')
        self.assertEqual(value['categories_ns']['cleanup'],33)
        self.assertEqual(value['categories_ns']['loading'],100)
        self.assertEqual(value['categories_ns']['retained_replay'],100)
        self.assertEqual(value['residual_ns'],450)
        self.assertTrue(set(REQUIRED_CATEGORIES)<=set(value['categories_ns']))
        # Nested old elapsed is neither accepted nor added to the total.
        observer['worker_outcome']={'elapsed_wall_ns':9000000}
        self.assertEqual(decompose_records(observer,child)['accounting_sum_ns'],1000)

    def test_overlap_escape_bad_totals_and_boolean_durations_rejected(self):
        for mutate in (
            lambda o,c:c['preflight']['loading_measurement'].update(wall_time_ns=210,timing_window=window(40,250,True)),
            lambda o,c:c['service_telemetry']['timing_windows'].__setitem__(1,window(880,1080)),
            lambda o,c:c['service_telemetry'].update(total_exclusive_ns=301),
            lambda o,c:c['service_telemetry']['timings']['extraction'].update(exclusive_ns=True),
            lambda o,c:o.update(adopted_cleanup_windows=[window(910,915)]),
            lambda o,c:o['timing_detail_spans'][2].update(start_offset_ns=21),
        ):
            observer,child=evidence();mutate(observer,child)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):
                decompose_records(observer,child)

    def test_clean_truncation_and_unknown_labels_never_gain_full_attribution(self):
        observer,child=evidence(); child['execution_mode']='clean'
        value=decompose_records(observer,child)
        self.assertEqual(value['status'],'partial')
        self.assertEqual(value['categories_ns']['loading'],0)
        self.assertEqual(value['residual_ns'],880)
        observer,child=evidence();child['service_telemetry']['timing_windows_omitted']=1
        value=decompose_records(observer,child)
        self.assertEqual(value['status'],'partial');self.assertEqual(value['residual_ns'],750)
        observer,child=evidence();part=child['service_telemetry']['timings'].pop('extraction')
        child['service_telemetry']['timings']['future_unknown']=part
        value=decompose_records(observer,child)
        self.assertEqual(value['status'],'partial')
        self.assertEqual(value['categories_ns']['unmapped_service_category'],50)
        self.assertEqual(value['accounting_sum_ns'],1000)

    def test_worker_cleanup_refinement_preserves_old_elapsed_and_receipts(self):
        old={'timing_boundary':{'clock':'time.perf_counter_ns_same_controller_process',
             'start_ns':3,'cleanup_end_ns':8},'outcome':{'elapsed_wall_ns':5}}
        coarse=accounting_partition(0,2,9,10,old)
        self.assertEqual(detailed_accounting_partition(coarse,old),coarse)
        current=deepcopy(old);current['timing_boundary']['cleanup_start_ns']=6
        detail=detailed_accounting_partition(coarse,current)
        self.assertEqual(sum(x['wall_ns'] for x in detail),10)
        self.assertEqual(next(x['wall_ns'] for x in detail if x['name']=='ordinary_process_cleanup'),2)
        self.assertEqual(old['outcome']['elapsed_wall_ns'],5)
        current['timing_boundary']['cleanup_start_ns']=9
        with self.assertRaises(ValueError):detailed_accounting_partition(coarse,current)

    def test_incomplete_worker_without_coordinates_retains_outer_cost_only(self):
        observer,child=evidence()
        observer['timing_detail_spans']=[{'name':'worker_call_unpartitioned',
            'start_offset_ns':0,'end_offset_ns':1000,'wall_ns':1000}]
        observer['outcome']['status']='incomplete'
        value=decompose_records(observer,child)
        self.assertEqual(value['status'],'partial')
        self.assertFalse(value['named_attribution_complete'])
        self.assertEqual(value['accounting_sum_ns'],1000)
        self.assertEqual(value['child_diagnostic_windows'],[])

    def test_collector_root_windows_equal_exclusive_sum_and_are_bounded(self):
        from src.service_telemetry import DiagnosticLimits
        clock=iter([0,2,5,10,20,25]).__next__
        collector=ServiceTelemetry(clock=clock,diagnostic_limits=DiagnosticLimits(max_counter_keys=1))
        with collector.span('outer'):
            with collector.span('nested'):pass
        with collector.span('outer'):pass
        value=collector.payload()
        self.assertEqual(value['total_exclusive_ns'],15)
        self.assertEqual(value['timing_windows'],[window(0,10)])
        self.assertEqual(value['timing_windows_omitted'],1)
        self.assertEqual(value['timing_clock'],'custom_unverified')

    def test_actual_diagnostic_artifacts_decompose_without_double_count(self):
        from src.measured_comparison import run_measured_comparison
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);plan,_=fixtures.fixture(root,mode='diagnostic')
            comparison=run_measured_comparison(plan,root/'out')
            self.assertEqual(comparison['outcome'],{'status':'complete'},comparison)
            report=diagnostic_report(root/'out')
            for role,value in report['roles'].items():
                self.assertTrue(value['verified_artifacts'])
                self.assertEqual(value['status'],'attributed',(role,value))
                self.assertEqual(value['accounting_sum_ns'],value['observed_wall_ns'])
                self.assertEqual(sum(value['categories_ns'].values()),value['observed_wall_ns'])
                self.assertGreater(value['categories_ns']['loading'],0)
                self.assertGreater(value['categories_ns']['serialization'],0)
                self.assertGreater(value['categories_ns']['durable_output'],0)
                self.assertGreater(value['categories_ns']['cleanup'],0)
                if role=='model_only_fresh':self.assertNotIn('chart_construction',value['categories_ns'])
                else:self.assertGreater(value['categories_ns']['chart_construction'],0)

if __name__=='__main__':unittest.main()
