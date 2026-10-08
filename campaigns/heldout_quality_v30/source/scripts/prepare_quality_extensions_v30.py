"""Write an unregistered extension specification without model execution."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.run_store import canonical_json
from scripts.run_followup_quality_v30 import policy_for_mode


def descriptor(path, *, sizes=True):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    result = dict(path=str(path), sha256=sha)
    if sizes:
        result['bytes'] = path.stat().st_size
    return result


def build_specification(root=ROOT):
    root = Path(root)
    old_registration = root/'campaigns/quality_v30/registration.json'
    reg = json.loads(old_registration.read_bytes())
    full = json.loads((root/'campaigns/full_service_v30/program.json').read_bytes())
    repair_plan = next(t['plan'] for t in full['trials'] if t['id'] == 'repair-001')
    base = {k:repair_plan[k] for k in ('checkpoint', 'solver_backend', 'solver_budget',
            'max_point_work_units', 'original_token_count', 'use_candidates')}
    base['method'] = 'model_only_fresh'
    base['inputs'] = {k:dict(repair_plan['inputs'][k]) for k in ('records','config','weights')}
    sequential = dict(base, record_ids=['wikitext2:train:article-row-5326'],
                      deleted_ids=['wikitext2:train:article-row-27113'])
    quality_inputs = {key:dict(entry, path=str((root/entry['path']).resolve())) for key,entry in reg['inputs'].items()}
    quality_inputs.update(first_registration=descriptor(old_registration),
        first_completion=descriptor(root/'campaigns/research_v30/attempts/quality-001/outputs/completion.json'))
    return dict(schema='quality-extensions-draft-v30', status='draft_unregistered',
        confirmation=False, phase_cpu_cap_seconds=1200,
        scope='matched larger-calibration quality after complete ordered/scalar model identity gates; adaptive development only',
        execution_order=['sequential-128', 'matched-quality-128'],
        required_external_condition='finish external phase work before registration; historical ledger changes block execution',
        external_attempts=dict(
            larger_preparation=dict(attempt=str(root/'campaigns/full_service_v30/attempts/prepare-128'),
                equals=dict(status='complete', method='direct_fresh', original_token_count=256,
                            retained_token_count=256, complete_model=True, complete_state=True)),
            larger_repair=dict(attempt=str(root/'campaigns/full_service_v30/attempts/repair-001'),
                equals=dict(status='complete', method='repair', original_token_count=256,
                            retained_token_count=128, complete_model=True, complete_state=True)),
            ordered_preparation=dict(attempt=str(root/'campaigns/ordered_service_v30/attempts/prepare-256'),
                equals=dict(status='complete',method='direct_fresh',original_token_count=256,
                            retained_token_count=256,complete_model=True,complete_state=True)),
            ordered_repair=dict(attempt=str(root/'campaigns/ordered_service_v30/attempts/repair-001'),
                equals=dict(status='complete',method='repair',original_token_count=256,
                            retained_token_count=128,complete_model=True,complete_state=True))),
        external_equalities=[dict(left='ordered_preparation',right='larger_preparation',artifacts=['model']),
                             dict(left='ordered_repair',right='larger_repair',artifacts=['model'])],
        trials=[dict(id='sequential-128', script='run_ordered_sequential_v30.py',
            cpu_seconds=900, wall_seconds=1200, plan=sequential,
            plan_from_external=dict(expected_target=dict(external='larger_repair',field='base_target_sha256'))),
            dict(id='matched-quality-128', script='run_followup_quality_v30.py',
                cpu_seconds=180, wall_seconds=240,
                depends=[dict(trial='sequential-128', equals=dict(complete_model=True))],
                plan=dict(checkpoint=base['checkpoint'], inputs=quality_inputs, policy=policy_for_mode(True)),
                inputs_from_external=dict(new_completion=dict(external='larger_repair',completion=True),
                    new_model=dict(external='larger_repair',artifact='model')),
                inputs_from_trial=dict(new_sequential_completion=dict(trial='sequential-128',completion=True),
                    new_sequential_model=dict(trial='sequential-128',artifact='model')))],
        limits='budgets are abort ceilings; no completion or speed guarantee; no automatic retries',
        claims='sequential time is not a fixed-target repair comparator; original256 preparation baseline belongs to the ordered benchmark phase')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'campaigns/quality_extensions_v30.spec.json')
    parser.add_argument('--revise-draft', action='store_true')
    args = parser.parse_args()
    raw = canonical_json(build_specification())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.revise_draft:
        if ((ROOT/'campaigns/quality_extensions_v30').exists()
                or not args.output.exists()
                or json.loads(args.output.read_bytes()).get('status') != 'draft_unregistered'):
            raise ValueError('only an existing unregistered draft may be revised')
    with args.output.open('wb' if args.revise_draft else 'xb') as stream:
        stream.write(raw)
    print(json.dumps(dict(status='draft_unregistered', path=str(args.output), bytes=len(raw))))
