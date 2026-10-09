# C4 recovery after the GitHub account lock

GitHub blocked the amended workflow before runner execution.
The account owner must ask GitHub to clear the account lock.
No workflow should start before that restriction is cleared.

The public annotation states:

> The job was not started because your account is locked due to a billing issue.

| Item | Value |
|---|---|
| Blocked run | `37949249514` |
| Source commit | `f174f072419a6fa954379bb36544ead9d926c103` |
| Job record | `113883433045` |
| Completed steps | Zero |
| Worker claims | None |
| C4 registrations | None |
| Bootstrap workers | None |
| C4 workers | None |

[Open the blocked run](https://github.com/priyankjairaj100/second/actions/runs/37949249514).
GitHub created the job record but did not start its steps.
This failure supplies no empirical result.
It does not change an earlier result or ledger.

The earlier run `37948393273` failed during YAML validation.
Its source commit was `1cf45ff1861b7e347bcef6308b3eddbb1e5e6534`.
That run created no job.
The reviewed block scalar fixed that syntax error.
The account lock is a separate infrastructure restriction.

The model allowance remains 1,900 CPU seconds.
The separate bootstrap allowance remains 122 CPU seconds.
Neither failed workflow created a new worker ledger.
These allowances are not measured usage.

## Steps after the account unlock

1. Confirm that GitHub cleared the account lock.
2. Read the current `main` branch and preserve both failed run records.
3. Confirm that `campaigns/ci_v38/execution-claim.json` does not exist.
4. Confirm that no bootstrap or C4 registration exists under `campaigns/ci_v38`.
5. Prepare one explicit account-unlock amendment for the trigger JSON.
6. Add the same amendment to `TRIGGER_PAYLOAD` in `scripts/execute_ci_c4_v38.py`.
7. Record the blocked run, its source commit, and the verified unlock in the amendment review.
8. Review the complete change before publication.
9. Parse the complete workflow and check its exact dependency command.
10. Run the CI and bootstrap software fixtures.
11. Publish the reviewed amendment as one new push to `main`.
12. Check that the new run has `run_attempt: 1`.

The trigger path remains `.github/ci/c4-v38-trigger.json`.
Keep the existing one-use revision and campaign path.
Keep all resource limits, workers, numerical rules, and publication checks.
The job must remain public-only on the standard `ubuntu-24.04` runner.
Keep the current permissions and the prohibition on artifact or cache storage.

Do not use GitHub's rerun button.
The workflow rejects `run_attempt` values other than one.
A new reviewed push is required after the unlock.
If a claim or registration exists, stop and audit it first.
Do not remove it or reset its ledger.

Use this fixture command before publication:

```bash
python -m unittest tests.test_ci_c4_v38 tests.test_bootstrap_target_v38 -v
```

The hosted fixture step also requires the actual-procfs constructor check.
It must pass without a skip on the selected runner.
A local skip does not establish that the runner can construct the target.

Once the new run starts, avoid concurrent pushes to `main`.
The workflow publishes its claim before dependency installation.
It publishes bootstrap registration before checkpoint construction.
It publishes C4 registration before all seven C4 workers.
It then publishes each settled trial and its actual binary audit.
A changed remote revision stops further model work.

## Existing local route and its target gate

The V32 controller already supports fresh local namespaces.
For example, use `local_runs/recovery-001` when that path is unused.
Use the same namespace for WikiText and C4.
This route does not depend on GitHub Actions execution.

Use a compatible Linux host with actual process maps and CPU information.
Use CPython 3.12, GCC, and the pinned numerical dependencies.
Read `docs/LOCAL_LLM_RESUME_V32.md` for setup and evidence export.
Start with the existing environment check:

```bash
.venv/bin/python scripts/preflight_environment_v34.py
```

Then inspect the unused namespace:

```bash
.venv/bin/python scripts/launch_independent_requests_v32.py --workspace local_runs/recovery-001 --corpus wikitext --status
.venv/bin/python scripts/launch_independent_requests_v32.py --workspace local_runs/recovery-001 --corpus c4 --status
```

These commands do not register or execute a model worker.
The V32 controller requires completed WikiText work before C4 in that namespace.
It does not import the V38 historical-WikiText amendment.

A fresh namespace does not solve host target identity.
The unchanged V32 plans retain a historical `expected_target` digest.
A new host can produce a different digest from genuine runtime facts.
The environment check does not prove that those digests agree.

Check the target with the reviewed static bootstrap procedure before V32 workers.
Publish its registration before target construction.
It uses unchanged constructors and performs no calibration or neural evaluation.
Compare its target digest with the intended V32 plans.

If the digests agree, the existing fresh V32 execution procedure remains applicable.
Preserve its WikiText prerequisite, limits, order, and complete evidence.
If they differ, prepare a reviewed local target-binding amendment first.
Use the V38 binding procedure as the reference.
Keep all numerical worker files unchanged.
Do not overwrite a registered plan or insert old runtime facts.

Thus, the existing namespace mechanism is available locally.
An arbitrary new host still needs the target gate before automatic execution.
The GitHub-only V38 wrapper must not be called as a local launcher.
