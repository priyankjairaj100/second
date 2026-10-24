"""Fixed matched-workload progress census; unchanged V87 per-file byte limits.

No record is dropped, shortened or coalesced. Unexpected output fails the new
worker. The bound requires the frozen V81/V84 call graph documented in PROTOCOL.
This module is not yet connected to a registered empirical worker.
"""
from collections import Counter
from pathlib import Path
from research_v84.config import ORDER, expected_artifacts, trial_parts
from research_v87 import outputs as old
from src.run_store import strict_json
from research_v80.io import read

STAGES = {'distilgpt2': 24, 'gpt2': 48}
MODEL_BYTES = {'distilgpt2': 21_233_664, 'gpt2': 42_467_328}


def verify_progress_sources():
    root = Path(__file__).resolve().parents[1]
    bindings = strict_json(read(root/'research_v90/PROGRESS_SOURCE_BINDINGS.json', maximum=2**20))
    for name, expected in bindings.items():
        p = Path(name)
        old.require(not p.is_absolute() and '..' not in p.parts, 'Relative progress source required')
        read(root/p, expected, maximum=2**20, retain=False)
    return bindings


def progress_limits(trial):
    profile, local = trial_parts(trial)
    stages = STAGES[profile]
    if local == 'prepare':
        return dict(context_ready=1, source_replayed=4,
                    stage_certified=stages, payload_stage=4*stages)
    if local == 'oracle':
        return dict(context_ready=1, source_replayed=3+2,
                    stage_certified=2*stages, payload_stage=8*stages)
    cell, step = local.rsplit('-', 1)
    return dict(context_ready=1, source_replayed=(3 if step == '1' else 2)
                if cell.endswith('_compressed') else 0,
                stage_certified=stages, payload_stage=0)


def complete_progress(trial, counts):
    limits = progress_limits(trial)
    old.require(set(counts) <= set(limits), 'Unknown progress phase')
    _, local = trial_parts(trial)
    for phase, maximum in limits.items():
        actual = counts.get(phase, 0)
        allowed = (0, maximum) if phase == 'source_replayed' and '_compressed-' in local else (maximum,)
        old.require(type(actual) is int and actual in allowed, 'Incomplete matched progress census')


def allowance(trial):
    profile, _ = trial_parts(trial)
    result = old.allowance(expected_artifacts(trial), MODEL_BYTES[profile])
    count = sum(progress_limits(trial).values())
    old.require(count <= old.PROGRESS_FILES, 'Matched progress exceeds historical maximum')
    result['progress_bytes'] = count*old.PROGRESS_BYTES
    result['output_bytes'] -= (old.PROGRESS_FILES-count)*old.PROGRESS_BYTES
    result['output_files'] -= old.PROGRESS_FILES-count
    return dict(result, progress_files=count, phase_limits=progress_limits(trial))


class Outputs(old.Outputs):
    def __init__(self, root, trial):
        verify_progress_sources()
        profile, _ = trial_parts(trial)
        self.trial = trial
        self.phase_limits = progress_limits(trial)
        self.phase_counts = Counter()
        super().__init__(root, expected_artifacts(trial), MODEL_BYTES[profile])

    def progress(self, item):
        try:
            old.require(type(item) is dict and type(item.get('phase')) is str,
                        'Explicit progress phase required')
            phase = item['phase']
            old.require(phase in self.phase_limits and self.phase_counts[phase] < self.phase_limits[phase],
                        'Matched progress phase allowance exhausted')
            result = super().progress(item)
            self.phase_counts[phase] += 1
            return result
        except BaseException:
            self.poisoned = True
            raise

    def finish(self, result):
        if type(result) is dict and result.get('status') == 'complete':
            complete_progress(self.trial, self.phase_counts)
        return super().finish(result)


def inspect_outputs(root, trial):
    profile, _ = trial_parts(trial)
    observation = old.inspect_outputs(root, expected_artifacts(trial), MODEL_BYTES[profile])
    counts = Counter()
    for name in observation['files']:
        if name.startswith('progress-'):
            raw = read(Path(root)/name, maximum=old.PROGRESS_BYTES)
            item = strict_json(raw)
            old.require(type(item) is dict and type(item.get('phase')) is str, 'Invalid progress record')
            counts[item['phase']] += 1
    complete_progress(trial, counts)
    limit = allowance(trial)
    old.require(observation['output_files'] <= limit['output_files']
                and observation['output_bytes'] <= limit['output_bytes'], 'Matched output allowance exceeded')
    return dict(observation, allowance=limit, phase_counts=dict(counts),
                scientific_correctness_checked=False)
