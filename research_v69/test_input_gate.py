"""Generated predecessor metadata and bytes; no actual cluster/data evidence."""
import copy,unittest
from unittest.mock import patch
from research_v68.test_data_runner import terminal_values
from research_v69 import input_gate as g
from src.run_store import canonical_json,digest


def service_fixture():
    root=canonical_json(dict(records=[dict(id=f'root-{i:02d}',tokens=[i]*128) for i in range(13)]))
    program=dict(directory=str(g.V67_RUN),normalization=1664,retained_counts=[12,6],stage_count=24,
        code_count=42_467_328,model_bytes=21_233_664,inputs=dict(data_records=dict(path='fixture',**g.info(root))))
    ph=digest(canonical_json(program))
    with patch.object(g.data_entry,'V67_PROGRAM',ph):values=terminal_values()
    values.update(v67_program=program,root_records=g.strict_json(root))
    for kind in ['primary','supplemental']:
        values['v67_'+kind].update(schema='disjoint-service-'+kind+'-audit-v67',inputs={})
    models={}
    for step,n in enumerate([12,6],1):
        trial='compressed-'+str(step);blob=bytes([step])*21_233_664;models['candidate_'+str(n)]=blob
        c=dict(schema='disjoint-complete-service-worker-v67',trial=trial,status='complete',complete_model=True,
            program_sha256=ph,base_target_sha256=g.BASE_TARGET,service_target_sha256=g.SERVICE_TARGET,
            calibration_target_sha256=g.CALIBRATION_TARGET,artifacts={'model.bin':dict(file='model.bin',**g.info(blob))},
            request=dict(retained_ids=[r['id'] for r in values['root_records']['records'][-n:]]))
        values['completion_'+str(n)]=c
        for kind in ['primary','supplemental']:
            entries=values['v67_'+kind]['inputs'];entries[str(g.V67_RUN/trial/'outputs/model.bin')]=g.info(blob)
            entries[str(g.V67_RUN/'oracle/outputs'/f'step-{step}/model.bin')]=g.info(blob)
            entries[str(g.V67_RUN/trial/'outputs/completion.json')]=g.info(canonical_json(c))
    values['v67_supplemental']['evidence']['primary_receipt_sha256']=digest(canonical_json(values['v67_primary']))
    return values,models,ph,digest(root)


def quality_fixture():
    policy=g.data.POLICY;prefix=b'\x00'*policy['transfer_bytes'];candidates=[]
    for i in range(321):
        candidates.append(dict(id=f'c4:en:validation:shard1:line{i}',tokens=[100+i]*128,available_tokens=128,
            body_sha256=digest(f'body{i}'.encode()),normalized_text_sha256=digest(f'normal{i}'.encode()),
            url_sha256=digest(f'url{i}'.encode()),token_offset=0,line_index=i,split='validation'))
    protected=g.data.Exclusions();protected.ids.add('old-reserved')
    selected=g.data.select(candidates,protected);before=g.data.serialized_exclusions(protected)
    frame=dict(complete_records=321,fixture_only=True)
    records=dict(records=sorted([dict(id=r['id'],tokens=r['tokens']) for r in selected['chosen']],key=lambda r:r['id']))
    selection=dict(schema='untouched-c4-selection-v68',status='complete',policy=policy,source_prefix=g.info(prefix),frame=frame,
        records=g.info(canonical_json(records)),requested_articles=320,selected_articles=320,
        selected_metadata=[{k:v for k,v in r.items() if k!='tokens'} for r in selected['chosen']],
        sampling_order_ids=[r['id'] for r in selected['chosen']],eligible_articles=321,candidate_articles=321,
        exclusions_before=g.info(canonical_json(before)),inspected_frame_permanently_reserved=True,
        model_inference=False,quality_evaluation=False,semantic_deduplication=False)
    p=dict(schema='untouched-quality-data-admission-v68',directory=str(g.data_entry.RUN),policy=policy,
        caps=g.data_entry.CAPS,expected_tests=22,allowance_cpu_seconds=1506,automatic_retry=False,
        model_inference=False,quality_evaluation=False);ph=digest(canonical_json(p))
    results=dict(checks=dict(tests=22,failures=0,errors=0,skips=0),data=selection,audit=dict(status='verified',
        selected_articles=320,actual_saved_prefix_retokenized=True,actual_records_equal=True,
        actual_full_candidate_inventory_equal=True,actual_exclusion_union_equal=True))
    x={trial:dict(status='complete',error=None,trial=trial,registration_sha256=ph,caps=g.data_entry.CAPS[trial],
        result=result,model_inference=False,quality_evaluation=False) for trial,result in results.items()}
    x.update(registration=p,selection=selection,records=records,before=before,after=selected['exclusions_after'],
        inventory=dict(candidates=selected['candidates'],frame=frame,eligible_ids_in_sampling_order=selected['eligible_ids_in_sampling_order']),
        acquisition=dict(status='complete',error=None,method='GET',url=g.data.url(),received=g.info(prefix),automatic_retry=False,
            whole_source_sha256_is_metadata_only=True,whole_source_sha256_metadata=policy['whole_source_sha256_metadata'],
            headers={'Content-Range':f"bytes 0-{len(prefix)-1}/{policy['source_total_bytes']}"}))
    return x,prefix,ph


def encoded(x):return {k:canonical_json(v) for k,v in x.items()}


class InputGateTests(unittest.TestCase):
    def test_actual_candidate_bytes_bind_both_terminal_audits_and_exact_memberships(self):
        values,models,ph,rh=service_fixture()
        with patch.object(g.data_entry,'V67_PROGRAM',ph),patch.object(g,'RECORDS_SHA',rh):
            result=g.service(encoded(values),models)
        self.assertEqual(set(result['candidates']),{'candidate_12','candidate_6'})
        self.assertFalse(result['actual_full_successor_state_audit_repeated'])

    def test_changed_candidate_fresh_binding_or_retained_ids_refuse(self):
        values,models,ph,rh=service_fixture()
        with patch.object(g.data_entry,'V67_PROGRAM',ph),patch.object(g,'RECORDS_SHA',rh):
            wrong=dict(models,candidate_6=models['candidate_12'])
            with self.assertRaises(ValueError):g.service(encoded(values),wrong)
            x=copy.deepcopy(values);x['completion_6']['request']['retained_ids'].reverse()
            with self.assertRaises(ValueError):g.service(encoded(x),models)
            x=copy.deepcopy(values);path=str(g.V67_RUN/'oracle/outputs/step-1/model.bin')
            x['v67_supplemental']['inputs'][path]['sha256']='0'*64
            with self.assertRaises(ValueError):g.service(encoded(x),models)

    def test_complete_quality_bindings_reserve_every_inspected_candidate(self):
        x,prefix,ph=quality_fixture();result=g.quality(encoded(x),prefix,registration_sha256=ph)
        self.assertEqual(result['selected_articles'],320);self.assertEqual(result['inspected_frame_articles'],321)
        self.assertFalse(result['actual_saved_prefix_retokenization_repeated'])

    def test_missing_phase_audit_failure_or_changed_prefix_refuses(self):
        x,prefix,ph=quality_fixture()
        for trial in ['checks','data','audit']:
            changed=copy.deepcopy(x);changed[trial]['status']='failed'
            with self.subTest(trial=trial),self.assertRaises(ValueError):g.quality(encoded(changed),prefix,registration_sha256=ph)
        x['audit']['result']['actual_saved_prefix_retokenized']=False
        with self.assertRaises(ValueError):g.quality(encoded(x),prefix,registration_sha256=ph)
        x,prefix,ph=quality_fixture()
        with self.assertRaises(ValueError):g.quality(encoded(x),prefix[:-1],registration_sha256=ph)

    def test_unselected_exclusion_or_fixed_sample_order_cannot_be_dropped(self):
        x,prefix,ph=quality_fixture();unselected=next(r['id'] for r in x['inventory']['candidates'] if r['id'] not in x['selection']['sampling_order_ids'])
        changed=copy.deepcopy(x);changed['after']['ids'].remove(unselected)
        with self.assertRaises(ValueError):g.quality(encoded(changed),prefix,registration_sha256=ph)
        changed=copy.deepcopy(x);changed['selection']['sampling_order_ids'].reverse();changed['data']['result']=changed['selection']
        with self.assertRaises(ValueError):g.quality(encoded(changed),prefix,registration_sha256=ph)

    def test_rebound_token_file_still_must_match_actual_selected_inventory(self):
        x,prefix,ph=quality_fixture();x['records']['records'][0]['tokens'][0]+=1
        x['selection']['records']=g.info(canonical_json(x['records']));x['data']['result']=x['selection']
        with self.assertRaises(ValueError):g.quality(encoded(x),prefix,registration_sha256=ph)


if __name__=='__main__':unittest.main()
