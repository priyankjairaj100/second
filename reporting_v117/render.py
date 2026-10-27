"""Render every row of the closed V112 screen without upgrading its scope.

The command first revalidates the exact actual terminal, reruns the unchanged
saved-metadata reducer, and compares its full output with the collected result.
It never connects to the cluster, changes a job, or executes numerical work.
No destination is created until all input and rendering checks have succeeded.
"""
import contextlib
import csv
from decimal import Decimal, localcontext
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reporting_v113.collect import validate_terminal, EXPECTED, JOBS
from reporting_v113.reduce import main as reduce_saved
from reporting_v93.cost_scope import comparisons

PROFILES = ('distilgpt2', 'gpt2')
CELLS = ('reference_compressed', 'optimized_compressed',
         'reference_modern', 'optimized_modern')
PROFILE_LABEL = {'distilgpt2': 'DistilGPT2', 'gpt2': 'GPT2'}


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(blob):
    return dict(bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest())


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def decimal(numerator, denominator=1, places=3):
    require(type(numerator) is int and type(denominator) is int and denominator > 0,
            'Exact integer numerator and positive denominator required')
    with localcontext() as ctx:
        ctx.prec = 40
        return format(Decimal(numerator)/Decimal(denominator), '.'+str(places)+'f')


def all_rows(result):
    require(result['schema'] == 'matched-screen-scalar-reduction-v113'
            and result['status'] == 'verified_saved_scalar_reduction',
            'Complete saved-scalar reduction required')
    for field in ('new_quality_evaluation', 'stable_latency_established',
                  'cross_architecture_generality', 'individual_optimization_effect_identified',
                  'preparation_reexecuted', 'preparation_cost_in_current_scheduler_total'):
        require(result[field] is False, 'Unsupported reporting scope: '+field)
    require(result['no_numerical_execution'] is True
            and result['preparation_cost_is_historical_not_zero'] is True
            and result['preparation_shared_across_cells'] is True
            and result['clocks_overlap'] is True,
            'Historical preparation and overlapping cost scope required')
    require(result['old_unknown_v80_cpu_seconds'] == 12602,
            'Historical unresolved debit must remain separate')
    expected = {(p, c, s) for p in PROFILES for c in CELLS for s in (1, 2)}
    rows = result['rows']
    require(len(rows) == len(expected) == 16, 'All sixteen request rows required')
    index = {(r['profile'], r['cell'], r['step']): r for r in rows}
    require(set(index) == expected, 'Duplicate, omitted or unexpected request row')
    require(set(result['reused_preparation_host_ns']) == set(PROFILES),
            'Both historical preparation clocks required')
    for p, value in result['reused_preparation_host_ns'].items():
        require(type(value) is int and value > 0, 'Historical preparation cannot be zero: '+p)
    for (p, c, s), row in index.items():
        operation = f'{p}/{c}-{s}'
        require(row['job_id'] == JOBS[operation]['job_id'], 'Wrong actual allocation')
        require(row['retained_records'] == (3 if s == 1 else 2), 'Wrong retained endpoint')
        for field in ('host_elapsed_ns', 'request_elapsed_ns', 'live_state_bytes',
                      'checkpoint_inclusive_bytes', 'max_rss_kib'):
            require(type(row[field]) is int and row[field] > 0, 'Invalid row scalar: '+field)
        require(row['host_elapsed_ns'] >= row['request_elapsed_ns']
                and row['checkpoint_inclusive_bytes'] >= row['live_state_bytes'],
                'Nested clock or checkpoint storage is inconsistent')
        parts = row['disjoint_host_partition_ns']
        require(all(type(v) is int and v >= 0 for v in parts.values())
                and sum(parts.values()) == row['host_elapsed_ns'],
                'Disjoint phase clocks must sum to complete host time')
        require(type(row['source_stage_record_pairs']) is int and row['source_stage_record_pairs'] >= 0
                and type(row['nested_source_extraction_ns']) is int and row['nested_source_extraction_ns'] >= 0
                and row['decoder_only_duration_available'] is False
                and row['remainder_is_not_a_named_operation'] is True,
                'Source access and telemetry limits must remain explicit')
    for p in PROFILES:
        measured = comparisons({(c, s): index[p, c, s] for c in CELLS for s in (1, 2)})
        require(measured == result['comparisons'][p], 'Ratios differ from complete saved rows')
    return index


def render(result):
    index = all_rows(result)
    scalars = ['profile', 'cell', 'step', 'retained_records', 'job_id',
               'host_elapsed_ns', 'request_elapsed_ns', 'live_state_bytes',
               'checkpoint_inclusive_bytes', 'max_rss_kib', 'source_stage_record_pairs',
               'nested_source_extraction_ns']
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
    writer.writerow(scalars+['fallback_stages', 'disjoint_host_partition_ns'])
    for p in PROFILES:
        for s in (1, 2):
            for c in CELLS:
                r = index[p, c, s]
                writer.writerow([r[k] for k in scalars]+[
                    json.dumps(r['fallback_stages'], separators=(',', ':')),
                    json.dumps(r['disjoint_host_partition_ns'], sort_keys=True, separators=(',', ':'))])

    tex = [r'\begin{table*}[t]', r'\centering\small',
           r'\begin{tabular}{llrrrrr}', r'\toprule',
           r'Checkpoint & Records & Ref. comp. & Opt. comp. & Ref. modern & Opt. modern & Opt. C/M \\',
           r'\midrule']
    contrasts = []
    for p in PROFILES:
        for s in (1, 2):
            r = [index[p, c, s] for c in CELLS]
            comp, modern = index[p, 'optimized_compressed', s], index[p, 'optimized_modern', s]
            ratio = decimal(comp['host_elapsed_ns'], modern['host_elapsed_ns'], 4)
            tex.append(' & '.join([PROFILE_LABEL[p], str(r[0]['retained_records'])]
                       + [decimal(q['host_elapsed_ns'], 10**9) for q in r]+[ratio])+r' \\')
            # Signed change is candidate-minus-baseline over baseline: positive is slower/larger.
            contrasts.append(dict(profile=p, step=s, retained_records=r[0]['retained_records'],
                complete_host_change_percent=decimal(100*(comp['host_elapsed_ns']-modern['host_elapsed_ns']), modern['host_elapsed_ns'], 3),
                live_storage_change_percent=decimal(100*(comp['live_state_bytes']-modern['live_state_bytes']), modern['live_state_bytes'], 3),
                checkpoint_inclusive_change_percent=decimal(100*(comp['checkpoint_inclusive_bytes']-modern['checkpoint_inclusive_bytes']), modern['checkpoint_inclusive_bytes'], 3)))
    tex.extend([r'\bottomrule', r'\end{tabular}',
        r'\caption{Complete host time in seconds for the matched point-token screen. Each cell is one observation. '
        r'C/M is optimized compressed time divided by optimized modern time; values above one mean compressed is slower. '
        r'All sixteen outputs match their same-checkpoint fresh reconstruction under both completed audits. '
        r'The related checkpoints, exposed four-record root, fixed normalization512, and $4\to3\to2$ trajectory '
        r'do not establish stable speed, cross-architecture generality, or predictive quality.}',
        r'\label{tab:matched-token}', r'\end{table*}'])

    costs = {k: result[k] for k in (
        'numerical_budget', 'scheduler_cpu_lower_ns', 'scheduler_cpu_upper_ns',
        'worker_controller_upper_ns', 'reused_preparation_host_ns',
        'old_unknown_v80_cpu_seconds', 'prior_screen_costs',
        'cumulative_screen_software_upper_cpu_ns', 'cumulative_screen_numerical_seconds',
        'cumulative_screen_controller_upper_ns')}
    costs.update(preparation_shared_across_cells=True, preparation_reexecuted=False,
                 preparation_cost_in_current_scheduler_total=False,
                 historical_preparation_cost_is_not_zero=True, clocks_overlap=True,
                 combine_scheduler_worker_controller_clocks=False,
                 all_experiments_total_established=False)
    scope = '''Matched point-token screen: closed-data reporting derivative

This derivative reports all sixteen actual request rows, both retained endpoints,
both related GPT-family checkpoints and all four matched implementation cells.
Complete host time is primary. Positive signed time/storage changes mean the
optimized compressed arm is slower/larger than optimized modern. No row is dropped
and no average pools away a losing endpoint. Nanosecond integers are retained;
the TeX table rounds seconds to three decimals and the ratio to four decimals.

Preparation was shared across cells and executed in the earlier V104 attempt.
Its original complete host clocks remain separate and nonzero. They cannot be
charged again as new numerical work or assigned entirely to one representation.
The current scheduler envelope includes the new checks, workers and both audits.
Contained worker/controller clocks overlap and must not be added to that envelope.
The prior software/controller/numerical charges and old unresolved12602-second
reservation remain separate. No complete all-experiments compute total is claimed.

Source extraction is nested within stage work on fallback; decoder-only duration
is unavailable. Unattributed request time is not assigned to decoding or another
named operation. The optimizations are bundled, so individual effects are not
identified. OS cache is uncontrolled and each cell has one observation. The two
related checkpoints do not establish cross-architecture generality. No new quality
evaluation was executed; earlier V72 quality cannot be transferred to this target.

Actual model/state/trust equality comes from the two completed cluster audits and
the frozen terminal check. This renderer rechecks their bound reporting metadata;
it does not rerun numerical work, independently re-audit binary payloads or prove
the trustworthiness of a fabricated receipt. Publication requires reviewing the
actual terminal and all outputs. No conference submission is performed.
'''
    return {'all-requests.tsv': stream.getvalue().encode(),
            'matched-table.tex': ('\n'.join(tex)+'\n').encode(),
            'signed-contrasts.json': encoded(contrasts),
            'costs-and-scope.json': encoded(costs), 'REPORTING_SCOPE.txt': scope.encode()}


def checked_collection(base):
    base = Path(base)
    terminal_path = base/'terminal-stdout.json'
    terminal_raw = terminal_path.read_bytes()
    terminal = json.loads(terminal_raw)
    validate_terminal(terminal)  # Fixed program and all21 actual registered job IDs.
    reduction_raw = (base/'reduction.json').read_bytes()
    with tempfile.TemporaryDirectory(prefix='second-closed-report-') as temp:
        recomputed = Path(temp)/'reduction.json'
        with contextlib.redirect_stdout(io.StringIO()):
            reduce_saved(terminal_path, base/'receipts', recomputed)
        result = json.loads(recomputed.read_bytes())
    require(result == json.loads(reduction_raw),
            'Collected reduction differs from recomputed bound metadata')
    require(result['actual_terminal'] == identity(terminal_raw), 'Terminal commitment differs')
    # Rehash the complete input set after rendering preparation as well.
    bindings = {str(terminal_path): identity(terminal_raw),
                str(base/'reduction.json'): identity(reduction_raw)}
    for relative, entry in result['inputs'].items():
        path = base/'receipts'/relative
        expected = {k: entry[k] for k in ('bytes', 'sha256')}
        require(identity(path.read_bytes()) == expected, 'Changed saved receipt: '+relative)
        bindings[str(path)] = expected
    return result, bindings


def main(collection, destination):
    target = Path(destination)
    require(not target.exists(), 'New exclusive reporting destination required')
    result, bindings = checked_collection(collection)
    payload = render(result)
    for name, expected in bindings.items():
        require(identity(Path(name).read_bytes()) == expected, 'Input changed before report commit')
    payload['MANIFEST.json'] = encoded(dict(schema='closed-matched-report-v117',
        program_sha256=EXPECTED, actual_terminal=result['actual_terminal'],
        inputs=bindings, files={n: identity(b) for n, b in payload.items()},
        reporting_sources={name: identity((ROOT/name).read_bytes()) for name in
            ('reporting_v117/render.py', 'reporting_v113/collect.py',
             'reporting_v113/reduce.py', 'reporting_v93/cost_scope.py')}, no_numerical_execution=True,
        independent_binary_reaudit=False, submission_ready=False))
    target.mkdir(parents=True, exist_ok=False)
    for name, blob in payload.items():
        with (target/name).open('xb') as stream:
            stream.write(blob)
    print(json.dumps(dict(status='rendered_closed_matched_report', rows=16,
                         files=len(payload), destination=str(target))))


if __name__ == '__main__':
    main(*sys.argv[1:])
