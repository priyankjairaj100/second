# Reproduce the shared-kernel complete-stage control

Use a fresh Linux checkout with a C compiler and the dependencies in
`requirements-recovery-v32.txt`. The committed V35 and V36 capsules provide all
real features, weights, and archived reference codes required by this component.
No full checkpoint download or neural feature generation is required.

Read `ACTIVE_SESSION_V37.md` and the V37 independent review before execution.
Use a new campaign path. Never overwrite a published registration or attempt.

```bash
.venv/bin/python -m unittest tests.test_direct_gram_ball_v37 tests.test_gram_ball_protocol_v37
.venv/bin/python scripts/launch_gram_ball_stage_v37.py --campaign campaigns/pooled_gram_ball_stage_local_v37 --register
.venv/bin/python -u scripts/launch_gram_ball_stage_v37.py --campaign campaigns/pooled_gram_ball_stage_local_v37 --execute
.venv/bin/python scripts/launch_gram_ball_stage_v37.py --campaign campaigns/pooled_gram_ball_stage_local_v37 --status
```

Publish the reviewed registration before running the measured worker.
Registration verifies inputs and checks resource admission without forming a Gram
or computing new codes. Run the worker alone, with no concurrent experiments or analysis.
One attempt receives an 880-second CPU limit, a 1,100-second wall limit, and a 3 GiB
address-space limit, within a separate 900-second phase.

All 2,304 rows and 1,769,472 decisions must match the archived retained reference.
The fixed arms cover original Gram preparation, pooled-Gram deletion, independently
rebuilt retained Gram, and cached-feature reconstruction. Both Gram arms use the new
ball adapter and pay for any interval fallback. The cached-feature control retains
its existing certified kernel and bounded fallback.

Inspect the plan, worker receipt, transaction, sealed completion, CPU ledger, and
`analysis.json`. A terminal worker can complete with a scientific refusal; inspect
every arm and `scientific_gate_passed`. A refused arm has no committed code artifact
and no complete-latency speed ratio. Preserve every refusal, loss, and failed attempt.

Store raw Gram and code binaries durably. Git tracks their metadata and hashes,
while the committed input capsules permit a fresh reproduction.
Single fixed-order stage timings are development observations, not full-model or
population speed claims. Do not claim the generic V36 kernel was the strongest baseline.
