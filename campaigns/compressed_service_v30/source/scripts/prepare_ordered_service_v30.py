"""Write the prospective stronger-baseline experiment without model execution."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.run_store import canonical_json


def build(root=ROOT):
    previous = root/'campaigns/full_service_v30'
    old = json.loads((previous/'program.json').read_bytes())
    originals = {row['id']:row for row in old['trials']}
    prepared = json.loads(json.dumps(originals['prepare-128']['plan']))
    retained = json.loads(json.dumps(originals['repair-001']['plan']))
    # Runtime policy and numerical target are unchanged. New preparation gives
    # the optimized source-local preparer its own truthful state identity.
    prepared['expected_model_sha256'] = json.loads(
        (previous/'attempts/prepare-128/outputs/completion.json').read_bytes())['model_artifact']['sha256']
    retained['expected_model_sha256'] = json.loads(
        (previous/'attempts/repair-001/outputs/completion.json').read_bytes())['model_artifact']['sha256']
    trials = []

    def add(name,method,*,original=False,depends=(),compare=()):
        plan = json.loads(json.dumps(prepared if original else retained))
        plan['method'] = method
        trial = dict(id=name,script='run_ordered_service_v30.py',plan=plan,
            cpu_seconds=900 if original else 600,wall_seconds=1200 if original else 900,
            depends=[dict(trial=previous) for previous in depends])
        if method in ('repair','indexed_fresh'):
            trial['inputs_from_trial'] = dict(
                preparation_completion=dict(trial='prepare-256',completion=True),
                prior_state=dict(trial='prepare-256',artifact='state'))
        if compare:
            trial['compare_to'] = [dict(trial=other,artifacts=list(kinds)) for other,kinds in compare]
        trial['compare_external'] = [dict(external='old_original' if original else 'old_retained',artifacts=['model'])]
        trials.append(trial)

    add('prepare-256','direct_fresh',original=True)
    add('original-model-256','model_only_fresh',original=True,depends=['prepare-256'],
        compare=[('prepare-256',['model'])])
    add('repair-001','repair',depends=['original-model-256'])
    add('cold-001','model_only_fresh',depends=['repair-001'],compare=[('repair-001',['model'])])
    add('indexed-001','indexed_fresh',depends=['cold-001'],compare=[('repair-001',['model','state'])])
    add('cold-002','model_only_fresh',depends=['indexed-001'],compare=[('repair-001',['model'])])
    add('repair-002','repair',depends=['cold-002'],compare=[('repair-001',['model','state'])])
    add('repair-003','repair',depends=['repair-002'],compare=[('repair-001',['model','state'])])
    add('cold-003','model_only_fresh',depends=['repair-003'],compare=[('repair-001',['model'])])
    return dict(schema='ordered-service-draft-v30',status='draft_unregistered',confirmation=False,
        phase_cpu_cap_seconds=3000,
        scope='stronger common neural implementation; one larger deletion; development timing replication',
        external_attempts=dict(
            old_original=dict(attempt=str(previous/'attempts/prepare-128'),
                equals=dict(status='complete',complete_model=True,complete_state=True,retained_token_count=256)),
            old_retained=dict(attempt=str(previous/'attempts/repair-001'),
                equals=dict(status='complete',complete_model=True,complete_state=True,retained_token_count=128))),
        trials=trials,
        primary_speed_estimator='geometric mean of three complete cold/repair pairs; report all pairs and descriptive range',
        lifetime_estimator='matched prepared-state minus original model-only cost; add paired request cost differences',
        method_order_policy='fixed alternating development order chosen before new outputs; OS caches uncontrolled',
        exactness_gate='every complete original/retained model must match its prior scalar finite reference',
        state_identity='new source-local preparer identity; same descriptors and models do not imply cross-implementation state equality',
        stop_rule='stop on error, refusal, mismatch, unsettled usage, or insufficient reservation; preserve failed and unstarted trials',
        repetition_scope='one shared request; not independent corpus or deletion replication',
        promotion='larger fixed/sequential quality gate and compressed service tradeoff remain separate prerequisites')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'campaigns/ordered_service_v30.spec.json')
    args=parser.parse_args()
    with args.output.open('xb') as stream:
        stream.write(canonical_json(build()))
    print(json.dumps(dict(status='draft_unregistered',path=str(args.output))))
