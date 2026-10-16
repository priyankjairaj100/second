"""Read-only portable verification of copied V59 metadata (no inference).

Usage: python3 -B validation/check_v59_metadata.py EXTRACTED_DIR
       [--prior-v58 EXTRACTED_V58_DIR_OR_TAR_GZ]

The default prior is the committed V58 metadata archive. Sources are checked in
this repository. Missing binary inputs remain explicit; cluster audit claims
about their contents are not promoted to a new local binary verification.
"""
import argparse
import json
import math
from pathlib import Path, PurePosixPath
import sys
import tarfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.run_store import canonical_json, digest, read_completed, strict_json

REMOTE = '/nfs_home/users/poonam/second-20261010'
CAMPAIGN = 'full-precision-anchor-v59-20261014-a'
LAUNCH = 'continuation-v59-20261014-a'
DIRECTORY = REMOTE+'/local_runs/'+CAMPAIGN
PROGRAM_SHA = '4a22292c903b4817629bd43449dcf6f22c827f7c31c9e525fcb3fdcca448e835'
SOURCE_COMMIT = '60a514098511526924cb5746a2a61851b5f6bd23'
PRIOR_PROGRAM_SHA = '4de04c4a0bd5db485c7ccd7511a4d5094195afdce15c115a909346879b84125f'
PRIOR_COMPLETION_SHA = '1c35aa42d570e51d17f800e538bf6118ccf4a0ede85d0903ddc1ed3c2689b135'
PRIOR_AUDIT_SHA = 'fa4a762a2ca6389968a503c0e224d1bd3f0d1bf0bb0aedb7acd24dd9d251b042'
FIRST_SHA = 'f397e6c54c44b3143921c67d49bc16bb39d7587ff66dcd740a4edcd5363863a0'
DEFAULT_PRIOR = REPO/'campaigns/csis_terminal_v54_v56_metadata_20261013.tar.gz'
CONTROLS = ('full_precision', 'nearest_rounding', 'fixed_feature', 'sequential')
CANDIDATE = 'full_precision_anchor'
LABELS = (*CONTROLS, CANDIDATE)
IDS = tuple('wikitext2:validation:article-row-'+str(i)
            for i in (2525, 2237, 132, 2115, 2352, 1040, 3636, 1299))
MODULES = ['research_v55.test_diagnostic', 'research_v55.test_sequential', 'research_v55.test_audit',
           'research_v59.test_anchor', 'research_v59.test_diagnostic', 'research_v59.test_audit', 'research_v59.test_campaign']
ARTIFACTS = {'sequential-target.json', 'fixed-target.json', 'execution-provenance.json',
    'historical-parity.json', 'candidate-target.json', 'candidate-model.bin',
    'candidate-model-metadata.json', 'candidate-diagnostics.json', 'first-stage-invariant.json'}
POLICY = dict(max_array_bytes=8*2**30, max_box_preconditioned_coordinates=16, max_box_rounds=4,
    max_point_refinement_coordinates=16, max_process_bytes=16*2**30,
    max_request_work_units=1_000_000_000_000, max_stage_work_units=64_000_000_000)
GUARDS = dict(max_pooled_candidate_over_sequential=1.05, max_article_candidate_over_sequential=1.20)


def require(value, message):
    if not value:
        raise ValueError(message)


def safe_path(root, name):
    relative = PurePosixPath(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe relative path')
    path = root.joinpath(*relative.parts)
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Symlink input refused')
    return path


def read_bytes(path):
    require(path.is_file() and not path.is_symlink(), 'Missing regular file: '+str(path))
    require(path.stat().st_size <= 32*2**20, 'Metadata exceeds 32 MiB: '+str(path))
    return path.read_bytes()


def read(path):
    return strict_json(read_bytes(path))


def byte_info(blob):
    return dict(bytes=len(blob), sha256=digest(blob))


def file_info(path):
    return byte_info(read_bytes(path))


def require_input_inventory(actual, expected):
    """Demand the complete frozen audit read set, including absent binaries."""
    require(type(actual) is dict and actual.keys() == expected.keys(), 'Audit input census differs')
    for name, entry in expected.items():
        require(canonical_json(actual[name]) == canonical_json(entry), 'Audit input commitment differs: '+name)


def ledger_sources(repository=REPO):
    paths = sorted((repository/'src').glob('*.py')) + sorted((repository/'scripts').glob('run_*.py'))
    require(bool(paths), 'Complete ledger source census missing')
    return {str(path.relative_to(repository)): file_info(path)['sha256'] for path in paths}


def validate_ledger(raw, sources):
    ledger = strict_json(raw)
    binding = dict(identity=dict(protocol_sha256=PROGRAM_SHA, source_sha256=sources),
        phase_cpu_seconds={'development':14402}, scope='trusted_worker_cpu_admission_not_process_tree_containment')
    require(canonical_json(ledger) == raw, 'Ledger requires canonical bytes')
    require(type(ledger) is dict and set(ledger) == {'schema','binding','attempts'}
            and ledger['schema'] == 'phase-cpu-ledger-v1'
            and canonical_json(ledger['binding']) == canonical_json(binding), 'Complete ledger source/schema/scope binding')
    require(type(ledger['attempts']) is dict and len(ledger['attempts']) <= 1, 'One-use ledger attempt census')
    for key, row in ledger['attempts'].items():
        require(type(key) is str and 0 < len(key) <= 1024 and type(row) is dict
                and set(row) == {'phase','reserved_cpu_seconds','state','charged_cpu_seconds','observed_cpu_ns'},
                'Ledger attempt fields')
        require(row['phase'] == 'development' and type(row['reserved_cpu_seconds']) is int
                and row['reserved_cpu_seconds'] == 14402 and type(row['charged_cpu_seconds']) is int
                and 0 < row['charged_cpu_seconds'] <= 14402, 'Ledger reservation/charge')
        if row['state'] == 'reserved':
            require(row['observed_cpu_ns'] is None and row['charged_cpu_seconds'] == 14402, 'Reserved debit')
        else:
            usage = row['observed_cpu_ns']
            require(row['state'] == 'settled' and type(usage) is int and usage >= 0
                    and row['charged_cpu_seconds'] == max(1,(usage+999999999)//1000000000), 'Settled debit usage')
    return ledger


def validate_resource_usage(usage):
    require(type(usage) is dict and all(type(usage.get(k)) is int and usage[k] >= 0
            for k in ('user_cpu_ns','system_cpu_ns','total_cpu_ns')), 'Nonnegative integer CPU usage')
    require(usage['total_cpu_ns'] == usage['user_cpu_ns']+usage['system_cpu_ns'], 'CPU usage sum')


def close_values(actual, expected, label):
    """Reporting-only tolerance for platform libm; gate booleans remain exact."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and actual.keys() == expected.keys(), label+' keys')
        for key in expected:
            close_values(actual[key], expected[key], label+'/'+key)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), label+' length')
        for i, (a, b) in enumerate(zip(actual, expected)):
            close_values(a, b, label+'/'+str(i))
    elif isinstance(expected, float):
        require(type(actual) in (float, int) and math.isfinite(actual) and math.isfinite(expected)
                and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), label+' value')
    else:
        require(type(actual) is type(expected) and actual == expected, label+' value')


def table(rows):
    require(type(rows) is list and len(rows) == 8 and tuple(r['id'] for r in rows) == IDS, 'Ordered article extent')
    for row in rows:
        require(type(row['predictions']) is int and row['predictions'] == 127
                and type(row['nll_sum']) in (int, float) and math.isfinite(row['nll_sum']), 'Finite raw NLL/count')
        if 'mean_nll' in row:
            require(row['mean_nll'] == row['nll_sum']/127, 'Reported mean NLL')
        if 'elapsed_ns' in row:
            require(type(row['elapsed_ns']) is int and row['elapsed_ns'] >= 0, 'Likelihood elapsed time')
    return {r['id']: r for r in rows}


def parity(quality, previous):
    require(set(quality) in (set(CONTROLS), set(LABELS)) and set(previous) == set(CONTROLS), 'Control labels')
    checks = []
    for label in CONTROLS:
        current, old = table(quality[label]), table(previous[label])
        for rid in IDS:
            delta = abs(current[rid]['nll_sum']-old[rid]['nll_sum'])/127
            checks.append(dict(model=label, record_id=rid, absolute_mean_nll_deviation=delta,
                               threshold=1e-8, passed=delta <= 1e-8))
    return dict(passed=all(r['passed'] for r in checks), checks=checks, checked_losses=32,
        max_absolute_mean_nll_deviation=max(r['absolute_mean_nll_deviation'] for r in checks),
        scope='All 32 frozen V55 full-precision, nearest, actual fixed-feature and actual sequential losses')


def finite_exp(value):
    try:
        return math.exp(value)
    except OverflowError:
        return None


def summarize(quality):
    require(set(quality) == set(LABELS), 'Five quality labels required')
    tables = {label: table(quality[label]) for label in LABELS}
    totals, comparisons = {}, {}
    for label in LABELS:
        loss = math.fsum(tables[label][rid]['nll_sum'] for rid in IDS)
        totals[label] = dict(nll_sum=loss, predictions=1016, mean_nll=loss/1016, perplexity=finite_exp(loss/1016))
    for reference in CONTROLS:
        deltas = [tables[CANDIDATE][rid]['nll_sum']-tables[reference][rid]['nll_sum'] for rid in IDS]
        logs = {rid: delta/127 for rid, delta in zip(IDS, deltas)}
        pooled, maximum = math.fsum(deltas)/1016, max(logs.values())
        comparisons[reference] = dict(pooled_log_perplexity_ratio=pooled, pooled_perplexity_ratio=finite_exp(pooled),
            article_log_perplexity_ratios=logs, article_perplexity_ratios={rid: finite_exp(v) for rid, v in logs.items()},
            max_article_log_ratio=maximum, max_article_ratio=finite_exp(maximum),
            articles_candidate_lower=sum(v < 0 for v in logs.values()), articles_candidate_equal=sum(v == 0 for v in logs.values()),
            articles_candidate_higher=sum(v > 0 for v in logs.values()))
    primary = comparisons['sequential']
    guards = dict(pooled_pass=primary['pooled_log_perplexity_ratio'] <= math.log(1.05),
                  every_article_pass=primary['max_article_log_ratio'] <= math.log(1.20))
    return dict(totals=totals, candidate_comparisons=comparisons, thresholds=GUARDS,
                guards=guards, development_guards_pass=all(guards.values()))


def check_progress(events, completion, diagnostics, first):
    quality = completion['quality']
    expected = [('targets_and_actual_models_validated', {})]
    for label in CONTROLS:
        expected.extend(('quality_article', dict(model=label, record_id=r['id'], nll_sum=r['nll_sum'])) for r in quality[label])
    expected.extend([('all_historical_controls_passed', dict(checked_losses=32)), ('candidate_construction_started', {})])
    expected.extend(('candidate_stage', {k: s[k] for k in ('stage_id', 'elapsed_ns', 'output_code_sha256')}) for s in diagnostics['stages'])
    expected.append(('candidate_model_validated', dict(first_stage_packed_sha256=first['packed_sha256'])))
    expected.extend(('quality_article', dict(model=CANDIDATE, record_id=r['id'], nll_sum=r['nll_sum'])) for r in quality[CANDIDATE])
    expected.append(('diagnostic_complete', dict(development_guards_pass=completion['development_guards_pass'])))
    require(len(events) == len(expected) == completion['progress_events'] == 69, '69 progress events required')
    previous = -1
    for event, (phase, values) in zip(events, expected):
        require(set(event) == {'phase', 'worker_elapsed_ns', *values}
                and event['phase'] == phase and all(event[k] == v for k, v in values.items()), 'Progress order/value')
        require(type(event['worker_elapsed_ns']) is int and event['worker_elapsed_ns'] >= previous, 'Progress clock order')
        previous = event['worker_elapsed_ns']
    require(previous <= completion['worker_elapsed_ns'], 'Progress outside worker clock')
    return dict(events=69, historical_losses_before_candidate=32, candidate_stages=24, candidate_losses=8, parity_before_candidate=True)


class Check:
    def __init__(self, root, prior=DEFAULT_PRIOR):
        self.root, self.prior = Path(root).resolve(), Path(prior).resolve()
        self.missing, self.verified, self.locations = {}, {}, {}
        self.tar = None
        self.p, self.old, self.previous, self.ledger = None, None, None, None
        self.jobs = {}
        self.partial_registration_capture = False
        self.plan_verified = False

    def close(self):
        if self.tar is not None:
            self.tar.close()

    def resolve(self, remote):
        require(remote.startswith(REMOTE+'/'), 'Input outside frozen checkout: '+remote)
        relative = remote[len(REMOTE)+1:]
        if not relative.startswith('local_runs/'):
            # Never read an uncopied large checkpoint to improve an inventory count.
            if Path(relative).suffix in ('.bin', '.npz', '.safetensors'):
                return None, None
            path = safe_path(REPO, relative)
            return (read_bytes(path), str(path)) if path.is_file() else (None, None)
        name = relative[len('local_runs/'):]
        path = safe_path(self.root, name)
        if path.is_file():
            return read_bytes(path), str(path)
        if Path(name).suffix in ('.bin', '.npz', '.safetensors'):
            return None, None
        if self.prior.is_dir():
            path = safe_path(self.prior, name)
            return (read_bytes(path), str(path)) if path.is_file() else (None, None)
        if self.prior.is_file():
            if self.tar is None:
                self.tar = tarfile.open(self.prior, 'r:*')
            try:
                member = self.tar.getmember(name)
            except KeyError:
                return None, None
            require(member.isfile() and member.size <= 32*2**20, 'Unsafe prior archive member')
            with self.tar.extractfile(member) as stream:
                return stream.read(), str(self.prior)+'::'+name
        return None, None

    def bound(self, remote, expected, *, required=False):
        expected = {k: expected[k] for k in ('bytes', 'sha256')}
        blob, location = self.resolve(remote)
        if blob is None:
            require(not required, 'Required metadata unavailable: '+remote)
            if remote in self.missing:
                require(self.missing[remote]['expected'] == expected, 'Conflicting absent-input hashes')
            self.missing[remote] = dict(expected=expected, status='NOT revalidated',
                kind='binary' if Path(remote).suffix in ('.bin', '.npz', '.safetensors') else 'metadata')
        else:
            require(byte_info(blob) == expected, 'Bound input hash mismatch: '+remote)
            self.verified[remote], self.locations[remote] = expected, location
        return blob

    def input_json(self, key):
        entry = self.p['inputs'][key]
        return strict_json(self.bound(entry['path'], entry, required=True))

    def collection(self):
        manifest = read(self.root/'collection-manifest.json')
        require(manifest.get('schema') in ('second-terminal-v59-metadata-v1', 'second-partial-v59-registration-metadata-v1')
                and type(manifest.get('files')) is dict and manifest['files'], 'Collection inventory required')
        self.partial_registration_capture = manifest['schema'] == 'second-partial-v59-registration-metadata-v1'
        if self.partial_registration_capture:
            require(manifest.get('terminal') is False, 'Partial registration capture cannot claim terminal outcome')
        for name, expected in manifest['files'].items():
            require(file_info(safe_path(self.root, name)) == expected, 'Copied file hash mismatch: '+name)
        actual = {str(p.relative_to(self.root)) for p in self.root.rglob('*') if p.is_file()}
        require(actual == set(manifest['files']) | {'collection-manifest.json'}, 'Unlisted/missing copied files')
        return manifest

    def registration(self):
        root = self.root/CAMPAIGN
        p = read(root/'program.json'); self.p = p
        require(file_info(root/'program.json')['sha256'] == digest(canonical_json(p)) == PROGRAM_SHA, 'Frozen V59 program')
        require(read(root/'registration.json') == dict(program_sha256=PROGRAM_SHA), 'Registration hash')
        require(read_bytes(self.root/LAUNCH/'source-commit.txt').decode().strip() == SOURCE_COMMIT,
                'Launch source commit')
        rows = [line.split('\t') for line in read_bytes(self.root/LAUNCH/'jobs.tsv').decode().splitlines()]
        require(len(rows) == 4 and [r[0] for r in rows] == ['checks','register','quality','audit']
                and all(len(r)==2 and r[1].isdigit() for r in rows), 'Four-stage one-use launch record')
        self.jobs = dict(rows)
        require(p['schema'] == 'full-precision-anchor-quality-diagnostic-v59' and p['directory'] == DIRECTORY
                and p['registered_source_commit'] == SOURCE_COMMIT and len(p['sources']) == 412, 'Program source identity')
        for name, sha in p['sources'].items():
            require(file_info(safe_path(REPO, name))['sha256'] == sha, 'Frozen source changed: '+name)
        for entry in p['inputs'].values():
            self.bound(entry['path'], entry)
        check = self.input_json('software_checks')
        require(check['status'] == 'passed' and check['tests'] == 49 and check['skipped'] == 0
                and check['modules'] == MODULES and check['sources'] == p['sources'] and check['runtime'] == p['runtime']
                and check['real_model_inference'] is False and check['slurm_job_id'] == self.jobs['checks']
                and p['registration_job'] == self.jobs['register'], 'Source/runtime-bound software gate')
        for key, expected in (('v55_program', PRIOR_PROGRAM_SHA), ('v55_completion', PRIOR_COMPLETION_SHA), ('v55_audit', PRIOR_AUDIT_SHA)):
            require(p['inputs'][key]['sha256'] == expected, 'Frozen V55 input commitment')
        old, previous, prior_audit = (self.input_json(k) for k in ('v55_program', 'v55_completion', 'v55_audit'))
        self.old, self.previous = old, previous
        require(old['runtime'] == p['runtime'] and p['records'] == old['records'] and p['retained_records'] == old['retained_records'], 'Prior runtime/data transfer')
        require(previous['status'] == 'complete' and previous['valid_diagnostic'] is True
                and previous['program_sha256'] == prior_audit['program_sha256'] == PRIOR_PROGRAM_SHA
                and prior_audit['status'] == 'verified' and previous['development_guards_pass'] is False
                and prior_audit['development_guards_pass'] is False and previous['summary'] == prior_audit['summary'], 'Prior adverse result preserved')
        require(self.input_json('v55_registration') == dict(program_sha256=PRIOR_PROGRAM_SHA), 'V55 registration')
        expected_design = dict(normalization=1664, ridge=[1, 100], bits=4, significant_bits=24, guards=GUARDS,
            parity_absolute_mean_nll_tolerance=1e-8, first_stage_packed_sha256=FIRST_SHA, controls=list(CONTROLS),
            candidate_count=1, teacher_stage_record_advances=144, quality_evaluations=40,
            worker_cpu_seconds=14400, worker_wall_seconds=18000, phase_cpu_seconds=14402,
            process_address_space_bytes=16*2**30, file_size_bytes=2*2**30, threads=1,
            automatic_retry=False, confirmation=False, acl_ready=False, new_evaluation_inputs=False,
            intervals=False, gpu_execution=False, repair_service=False, feature_drift_traversals=False)
        require(all(p[k] == v for k, v in expected_design.items()), 'Prospective design changed')
        require(tuple(r['id'] for r in p['records']) == IDS and all(len(r['tokens']) == 128 for r in p['records'])
                and len(p['retained_records']) == 6 and all(len(r['tokens']) == 128 for r in p['retained_records']), 'Registered data extent')
        exclusions = self.input_json('historical_exclusions')['excluded_from_future_confirmation_ids']
        require(len(set(exclusions)) == 60 and set(IDS) <= set(exclusions), 'Frozen exclusions')
        if (root/'budget/ledger.json').exists():
            sources = ledger_sources()
            require(len(sources) == 158 and all(p['sources'].get(name) == sha for name,sha in sources.items()),
                    'Ledger sources differ from frozen program')
            self.ledger = validate_ledger(read_bytes(root/'budget/ledger.json'), sources)
        else:
            require(self.partial_registration_capture, 'Terminal capture missing ledger')
        return dict(software_tests=49, software_skips=0, frozen_source_files=412, registered_program_sha256=PROGRAM_SHA,
                    inherited_runtime_equal=True, prior_adverse_quality_preserved=True)

    def worker(self):
        root = self.root/CAMPAIGN/'quality'
        if not (root/'plan.json').exists():
            return None
        plan = read(root/'plan.json')
        require(plan == dict(schema='full-precision-anchor-quality-plan-v59', directory=DIRECTORY,
            program=DIRECTORY+'/program.json', program_sha256=PROGRAM_SHA,
            output=DIRECTORY+'/quality/outputs', slurm_job_id=self.jobs['quality']), 'Worker plan binding')
        self.plan_verified = True
        if self.ledger is None or not (root/'worker/identity.json').exists():
            require(self.partial_registration_capture, 'Worker identity/ledger missing')
            return None
        identity = read(root/'worker/identity.json')
        command = [REMOTE+'/.venv-container/bin/python', '-B', '-m', 'research_v59.worker', DIRECTORY+'/quality/plan.json']
        require(identity['cwd'] == REMOTE and identity['command'] == command
                and identity['identity'] == dict(program_sha256=PROGRAM_SHA)
                and identity['phase_budget'] == dict(directory=DIRECTORY+'/budget', phase='development',
                    binding_sha256=digest(canonical_json(self.ledger['binding']))), 'Literal command/phase identity')
        expected = dict(cpu_seconds=14400, wall_seconds=18000, address_space_bytes=16*2**30,
                        file_size_bytes=2*2**30, threads=1, termination_grace_seconds=1)
        require(all(identity['limits'][k] == v for k, v in expected.items())
                and len(identity['limits']['affinity_cpus']) == 1, 'Worker limits')
        sealed = read_completed(root/'worker', identity)
        if sealed is None:
            return None
        require(canonical_json(sealed) == canonical_json(read(root/'worker'/sealed['attempt']/'status.json'))
                and sealed['limits'] == identity['limits'] and sealed['worker_identity'] == identity['identity'], 'Terminal worker seal')
        tx = read(root/'transaction.json')
        require(tx['worker_outcome'] == sealed['outcome'] and tx['slurm_job_id'] == plan['slurm_job_id'], 'Transaction outcome')
        require(sealed['outcome']['status'] == 'complete' and sealed['outcome']['returncode'] == 0, 'Captured worker execution failed')
        request = read(root/'worker'/sealed['attempt']/'request.json')
        ack = read(root/'worker'/sealed['attempt']/'limits-applied.json')
        require(request['command'] == command and request['cwd'] == REMOTE and request['limits'] == identity['limits'], 'Executed request')
        require(ack == sealed['limits_applied'] and ack['request_sha256'] == digest(canonical_json(request))
                and ack['cpu_seconds'] == [14400, 14401] and ack['address_space'] == [16*2**30]*2
                and ack['file_size'] == [2*2**30]*2 and ack['affinity_cpus'] == identity['limits']['affinity_cpus']
                and all(v == '1' for v in ack['thread_environment'].values()), 'Applied limit acknowledgment')
        debit = sealed['budget_debit']
        validate_resource_usage(sealed['resource_usage'])
        require(canonical_json(self.ledger['attempts']) == canonical_json({sealed['budget_attempt_id']: debit})
                and debit['state'] == 'settled'
                and debit['phase'] == 'development' and debit['observed_cpu_ns'] == sealed['resource_usage']['total_cpu_ns']
                and debit['charged_cpu_seconds'] == max(1,(debit['observed_cpu_ns']+999999999)//1000000000)
                and debit['reserved_cpu_seconds'] == 14402 and debit['charged_cpu_seconds'] <= 14402
                and sealed['budget_reservation_overrun'] is False, 'Settled CPU debit')
        snapshot = dict(binding_sha256=digest(canonical_json(self.ledger['binding'])), phase_cpu_seconds={'development':14402},
                        charged_cpu_seconds={'development':debit['charged_cpu_seconds']}, attempts=self.ledger['attempts'], over_cap={'development':False})
        require(canonical_json(tx['budget']) == canonical_json(snapshot), 'Transaction budget snapshot')
        return dict(plan=plan, sealed=sealed, transaction=tx, charged_cpu_seconds=debit['charged_cpu_seconds'],
                    observed_cpu_ns=debit['observed_cpu_ns'])

    def audit_inputs(self, worker, completion):
        """Reconstruct research_v59.audit's explicit Inputs reads exactly."""
        expected = {}

        def add(remote, entry):
            entry = {key:entry[key] for key in ('bytes','sha256')}
            require(type(entry['bytes']) is int and entry['bytes'] >= 0 and type(entry['sha256']) is str
                    and len(entry['sha256']) == 64 and all(c in '0123456789abcdef' for c in entry['sha256']),
                    'Malformed audit input commitment')
            require(remote not in expected or expected[remote] == entry, 'Conflicting audit input commitments')
            expected[remote] = entry

        def copied(relative):
            add(DIRECTORY+'/'+relative, file_info(safe_path(self.root/CAMPAIGN, relative)))

        for name in ('program.json','registration.json','budget/ledger.json',
                     'quality/worker/identity.json','quality/transaction.json','quality/plan.json',
                     'quality/worker/result.json','quality/outputs/completion.json'):
            copied(name)
        for entry in self.p['inputs'].values():
            add(entry['path'], entry)
        for name in self.p['sources']:
            add(REMOTE+'/'+name, file_info(safe_path(REPO,name)))
        sealed = worker['sealed']
        attempt = 'quality/worker/'+sealed['attempt']+'/'
        copied(attempt+'status.json')
        for name,entry in sealed['artifacts'].items():
            add(DIRECTORY+'/'+attempt+name, entry)
        for name,entry in completion['artifacts'].items():
            add(DIRECTORY+'/quality/outputs/'+name, entry)
        for index in range(69):
            copied(f'quality/outputs/progress-{index:04d}.json')
        return expected

    def candidate_metadata(self, c):
        out = self.root/CAMPAIGN/'quality/outputs'
        base, fixed, execution, target, meta, diagnostics, first = (read(out/name) for name in
            ('sequential-target.json', 'fixed-target.json', 'execution-provenance.json', 'candidate-target.json',
             'candidate-model-metadata.json', 'candidate-diagnostics.json', 'first-stage-invariant.json'))
        require(base == self.input_json('v55_sequential_target') and fixed == self.input_json('v55_fixed_target')
                and execution == self.input_json('v55_execution_provenance'), 'Historical target/execution identity')
        base_hash, target_hash = digest(canonical_json(base)), digest(canonical_json(target))
        require(base_hash == c['sequential_target_sha256'] and digest(canonical_json(fixed)) == c['fixed_target_sha256']
                and target_hash == c['candidate_target_sha256'] and target_hash not in (base_hash, c['fixed_target_sha256']), 'Distinct candidate target identity')
        feature_rule = 'each stage uses source-local features from original full-precision checkpoint weights'
        anchor_rule = 'original pinned binary64 checkpoint stage matrices; no quantized matrix is installed'
        teachers, seen = [], []
        require(len(base['stages']) == 24 and base['recipe']['original_token_count'] == 1664
                and base['recipe']['bits'] == 4 and base['recipe']['ridge'] == [1,100]
                and base['significant_bits'] == 24 and base['weight_digest_encoding'] == 'binary64_matrix_v1', 'Base target recipe')
        for row in base['stages']:
            require(len(row['dependencies']) == len(seen) and set(row['dependencies']) == set(seen)
                    and row['normalization'] == [1664,1] and row['ridge'] == [1,100], 'Base stage dependencies/recipe')
            seen.append(row['stage_id'])
            teachers.append({k: row[k] for k in ('stage_id', 'shape', 'weights_sha256')})
        expected = dict(schema='fixed-full-precision-anchor-calibration-target-v59', base_target_sha256=base_hash,
            decoder_sha256=digest(canonical_json(execution['decoder'])), implementation_manifest_sha256=digest(canonical_json(execution['implementation'])),
            constructor_source_sha256=self.p['sources']['research_v59/anchor.py'], feature_rule=feature_rule, anchor_rule=anchor_rule,
            prefix_rule='calibrated output codes never affect any feature', calibrated_dependencies='empty for every stage',
            original_normalization=1664, normalization_rule='unchanged original normalization from base target',
            grid_rule='unchanged base-only dyadic24 output-row grids; lower midpoint ties',
            record_rule='positions reset per source; causal within source; no cross-source state',
            teacher_weight_digest_encoding='binary64-matrix-little-endian-row-major-v1', teacher_stages=teachers,
            output_rule='complete stage codes only; no canonical repair-state contract declared',
            failure_rule='bounded certified stage solver; unresolved or exhausted resource budget aborts')
        require(target == expected and base['evaluator_id'] == 'certified-decoder-v1:'+expected['decoder_sha256'], 'Full-precision teacher target contract')
        prior_meta = self.input_json('v55_sequential_metadata')
        require(meta['target_sha256'] == target_hash and len(meta['stages']) == len(prior_meta['stages']) == 24, 'Candidate metadata extent')
        require(diagnostics['schema'] == 'full-precision-anchor-calibration-v59' and diagnostics['target_sha256'] == target_hash
                and diagnostics['base_target_sha256'] == base_hash and diagnostics['records'] == 6
                and diagnostics['retained_tokens'] == 768 and diagnostics['original_normalization'] == 1664
                and diagnostics['neural_stage_record_pairs'] == 144 and diagnostics['calibrated_prefix_access'] is False
                and diagnostics['prior_model_access'] is False and diagnostics['prior_factor_access'] is False
                and not diagnostics.get('aborted',False) and diagnostics['feature_rule'] == feature_rule
                and diagnostics['anchor_rule'] == anchor_rule and diagnostics['implementation'] == 'ordered-finite-decoder-v30'
                and diagnostics['implementation_manifest_sha256'] == target['implementation_manifest_sha256']
                and len(diagnostics['stages']) == len(diagnostics['point_admission']) == 24,
                'Candidate diagnostic extent')
        routes = {'streamed':0,'token':0}; work = 0
        for index, (m, old, base_row, stage, admission) in enumerate(zip(meta['stages'], prior_meta['stages'], base['stages'], diagnostics['stages'], diagnostics['point_admission'])):
            require(all(m[k] == old[k] for k in ('stage_id','rows','columns','grid_axis','bits','scale_values_hex','nbytes'))
                    and m['grid_axis'] == 'dyadic_row' and m['bits'] == 4 and m['nbytes'] == (m['rows']*m['columns']+1)//2
                    and m['scale_values_hex'] == base_row['row_scale_hex'] and [m['rows'],m['columns']] == base_row['shape'], 'Candidate stage/grid metadata')
            route = 'token' if 4*768 <= m['columns'] else 'streamed'
            require(stage['stage_id'] == m['stage_id'] and stage['output_code_sha256'] == m['sha256']
                    and stage['feature_tokens'] == 768 and stage['input_width'] == m['columns'] and stage['output_rows'] == m['rows']
                    and stage['route'] == route and stage['teacher_parent_stage_id'] == (seen[index-1] if index else None)
                    and stage['teacher_parent_weights_sha256'] == (base['stages'][index-1]['weights_sha256'] if index else None), 'Teacher parent/output commitment')
            require(admission['stage_id'] == m['stage_id'] and admission['target_sha256'] == target_hash
                    and admission['admitted'] is True and admission['selected_route'] == route
                    and admission['weights_sha256'] == base_row['weights_sha256'] and admission['kind'] == 'point'
                    and admission['total_tokens'] == 768 and admission['block_tokens'] == 128 and admission['max_blocks'] == 6
                    and admission['width'] == m['columns'] and admission['rows'] == m['rows']
                    and admission['policy'] == POLICY and admission['work_units'] <= POLICY['max_stage_work_units']
                    and admission['explicit_array_bytes'] <= POLICY['max_array_bytes'], 'Recorded admission metadata')
            routes[route] += 1; work += admission['work_units']
        require(sum(s['rows']*s['columns'] for s in meta['stages']) == 42467328
                and sum(s['nbytes'] for s in meta['stages']) == c['artifacts']['candidate-model.bin']['bytes'] == 21233664
                and routes == {'streamed':18,'token':6} and work == 321015398400, 'Complete candidate metadata/work extent')
        require(first == c['first_stage_invariant'] and first['passed'] is True and first['actual_packed_bytes_equal'] is True
                and first['stage_id'] == meta['stages'][0]['stage_id']
                and first['packed_sha256'] == meta['stages'][0]['sha256'] == prior_meta['stages'][0]['sha256'] == FIRST_SHA
                and first['model_hashes'] == dict(candidate=FIRST_SHA,fixed_feature=FIRST_SHA,sequential=FIRST_SHA), 'First-stage hash commitments')
        files = sorted(out.glob('progress-*.json'))
        require([x.name for x in files] == [f'progress-{i:04d}.json' for i in range(69)], 'Progress file census')
        progress = check_progress([read(x) for x in files],c,diagnostics,first)
        require(c['candidate_construction_elapsed_ns'] >= diagnostics['service_elapsed_ns'], 'Constructor timing containment')
        return dict(candidate_target_sha256=target_hash, candidate_model_sha256=c['artifacts']['candidate-model.bin']['sha256'],
                    stage_code_count_commitment=42467328, packed_model_bytes_commitment=21233664,
                    first_stage_hash_commitment=FIRST_SHA, first_stage_invariant_reported_passed=first['passed'],
                    recorded_teacher_stage_record_advances=diagnostics['neural_stage_record_pairs'],
                    routes=routes, recorded_work_units=work, progress=progress)

    def terminal(self, worker):
        out = self.root/CAMPAIGN/'quality/outputs'
        c = read(out/'completion.json')
        require(c['schema'] == 'full-precision-anchor-quality-worker-v59' and c['status'] == 'complete'
                and c['valid_diagnostic'] is True and c['program_sha256'] == PROGRAM_SHA
                and c['slurm_job_id'] == worker['plan']['slurm_job_id'] and c['original_normalization'] == 1664
                and c['retained_calibration_tokens'] == 768 and c['code_count'] == 42467328
                and c['candidate_count'] == 1 and c['repair_service'] is False and c['confirmation'] is False
                and c['certified_inference'] is False and c['candidate_resource_policy'] == POLICY, 'Worker completion scope/extent')
        require(c['fixed_model_sha256'] == self.p['inputs']['v54_model']['sha256']
                and c['sequential_model_sha256'] == self.p['inputs']['v55_sequential_model']['sha256']
                and c['shared_evaluator_sha256'] == self.p['sources']['scripts/run_quality_v30.py'], 'Control model/evaluator binding')
        require(set(c['artifacts']) == ARTIFACTS, 'Declared candidate artifact inventory')
        for name, entry in c['artifacts'].items():
            require(entry['file'] == name, 'Candidate artifact name')
            self.bound(DIRECTORY+'/quality/outputs/'+name, entry, required=name != 'candidate-model.bin')
        observed_parity = parity(c['quality'], self.previous['quality'])
        require(observed_parity['passed'] and observed_parity == c['historical_parity'] == read(out/'historical-parity.json'), 'All 32 controls must reproduce')
        summary = summarize(c['quality'])
        for key, value in summary.items():
            close_values(c['summary'][key],value,'Completion summary/'+key)
        require(c['development_guards_pass'] == summary['development_guards_pass'], 'Quality guard flag')
        require(c['excluded_from_future_confirmation_ids'] == self.input_json('historical_exclusions')['excluded_from_future_confirmation_ids'], 'Exclusions changed')
        candidate = self.candidate_metadata(c)
        result = dict(charged_cpu_seconds=worker['charged_cpu_seconds'],observed_cpu_ns=worker['observed_cpu_ns'],
            worker_seal_verified=True, historical_control_parity=observed_parity, quality=summary, candidate=candidate)
        result.update(completion_receipt=file_info(out/'completion.json'),
            constructor_elapsed_ns=c['candidate_construction_elapsed_ns'], worker_elapsed_ns=c['worker_elapsed_ns'],
            controller_transaction_elapsed_ns=worker['transaction']['elapsed_ns'], checked_losses=40,
            actual_quality_guard_passed=summary['development_guards_pass'])
        audit_path = self.root/CAMPAIGN/'artifact-audit.json'
        if not audit_path.exists():
            return result, False
        a = read(audit_path)
        require(a['schema'] == 'full-precision-anchor-quality-artifact-audit-v59' and a['status'] == 'verified'
                and a['campaign'] == DIRECTORY and a['program_sha256'] == PROGRAM_SHA and a['source_sha256'] == self.p['sources']
                and a['runtime'] == self.p['runtime'] and a['actual_model_codes_reconstructed'] == 42467328 and a['complete_stages'] == 24
                and a['checked_losses'] == 40 and a['sealed_cpu_receipt_verified'] is True
                and a['slurm_job_id'] == self.jobs['audit'], 'Cluster terminal audit binding')
        expected_inputs = self.audit_inputs(worker,c)
        require_input_inventory(a['inputs'], expected_inputs)
        for remote, entry in expected_inputs.items():
            self.bound(remote,entry)
        for key, value in summary.items():
            close_values(a['summary'][key],value,'Audit summary/'+key)
        require(a['development_guards_pass'] == summary['development_guards_pass'] and a['historical_control_parity'] == observed_parity
                and a['first_stage_invariant'] == c['first_stage_invariant'] and a['progress'] == candidate['progress']
                and a['actual_candidate_model_sha256'] == candidate['candidate_model_sha256']
                and a['candidate_target_sha256'] == candidate['candidate_target_sha256'], 'Audit result commitments')
        require(a['construction']['complete_stages'] == 24 and a['construction']['neural_stage_record_pairs'] == 144
                and a['construction']['total_reserved_work_units'] == candidate['recorded_work_units']
                and a['construction']['calibrated_outputs_never_installed'] is True
                and a['construction']['complete_admissions_rederived'] is True, 'Cluster construction audit metadata')
        ledger_info = file_info(self.root/CAMPAIGN/'budget/ledger.json')
        snapshot = dict(schema='phase-cpu-read-snapshot-v1', path=DIRECTORY+'/budget/ledger.json',
            binding=self.ledger['binding'], **worker['transaction']['budget'], status='verified',
            ledger_sha256=ledger_info['sha256'], ledger_bytes=ledger_info['bytes'], read_only=True,
            scope='complete trusted protocol ledger at read time; not project/global/hostile completeness',
            reserved_unknown_attempts=0, reservation_overrun_attempts=[])
        require(canonical_json(a['budget']) == canonical_json(snapshot), 'Audited settled ledger')
        result['cluster_audit_receipt'] = file_info(audit_path)
        result['cluster_audit_inputs_verified'] = len(expected_inputs)
        result['cluster_audit_analysis_cpu_ns'] = a['analysis_cpu_ns']
        return result, True

    def run(self):
        manifest = self.collection(); gates = self.registration(); worker = self.worker()
        numerical, audited = (self.terminal(worker) if worker is not None and not self.partial_registration_capture else ({},False))
        return dict(schema='second-v59-portable-metadata-check',
            validation_status='passed_metadata_only' if audited else 'pending_terminal',
            archive=str(self.root), collection_manifest=file_info(self.root/'collection-manifest.json'),
            copied_files_verified=len(manifest['files']), available_bound_inputs_verified=len(self.verified),
            registration=gates, result=numerical, inputs_not_revalidated=self.missing,
            launch_jobs=self.jobs,
            partial_registration_capture=self.partial_registration_capture, worker_plan_verified=self.plan_verified,
            worker_ledger_metadata_available=self.ledger is not None,
            scheduler_accounting_copied=bool(manifest.get('scheduler_steps') or manifest.get('scheduler')),
            missing_binary_count=sum(v['kind']=='binary' for v in self.missing.values()),
            missing_metadata_count=sum(v['kind']=='metadata' for v in self.missing.values()),
            metadata_locations=self.locations, candidate_binary_locally_interpreted=False,
            cluster_terminal_audit_present=audited, inference_or_calibration_executed=False,
            scope_limitations=['Copied metadata, source commitments, sealed CPU accounting and descriptive loss arithmetic only.',
                'Missing binaries are NOT revalidated; byte equality, feature arithmetic and calibrated grids rely on the frozen cluster audit.',
                'Admission metadata and structural bounds are checked; dispatcher reports are not regenerated locally.',
                'Recorded runtime commitments do not establish local numerical runtime equivalence.',
                'Reporting-only floating comparison uses 1e-12 relative/absolute tolerance; all quality/parity gate booleans use the frozen exact thresholds.',
                'A verified audit and passing metadata check can accompany a failed quality guard.',
                'Exposed development candidate only; no repair-service, held-out, speedup or submission-readiness claim.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('extracted_directory',type=Path)
    parser.add_argument('--prior-v58',type=Path,default=DEFAULT_PRIOR)
    args=parser.parse_args(); checker=Check(args.extracted_directory,args.prior_v58)
    try:
        result=checker.run()
    except (ValueError,KeyError,TypeError,OSError,tarfile.TarError) as error:
        print(json.dumps(dict(schema='second-v59-portable-metadata-check',validation_status='failed',
            error_type=type(error).__name__,error=str(error)),sort_keys=True))
        return 1
    finally:
        checker.close()
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
