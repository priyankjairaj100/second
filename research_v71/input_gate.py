"""Bind actual candidate and quality bytes to completed predecessor receipts.

These checks do not reparse V67 successor state, retokenize the quality prefix,
authenticate a checkpoint or settle runtime budgets. Those gates remain required.
"""
from research_v67.io import require,info
from research_v67.config import RUN as V67_RUN,RECORDS_SHA,BASE_TARGET,SERVICE_TARGET,CALIBRATION_TARGET
from research_v68 import data_runner as data_entry,quality_data as data
from research_v71.quality_flow import records_check
from research_v71.construction_flow import membership
from src.run_store import canonical_json,strict_json,digest


def objects(values,keys):
    require(type(values) is dict and set(values)==set(keys),'Exact predecessor artifact census required')
    result={}
    for name,raw in values.items():
        require(type(raw) is bytes and len(raw)<=64*2**20,'Bounded actual metadata bytes required')
        value=strict_json(raw);require(type(value) is dict and canonical_json(value)==raw,'Canonical actual predecessor metadata required')
        result[name]=value
    return result


SERVICE_KEYS={'v67_primary','v67_supplemental','v67_primary_entry','v67_supplemental_entry',
    'v67_program','root_records','completion_12','completion_6'}


def service(values,models):
    x=objects(values,SERVICE_KEYS)
    require(digest(values['v67_program'])==data_entry.V67_PROGRAM,'Frozen V67 program required')
    p=x['v67_program'];primary=x['v67_primary'];supp=x['v67_supplemental']
    require(primary['schema']=='disjoint-service-primary-audit-v67'
        and supp['schema']=='disjoint-service-supplemental-audit-v67','Both V67 terminal audit schemas required')
    data_entry.terminal_audits(values)
    records=x['root_records']['records'];membership(records,12,RECORDS_SHA)
    require(info(values['root_records'])=={k:p['inputs']['data_records'][k] for k in ['bytes','sha256']}
        and p['directory']==str(V67_RUN) and p['normalization']==1664 and p['retained_counts']==[12,6]
        and p['stage_count']==24 and p['code_count']==42_467_328 and p['model_bytes']==21_233_664,
        'Actual original root or production geometry differs')
    require(type(models) is dict and set(models)=={'candidate_12','candidate_6'},'Both actual candidate models required')
    report={}
    for step,n in enumerate([12,6],1):
        label='candidate_'+str(n);blob=models[label];completion=x['completion_'+str(n)];trial='compressed-'+str(step)
        require(type(blob) is bytes and len(blob)==21_233_664,'Actual complete candidate model extent required')
        model_path=str(V67_RUN/trial/'outputs/model.bin');receipt_path=str(V67_RUN/trial/'outputs/completion.json')
        oracle_path=str(V67_RUN/'oracle/outputs'/f'step-{step}/model.bin');actual=info(blob)
        for audit in [primary,supp]:
            require(audit['inputs'][model_path]==audit['inputs'][oracle_path]==actual
                and audit['inputs'][receipt_path]==info(values['completion_'+str(n)]),
                'Actual candidate/fresh model and worker receipt differ from terminal audit inputs')
        require(completion['schema']=='disjoint-complete-service-worker-v67' and completion['trial']==trial
            and completion['status']=='complete' and completion['complete_model'] is True
            and completion['program_sha256']==data_entry.V67_PROGRAM
            and completion['base_target_sha256']==BASE_TARGET and completion['service_target_sha256']==SERVICE_TARGET
            and completion['calibration_target_sha256']==CALIBRATION_TARGET
            and {k:completion['artifacts']['model.bin'][k] for k in ['bytes','sha256']}==actual
            and completion['request']['retained_ids']==[r['id'] for r in records[-n:]],
            'Complete actual candidate worker/target/membership binding required')
        report[label]=dict(packed_model=actual,retained_records_sha256=digest(canonical_json(dict(records=records[-n:]))),
            actual_candidate_equals_both_audited_model_bindings=True)
    return dict(status='verified_candidate_byte_bindings',candidates=report,root_records=info(values['root_records']),
        actual_full_successor_state_audit_repeated=False,terminal_cost_audit_repeated=False)


QUALITY_KEYS={'registration','checks','data','audit','selection','records','inventory','before','after','acquisition','frame_audit'}


def quality(values,prefix,*,registration_sha256):
    x=objects(values,QUALITY_KEYS);p=x['registration'];s=x['selection'];audit=x['audit'];acq=x['acquisition']
    require(digest(values['registration'])==registration_sha256 and p['schema']=='untouched-quality-data-admission-v68'
        and p['directory']==str(data_entry.RUN) and p['policy']==data.POLICY
        and p['caps']==data_entry.CAPS and p['expected_tests']==22 and p['allowance_cpu_seconds']==1506
        and p['automatic_retry'] is False and p['model_inference'] is False and p['quality_evaluation'] is False,
        'Complete prospective V68 data registration required')
    for trial in ['checks','data','audit']:
        r=x[trial]
        require(r['status']=='complete' and r['error'] is None and r['trial']==trial
            and r['registration_sha256']==registration_sha256 and r['caps']==data_entry.CAPS[trial]
            and r['model_inference'] is False and r['quality_evaluation'] is False,'All completed V68 phases required')
    check=x['checks']['result']
    require(check['tests']==22 and check['failures']==check['errors']==check['skips']==0,'Passed V68 Linux data tests required')
    require(audit['result']['status']=='verified' and audit['result']['selected_articles']==320
        and all(audit['result'][k] is True for k in ['actual_saved_prefix_retokenized','actual_records_equal',
            'actual_full_candidate_inventory_equal','actual_exclusion_union_equal']), 'Actual V68 saved-data audit required')
    require(type(prefix) is bytes and len(prefix)==data.POLICY['transfer_bytes']
        and acq['status']=='complete' and acq['error'] is None and acq['method']=='GET'
        and acq['url']==data.url() and acq['received']==info(prefix) and acq['automatic_retry'] is False
        and acq['whole_source_sha256_is_metadata_only'] is True
        and acq['whole_source_sha256_metadata']==data.POLICY['whole_source_sha256_metadata']
        and acq['headers']['Content-Range']==f"bytes 0-{len(prefix)-1}/{data.POLICY['source_total_bytes']}",
        'Actual once-only bounded source prefix differs')
    require(s==x['data']['result'] and s['schema']=='untouched-c4-selection-v68' and s['status']=='complete'
        and s['policy']==data.POLICY and s['selected_articles']==s['requested_articles']==320
        and s['records']==info(values['records']) and s['source_prefix']==info(prefix)
        and s['exclusions_before']==info(values['before']) and s['inspected_frame_permanently_reserved'] is True
        and s['model_inference'] is False and s['quality_evaluation'] is False,'Exact actual selection bindings required')
    records=x['records']['records'];require(set(x['records'])=={'records'} and records_check(records)==s['records'],
        'All320 canonical actual selected token sequences required')
    before,after=x['before'],x['after']
    for e in [before,after]:
        require(set(e)=={'ids','content','chunks'} and all(type(v) is list and all(type(i) is str for i in v)
            and v==sorted(set(v)) for v in e.values()),'Canonical exclusion sets required')
    inventory=x['inventory'];rows=inventory['candidates'];require(type(rows) is list
        and len(rows)==s['candidate_articles']==s['frame']['complete_records'] and inventory['frame']==s['frame']
        and [r['line_index'] for r in rows]==list(range(len(rows))) and len({r['id'] for r in rows})==len(rows),
        'Full original-order candidate census required')
    # V69 omitted full short-sequence hashes present in the frozen Exclusions
    # implementation. V70 independently retokenized the SAME saved prefix and
    # bound their complete ordered census. Preserve exact union equality below.
    frame=x['frame_audit'];audit=frame['result']
    require(frame['schema']=='complete-frame-exclusion-audit-v70' and frame['status']=='complete'
        and frame['error'] is None and frame['registration_sha256']=='1120b96623394d9a4bf4314b6167b824b350a5665f4a446f781edbc67ef7bf84'
        and frame['job_id']=='15404' and frame['model_inference'] is False and frame['new_data_acquired'] is False,
        'Actual separate saved-frame audit required')
    require(audit['status']=='verified' and audit['actual_exact_exclusion_union'] is True
        and audit['retokenized_saved_prefix'] is True and audit['full_frame_articles']==len(rows),
        'Complete retokenized frame audit required')
    for name in ['before','after','inventory','selection','records','acquisition']:
        require(audit['inputs'][name]==info(values[name]),'Frame audit input commitment differs')
    require(audit['inputs']['prefix']==info(prefix),'Frame audit prefix commitment differs')
    saved=audit['saved_data_audit']
    require(saved['status']=='verified' and saved['selected_articles']==320 and all(saved[k] is True
        for k in ['actual_saved_prefix_retokenized','actual_records_equal','actual_full_candidate_inventory_equal',
                  'actual_exclusion_union_equal']),'Complete original saved-data audit required')
    full=audit['complete_token_hashes']
    require(type(full) is list and len(full)==len(rows) and [f['id'] for f in full]==[r['id'] for r in rows],
        'Ordered full-frame token commitment census required')
    import re
    for row,f in zip(rows,full):
        require(set(f)=={'id','token_count','tokens_sha256'} and type(f['token_count']) is int
            and f['token_count']==min(128,row['available_tokens']) and f['token_count']>=0
            and re.fullmatch('[0-9a-f]{64}',f['tokens_sha256']), 'Actual full token extent/hash differs')
        if str(f['token_count']) in row['token_prefixes']:
            require(f['tokens_sha256']==row['token_prefixes'][str(f['token_count'])],'Full standard-length prefix differs')
    require(audit['short_records']==sum(f['token_count']<128 for f in full),'Short-record census differs')
    full_byid={f['id']:f for f in full}
    byid={r['id']:r for r in rows};expected={k:set(v) for k,v in before.items()}
    for r in rows:
        expected['ids'].add(r['id']);expected['content'].update(r[k] for k in ['body_sha256','normalized_text_sha256','url_sha256'])
        expected['chunks'].update(r['token_prefixes'].values())
        if full_byid[r['id']]['token_count']:
            expected['chunks'].add(full_byid[r['id']]['tokens_sha256'])
    require(after=={k:sorted(v) for k,v in expected.items()},'Entire inspected frame must remain excluded')
    eligible=sorted([r['id'] for r in rows if r['eligible']],key=lambda rid:(digest((data.POLICY['order_seed']+rid).encode()),rid))
    require(eligible==inventory['eligible_ids_in_sampling_order'] and len(eligible)==s['eligible_articles']
        and s['sampling_order_ids']==eligible[:320] and [r['id'] for r in records]==sorted(eligible[:320]),
        'Fixed outcome-blind sample order differs')
    metadata=s['selected_metadata'];require(len(metadata)==320 and [m['id'] for m in metadata]==s['sampling_order_ids'],
        'Complete selected metadata order required')
    selected={m['id']:m for m in metadata}
    for r in records:
        row=byid[r['id']];m=selected[r['id']]
        require(full_byid[r['id']]['tokens_sha256']==digest(canonical_json(r['tokens'])),
            'Actual selected full tokens differ from the separate frame audit')
        require(row['eligible'] is True and row['exclusion_reasons']==[] and r['id'] not in before['ids']
            and all(row[k] not in before['content'] and row[k]==m[k] for k in ['body_sha256','normalized_text_sha256','url_sha256']),
            'Selected article overlaps protected metadata or differs from saved inventory')
        for n in [16,32,64,128]:
            h=digest(canonical_json(r['tokens'][:n]))
            require(row['token_prefixes'][str(n)]==h and h not in before['chunks'],'Actual selected tokens differ or overlap protected prefixes')
    return dict(status='verified_quality_byte_bindings',selected_articles=320,records=info(values['records']),
        inspected_frame_articles=len(rows),complete_frame_exclusions_verified=True,
        actual_saved_prefix_retokenization_repeated=False,shared_saved_data_audit_required=True,
        predecessor_runtime_and_cost_audit_still_required=True)
