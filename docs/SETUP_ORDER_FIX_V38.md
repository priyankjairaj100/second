# Checkpoint setup correction

The previous run checked historical evidence before downloading its required checkpoint.
Its software test failed on the missing config file.
The local checkpoint concealed this ordering defect during earlier tests.

The corrected workflow restores and verifies checkpoint bytes before software tests.
It publishes a checkpoint audit before those tests start.
The test launcher also checks current checkpoint bytes before it starts its subprocess.
The experiment launcher checks those bytes again.
The workflow keeps all original numerical methods and resource limits.

The new evidence directory is `campaigns/ci_v38_setup_fix`.
The original directory remains unchanged.
The controller now reads its bootstrap from the selected evidence directory.
It does not reuse a target or prepared state from the failed run.
The trigger has a new revision and requests one fresh run.
No failed empirical attempt is repeated.

The previous run published complete finalization evidence.
It created no bootstrap or model ledger.
Its software tests used 0.977886 child CPU seconds outside those ledgers.
No unknown model reservation needs a new hold.
All older holds remain unchanged.

The primary agent reviewed the complete change before publication.
Thirty-eight checks passed; one genuine-procfs check skipped locally.
The hosted workflow requires that check to pass.
Both checkpoint files were restored and verified after workspace maintenance.
The historical WikiText prerequisite then passed locally.
Regression checks cover missing files, changed bytes, preparation order, and the selected evidence directory.

Read `validation/setup_order_fix_v38.json` for exact source hashes.
The empirical program remains incomplete until actual worker results pass their checks.
