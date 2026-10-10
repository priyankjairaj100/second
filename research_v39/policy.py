"""Fixed policies for a bounded real-data scale pilot."""
from pathlib import Path
import hashlib
import json
import os

from src.run_store import canonical_json, digest
from src.experiment_inventory import source_hashes

ROOT = Path(__file__).resolve().parents[1]
PREFIX = Path('campaigns/ci_scale_v39')
REVISION = 'scale-v39-2026-10-10'
REPOSITORY = 'priyankjairaj100/second'
RETAINED_COUNTS = (1, 6, 12)
ORIGINAL_RECORDS = 13
TOKENS = 128
NORMALIZATION = ORIGINAL_RECORDS * TOKENS
WIDTH, ROWS = 768, 2304
STAGE = 'block.0000.qkv'
PHASE_CAP = 2400
DATA_CAP = 122
TRIGGER = dict(revision=REVISION, campaign=str(PREFIX), paid_compute_allowed=False,
               automatic_retry_allowed=False, phase_cpu_seconds=PHASE_CAP, data_cpu_seconds=DATA_CAP)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Missing or symbolic evidence: ' + str(path))
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def new(path, value, *, raw=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value if raw else canonical_json(value)
    with path.open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return dict(file=path.name, sha256=digest(payload), bytes=len(payload))


def extra_sources():
    paths = [p for folder in ('research_v35', 'research_v37', 'research_v39')
             for p in (ROOT / folder).glob('*.py')]
    paths += [ROOT / 'scripts/prepare_wikitext_pilot.py', ROOT / 'scripts/recover_assets_v32.py',
              ROOT / 'scripts/execute_gram_pilot_v35.py', ROOT / 'research_v38/bootstrap_target.py']
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}


def arm_order(retained):
    arms = ['gram_delete', 'gram_fresh', 'cached_token', 'cached_primal', 'compressed_48']
    if retained == 6:
        arms += ['compressed_32', 'compressed_40']
    return sorted(arms, key=lambda arm: digest(f'v39-order-20261010:{retained}:{arm}'.encode()))


def gram_budget():
    from research_v35.exact_gram import GramBudget
    return GramBudget(max_tokens=NORMALIZATION, max_product_terms=WIDTH * (WIDTH + 1) // 2 * NORMALIZATION,
                      max_memory_bytes=768 * 2**20)


def point_budget():
    from src.primal_certificate_v30 import PrimalBudget
    return PrimalBudget(max_workspace_bytes=512 * 2**20, max_work_units=6_000_000_000)


def verify_sources(program):
    require(source_hashes(ROOT) == program['source_sha256'], 'Numerical sources changed')
    require(extra_sources() == program['extra_source_sha256'], 'V39 sources changed')
    for name, expected in program['historical_ledgers_sha256'].items():
        require(sha(ROOT / name) == expected, 'Historical ledger changed: ' + name)
