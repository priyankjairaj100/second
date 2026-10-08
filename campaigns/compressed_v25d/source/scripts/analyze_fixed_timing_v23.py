"""Verify V23 artifacts and summarize every registered timing outcome."""
import hashlib
import math
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.experiment_inventory import source_hashes
from src.pilot_budget import inherited_allowance
from src.run_store import canonical_json,digest
from launch_fixed_timing_v23 import load_progress


def main():
    campaign=ROOT/'campaigns/fixed_feature_v23'
    program_raw=(campaign/'program.json').read_bytes();program=json.loads(program_raw)
    protocol=(campaign/'protocol.json').read_bytes()
    assert json.loads(protocol)['program_sha256']==digest(program_raw)
    assert source_hashes(campaign/'source')==program['source_sha256']
    extension_path=campaign/'continuation-v24/program.json'
    extension=json.loads(extension_path.read_bytes()) if extension_path.exists() else None
    trials=list(program['trials'])
    if extension:
        assert extension['program_sha256']==digest(program_raw)
        ids={t['id'] for t in trials}
        trials.extend(t for t in extension['trials'] if t['id'] not in ids)
    rows=[];complete={};model_paths={}
    for trial in trials:
        base=campaign/'attempts'/trial['id'];receipt_path=base/'worker/result.json'
        if not receipt_path.exists():
            rows.append(dict(id=trial['id'],status='running' if base.exists() else 'unstarted'))
            continue
        receipt_raw=receipt_path.read_bytes();receipt=json.loads(receipt_raw)
        plan_raw=(base/'plan.json').read_bytes();plan=json.loads(plan_raw)
        assert receipt['worker_identity']['plan_sha256']==digest(plan_raw)
        if receipt.get('status')!='complete' or not (base/'transaction.json').exists():
            progress=json.loads((base/'outputs/progress.json').read_bytes())
            row=dict(id=trial['id'],status='controller_incomplete',outer_seconds=None,
                charged_or_reserved_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],
                observed_cpu_ns=None,numerical_progress_status=progress['status'],
                body_diagnostic_seconds=progress['phases'][-1]['elapsed_ns']/1e9,
                timing_inference='unavailable; body diagnostic is not a complete transaction')
            artifact=progress.get('model_artifact')
            if artifact:
                path=base/'outputs'/artifact['file']
                with path.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==artifact['sha256']
                row['verified_model_artifact']=artifact
            rows.append(row);continue
        assert receipt['budget_debit']['state']=='settled'
        for label,artifact in receipt['artifacts'].items():
            payload=(base/'worker'/receipt['attempt']/label).read_bytes()
            assert len(payload)==artifact['bytes'] and digest(payload)==artifact['sha256']
        assert plan['source_sha256']==program['source_sha256']
        assert plan['program_sha256']==digest(program_raw)
        assert plan['protocol_sha256']==digest(protocol)
        tx=json.loads((base/'transaction.json').read_bytes())
        assert tx['receipt_sha256']==digest(receipt_raw)
        row=dict(id=trial['id'],status=receipt['outcome']['status'],
            outer_seconds=tx['outer_transaction_elapsed_ns']/1e9,
            worker_seconds=receipt['outcome']['elapsed_wall_ns']/1e9,
            charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],
            receipt_sha256=digest(receipt_raw),plan_sha256=digest(plan_raw))
        if row['status']=='complete':
            progress_raw=(base/'outputs/progress.json').read_bytes();progress=load_progress(base)
            assert progress['status']=='complete' and progress['plan_sha256']==digest(plan_raw)
            assert progress['stage_count']==24 and progress['model_code_elements']==42467328
            assert progress['complete_model']
            row.update(progress_sha256=digest(progress_raw),model_sha256=progress['model_sha256'],
                fixed_target_sha256=progress['fixed_target_sha256'],base_target_sha256=progress['base_target_sha256'],
                recovered_terminal_metadata=progress.get('recovered_terminal_metadata',False))
            for label in ('model','state'):
                artifact=progress.get(label+'_artifact')
                if artifact is None:continue
                path=base/'outputs'/artifact['file']
                with path.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
                assert actual==artifact['sha256'] and path.stat().st_size==artifact['bytes']
                row[label+'_artifact']=artifact
                if label=='model':model_paths[trial['id']]=path
            d=progress['diagnostics']
            row['neural_stage_record_pairs']=d['neural_stage_record_pairs']+d['anchor_preparation_stage_record_pairs']
            row['stored_factor_bytes']=progress.get('state_factor_bytes',0)
            row['fixed_feature_values_read']=d['fixed_feature_values_read']
            row['native_compile_ns']=(d.get('native_build_manifest') or {}).get('compile_elapsed_ns')
            complete[trial['id']]=row
        rows.append(row)
    target_equal=len({r['fixed_target_sha256'] for r in complete.values()})<=1
    assert target_equal
    retained=[row for name,row in complete.items() if name!='prepare-001']
    model_equal=len({r['model_sha256'] for r in retained})<=1
    assert model_equal
    states=[r['state_artifact']['sha256'] for r in retained if 'state_artifact' in r]
    state_equal=len(set(states))<=1;assert state_equal
    pairs=[]
    for i in (1,2,3):
        repair,cold=f'repair-{i:03d}',f'cold-{i:03d}'
        if repair in complete and cold in complete:
            a,b=complete[repair]['outer_seconds'],complete[cold]['outer_seconds']
            pairs.append(dict(repetition=i,repair_seconds=a,cold_seconds=b,
                cold_over_repair_speedup=b/a,repair_over_cold_ratio=a/b))
    pilot_gate=None
    warm='warm-cold-replacement-001' if extension else 'warm-cold-001'
    gate_ids=['prepare-001','repair-001','cold-001','indexed-001','fresh-001',warm,'warm-repair-001']
    if all(x in complete for x in gate_ids):
        repair=complete['repair-001']['outer_seconds']
        replay=min(complete['cold-001']['outer_seconds'],complete[warm]['outer_seconds'])
        pilot_gate=(repair/replay<=.90 and repair<complete['fresh-001']['outer_seconds']
                    and complete['repair-001']['neural_stage_record_pairs']==0
                    and complete['cold-001']['neural_stage_record_pairs']==24
                    and complete['repair-001']['model_sha256']!=complete['prepare-001']['model_sha256'])
    code_change=None
    if 'prepare-001' in model_paths and 'repair-001' in model_paths:
        import numpy as np
        from src.compact_state import parse,_unpack
        original=parse(model_paths['prepare-001'].read_bytes())
        repaired=parse(model_paths['repair-001'].read_bytes())
        count=0;per_stage=[]
        for a,b in zip(original.stages,repaired.stages):
            assert (a.stage_id,a.shape,a.bits,a.scale_values)==(b.stage_id,b.shape,b.bits,b.scale_values)
            n=a.rows*a.columns
            differences=int(np.count_nonzero(_unpack(a.packed_indices,n,a.bits)!=_unpack(b.packed_indices,n,b.bits)))
            count+=differences;per_stage.append(dict(stage=a.stage_id,changed_codes=differences,total_codes=n))
        code_change=dict(changed_codes=count,total_codes=42467328,per_stage=per_stage)
    ledger=json.loads((campaign/'phase-cpu-budget/ledger.json').read_bytes())
    used=sum(row['charged_cpu_seconds'] for row in ledger['attempts'].values())
    settled=all(row['state']=='settled' for row in ledger['attempts'].values())
    old_used,old_left=inherited_allowance(ROOT)
    summary=dict(schema='fixed-timing-analysis-v23',program_sha256=digest(program_raw),
        rows=rows,pairs=pairs,pilot_repeat_gate_pass=pilot_gate,
        minimum_observed_pair_speedup=min((p['cold_over_repair_speedup'] for p in pairs),default=None),
        geometric_mean_pair_speedup=math.exp(sum(math.log(p['cold_over_repair_speedup']) for p in pairs)/len(pairs)) if pairs else None,
        continuation_program_sha256=digest(extension_path.read_bytes()) if extension else None,
        recorded_cpu_seconds=sum(r['charged_cpu_seconds'] for r in ledger['attempts'].values() if r['state']=='settled'),
        unknown_reserved_cpu_seconds=sum(r['charged_cpu_seconds'] for r in ledger['attempts'].values() if r['state']=='reserved'),
        all_registered_attempts_have_completion_or_documented_incident=all(r['status'] in ('complete','controller_incomplete') for r in rows),
        unknown_usage_permanently_charged=not settled,
        complete_target_identity_equal=target_equal,retained_models_equal=model_equal,
        retained_states_equal=state_equal,code_changes=code_change,
        new_phase_charged_or_reserved_cpu_seconds=used,new_phase_remaining_cpu_seconds=900-used,
        legacy_charged_cpu_seconds=old_used,legacy_remaining_cpu_seconds=old_left,
        combined_charged_or_reserved_cpu_seconds=old_used+used,all_workers_settled=settled,
        timing_scope=program['primary_clock'],roots=1,original_records=2,retained_records=1,
        tokens_per_record=16,confirmation=False,population_speedup_established=False,
        measured_lifetime_superiority=False,novelty_established=False,
        scientific_program_complete=False)
    (campaign/'summary.json').write_bytes(canonical_json(summary))
    print(json.dumps(dict(completed=len(complete),pilot_gate=pilot_gate,pairs=pairs,
        new_phase_remaining=900-used,all_settled=settled)))


if __name__=='__main__':main()
