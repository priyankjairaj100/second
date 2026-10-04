"""Analysis correctness fixtures only; no research results or speed claims."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import measured_analysis as a
from src.instrumentation import instrumentation_scope, instrumentation_state
from src.run_store import canonical_json, digest


def fixture_evidence(*, roots=2, requests=2, repeats=3, phase='confirmation'):
    slots=[]
    for root in range(roots):
        for request in range(requests):
            for repeat in range(repeats):
                slots.append(dict(run_id=f'{root}-{request}-{repeat}',configuration_id='fixture',phase=phase,
                    root_id=str(root),request_id=str(request),repeat_index=repeat,target_manifest_sha256='a'*64,
                    execution_mode='clean',service_family='response',response_tier='linear',service_mode='certified',
                    verifier_policy='spectral',methods={name:dict(outcome='exact_complete',wall_ns=20 if name!='repair' else 10)
                                                        for name in a.METHODS}))
    return {'schema':'verified-measured-evidence-v1','kind':'single_request','inventory_sha256':'b'*64,
        'protocol_sha256':'c'*64,'protocol_status':'frozen_confirmation','protocol_blocked_fields':[],
        'primary_baseline':'model_only_fresh','primary_candidate':'repair','primary_comparison_count':1,
        'inference_settings_frozen':True,
        'analysis_group':'primary','settings':dict(seed=11,draws=100,confidence=.95,threshold=1.05),'slots':slots}


def issued(payload):
    # White-box pure arithmetic fixture. Production callers must use the loaders.
    return a.VerifiedMeasuredEvidence(payload,_issuer=a._ISSUER)


class MeasuredAnalysisTests(unittest.TestCase):
    def test_plain_dictionary_cannot_assert_verified_status(self):
        with self.assertRaises(a.MeasuredAnalysisError):a.VerifiedMeasuredEvidence(fixture_evidence())
        with self.assertRaises(a.MeasuredAnalysisError):a.analyze_verified_evidence(fixture_evidence())
        evidence=issued(fixture_evidence());copy=evidence.payload();copy['slots'].clear()
        self.assertTrue(evidence.payload()['slots'])

    def test_root_clustering_all_repeats_and_three_comparisons(self):
        result=a.analyze_verified_evidence(issued(fixture_evidence()))
        self.assertEqual(len(result['results']),3)
        for item in result['results']:
            self.assertEqual(item['planned_slots'],12);self.assertEqual(item['available_roots'],2)
            self.assertAlmostEqual(item['conditional_ratio'],2)
            self.assertEqual(len(item['root_mean_log_ratios']),2)
            self.assertEqual(item['confirmation_speed_rule_met'],item['baseline']=='model_only_fresh')
        self.assertFalse(result['empirical_attainment_established'])

    def test_one_failed_repeat_keeps_failure_and_blocks_confirmation(self):
        payload=fixture_evidence();payload['slots'][0]['methods']['repair']=dict(outcome='timeout',wall_ns=None)
        result=a.analyze_verified_evidence(issued(payload))['results'][0]
        self.assertEqual(result['outcome_counts']['repair']['timeout'],1)
        self.assertEqual(sum(r['complete_all_repeats'] for r in result['requests']),3)
        self.assertIsNotNone(result['conditional_ratio'])
        self.assertFalse(result['all_planned_exact_clean_complete']);self.assertFalse(result['confirmation_speed_rule_met'])

    def test_single_root_controls_and_diagnostic_never_confirmation(self):
        for change in ('root','control','diagnostic'):
            payload=fixture_evidence(roots=1 if change=='root' else 2)
            if change=='control':payload['analysis_group']='correctness_controls'
            if change=='diagnostic':
                for s in payload['slots']:
                    for row in s['methods'].values():row.update(outcome='diagnostic_timing',wall_ns=None)
            result=a.analyze_verified_evidence(issued(payload))['results'][0]
            self.assertFalse(result['confirmation_timing_eligible'])

    def test_multiple_primary_configurations_need_one_frozen_selector(self):
        payload=fixture_evidence();extra=deepcopy(payload['slots'])
        for row in extra:row.update(configuration_id='second',run_id='second-'+row['run_id'])
        payload['slots']+=extra
        report=a.analyze_verified_evidence(issued(payload))
        self.assertFalse(any(r['confirmation_speed_rule_met'] for r in report['results']))
        payload['primary_configuration']='fixture'
        report=a.analyze_verified_evidence(issued(payload))
        passing=[r for r in report['results'] if r['confirmation_speed_rule_met']]
        self.assertEqual([(r['configuration_id'],r['baseline']) for r in passing],[('fixture','model_only_fresh')])

    def test_request_weights_then_root_weights_not_repeat_weights(self):
        payload=fixture_evidence(roots=2,requests=2,repeats=1)
        for slot in payload['slots']:
            slot['methods']['model_only_fresh']['wall_ns']=40 if slot['root_id']=='0' else 10
        report=a.analyze_verified_evidence(issued(payload))['results'][0]
        self.assertAlmostEqual(report['conditional_ratio'],2)
        payload['slots'].append(deepcopy(payload['slots'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate planned'):a.analyze_verified_evidence(issued(payload))

    def test_partition_rejects_overlap_bool_and_missing_tail(self):
        valid={'observed_wall_ns':7,'accounting_sum_ns':7,'timing_spans':[
            dict(start_offset_ns=0,end_offset_ns=2,wall_ns=2),dict(start_offset_ns=2,end_offset_ns=7,wall_ns=5)]}
        self.assertEqual(a._partition(valid),7)
        for changed in (dict(valid,observed_wall_ns=True),dict(valid,accounting_sum_ns=6),
                        dict(valid,timing_spans=[dict(start_offset_ns=1,end_offset_ns=7,wall_ns=6)])):
            with self.assertRaises(a.MeasuredAnalysisError):a._partition(changed)

    def test_explicit_clean_contract_requires_every_marker(self):
        with instrumentation_scope('clean'):clean=instrumentation_state()
        self.assertTrue(a._clean(clean))
        for key in ('monitoring_tools_allocated','python_profiler_active','allocation_tracing_active'):
            changed=dict(clean);changed.pop(key)
            self.assertFalse(a._clean(changed))
            changed=dict(clean);changed[key]=True
            self.assertFalse(a._clean(changed))

    def test_model_only_has_no_state_equality_obligation(self):
        rows={name:dict(outcome='completed_unverified',model_sha256='a',state_sha256=None if name=='model_only_fresh' else 'b')
              for name in a.METHODS}
        a._exact(rows)
        self.assertTrue(all(r['outcome']=='exact_complete' for r in rows.values()))
        self.assertIsNone(rows['model_only_fresh']['exact_state'])
        rows['direct_fresh']['model_sha256']='wrong'
        for row in rows.values():row['outcome']='completed_unverified'
        a._exact(rows);self.assertTrue(all(r['outcome']=='mismatch' for r in rows.values()))

    def test_unstarted_method_remains_unstarted(self):
        row=a._role({'status':'not_started'},target='a'*64,execution_mode='clean',seen={},slot='r',role='model_only_fresh')
        self.assertEqual(row['outcome'],'not_started')
        with self.assertRaisesRegex(ValueError,'lacks an observer'):
            a._role({'status':'complete','wall_time_ns':1},target='a'*64,execution_mode='clean',seen={},slot='r',role='repair')

    def test_diagnostic_projection_preserves_omissions_and_unavailable_fields(self):
        target={'stages':[{'stage_id':'s','dependencies':[]}]}
        child={'preflight':{'target':target},'service_telemetry':{'certificate_funnel':{'counters':{'observations_dropped':3}}}}
        projected=a._child_projection(child,{},digest(canonical_json(target)))
        self.assertEqual(projected['target_graph'],{'stage_order':['s'],'parents':{'s':[]}})
        self.assertEqual(projected['service_telemetry']['certificate_funnel']['counters']['observations_dropped'],3)
        self.assertIsNone(projected['stage_audits']);self.assertIsNone(projected['ledger']);self.assertIsNone(projected['quality_payload'])
        child['service_telemetry'].clear()
        self.assertTrue(projected['service_telemetry'])
        self.assertIsNone(a._child_projection(child,{},'f'*64)['target_graph'])


class MeasuredArtifactAnalysisTests(unittest.TestCase):
    def test_unsealed_parent_with_all_finished_leaves_cannot_enter_ratios(self):
        from tests.test_measured_campaign_v9 import fixture
        from src.measured_comparison import run_measured_comparison
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);inventory,payload=fixture(root,quality=True)
            run_id=payload['entries'][0]['run_id'];output=root/'out'/'runs'/run_id
            with patch('src.measured_comparison._finalize_methods',side_effect=KeyboardInterrupt('before final seal')):
                with self.assertRaises(KeyboardInterrupt):
                    run_measured_comparison(root/'plan.json',output,inventory_path=inventory,inventory_run_id=run_id)
            evidence=a.load_measured_campaign_evidence(inventory,root/'out');slot=evidence.payload()['slots'][0]
            self.assertEqual(slot['archive_status'],'unsealed')
            self.assertTrue(all(row['outcome']=='unsealed_parent' for row in slot['methods'].values()),slot)
            self.assertIsNone(a.analyze_verified_evidence(evidence)['results'][0]['conditional_ratio'])

    def test_verified_output_failure_is_reported_not_promoted_or_dropped(self):
        from tests.test_measured_campaign_v9 import fixture
        from src.measured_inventory import run_measured_campaign
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);inventory,_=fixture(root,bad_target=True)
            result=run_measured_campaign(inventory,root/'out');self.assertEqual(result['outcome'],'failed')
            evidence=a.load_measured_campaign_evidence(inventory,root/'out')
            report=a.analyze_verified_evidence(evidence)['results'][0]
            self.assertIsNone(report['conditional_ratio'])
            self.assertEqual(sum(report['outcome_counts']['model_only_fresh'].values()),1)
            self.assertEqual(sum(report['outcome_counts']['repair'].values()),1)

    def test_missing_inventory_slots_do_not_create_outputs(self):
        from tests.test_measured_campaign_v9 import fixture
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);inventory,_=fixture(root)
            with patch('src.measured_comparison.run_measured_comparison',side_effect=AssertionError('analysis executed work')):
                evidence=a.load_measured_campaign_evidence(inventory,root/'absent')
            self.assertFalse((root/'absent').exists())
            self.assertTrue(all(row['outcome']=='missing_run' for row in evidence.payload()['slots'][0]['methods'].values()))
            self.assertIsNone(a.analyze_verified_evidence(evidence)['results'][0]['conditional_ratio'])

    def test_real_sealed_campaign_exact_models_duplicate_and_tampering(self):
        from tests.test_measured_campaign_v9 import fixture
        from src.measured_inventory import run_measured_campaign
        from src.run_store import strict_json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);inventory,payload=fixture(root)
            result=run_measured_campaign(inventory,root/'out')
            self.assertEqual(result['outcome'],'complete',result)
            evidence=a.load_measured_campaign_evidence(inventory,root/'out')
            slot=evidence.payload()['slots'][0]
            budget=evidence.payload()['phase_budget_snapshot'];storage=evidence.payload()['archive_storage_snapshot']
            self.assertEqual(budget['status'],'verified');self.assertEqual(storage['status'],'verified_at_read')
            self.assertTrue(budget['attempts']);self.assertEqual(len(budget['linked_archived_attempt_ids']),len(budget['attempts']))
            self.assertGreater(storage['nontransaction_file_bytes'],0)
            self.assertEqual(storage['total_unique_file_bytes'],storage['transaction_file_bytes']+storage['nontransaction_file_bytes'])
            self.assertTrue(all(row['outcome']=='exact_complete' for row in slot['methods'].values()),slot)
            for row in slot['methods'].values():
                self.assertEqual(set(row['target_graph']['stage_order']),set(row['stage_code_sha256']))
                self.assertEqual(digest(canonical_json(row['target_manifest'])),slot['target_manifest_sha256'])
                self.assertIsNone(row['stage_audits'])
                self.assertFalse(row['service_telemetry']['instrumented'])
            self.assertEqual(a.load_measured_campaign_evidence(inventory,root/'out').sha256,evidence.sha256)
            self.assertFalse(a.analyze_verified_evidence(evidence)['results'][0]['confirmation_speed_rule_met'])
            result_path=root/'out'/'runs'/payload['entries'][0]['run_id']/'result.json'
            saved=strict_json(result_path.read_bytes());row=saved['methods']['repair'];seen={}
            a._role(row,target=saved['target_manifest_sha256'],execution_mode='clean',seen=seen,slot='first',role='repair')
            with self.assertRaisesRegex(ValueError,'multiple planned'):
                a._role(row,target=saved['target_manifest_sha256'],execution_mode='clean',seen=seen,slot='second',role='repair')
            saved['methods']['repair']['wall_time_ns']+=1;result_path.write_bytes(canonical_json(saved))
            with self.assertRaises(ValueError):a.load_measured_campaign_evidence(inventory,root/'out')

    def test_real_sequence_lifetime_distinct_setup_and_single_charge(self):
        from tests.test_measured_sequence_v9 import fixture
        from src.measured_sequence import run_measured_sequence_campaign
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);_,inventory,_=fixture(root,requests=[{'request_id':'one','deleted_ids':['a']}],quality=True)
            result=run_measured_sequence_campaign(inventory,root/'out')
            self.assertEqual(result['outcome'],'complete',result)
            evidence=a.load_measured_sequence_evidence(inventory,root/'out');slot=evidence.payload()['slots'][0]
            for method in ('repair','indexed_fresh','model_only_fresh'):
                prep=slot['preparation']['model_only_fresh' if method=='model_only_fresh' else 'repair']
                self.assertEqual(slot['methods'][method]['wall_ns'],prep['wall_ns']+slot['steps'][0]['methods'][method]['wall_ns'])
            self.assertNotEqual(slot['preparation']['repair']['observation_id'],slot['preparation']['model_only_fresh']['observation_id'])
            self.assertEqual(slot['record_token_counts'],{'a':2,'b':2,'c':2})
            quality=slot['steps'][0]['quality']
            self.assertEqual(quality['outcome'],'complete_quality')
            self.assertEqual(quality['heldout_target_tokens'],slot['heldout_target_tokens'])
            self.assertEqual(set(quality['quality_payload']),{'base','original','direct_fresh','repair'})
            self.assertIsNone(quality['wall_ns'])
            self.assertEqual(len(a.analyze_verified_evidence(evidence)['results']),2)

    def test_diagnostic_sequence_exports_stage_audit_groups_without_clean_ratio(self):
        from tests.test_measured_sequence_v9 import fixture
        from src.measured_sequence import run_measured_sequence_campaign
        from src.run_store import strict_json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);plan_path,inventory_path,manifest=fixture(root,requests=[{'request_id':'one','deleted_ids':['a']}])
            plan=strict_json(plan_path.read_bytes());plan['execution_mode']='diagnostic'
            inventory=strict_json(inventory_path.read_bytes())
            inventory['plans'][0].update(plan_payload=plan,plan_sha256=digest(canonical_json(plan)))
            inventory_path.write_bytes(canonical_json(inventory));plan_path.write_bytes(canonical_json(plan))
            protocol=strict_json((root/'protocol.json').read_bytes());protocol['planned_inventory_sha256']=digest(canonical_json(inventory))
            (root/'protocol.json').write_bytes(canonical_json(protocol))
            manifest['protocol']['sha256']=digest(canonical_json(protocol));(root/'sequence0.json').write_bytes(canonical_json(manifest))
            result=run_measured_sequence_campaign(inventory_path,root/'out');self.assertEqual(result['outcome'],'complete',result)
            evidence=a.load_measured_sequence_evidence(inventory_path,root/'out',execution_mode='diagnostic');slot=evidence.payload()['slots'][0]
            self.assertEqual(evidence.payload()['execution_mode_filter'],'diagnostic')
            with self.assertRaisesRegex(ValueError,'no frozen sequences'):
                a.load_measured_sequence_evidence(inventory_path,root/'out',execution_mode='clean')
            row=slot['steps'][0]['methods']['repair']
            self.assertEqual(row['outcome'],'diagnostic_timing');self.assertTrue(row['exact_model'])
            self.assertTrue(row['stage_audits']);self.assertTrue(row['ledger'])
            self.assertEqual(set(row['record_groups']),{'b','c'})
            self.assertTrue(row['service_telemetry']['instrumented'])
            self.assertIn('counters',row['service_telemetry']['certificate_funnel'])
            self.assertIsNone(a.analyze_verified_evidence(evidence)['results'][0]['conditional_ratio'])


if __name__=='__main__':unittest.main()
