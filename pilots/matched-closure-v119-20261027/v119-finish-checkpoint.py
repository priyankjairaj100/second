"""Publishable closed-evidence checkpoint; no cluster work or scientific rerun."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess

R=Path('/Users/priyankjairaj/Downloads/ACL/Second')
W=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2')
S=W/'work/second-speed-campaign'
P=R/'pilots/matched-closure-v119-20261027'
assert not P.exists()
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
info=lambda b:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
enc=lambda o:(json.dumps(o,indent=2,sort_keys=True)+'\n').encode()
read=lambda p:json.loads(p.read_bytes())
prior=read(R/'handoff/program_v118.json')
program=read(S/'v112-program.json')
observed=read(S/'v119-chain-observation-20261027T103648Z.json')
terminal=read(S/'v119-closed-collection/terminal-stdout.json')
result=read(S/'v119-closed-collection/reduction.json')
assert terminal['status']=='verified' and terminal['evidence']['actual_model_state_trust_pairs']==16
assert len(terminal['jobs'])==21 and observed['queue']==''
assert observed['numerical_status']==''
source_files={};excluded=[]
for n,e in program['sources'].items():
    file=R/n
    if not file.is_file():excluded.append(n);continue
    assert info(file.read_bytes())==e,n
    source_files[n]=e
assert len(source_files)==1322 and len(excluded)==17
reporting={}
for key in ('reporting_preparation','closed_report_preparation'):
    for n,h in prior[key]['source_hashes'].items():
        assert info((R/n).read_bytes())['sha256']==h,n
        reporting[n]=h
checks=read(R/'validation/v119_manuscript_checks.json')
bundle=read(R/'validation/v119_development_bundle.json')
assert info((W/'outputs/second-research-draft.tex').read_bytes())==checks['manuscript']==bundle['manuscript']
assert info(Path(bundle['path']).read_bytes())==bundle['archive']
assert read(R/'validation/v119_bundle_rejections.json')['rejection_cases']==6
cfg=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'automations/continue-second-research/automation.toml'
assert 'status = "PAUSED"' in cfg.read_text()
scheduler=dict(automation_id='continue-second-research',status='PAUSED',verified_from_configuration=True,
               verified_utc=now,user_requested_stop=True,new_monitor_created=False)
verification=dict(schema='final-sources-and-artifacts-v119',created_utc=now,original_sources_verified=len(source_files),
    original_source_inventory=source_files,excluded_execution_receipts=excluded,reporting_source_hashes=reporting,
    numerical_checkout=observed['numerical_checkout'],numerical_checkout_clean_at_terminal_observation=True,
    terminal=info((S/'v119-closed-collection/terminal-stdout.json').read_bytes()),manuscript=checks['manuscript'],
    bundle=bundle['archive'],scheduler=scheduler,no_new_cluster_job=True)
(R/'validation/v119_final_verification.json').write_bytes(enc(verification))
P.mkdir()
for path in sorted(S.glob('v119*')):
    if path.is_dir():shutil.copytree(path,P/path.name)
    elif path.is_file():shutil.copy2(path,P/path.name)
(P/'README.txt').write_text('''V119 actual matched closure, 27 October 2026

All 21 V112 allocations completed 0:0. Both same-checkpoint fresh oracles, both
actual binary audits and frozen terminal closure passed. The collector executed
once after closure; v119-closed-collection preserves its intents, exact returned
bytes, 38 bound metadata receipts, historical preparation hosts and reduction.
v119-closed-report preserves all 16 requests, exact signed contrasts and costs.
No numerical job was rerun, modified or duplicated. Checkpoint sources are frozen.

Earlier v119-chain-observation files and v119-active-work.json are timestamped
historical progress, not current running-job claims. The final scheduler snapshot
is v119-chain-observation-20261027T103648Z.json, captured at10:36:51UTC with an empty
queue. Terminal closure was captured at10:37:38UTC. No bulk model, corpus, token
or runtime payload was collected. Retained receipts bind the actual cluster audit;
these local copies do not independently re-audit its binary outputs.

See docs/RESEARCH_DECISION_V119.txt for the final bounded tradeoff decision and
docs/ACTIVE_SESSION_V119.md for delivery state. Scheduler remains PAUSED.
''')
files={str(f.relative_to(P)):info(f.read_bytes()) for f in sorted(P.rglob('*')) if f.is_file()}
(P/'MANIFEST.json').write_bytes(enc(files))
for n,e in files.items():assert info((P/n).read_bytes())==e
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
h=dict(schema='second-handoff-v119',updated_utc=now,current_handoff='docs/ACTIVE_SESSION_V119.md',
    prior_handoff='docs/ACTIVE_SESSION_V118.md',publication_baseline=head,github_repository='priyankjairaj100/second',
    branch='codex/second-cluster-v42',draft_pr='https://github.com/priyankjairaj100/second/pull/1',
    numerical_checkout=observed['numerical_checkout'],scheduler='PAUSED',scheduler_observation=scheduler,
    evidence_directory=str(P.relative_to(R)),evidence_manifest=info((P/'MANIFEST.json').read_bytes()),
    experiment=dict(version=112,status='closed_verified',namespace=prior['experiment']['namespace'],
        current_observation=observed,jobs=prior['experiment']['jobs'],all_21_jobs_completed_0_0=True,
        complete_requests=16,fresh_oracles=2,both_binary_audits_passed=True,actual_terminal=verification['terminal'],
        terminal_captured_utc=terminal['captured_utc'],program_sha256=terminal['program_sha256'],
        collector_executions=1,collector_consumed=True,rendered_all_16_requests=True,
        cumulative_screen_numerical_seconds=result['cumulative_screen_numerical_seconds'],
        carried_numerical_seconds=6304,new_numerical_seconds=14222,unchanged_numerical_cap_seconds=82840,
        scheduler_cpu_lower_ns=result['scheduler_cpu_lower_ns'],scheduler_cpu_upper_ns=result['scheduler_cpu_upper_ns'],
        reused_preparation_host_ns=result['reused_preparation_host_ns'],old_unknown_v80_cpu_seconds=12602,
        overlapping_clocks_not_added=True,all_launchers_consumed=True,no_retry_or_duplicate=True),
    current_science=dict(all_prior_V72_V89_findings_preserved=True,new_complete_related_checkpoint_correctness=True,
        actual_complete_model_state_trust_pairs=16,new_complete_speed_comparison=True,
        optimized_compressed_slower_in_all_four_matched_strata=True,live_storage_savings_percent_range=[7.009,7.858],
        complete_host_time_increase_percent_range=[43.593,166.148],source_replay_at_gpt2_three_records=True,
        stable_latency_established=False,general_speedup=False,cross_architecture_generality=False,new_quality_evaluation=False),
    scientific_decision='docs/RESEARCH_DECISION_V119.txt',speed_campaign_closed=True,new_experiment_required_for_current_claim=False,
    proposed_64_request_replication_launched=False,frozen_local_source_counterparts_verified=1322,
    verification='validation/v119_final_verification.json',
    manuscript=dict(version=119,path=str(W/'outputs/second-research-draft.tex'),identity=checks['manuscript'],
        native_compile_success=True,rendered_layout_verified=False,pdf_export_verified=False,
        validation='validation/v119_manuscript_checks.json',same_open_document=True),
    review_bundle=dict(version=119,path=bundle['path'],identity=bundle['archive'],components=14,members=19,
        unchanged_prior_components=13,source_files=1322,actual_matched_comparisons=16,portable_checks_passed=True,
        negative_scope_and_corruption_cases=6,verification='validation/v119_development_bundle.json',submission_ready=False),
    pending=['Rendered page count, table/math layout and PDF export remain unverified after the saved preview startup failure',
             'Final venue/cycle/category and current policy review; existing question pending, do not repeat routinely',
             'Author-controlled declarations only before any separately authorized submission'],
    preview_attempt='validation/v116_preview_attempt.json',paid_compute=False,subagents_used=False,
    credentials_stored=False,conference_submission=False,scientific_work_complete_for_current_claim=True,
    submission_bundle_complete_and_verified=False)
(R/'handoff/program_v119.json').write_bytes(enc(h))
print(json.dumps(dict(evidence_files=len(files),evidence_bytes=sum(e['bytes'] for e in files.values()),
    all_frozen_sources_verified=1322,manuscript=checks['manuscript'],bundle=bundle['archive'],scheduler='PAUSED'),sort_keys=True))
