"""Prepare an unregistered ordered compressed-service pilot."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.run_store import canonical_json


def build(root=ROOT):
    old=json.loads((root/'campaigns/full_service_v30/program.json').read_bytes())
    template=next(row['plan'] for row in old['trials'] if row['id']=='repair-001')
    original=json.loads((root/'campaigns/ordered_service_v30/attempts/prepare-256/outputs/completion.json').read_bytes())
    retained=json.loads((root/'campaigns/ordered_service_v30/attempts/repair-001/outputs/completion.json').read_bytes())
    common={key:template[key] for key in ('checkpoint','original_token_count','solver_backend',
        'solver_budget','max_point_work_units','use_candidates')}
    common.update(codec_bits=40,block_size=256,decoder_backend='ordered',certificate_backend='sparse',
        sparse_budget=dict(max_work_units=6_000_000_000,max_workspace_bytes=2**30,
                           max_preconditioned_coordinates=16,max_rounds=4),
        max_certificate_work_units=96_000_000_000,max_certificate_workspace_bytes=2**30,
        expected_target=original['fixed_target_sha256'])
    conversion=dict(common,method='convert_lossless',record_ids=original['original_record_ids'],deleted_ids=[],
        max_neural_stage_record_pairs=0,inputs=dict(records=template['inputs']['records']))
    repair=dict(common,method='repair',record_ids=template['record_ids'],deleted_ids=template['deleted_ids'],
        max_neural_stage_record_pairs=24,inputs=dict(template['inputs']))
    return dict(schema='ordered-compressed-pilot-draft-v30',status='draft_unregistered',confirmation=False,
        phase_cpu_cap_seconds=1200,scope='one complete compressed repair under matched ordered decoding',
        external_attempts=dict(
            original=dict(attempt=str(root/'campaigns/ordered_service_v30/attempts/prepare-256'),
                equals=dict(status='complete',schema='ordered-complete-service-transaction-v30',
                    method='direct_fresh',complete_model=True,complete_state=True,original_token_count=256,
                    retained_token_count=256,fixed_target_sha256=original['fixed_target_sha256'])),
            retained_lossless=dict(attempt=str(root/'campaigns/ordered_service_v30/attempts/repair-001'),
                equals=dict(status='complete',schema='ordered-complete-service-transaction-v30',
                    method='repair',complete_model=True,complete_state=True,original_token_count=256,
                    retained_token_count=128,fixed_target_sha256=original['fixed_target_sha256'])),
            retained_cold=dict(attempt=str(root/'campaigns/ordered_service_v30/attempts/cold-001'),
                equals=dict(status='complete',schema='ordered-complete-service-transaction-v30',
                    method='model_only_fresh',complete_model=True,original_token_count=256,
                    retained_token_count=128,fixed_target_sha256=original['fixed_target_sha256'])),
            quality=dict(attempt=str(root/'campaigns/quality_extensions_v30/attempts/matched-quality-128'),
                equals={'status':'complete','development_safety_gate_pass':True,'matched_quality_gate_pass':True,
                    'historical_control_parity_pass':True,
                    'provenance.new_model_sha256':retained['model_artifact']['sha256']})),
        external_equalities=[dict(left='retained_lossless',right='retained_cold',artifacts=['model'])],
        trials=[dict(id='convert-256',script='run_compressed_service_v30.py',cpu_seconds=240,wall_seconds=360,
            plan=conversion,inputs_from_external=dict(lossless_completion=dict(external='original',completion=True),
                lossless_model=dict(external='original',artifact='model'),
                lossless_state=dict(external='original',artifact='state')),
            compare_external=[dict(external='original',artifacts=['model'])]),
            dict(id='repair-128',script='run_compressed_service_v30.py',cpu_seconds=600,wall_seconds=900,
                plan=repair,depends=[dict(trial='convert-256')],
                inputs_from_external=dict(reference_completion=dict(external='retained_cold',completion=True)),
                inputs_from_trial=dict(prior_state=dict(trial='convert-256',artifact='state'),
                    compressed_preparation_completion=dict(trial='convert-256',completion=True)),
                compare_external=[dict(external='retained_cold',artifacts=['model'])],
                storage_gate=dict(external='retained_lossless',artifact='state',strictly_smaller=True),
                latency_gate=dict(external='retained_cold',strictly_faster=True))],
        scientific_gate='exact full output; smaller complete state than matched lossless; complete latency below ordered cold before repeating',
        certificate_policy='sparse at 128 retained tokens, selected prospectively from the reviewed 128-token point-backend screen; this is a certificate-route hypothesis, not measured sparse-certificate superiority',
        certificate_workspace_policy='independent one-GiB certificate array allowance; matched point policy remains 512 MiB; six-GiB process ceiling remains unchanged',
        cost_boundary='includes evidence-closure verification and oracle artifact hashing; extra auditing is conservative against compressed repair',
        preparation_cost='matched ordered lossless original preparation plus measured conversion; subtract matched original model-only baseline for overhead',
        stop_rule='preserve refusal/error/mismatch; do not automatically retry or promote a losing pilot',
        exclusions='same training calibration documents; no new evaluation article or confirmation access')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'campaigns/compressed_service_v30.spec.json')
    args=p.parse_args()
    with args.output.open('xb') as stream:stream.write(canonical_json(build()))
    print(json.dumps(dict(status='draft_unregistered',path=str(args.output))))
