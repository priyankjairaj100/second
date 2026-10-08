"""Fail-closed archive analysis fixtures; no neural model work."""
import copy
import unittest
from scripts import analyze_compressed_service_v30 as audit


class CompressedAnalysisTests(unittest.TestCase):
    def comparison(self,**changes):
        values = dict(repair_ns=90,conversion_ns=20,prepared_ns=300,original_model_ns=250,
            cold_times=dict(zip(audit.COLD_REFERENCES,(100,110,80))),compressed_bytes=80,lossless_bytes=100,lossless_repair_ns=60)
        values.update(changes)
        return audit.summarize_comparison(**values)

    def test_quality_schema_uses_only_its_explicit_frozen_source_contract(self):
        program = {'source_sha256':{'scripts/run_quality_v30.py':'a'*64}}
        trial = {'script':'run_followup_quality_v30.py'}
        result = dict(schema='adaptive-quality-followup-v30',provenance={'shared_evaluator_sha256':'a'*64})
        audit.verify_archive_source(result,program,trial)
        for bad in (dict(result,schema='unknown'),dict(result,provenance={})):
            with self.assertRaises(ValueError):audit.verify_archive_source(bad,program,trial)
        with self.assertRaises(ValueError):audit.verify_archive_source(result,program,{'script':'other.py'})

    def test_all_cold_times_and_fastest_gate_preserve_a_loss(self):
        result = self.comparison()
        self.assertFalse(result['latency_gate_passed'])
        self.assertTrue(result['storage_gate_passed'])
        self.assertFalse(result['combined_pilot_gate_passed'])
        self.assertEqual(len(result['cold_comparators']),3)
        self.assertEqual(result['minimum_cold_over_compressed_repair'],80/90)
        self.assertEqual(result['cold_comparators'][0]['cold_over_compressed_repair'],100/90)
        self.assertEqual(result['lossless_over_compressed_repair'],60/90)

    def test_conversion_is_additional_complete_preparation_cost(self):
        result = self.comparison()
        self.assertEqual(result['complete_compressed_preparation_seconds'],320/1e9)
        self.assertEqual(result['preparation_incremental_overhead_seconds'],70/1e9)
        self.assertEqual(result['one_request_prepared_total_seconds'],410/1e9)
        self.assertFalse(result['changing_state_lifetime_benefit_established'])

    def test_missing_comparator_zero_cost_and_storage_ties_do_not_pass(self):
        with self.assertRaises(ValueError):self.comparison(cold_times={'retained_cold':100})
        for value in (0,-1,True,1.5):
            with self.assertRaises(ValueError):self.comparison(conversion_ns=value)
        result = self.comparison(repair_ns=70,compressed_bytes=100)
        self.assertTrue(result['latency_gate_passed'])
        self.assertFalse(result['storage_gate_passed'])
        self.assertFalse(result['combined_pilot_gate_passed'])

    def diagnostics_fixture(self):
        stage_ids = ['stage-'+str(i) for i in range(24)]
        stages = []
        for index,sid in enumerate(stage_ids):
            route = 'box_certificate' if index<20 else 'singleton_exact_point' if index<23 else 'exact_retained_replay'
            stages.append(dict(stage_id=sid,route=route,certificate_accepted=True if index<20 else None if index<23 else False,
                singleton_box=20<=index<23,certificate_rejection='uncertain' if index==23 else None,
                certificate_route='sparse',neural_stage_record_pairs=24 if index==23 else 0,elapsed_ns=1))
        reservations = []
        for row in stages:
            row['certificate_admission'] = {'routes':{'sparse':dict(admitted=True,work_units_reserved=1)}}
            row['solver_diagnostics'] = dict(backend='token',admission=dict(selected='token',
                routes={'token':dict(admitted=True,work_units=1)}))
            if row['route'] != 'singleton_exact_point':
                reservations.append(dict(kind='certificate',stage_id=row['stage_id'],route='sparse',work_units=1))
            if row['route'] != 'box_certificate':
                reservations.append(dict(kind='point',stage_id=row['stage_id'],route='token',work_units=1))
        d = dict(stages=stages,pending_stage=None,certificate_accepted_stages=20,certificate_rejected_stages=1,
            singleton_point_stages=3,certificate_attempted_stages=21,certificate_admission_refused_stages=0,
            point_solver_stages=4,point_solver_attempted_stages=4,neural_stage_record_pairs=24,
            replay_verified_stage_record_pairs=24,neural_stage_record_pairs_by_source={'source':24},
            total_possible_neural_stage_record_pairs=24,avoided_neural_stage_record_pairs=0,
            coefficient_reservations=reservations,
            certificate_work_units_reserved=21,point_work_units_reserved=4,model_seed_source='none',
            trusted_preparation_required=True,certificate_elapsed_ns=1,replay_elapsed_ns=1,point_solver_elapsed_ns=1,service_elapsed_ns=24)
        plan = dict(method='repair',record_ids=['source'],max_neural_stage_record_pairs=24,
                    max_point_work_units=10,max_certificate_work_units=30)
        result = dict(stage_ids=stage_ids,stage_count=24,diagnostics=d)
        return result,plan

    def test_certificate_acceptance_does_not_invent_avoided_ancestor_replay(self):
        result,plan = self.diagnostics_fixture()
        report = audit.verify_diagnostics(result,plan)
        self.assertEqual(report['certificate_accepted_stages'],20)
        self.assertEqual(report['neural_stage_record_pairs'],24)
        self.assertEqual(report['avoided_neural_stage_record_pairs'],0)

    def test_inconsistent_stage_replay_or_work_accounting_is_rejected(self):
        result,plan = self.diagnostics_fixture()
        for field,value in (('certificate_accepted_stages',21),('certificate_attempted_stages',22),
            ('neural_stage_record_pairs',0),('avoided_neural_stage_record_pairs',20),
            ('certificate_work_units_reserved',22),('point_solver_attempted_stages',5)):
            bad = copy.deepcopy(result);bad['diagnostics'][field] = value
            with self.subTest(field=field),self.assertRaises(ValueError):audit.verify_diagnostics(bad,plan)
        bad = copy.deepcopy(result);bad['diagnostics']['stages'].pop()
        with self.assertRaises(ValueError):audit.verify_diagnostics(bad,plan)
        with self.assertRaises(ValueError):audit.verify_diagnostics(result,dict(plan,max_neural_stage_record_pairs=23))
        with self.assertRaises(ValueError):audit.verify_diagnostics(result,dict(plan,max_certificate_work_units=20))

    def test_each_attempt_requires_one_matching_stage_and_route_reservation(self):
        result,plan = self.diagnostics_fixture()
        changes = (
            lambda d:d['coefficient_reservations'].append(dict(d['coefficient_reservations'][0])),
            lambda d:d['coefficient_reservations'].pop(),
            lambda d:d['coefficient_reservations'][0].update(stage_id='absent'),
            lambda d:d['coefficient_reservations'][0].update(route='primal'),
            lambda d:d['coefficient_reservations'][0].update(work_units=2),
            lambda d:d['neural_stage_record_pairs_by_source'].update(source=-1,extra=25),
            lambda d:d['stages'][0].update(neural_stage_record_pairs=1),
        )
        for change in changes:
            bad = copy.deepcopy(result);change(bad['diagnostics'])
            with self.assertRaises(ValueError):audit.verify_diagnostics(bad,plan)

    def test_accepted_box_cannot_discard_its_certificate_and_reservation(self):
        result,plan = self.diagnostics_fixture()
        bad = copy.deepcopy(result)
        bad['diagnostics']['stages'][0]['certificate_route'] = None
        bad['diagnostics']['coefficient_reservations'].pop(0)
        bad['diagnostics']['certificate_work_units_reserved'] -= 1
        with self.assertRaises(ValueError):audit.verify_diagnostics(bad,plan)
        for index in (0,20):
            bad = copy.deepcopy(result);bad['diagnostics']['stages'][index]['certificate_rejection'] = 'contradiction'
            with self.assertRaises(ValueError):audit.verify_diagnostics(bad,plan)

    def test_fallback_without_reported_coordinate_rounds_remains_valid(self):
        result,plan = self.diagnostics_fixture()
        result['diagnostics']['stages'][-1]['certificate_failure_diagnostics'] = {
            'native_diagnostics':{'unresolved_coordinate_rounds':[]}}
        report = audit.verify_diagnostics(result,plan)
        self.assertIsNone(report['unresolved_coordinates_by_stage'][0]['final_reported_row_coordinate_pairs'])

    def test_conversion_requires_every_source_enclosure_and_zero_neural_work(self):
        d = dict(schema='verified-lossless-to-compressed-conversion-v30',every_source_hash_verified=True,
            every_enclosure_contains_source=True,complete_original_model_preserved=True,conversion_uses_no_quantizer=True,
            checked_enclosures=48,decoded_exact_factors=48,neural_stage_record_pairs=0,point_solver_stages=0,decoded_source_bytes=1024)
        result = dict(stage_count=24,diagnostics=d,containment_verified_for_all_factors=True)
        plan = dict(method='convert_lossless',record_ids=['a','b'])
        self.assertEqual(audit.verify_diagnostics(result,plan)['checked_enclosures'],48)
        for key,value in (('checked_enclosures',47),('neural_stage_record_pairs',1),
                          ('every_enclosure_contains_source',False)):
            bad = copy.deepcopy(result);bad['diagnostics'][key] = value
            with self.assertRaises(ValueError):audit.verify_diagnostics(bad,plan)

    def test_external_input_path_must_be_exact_registered_artifact(self):
        entry = dict(attempt='/archive/original',completion_sha256='a'*64,
            verified_artifacts={'state':dict(file='state.bin',sha256='b'*64,bytes=1)})
        trial = dict(inputs_from_external={'lossless_state':dict(external='original',artifact='state')},
            plan=dict(inputs={'lossless_state':dict(path='/archive/original/outputs/state.bin',sha256='b'*64)}))
        program = dict(external_attempts={'original':entry})
        audit.verify_trial_external_inputs(trial,program)
        bad = copy.deepcopy(trial);bad['plan']['inputs']['lossless_state']['path'] = '/same-bytes/other.bin'
        with self.assertRaises(ValueError):audit.verify_trial_external_inputs(bad,program)


if __name__=='__main__':
    unittest.main()
