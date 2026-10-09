# C4 execution on a public GitHub runner

This protocol starts a fresh C4 campaign.
It preserves all earlier C4 failures and ledgers.
It uses the original numerical worker code.
It does not change the calibration rule.

The workflow uses one standard `ubuntu-24.04` runner.
The job rejects private repositories before runner allocation.
The workflow permits only `contents: write`.
It does not use artifact storage, dependency caches, or paid runners.
Its wall limit is 60 minutes.

The exact trigger file is `.github/ci/c4-v38-trigger.json`.
Only a push to `main` can start this workflow.
The job rejects all GitHub reruns.
A durable claim blocks later execution of this campaign.
The wrapper publishes that claim before dependency installation.

The workflow pins both action revisions.
It selects CPython 3.12.14.
It installs exact NumPy and gmpy2 wheels with verified hashes.
It disables dependency caching.
A bounded step runs the CI and bootstrap software fixtures.
It requires the actual-procfs constructor fixture to pass without a skip.
It publishes fixture results before model work.

## Registration and runtime

The original decoder requires actual process maps and CPU information.
The preflight reads those interfaces on the hosted runner.
Missing interfaces stop execution.
The workflow does not supply replacement runtime facts.

The runtime comparison checks the original and portable collectors.
This check uses no model or dataset.
C4 continues to use the original backend.
A narrow portable-interface refusal permits C4 only when original runtime checks pass.
Such a refusal does not permit portable runtime promotion.
Contradictory facts and unknown errors stop C4.
The workflow publishes each refusal and its reason.

The target digest includes runtime facts.
Thus, the new host requires a new target digest.
A bounded worker loads the pinned checkpoint and constructs the target manifest.
It performs no neural inference or calibration.
It computes no calibration features or model codes.

The wrapper publishes the bootstrap registration before that worker starts.
It then verifies the bootstrap receipt and outputs.
It publishes the target manifest before C4 registration.
Every C4 trial receives that exact target digest.
All seven trials retain the original mathematical recipe.

The bootstrap has a separate allowance of 122 CPU seconds.
Its worker limit is 120 CPU seconds.
The two extra seconds cover the existing reservation rule.
This allowance does not replace any historical reservation.

The C4 campaign has a separate allowance of 1,900 CPU seconds.
Its seven maximum reservations total 1,844 seconds.
The workflow preserves the original trial limits and order.
Each worker uses one CPU and a six-GiB address limit.

The V38 controller explicitly changes the WikiText prerequisite.
It accepts the published, completed WikiText analysis as development evidence.
It verifies all 699 bound files and the settled ledger.
It does not repeat WikiText on the new runner.
It does not claim a new audit of historical binary outputs.
It preserves the disclosed WikiText recovery incident.

The wrapper publishes the full C4 registration before any C4 worker starts.
The registration binds source files, runtime facts, inputs, controls, and ledgers.
The original controller guards remain active.
The new controller checks the verified bootstrap target.

## Trials and evidence

| Order | Trial |
|---|---|
| 1 | Prepare the original C4 state |
| 2 | Reconstruct deletion direction zero |
| 3 | Repair deletion direction zero |
| 4 | Repair deletion direction one |
| 5 | Reconstruct deletion direction one |
| 6 | Convert the original state to the compressed format |
| 7 | Repair direction zero from the compressed state |

The wrapper publishes an intent before each trial.
The intent records planned limits, without claiming measured usage.
Each completed trial receives an audit of its actual binary files.
The audit parses all 24 model stages and all 42,467,328 codes.
It compares actual model bytes with each required reference.
It records changed codes against the original model.
It verifies native certificate evidence when applicable.

The wrapper publishes every settled trial before it starts the next trial.
It preserves scientific losses and certificate fallback costs.
A scientific latency loss does not stop later registered work.
An execution, integrity, or exactness failure stops dependent work.
No failed trial receives an automatic retry.

The final analysis reads all seven trials and their actual binary files.
It publishes times, gates, hashes, state sizes, and both ledgers.
The temporary runner holds model files until this analysis finishes.
GitHub receives text evidence only.
No external artifact storage is used.

Each publication uses one normal Git push.
A changed remote revision stops publication and further model work.
The wrapper never force-pushes or changes historical evidence.

If a runner disappears, its prior claim and trial intents remain published.
Missing settlement does not become an inferred timing.
Hold the full missing allowance until valid settlement evidence is recovered.
The campaign and bootstrap allowances total 2,022 CPU seconds.
This total is an allowance, not measured usage.

These runs provide development replication on one shared runner.
They do not provide prospective confirmation or a population interval.
The target still uses fixed nearest-anchor calibration.
It remains distinct from original sequential quantization.
