"""Portable read-only check of the copied V54--V56 terminal metadata.

Usage: python3 -B validation/check_v58_terminal_metadata.py EXTRACTED_DIRECTORY
Only standard-library modules and the unchanged run-store verifier are used.
No numerical engine, model, ledger writer, network operation or inference runs.
The printed JSON explicitly distinguishes remote binary-audit assertions from
the copied metadata and repository source bytes actually rehashed here.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.run_store import canonical_json, digest, read_completed, strict_json

REMOTE = '/nfs_home/users/poonam/second-20261010'
FOLDERS = {54: 'full-model48-v54-20261011-a',
           55: 'exposed-quality-v55-20261011-a',
           56: 'gpu-parity-v56-20261011-a'}
SCHEMAS = {54: 'adaptive-compressed48-complete-development-v54',
           55: 'exposed-quality-diagnostic-v55', 56: 'cuda-likelihood-parity-v56'}
AUDITS = {54: 'complete-service-artifact-audit-v54',
          55: 'exposed-quality-artifact-audit-v55', 56: 'cuda-likelihood-artifact-audit-v56'}
V54_SHA = '03a6181b0d32ad023706145fbde28f202ed5d137e95a4b16ecbd19686858465b'
PROGRAM_SHA = {54: V54_SHA,
    55: '4de04c4a0bd5db485c7ccd7511a4d5094195afdce15c115a909346879b84125f',
    56: '8c3f46537f6b1cdc51c2b43dd3c1ebf2a7afff5114d6b185bcb160c6eaf98f6d'}
# Exact historical metadata locations only. Each alternate copy must still
# match the bound remote file's hash and byte count; no binary fallback occurs.
HISTORICAL_COPIES = {}
for _remote_folder, _repo_folder, _files in (
    ('c4-data-v45-20261010-a', 'csis_c4_data_v45',
     ('program.json', 'completion.json', 'budget/ledger.json', 'outputs/exclusions.json', 'outputs/records.json', 'outputs/selection.json')),
    ('cpu-parameters-v47-20261010-a', 'csis_cpu_parameter_export_v47',
     ('program.json', 'registration.json', 'completion.json', 'budget/ledger.json', 'outputs/manifest.json')),
    ('exposed-quality-v44-20261010-b', 'csis_exposed_quality_v44',
     ('budget/ledger.json', 'quality/outputs/completion.json')),
    ('full-model-v43-20261010-b', 'csis_full_model_v43', ('artifact-audit.json', 'postrun-audit.json'))):
    for _name in _files:
        HISTORICAL_COPIES['local_runs/'+_remote_folder+'/'+_name] = 'campaigns/'+_repo_folder+'/'+_name
HISTORICAL_COPIES.update({
    'local_runs/v54-software-a.json': 'campaigns/csis_full_model48_v54_launch/software-checks.json',
    'local_runs/v55-software-a.json': 'campaigns/csis_quality_v55_launch/checks.json',
    'local_runs/v56-software-a.json': 'campaigns/csis_gpu_v56_launch/checks.json'})
LABELS = ('full_precision', 'nearest_rounding', 'fixed_feature', 'sequential')
IDS = tuple('wikitext2:validation:article-row-'+str(i)
            for i in (2525, 2237, 132, 2115, 2352, 1040, 3636, 1299))
REPRESENTATIONS = dict(cached='lossless', compressed='compressed48',
                       hybrid='hybrid_gram', cold='lossless')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    require(path.is_file() and not path.is_symlink(), 'Missing regular JSON: '+str(path))
    return strict_json(path.read_bytes())


def info(path):
    require(path.is_file() and not path.is_symlink(), 'Missing regular input: '+str(path))
    h = hashlib.sha256()
    count = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
            count += len(block)
    return dict(bytes=count, sha256=h.hexdigest())


def safe_path(root, name):
    p = PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts, 'Unsafe relative input path')
    path = root.joinpath(*p.parts)
    require(not any(v.is_symlink() for v in (path, *path.parents)), 'Symlink input refused')
    return path


def numeric_equal(actual, expected, label):
    """Allow libm reporting differences only, never relax boolean gate decisions."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and actual.keys() == expected.keys(), label+' keys')
        for k in expected:
            numeric_equal(actual[k], expected[k], label+'/'+k)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), label+' extent')
        for i, (a, b) in enumerate(zip(actual, expected)):
            numeric_equal(a, b, label+'/'+str(i))
    elif isinstance(expected, float):
        require(isinstance(actual, (int, float)) and not isinstance(actual, bool)
                and math.isfinite(actual) and math.isfinite(expected)
                and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), label+' number')
    else:
        require(actual == expected, label+' value')


def exp(value):
    try:
        return math.exp(value)
    except OverflowError:
        return None


def quality_tables(quality):
    require(set(quality) == set(LABELS), 'Four quality models required')
    tables = {}
    for label in LABELS:
        rows = quality[label]
        require(len(rows) == 8 and {r['id'] for r in rows} == set(IDS), 'Quality article extent')
        require(all(r['predictions'] == 127 and math.isfinite(r['nll_sum']) for r in rows),
                'Quality finite loss/count')
        tables[label] = {r['id']: r for r in rows}
    return tables


def quality_summary(quality):
    # Same frozen formulas as research_v55/diagnostic.py, without its numerical imports.
    tables = quality_tables(quality)
    totals, comparisons = {}, {}
    for label in LABELS:
        loss = math.fsum(tables[label][rid]['nll_sum'] for rid in IDS)
        totals[label] = dict(nll_sum=loss, predictions=1016, mean_nll=loss/1016, perplexity=exp(loss/1016))
    for reference in ('sequential', 'nearest_rounding', 'full_precision'):
        deltas = [tables['fixed_feature'][rid]['nll_sum']-tables[reference][rid]['nll_sum'] for rid in IDS]
        logs = {rid: d/127 for rid, d in zip(IDS, deltas)}
        pooled, maximum = math.fsum(deltas)/1016, max(logs.values())
        comparisons[reference] = dict(pooled_perplexity_ratio=exp(pooled), pooled_log_perplexity_ratio=pooled,
            article_log_perplexity_ratios=logs, article_perplexity_ratios={k: exp(v) for k, v in logs.items()},
            max_article_ratio=exp(maximum), max_article_log_ratio=maximum,
            articles_fixed_lower=sum(v < 0 for v in logs.values()),
            articles_fixed_equal=sum(v == 0 for v in logs.values()), articles_fixed_higher=sum(v > 0 for v in logs.values()))
    primary = comparisons['sequential']
    guards = dict(pooled_pass=primary['pooled_log_perplexity_ratio'] <= math.log(1.05),
                  every_article_pass=primary['max_article_log_ratio'] <= math.log(1.20))
    return dict(totals=totals, fixed_feature_comparisons=comparisons, guards=guards,
                thresholds=dict(max_pooled_fixed_over_sequential=1.05, max_article_fixed_over_sequential=1.20),
                development_guards_pass=all(guards.values()))


class Check:
    def __init__(self, root):
        self.root = root.resolve()
        self.missing, self.verified = {}, {}
        self.historical_copies = {}
        self.programs, self.audits, self.ledgers, self.workers = {}, {}, {}, {}

    def mapped(self, remote):
        require(remote.startswith(REMOTE+'/'), 'Input outside registered checkout: '+remote)
        name = remote[len(REMOTE)+1:]
        if name.startswith('local_runs/'):
            extracted = safe_path(self.root, name[len('local_runs/'):])
            if extracted.exists() or name not in HISTORICAL_COPIES:
                return extracted
            return safe_path(REPO, HISTORICAL_COPIES[name])
        return safe_path(REPO, name)

    def bound(self, remote, expected, *, mandatory=False):
        expected = {k: expected[k] for k in ('bytes', 'sha256')}
        path = self.mapped(remote)
        if not path.exists():
            require(not mandatory, 'Required metadata not copied: '+remote)
            if remote in self.missing:
                require(self.missing[remote]['expected'] == expected, 'Conflicting missing-input hashes')
            self.missing[remote] = dict(expected=expected, status='NOT revalidated',
                kind='binary' if path.suffix in ('.bin', '.npz', '.safetensors') else 'metadata')
            return None
        actual = info(path)
        require(actual == expected, 'Bound input hash mismatch: '+remote)
        self.verified[remote] = actual
        if path.is_relative_to(REPO) and remote[len(REMOTE)+1:].startswith('local_runs/'):
            self.historical_copies[remote] = dict(repository_path=str(path.relative_to(REPO)), **actual)
        return path

    def campaign(self, version):
        return self.root/FOLDERS[version]

    def collection(self):
        manifest = read(self.root/'collection-manifest.json')
        require(manifest['schema'] == 'second-terminal-chain-metadata-v1', 'Collection schema')
        for name, expected in manifest['files'].items():
            require(info(safe_path(self.root, name)) == expected, 'Copied file hash mismatch: '+name)
        actual = {str(p.relative_to(self.root)) for p in self.root.rglob('*') if p.is_file()}
        require(actual == set(manifest['files']) | {'collection-manifest.json'}, 'Unlisted or missing copied file')
        return manifest

    def program(self, version):
        root = self.campaign(version)
        p = read(root/'program.json')
        ph = info(root/'program.json')['sha256']
        require(ph == PROGRAM_SHA[version], 'Unexpected registered V'+str(version)+' program')
        require(digest(canonical_json(p)) == ph, 'Noncanonical program')
        require(p['schema'] == SCHEMAS[version] and p['directory'] == REMOTE+'/local_runs/'+FOLDERS[version], 'Program identity')
        require(read(root/'registration.json') == dict(program_sha256=ph), 'Registration binding')
        require(p['automatic_retry'] is False and p['confirmation'] is False, 'Program scope')
        require(len(p['sources']) == {54: 386, 55: 399, 56: 409}[version], 'Frozen source inventory extent')
        for name, expected in p['sources'].items():
            require(info(safe_path(REPO, name))['sha256'] == expected, 'Frozen source changed: '+name)
        for entry in p['inputs'].values():
            self.bound(entry['path'], entry)
        audit = read(root/'artifact-audit.json')
        require(audit['schema'] == AUDITS[version] and audit['status'] == 'verified'
                and audit['program_sha256'] == ph and audit['campaign'] == p['directory'], 'Audit binding')
        for remote, expected in audit.get('inputs', {}).items():
            self.bound(remote, expected)
        if 'source_sha256' in audit:
            require(audit['source_sha256'] == p['sources'], 'Audit source commitment')
        ledger = read(root/'budget/ledger.json')
        phase = 'feasibility' if version == 54 else 'development'
        require(ledger['binding']['identity']['protocol_sha256'] == ph
                and ledger['binding']['phase_cpu_seconds'] == {phase: p['phase_cpu_seconds']}, 'Ledger binding')
        for name, expected in ledger['binding']['identity']['source_sha256'].items():
            require(info(safe_path(REPO, name))['sha256'] == expected, 'Ledger source changed')
        require(len(ledger['attempts']) == (6 if version == 54 else 1)
                and all(r['state'] == 'settled' and r['phase'] == phase for r in ledger['attempts'].values()), 'Unsettled/extra attempt')
        charged = sum(r['charged_cpu_seconds'] for r in ledger['attempts'].values())
        require(charged <= p['phase_cpu_seconds'], 'Phase over cap')
        snapshot = audit['budget']
        require(snapshot['status'] == 'verified' and snapshot['attempts'] == ledger['attempts']
                and snapshot['binding'] == ledger['binding'] and snapshot['binding_sha256'] == digest(canonical_json(ledger['binding']))
                and snapshot['ledger_sha256'] == info(root/'budget/ledger.json')['sha256']
                and snapshot['ledger_bytes'] == info(root/'budget/ledger.json')['bytes']
                and snapshot['charged_cpu_seconds'] == {phase: charged}
                and not snapshot['reserved_unknown_attempts'] and not any(snapshot['over_cap'].values()), 'Audited ledger differs')
        self.programs[version], self.audits[version], self.ledgers[version] = p, audit, ledger
        trials = tuple(p['trials']) if version == 54 else ('quality' if version == 55 else 'parity',)
        worker_ids = set()
        for trial in trials:
            worker_ids.add(self.worker(version, trial, ph))
        require(worker_ids == set(ledger['attempts']), 'Worker/debit census differs')

    def worker(self, version, trial, ph):
        p, ledger = self.programs[version], self.ledgers[version]
        root = self.campaign(version)/trial
        remote = p['directory']+'/'+trial
        identity, plan, tx = (read(root/name) for name in ('worker/identity.json', 'plan.json', 'transaction.json'))
        executable = REMOTE+'/.venv-container/bin/python' if version != 56 else '/nfs_home/software/envs/pytorch-12.8/bin/python'
        command = [executable, '-B', '-m', 'research_v'+str(version)+'.worker', remote+'/plan.json']
        wid = dict(campaign_sha256=ph, trial=trial) if version == 54 else dict(program_sha256=ph)
        phase = 'feasibility' if version == 54 else 'development'
        require(identity['command'] == command and identity['identity'] == wid and identity['cwd'] == REMOTE, 'Literal worker command/identity')
        require(identity['phase_budget'] == dict(binding_sha256=digest(canonical_json(ledger['binding'])),
                directory=p['directory']+'/budget', phase=phase), 'Worker budget phase')
        if version == 54:
            limits = dict(p['trials'][trial], address_space_bytes=p['process_address_space_bytes'])
        elif version == 55:
            limits = dict(cpu_seconds=p['worker_cpu_seconds'], wall_seconds=p['worker_wall_seconds'], address_space_bytes=p['process_address_space_bytes'])
        else:
            limits = {k: p[k] for k in ('cpu_seconds', 'wall_seconds', 'address_space_bytes')}
        limits.update(file_size_bytes=p['file_size_bytes'], threads=1, termination_grace_seconds=1)
        require(all(identity['limits'][k] == v for k, v in limits.items()) and len(identity['limits']['affinity_cpus']) == 1, 'Worker limits')
        sealed = read_completed(root/'worker', identity)
        require(sealed is not None and sealed == read(root/'worker'/sealed['attempt']/'status.json'), 'Terminal seal/status')
        require(sealed['outcome'] == tx['worker_outcome'] and sealed['outcome']['status'] == 'complete'
                and sealed['outcome']['returncode'] == 0 and sealed['limits'] == identity['limits']
                and sealed['worker_identity'] == wid and sealed['no_shell'] is True, 'Worker outcome or sealed limits')
        request = read(root/'worker'/sealed['attempt']/'request.json')
        require(request['command'] == command and request['limits'] == identity['limits'] and request['cwd'] == REMOTE, 'Actual request differs')
        ack = read(root/'worker'/sealed['attempt']/'limits-applied.json')
        require(ack == sealed['limits_applied'] and ack['request_sha256'] == digest(canonical_json(request))
                and ack['cpu_seconds'] == [limits['cpu_seconds'], limits['cpu_seconds']+1]
                and ack['address_space'] == [limits['address_space_bytes']]*2
                and ack['file_size'] == [limits['file_size_bytes']]*2
                and ack['affinity_cpus'] == identity['limits']['affinity_cpus']
                and all(v == '1' for v in ack['thread_environment'].values()), 'Applied limits')
        debit = sealed['budget_debit']
        require(ledger['attempts'][sealed['budget_attempt_id']] == debit
                and debit['observed_cpu_ns'] == sealed['resource_usage']['total_cpu_ns']
                and debit['observed_cpu_ns'] == sealed['resource_usage']['user_cpu_ns']+sealed['resource_usage']['system_cpu_ns']
                and debit['charged_cpu_seconds'] == (debit['observed_cpu_ns']+999999999)//1000000000
                and debit['charged_cpu_seconds'] <= debit['reserved_cpu_seconds']
                and sealed['budget_reservation_overrun'] is False, 'Settled CPU debit')
        require(tx['budget']['binding_sha256'] == identity['phase_budget']['binding_sha256']
                and tx['budget']['attempts'].get(sealed['budget_attempt_id']) == debit
                and all(ledger['attempts'].get(k) == v for k, v in tx['budget']['attempts'].items())
                and tx['budget']['charged_cpu_seconds'] == {phase: sum(v['charged_cpu_seconds'] for v in tx['budget']['attempts'].values())}
                and tx['budget']['phase_cpu_seconds'] == {phase: p['phase_cpu_seconds']}
                and not any(tx['budget']['over_cap'].values()), 'Transaction ledger snapshot')
        expected_plan = dict(program=p['directory']+'/program.json', program_sha256=ph,
                             output=remote+'/outputs', slurm_job_id=tx['slurm_job_id'])
        if version == 54:
            expected_plan['trial'] = trial
        require(plan == expected_plan, 'Worker plan binding')
        c = read(root/'outputs/completion.json')
        expected_schema = {54: 'complete-service-worker-v54', 55: 'exposed-quality-worker-v55', 56: 'cuda-likelihood-parity-result-v56'}[version]
        require(c['schema'] == expected_schema and c['status'] == 'complete' and c['program_sha256'] == ph
                and c['slurm_job_id'] == tx['slurm_job_id'] and c['confirmation'] is False, 'Completion binding')
        if version == 54:
            require(c['source_sha256'] == p['sources'] and c['trial'] == trial and c['complete_model'] is True, 'Complete V54 model metadata')
        else:
            require(c['valid_diagnostic'] is True, 'Invalid diagnostic')
        for name, entry in c.get('artifacts', {}).items():
            require(entry['file'] == name, 'Artifact filename differs')
            self.bound(remote+'/outputs/'+name, entry)
        if version == 54:
            names = {'execution-provenance.json', 'admission.json'}
            if trial == 'prepare':
                names.add('original-model.bin')
                for rep in ('lossless', 'compressed48', 'hybrid_gram'):
                    names.update((rep+'-original.bin', rep+'-trust.json'))
            elif trial == 'oracle':
                for step in (1, 2):
                    names.add(f'step-{step}-model.bin')
                    for rep in ('lossless', 'compressed48', 'hybrid_gram'):
                        names.update((f'step-{step}-{rep}.bin', f'step-{step}-{rep}-trust.json'))
            else:
                names.update(f'step-{step}-{suffix}' for step in (1, 2)
                             for suffix in ('model.bin', 'state.bin', 'trust.json'))
            require(set(c['artifacts']) == names, 'Full-model declared artifact census')
        elif version == 55:
            require(set(c['artifacts']) == {'sequential-target.json', 'fixed-target.json', 'execution-provenance.json',
                'historical-parity.json', 'sequential-model.bin', 'sequential-model-metadata.json', 'sequential-diagnostics.json'},
                'CPU diagnostic declared artifact census')
        self.workers[version, trial] = dict(completion=c, transaction=tx, sealed=sealed)
        return sealed['budget_attempt_id']

    def full_model(self):
        p, a = self.programs[54], self.audits[54]
        require(info(self.campaign(54)/'program.json')['sha256'] == V54_SHA, 'Unexpected V54 program')
        b = read(self.campaign(54)/'postrun-audit.json')
        require(b['schema'] == 'complete-service-additive-artifact-audit-v54' and b['status'] == 'verified'
                and b['program_sha256'] == V54_SHA and b['campaign'] == p['directory']
                and b['frozen_audit_sha256'] == info(self.campaign(54)/'artifact-audit.json')['sha256']
                and b['ledger_snapshot'] == a['budget'], 'Second V54 audit binding')
        for remote, entry in b['inputs'].items():
            self.bound(remote, entry)
        require(a['all_declared_artifacts_rehashed'] is True and a['complete_model'] is True
                and a['original_tokens'] == 1664 and a['retained_tokens'] == [1536, 768]
                and p['normalization'] == 1664 and p['retained_counts'] == [12, 6], 'V54 registered extent')
        expected = {(t, s) for t in REPRESENTATIONS for s in (1, 2)}
        require(len(a['comparisons']) == len(b['evidence']['comparisons']) == 8, 'Duplicate comparison row')
        tables = [{(r['trial'], r['step']): r for r in table} for table in (a['comparisons'], b['evidence']['comparisons'])]
        require(all(len(table) == 8 and set(table) == expected for table in tables), 'Eight comparisons required')
        for key in expected:
            row, other = (t[key] for t in tables)
            require(all(row[k] == other[k] for k in ('state_sha256', 'complete_model_sha256', 'state_bytes', 'code_count',
                'stages', 'retained_records', 'retained_tokens', 'deleted_count', 'representation')), 'Audit comparison mismatch')
            for record in (row, other):
                require(record['actual_bytes_equal'] is True and record['actual_model_bytes_equal'] is True
                        and record['exact_retained_membership_verified'] is True and record['stages'] == 24
                        and record['code_count'] == 42467328 and record['retained_records'] == (12 if key[1] == 1 else 6)
                        and record['retained_tokens'] == (1536 if key[1] == 1 else 768), 'Comparison extent/flags')
            require(all(other[k] is True for k in ('model_export_matches_state_codes',
                'registered_record_binding_verified', 'cross_representation_target_and_model_verified')), 'Supplemental artifact flags')
            c = self.workers[54, key[0]]['completion']; step = key[1]
            require(c['artifacts'][f'step-{step}-model.bin']['sha256'] == row['complete_model_sha256']
                    and c['artifacts'][f'step-{step}-state.bin']['sha256'] == row['state_sha256'], 'Comparison/artifact binding')
        prep = self.workers[54, 'prepare']['completion']; timing = {}
        require(a['preparation'] == prep['preparation'], 'Preparation metadata')
        for trial, representation in REPRESENTATIONS.items():
            c, tx = (self.workers[54, trial][k] for k in ('completion', 'transaction'))
            pp = prep['preparation']
            common = prep['context_elapsed_ns']+pp['common_source_ns']+pp['common_original_model_ns']+pp['common_disposal_ns']
            own = pp['representations'][representation]['representation_elapsed_ns']
            timing[trial] = dict(request_elapsed_ns=[s['request_elapsed_ns'] for s in c['steps']],
                live_state_bytes=[s['state_bytes']+s['trust_bytes'] for s in c['steps']],
                complete_deployment_bytes=[s['complete_deployment_bytes'] for s in c['steps']],
                attributed_preparation_ns=common+own, attributed_two_deletion_lifetime_ns=common+own+tx['elapsed_ns'],
                transaction_elapsed_ns=tx['elapsed_ns'], worker_elapsed_ns=c['worker_elapsed_ns'],
                worker_outside_request_ns=c['worker_elapsed_ns']-sum(s['request_elapsed_ns'] for s in c['steps']))
            for k, v in timing[trial].items():
                require(a['timings'][trial][k] == v, 'Timing/storage formula differs: '+trial+'/'+k)
        ratios = {}
        for control in ('cached', 'hybrid', 'cold'):
            x, y = timing['compressed'], timing[control]
            ratios[control] = dict(compressed_over_control_request_time=[u/v for u, v in zip(x['request_elapsed_ns'], y['request_elapsed_ns'])],
                compressed_live_state_saving=[1-u/v for u, v in zip(x['live_state_bytes'], y['live_state_bytes'])],
                compressed_deployment_saving=[1-u/v for u, v in zip(x['complete_deployment_bytes'], y['complete_deployment_bytes'])],
                compressed_over_control_observed_lifetime=x['attributed_two_deletion_lifetime_ns']/y['attributed_two_deletion_lifetime_ns'])
        require(ratios == a['ratios'], 'Derived cost ratios differ')
        require(a['prior_failed_cpu_seconds'] == p['prior_failed_charge'] and
            a['total_continuation_cpu_seconds'] == p['prior_failed_charge']+a['budget']['charged_cpu_seconds']['feasibility'], 'Prior failure accounting')
        return dict(comparisons=8, ratios=ratios, timings=timing,
            current_worker_cpu_seconds=a['budget']['charged_cpu_seconds']['feasibility'],
            prior_failed_cpu_seconds=p['prior_failed_charge'], total_continuation_cpu_seconds=a['total_continuation_cpu_seconds'])

    def diagnostics(self):
        p, a, c = self.programs[55], self.audits[55], self.workers[55, 'quality']['completion']
        require(p['inputs']['v54_program']['sha256'] == V54_SHA and p['retained_records'] == self.programs[54]['records'][-6:]
                and p['normalization'] == c['original_normalization'] == 1664 and c['retained_calibration_tokens'] == 768
                and a['actual_model_codes_reconstructed'] == c['code_count'] == 42467328 and a['complete_stages'] == 24
                and a['sealed_cpu_receipt_verified'] is True, 'CPU diagnostic extent')
        selected = next(r for r in self.audits[54]['comparisons'] if (r['trial'], r['step']) == ('compressed', 2))
        require(selected['complete_model_sha256'] == p['inputs']['fixed_model']['sha256'] == c['fixed_model_sha256']
                and selected['state_sha256'] == p['inputs']['fixed_state']['sha256'], 'Quality uses wrong V54 successor')
        require(p['inputs']['first_audit']['sha256'] == info(self.campaign(54)/'artifact-audit.json')['sha256']
                and p['inputs']['second_audit']['sha256'] == info(self.campaign(54)/'postrun-audit.json')['sha256'], 'V55 prerequisite audits')
        history = read(self.mapped(p['inputs']['historical_losses']['path']))
        checks = []
        for label in ('full_precision', 'nearest_rounding'):
            old = {r['id']: r for r in history['quality'][label]}
            for row in c['quality'][label]:
                delta = abs(row['nll_sum']-old[row['id']]['nll_sum'])/127
                checks.append(dict(model=label, record_id=row['id'], absolute_mean_nll_deviation=delta, threshold=1e-8, passed=delta <= 1e-8))
        require(len(checks) == 16 and all(r['passed'] for r in checks)
                and c['historical_parity']['checks'] == a['historical_control_parity']['checks'] == checks
                and c['historical_parity']['passed'] is True, 'Historical control parity')
        summary = quality_summary(c['quality'])
        require(p['guards'] == summary['thresholds'] and p['parity_absolute_mean_nll_tolerance'] == 1e-8
                and p['ridge'] == [1, 100] and p['bits'] == 4 and p['significant_bits'] == 24, 'Frozen CPU design')
        require(c['historical_parity'] == a['historical_control_parity'] ==
                read(self.campaign(55)/'quality/outputs/historical-parity.json'), 'Historical parity artifact binding')
        for k, value in summary.items():
            numeric_equal(c['summary'][k], value, 'CPU completion summary/'+k)
            numeric_equal(a['summary'][k], value, 'CPU audit summary/'+k)
        require(summary['development_guards_pass'] == c['development_guards_pass'] == a['development_guards_pass'], 'CPU guard flags')
        exclusions = read(self.mapped(p['inputs']['all_exclusions']['path']))['excluded_from_future_confirmation_ids']
        require(len(set(exclusions)) == 60 and set(IDS) <= set(exclusions)
                and c['excluded_from_future_confirmation_ids'] == exclusions, 'Exclusions changed')
        gp, ga, gc = self.programs[56], self.audits[56], self.workers[56, 'parity']['completion']
        require(p['sources'] == read(REPO/'research_v56/SOURCE_BASE.json'), 'GPU frozen CPU source base')
        for key, suffix in (('cpu_program', 'program.json'), ('cpu_registration', 'registration.json'),
                            ('cpu_audit', 'artifact-audit.json'), ('cpu_completion', 'quality/outputs/completion.json'), ('cpu_ledger', 'budget/ledger.json')):
            require(gp['inputs'][key]['sha256'] == info(self.campaign(55)/suffix)['sha256'], 'GPU/CPU chain binding')
        require(gp['records'] == p['records'] and tuple(r['id'] for r in p['records']) == IDS
                and all(len(r['tokens']) == 128 for r in p['records']) and gp['threshold'] == 1e-8, 'GPU article/threshold binding')
        require(gc['dtype'] == 'float64' and gc['tf32'] is False and gc['amp'] is False
                and gc['deterministic_algorithms'] is True and gc['copied_arrays_with_bitwise_roundtrip'] == 150
                and gc['peak_cuda_reserved_bytes'] <= gp['gpu_allocator_bytes'] == 8*2**30
                and gc['first_actual_batch_parity_passed'] is True and gc['certified_inference'] is False
                and gc['exact_calibration_equivalence'] is False, 'GPU completion execution contract')
        require(gc['cpu_development_guards_pass'] == ga['cpu_development_guards_pass'] == summary['development_guards_pass'], 'GPU CPU-guard report')
        quality_tables(gc['quality']); gpu_checks = []
        for label in sorted(LABELS):
            old = {r['id']: r for r in c['quality'][label]}
            for row in gc['quality'][label]:
                delta = abs(row['nll_sum']-old[row['id']]['nll_sum'])/127
                gpu_checks.append(dict(model=label, id=row['id'], absolute_mean_nll_deviation=delta, threshold=1e-8, passed=delta <= 1e-8))
        parity = dict(passed=all(r['passed'] for r in gpu_checks), checks=gpu_checks,
                      maximum_absolute_mean_nll_deviation=max(r['absolute_mean_nll_deviation'] for r in gpu_checks))
        require(len(gpu_checks) == 32 and parity == gc['parity'] == ga['parity']
                and parity['passed'] == gc['parity_passed'] == ga['parity_passed'], 'GPU recomputed parity')
        return dict(cpu_quality=summary, gpu_parity=dict(passed=parity['passed'], comparisons=32,
            maximum_absolute_mean_nll_deviation=parity['maximum_absolute_mean_nll_deviation'], threshold=1e-8),
            exclusions=60)

    def run(self):
        manifest = self.collection()
        for version in (54, 55, 56):
            self.program(version)
        full = self.full_model(); diagnostics = self.diagnostics()
        return dict(schema='second-terminal-metadata-check-v58', validation_status='passed_metadata_only',
            archive=str(self.root), collection_manifest=info(self.root/'collection-manifest.json'),
            collection_captured_at_utc=manifest['captured_at_utc'], collection_cluster_commit=manifest['cluster_commit'],
            copied_files_verified=len(manifest['files']), available_bound_inputs_verified=len(self.verified),
            historical_metadata_copies_verified=self.historical_copies,
            sources_verified={str(v): len(p['sources']) for v, p in self.programs.items()},
            worker_seals_verified=len(self.workers), program_sha256={str(v): info(self.campaign(v)/'program.json')['sha256'] for v in FOLDERS},
            v54=full, **diagnostics, inputs_not_revalidated=self.missing,
            missing_binary_count=sum(v['kind'] == 'binary' for v in self.missing.values()),
            missing_metadata_count=sum(v['kind'] == 'metadata' for v in self.missing.values()),
            numerical_inference_or_calibration=False, binary_model_state_revalidation=False,
            summary_reporting_float_comparison_tolerance=dict(relative=1e-12, absolute=1e-12, gate_booleans='exact'),
            scope_limitations=['Copied metadata, portable source hashes, worker seals and derived reporting arithmetic only.',
                'Missing model/state/checkpoint binaries and other uncopied inputs were NOT revalidated locally; existing cluster audits are the evidence for their bytes.',
                'Runtime identities are recorded commitments, not local runtime equivalence or a new remote runtime inspection.',
                'Collection manifest is a trusted transport inventory, not an independent authentication signature.',
                'No inference, feature construction, certification, independent numerical replay, controlled speed comparison or confirmatory quality claim.',
                'Successful metadata validation is independent of whether quality guards or GPU parity passed.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('extracted_directory', type=Path)
    args = parser.parse_args()
    try:
        result = Check(args.extracted_directory).run()
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps(dict(schema='second-terminal-metadata-check-v58', validation_status='failed',
                              error_type=type(error).__name__, error=str(error)), sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
