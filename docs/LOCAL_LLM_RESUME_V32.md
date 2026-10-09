# Local LLM restart guide

Updated 9 October 2026. Start here after cloning this repository.
The user authorizes local experiments and GitHub checkpoints.
Do not use paid compute, force-push, remove adverse results, or overwrite historical registrations.

## Current incident to understand before execution

The latest verified publication before this update is `36dfb39656333506fde0d01a0f98d620824d92db`.
The default `campaigns/independent_wikitext_v32` root currently stops at a metadata consistency check.
Four workers have settled, charging 656 CPU seconds.
The first lossless repair/cold pair agrees exactly and shows a 1.868474× observed request speedup.
The second cold worker exited successfully, but its live progress file still reports `running`.
Completion, sealed progress, and stdout consistently describe the completed output.
The cause remains unknown.

Read the exact hashes and timing table in `docs/EMPIRICAL_STATUS_V32.md`.
Preserve `wikitext-delete-1-cold/outputs/progress.json` and every original record.
Do not overwrite progress, bypass its guard, mark the root complete, or rerun that attempt.
A possible append-only continuation is being diagnosed and reviewed.
This note does not approve that continuation.
The remaining three WikiText trials and all C4 trials have not run.

The generic fresh-workspace commands below are separate replication instructions.
They do not resolve the default campaign's incident or recover its missing binary files from Git.
Before resuming that campaign, inspect any later reviewed incident and continuation records.
If those records are absent, keep dependent work blocked and report the evidence discrepancy.

## Read these files first

1. `docs/RECOVERY_EVENT_V32.md`: runtime loss and unresolved accounting.
2. `docs/EMPIRICAL_STATUS_V32.md`: supported results and remaining research tasks.
3. `scripts/launch_independent_requests_v32.py`: current recovery controller.
4. `campaigns/independent_requests_v30_draft/selection.json`: preserved source selection.
5. `campaigns/heldout_quality_v30_exclusions.json`: all 60 exposed quality articles.
6. `docs/POOLED_GRAM_CONTROL_V30.md` and `docs/NOVELTY_AUDIT_V30.md`: remaining baseline and positioning limits.

Older `RESUME.md`, `LOCAL_LLM_START.md`, and V31 execution notes are historical.
They must not override current receipts or the recovery event.
The successful method uses fixed nearest-anchor features.
The original sequential calibration target still lacks a complete repair speed advantage.

## Clone and verify the durable evidence

Use Linux, CPython 3.12, GCC, and sufficient local disk space.
The registered workers require bounded memory and a single CPU affinity.
Do not compare timings across machines as matched measurements.

```bash
git clone https://github.com/priyankjairaj100/second.git
cd second
git status --short
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-recovery-v32.txt
.venv/bin/python scripts/audit_published_results_v32.py
```

The audit requires commit `604de5b830bd1386055b394df13275ef7e55475a` in local Git history.
A full clone provides it; deepen a shallow clone before running the audit.
Its successful output says `metadata_checks_passed` and verifies 170 archived metadata files.
It does not rerun model inference or verify missing binary artifacts.
It recomputes historical timing ratios and perplexities, but does not rerun the bootstrap.
Do not convert metadata verification into a claim of new empirical replication.

## Restore the pinned checkpoint

The selected token JSON files are already tracked.
These two independent roots need no raw corpus download or tokenizer run.
The checkpoint helper downloads only two pinned DistilGPT2 files.
It checks exact SHA-256 hashes and byte counts before installation.

```bash
.venv/bin/python scripts/recover_assets_v32.py --fetch-checkpoint --checkpoint-only
```

The pinned model revision is `2290a62682d06624634c1f46a6ad5be0f47f38aa`.
The model file contains 352,824,413 bytes.
Its SHA-256 is `e1ff18884359fe8beb795a5f414feb85a6ce3d929ad019c0d958c039d2b94a1b`.
The configuration contains 762 bytes.
Its SHA-256 is `4ec5947c1d59fee6212cdf3b0ec1a53eac02092554c5ff0a733488cbd2c64f3a`.

The checkpoint-only command exits successfully when both direct inputs match.
The broader inventory, without `--checkpoint-only`, may exit with code 2 afterward.
That means some historical model or state binaries remain absent.
Read its JSON before deciding whether a checkpoint download failed.
Do not manufacture those historical binaries, completion records, or hashes.
The V32 controller prepares new states from the pinned checkpoint and selected token records.
Preserve all new binary outputs locally throughout the campaign.

## Complete the two recovery roots

Check each root's status before deciding whether to register it.
Register only when its status reports `registered: false`.
The preflight checks inputs, archived metadata, numerical policy, and resource admission.
Do not substitute the older V31 controller.
Use a new local workspace, such as `local_runs/replay-001`, for fresh replication.
Published campaign folders can contain registrations whose binary outputs are absent from Git.
Do not resume those folders without restoring their exact artifacts.
Use the same workspace option on every command for both roots.

Use this single command to complete the fixed two-root program:

```bash
.venv/bin/python scripts/continue_empirical_v32.py --workspace local_runs/replay-001 --execute
```

The wrapper registers missing roots and runs WikiText before C4.
It stops on blocked attempts, execution failures, or mismatched outputs.
It never retries failed work or changes budgets.
Completed scientific losses remain in the program.
Without `--execute`, the wrapper only reports both roots' status:

```bash
.venv/bin/python scripts/continue_empirical_v32.py --workspace local_runs/replay-001
```

Use these individual controller commands when you need stepwise inspection:

```bash
.venv/bin/python scripts/launch_independent_requests_v32.py --help
.venv/bin/python scripts/launch_independent_requests_v32.py --workspace local_runs/replay-001 --corpus wikitext --status
.venv/bin/python scripts/launch_independent_requests_v32.py --workspace local_runs/replay-001 --corpus wikitext --preflight
.venv/bin/python scripts/launch_independent_requests_v32.py --workspace local_runs/replay-001 --corpus wikitext --register
.venv/bin/python scripts/launch_independent_requests_v32.py --workspace local_runs/replay-001 --corpus wikitext --run-next
```

Repeat `--run-next` only after the previous worker reports `status: complete`.
Use `--status` between calls; stop when it reports `complete: true`.
Read its transaction, completion, agreement, and budget files after each step.
The controller must choose the next registered trial; do not select a favorable trial manually.
Run seven registered trials per root, unless an execution or exactness failure stops dependent work.
The expected scientific design is preparation, both lossless deletion pairs, conversion, and one compressed repair.
One deletion pair reverses the repair/cold order.
Both requests start from the original state; neither is a successor-state lifetime experiment.

After the WikiText root settles, use the C4 root:

```bash
.venv/bin/python scripts/launch_independent_requests_v32.py --workspace local_runs/replay-001 --corpus c4 --status
.venv/bin/python scripts/launch_independent_requests_v32.py --workspace local_runs/replay-001 --corpus c4 --preflight
.venv/bin/python scripts/launch_independent_requests_v32.py --workspace local_runs/replay-001 --corpus c4 --register
.venv/bin/python scripts/launch_independent_requests_v32.py --workspace local_runs/replay-001 --corpus c4 --run-next
```

Repeat the final command under the same completion rule.
Both corpora remain required if one has an unfavorable scientific result.
An execution failure, resource refusal, or output mismatch requires diagnosis before dependent work.
Never retry automatically or replace a selected source.
Any new method, precision, budget, or trial order needs a new prospective registration.
Never edit an already registered source snapshot or plan.

The roots each have a separate 1,900 CPU-second limit.
Do not pool their allowances or reset an old ledger.
Keep the lost V31 phase's separate 1,900-second recovery hold unresolved.
Keep the older unknown 122-second reservation unchanged.

Analyze each root after all seven trials finish and while its binary artifacts remain available:

```bash
.venv/bin/python scripts/analyze_independent_requests_v32.py --workspace local_runs/replay-001 --corpus wikitext --output local_runs/replay-001/wikitext-analysis.json
.venv/bin/python scripts/analyze_independent_requests_v32.py --workspace local_runs/replay-001 --corpus c4 --output local_runs/replay-001/c4-analysis.json
```

The analyzer refuses incomplete roots and verifies actual new model and state bytes.
It writes only a new output file; it never overwrites an earlier report.
The primary timing excludes archive/bootstrap checks and post-receipt agreement, gate, and analysis work.
Report that boundary explicitly; it is not the entire command's elapsed time.
Analysis CPU is separate from the registered worker allowance.

## Preserve progress before an interruption

After each settled trial, inspect and commit the new text evidence.
Include registration, source snapshot, plan, receipt, transaction, budget ledger, result metadata, and failure evidence.
Include analysis only after it validates the complete evidence chain.
The local workspace is ignored by Git.
Export a publication copy after the current worker stops:

```bash
.venv/bin/python scripts/export_local_evidence_v32.py --workspace local_runs/replay-001
.venv/bin/python scripts/export_local_evidence_v32.py --workspace local_runs/replay-001 --output archives/local-replay-001-checkpoint-01
```

The first command inventories files without creating an export.
The second copies both roots' JSON metadata and frozen Python sources.
It includes failed attempts, partial progress, and unresolved ledger records.
It also includes existing root analysis files.
It excludes binary outputs, caches, locks, and other file formats.
The manifest records original locations, copied locations, hashes, byte counts, and omissions.

The exported archive is metadata-only and cannot resume execution.
The helper preserves every copied byte and every original absolute path inside metadata.
It never moves or renames the live campaign.
Its shared lock refuses export while a research launcher holds admission.
Use a new archive destination for each checkpoint; exports are never overwritten.
Review the exported text before publication, including any captured error messages.
Keep the live workspace unchanged until both roots and their analysis finish.
Keep full raw corpora, credentials, virtual environments, checkpoint weights, and model/state binaries outside Git.
Keep binary artifacts on durable local storage, with their recorded hashes.
Do not rename a campaign directory after registration; plans bind its paths.

Stage the reviewed archive and any new source or status files:

```bash
git add -- archives/local-replay-001-checkpoint-01
git diff --cached --stat
git diff --cached --check
```

Before publishing, rebuild `MANIFEST.sha256` from staged Git blobs, excluding the manifest itself.
This command reads the index, so unstaged edits cannot enter its checksums:

```bash
.venv/bin/python - <<'PY_MANIFEST'
import hashlib, subprocess
from pathlib import Path
rows = subprocess.check_output(['git', 'ls-files', '--stage', '-z']).split(b'\0')
entries = []
for row in filter(None, rows):
    metadata, name = row.split(b'\t', 1)
    mode, oid, stage = metadata.split()
    if stage != b'0':
        raise SystemExit('Resolve index conflicts before publication.')
    if name == b'MANIFEST.sha256':
        continue
    if any(c in name for c in (b'\n', b'\r', b'\\')):
        raise SystemExit('Unsupported filename in checksum manifest.')
    entries.append((name.decode('utf-8'), oid))
cache = {}
with subprocess.Popen(['git', 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE) as reader:
    for name, oid in entries:
        if oid in cache:
            continue
        reader.stdin.write(oid + b'\n'); reader.stdin.flush()
        header = reader.stdout.readline().split()
        if len(header) != 3 or header[1] != b'blob':
            raise SystemExit('Index entry does not identify a blob.')
        raw = reader.stdout.read(int(header[2]))
        if reader.stdout.read(1) != b'\n':
            raise SystemExit('Invalid Git blob response.')
        cache[oid] = hashlib.sha256(raw).hexdigest()
    reader.stdin.close()
Path('MANIFEST.sha256').write_text(''.join(f'{cache[oid]}  {name}\n' for name, oid in sorted(entries)))
PY_MANIFEST
git add -- MANIFEST.sha256
git diff --cached --stat
git diff --cached --check
```

Verify the staged diff contains no credentials or large binary artifacts.
Commit and push normally; never force-push:

```bash
git commit -m "Checkpoint local V32 empirical evidence"
git push origin HEAD
```
Record the pushed commit in the current status note.
Do not say GitHub contains an artifact unless it is actually committed there.

If a process disappears, preserve its reservation and partial outputs.
Do not infer completion or observed CPU use from an old chat message.
Diagnose the controller's durable records before deciding how to continue.

## What to send back for analysis

Provide the pushed commit and campaign directory paths.
Provide each root's final ledger, transactions, worker receipts, and completion records.
Provide complete model and state hashes, code counts, and retained/deleted source IDs.
Provide cold, repair, preparation, and conversion controller times.
Provide certificate acceptance, retained replay counts, refusal counts, and peak memory.
Include adverse results, incomplete trials, interruptions, and any recovery decisions.
Never report only the best timing or a successful subset.

After these roots finish, follow the open-item table in `docs/EMPIRICAL_STATUS_V32.md`.
The broader program still needs scaling, another model, pooled-Gram controls, lifetime sequences, and prospective confirmation.
Do not mark those tasks complete from software tests or small component results.

## Copyable instruction for a local coding agent

> Continue this calibration-data unlearning project from the current Git commit.
> Read the V32 recovery, status, and restart documents first.
> Verify durable receipts before running anything.
> Complete the registered V32 independent roots without selecting favorable outcomes.
> Preserve all failures, old ledgers, numerical targets, and source exclusions.
> Use matched within-root comparisons and verify every full model exactly.
> Report the fixed-feature target distinctly from the original sequential target.
> Commit each settled checkpoint and keep binary artifacts on durable local storage.
> Then address remaining paper gaps through prospective pilots and honest gates.
