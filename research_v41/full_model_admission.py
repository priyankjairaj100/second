"""Read-only full-model shape audit using existing public admission helpers.

This allocates no model or feature arrays and launches no empirical worker.
Component admission is not whole-process fit or a runtime guarantee.
"""
from pathlib import Path
import argparse
import hashlib
import json

from research_v37.direct_gram_ball import assess_direct_gram_ball_budget
from research_v40.streamed_primal_ball import assess_streamed
from research_v40.policy import point_budget
from src.native_token_coefficients_v30 import assess_native_coefficients
from src.native_box_coefficients_v31 import assess_native_box_coefficients

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path('campaigns/ci_scale_v39/attempts/prepare/outputs/base-target.json')


def audit():
    raw = (ROOT / TARGET).read_bytes()
    target = json.loads(raw)
    shapes = {}
    for stage in target['stages']:
        rows, width = stage['shape']
        shapes.setdefault((rows, width), []).append(stage['stage_id'])
    reports = []
    for (rows, width), stages in shapes.items():
        for tokens in (768, 1536):
            reports.append(dict(rows=rows, width=width, stages=stages, retained_tokens=tokens,
                raw_feature_bytes=8 * width * tokens,
                packed_gram_entries=width * (width + 1) // 2,
                direct_gram=assess_direct_gram_ball_budget(rows=rows, width=width, budget=point_budget()),
                streamed=assess_streamed(rows=rows, width=width, tokens=tokens, block_tokens=128,
                    max_blocks=tokens // 128, budget=point_budget()),
                token_point_coefficients=assess_native_coefficients(width, tokens),
                token_box_coefficients=assess_native_box_coefficients(width, tokens)))
    return dict(schema='full-model-shape-admission-v41', target_path=str(TARGET),
        target_sha256=hashlib.sha256(raw).hexdigest(), stages=len(target['stages']),
        observations=reports, numerical_arrays_allocated=False, empirical_worker_launched=False,
        uses_v40_primal_policy=True, token_coefficients_use_existing_default_policy=True,
        component_budgets_have_different_work_proxies=True,
        whole_process_fit_guaranteed=False, wall_time_guaranteed=False,
        complete_model_solver_dispatch_implemented=False,
        scope='Existing component admission only. Exact Gram parsing, model residency, replay, output, and token row work are not admitted here.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps([dict(rows=r['rows'], width=r['width'], tokens=r['retained_tokens'],
        admitted={name:r[name]['admitted'] for name in
                  ('direct_gram','streamed','token_point_coefficients','token_box_coefficients')})
        for r in report['observations']]))
