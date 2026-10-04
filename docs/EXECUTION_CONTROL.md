# Local execution control

Research experiments remain paused.
The checks described here use software fixtures only.
The executor does not download models, data, or tokenizers.

`WorkerLimits` defines enforced limits for each comparison process.
`run_campaign` executes every entry from one frozen campaign.

## Command

Validate a local campaign:

```bash
python scripts/run_campaign.py campaign.json --output runs/campaign-001 --validate-only
```

Execute an authorized campaign:

```bash
python scripts/run_campaign.py campaign.json --output runs/campaign-001
```

Validation reads manifests and executable sources.
It does not load checkpoint tensors or evaluate transformer features.
The existing run manifest provides deeper input validation.
The campaign refuses research execution when its protocol keeps experiments paused.
Software fixtures remain allowed.

## Enforced process limits

The campaign requires every limit explicitly.
The executor does not replace missing limits with permissive defaults.

| Field | Enforcement |
| --- | --- |
| `wall_seconds` | The parent stops the process group after the worker deadline |
| `cpu_seconds` | `RLIMIT_CPU` sets the soft limit; the hard limit adds one second |
| `address_space_bytes` | `RLIMIT_AS` sets equal soft and hard limits |
| `file_size_bytes` | `RLIMIT_FSIZE` limits each file written by the worker |
| `affinity_cpus` | Linux CPU affinity restricts worker execution |
| `threads` | Common numerical libraries receive explicit thread environment values |
| `termination_grace_seconds` | The parent allows zero through ten seconds before forced cleanup |

All limits use positive integers, except termination grace can equal zero.
CPU identifiers must form a sorted list without duplicates.
The current process must permit every requested CPU identifier.
The worker cannot raise an inherited hard limit.

The wrapper applies limits before it starts the experiment program.
The wrapper records the effective limits and the request hash.
The controller verifies those values before accepting success.
A missing or invalid acknowledgment prevents success.

`RLIMIT_AS` limits virtual address space.
It does not directly limit physical memory.
CPU limits apply separately to each process.
These per-process limits alone do not enforce cumulative CPU use.
Revision 7 adds protocol-scoped admission and observed CPU debits; see `docs/EXECUTION_BUDGETS.md`.
This remains distinct from physical process-tree containment.
Thread environment values request library behavior.
CPU affinity supplies the additional execution restriction.
Neither mechanism proves that a library creates a particular thread count.

The file limit also applies to model and state artifacts.
An artifact can therefore exceed its limit before the process reaches its memory limit.
A forced signal alone does not prove memory exhaustion.
The controller records an unexplained forced signal as `killed_unknown`.

The parent creates a separate process group.
It stops ordinary descendants after completion, failure, or timeout.
It reaps the direct worker process.
This cleanup does not contain hostile programs that create separate sessions.
The reference runner does not execute checkpoint code.

## Frozen inventory binding

The inventory schema is `calibration-campaign-v1`.
Write inventory bytes with `canonical_json`.
The executor rejects other byte formats for the inventory.

Each entry binds these values:

- Run identity and phase.
- Request membership and source records.
- Target hash and analysis group.
- Complete run manifest, except its final protocol hash.
- Deterministic method order and repetition index.

The inventory also binds workload definitions, limits, executable sources, and entry order.
The source map covers every `src/*.py` file and both execution scripts.
The executor requires the complete current source map.
A changed source file prevents dispatch and reuse of saved outcomes.

A direct hash cycle would make a frozen plan impossible to construct.
The inventory therefore clears only `protocol.sha256` inside each bound run manifest.
The protocol then binds the inventory hash.
The final run manifests bind the protocol hash.
The executor checks all three bindings before dispatch.
It also records each final run manifest hash.

The executor checks membership again before every worker starts.
It does not select a favorable subset of entries.
A changed inventory or protocol stops the campaign.
Existing terminal outcomes remain available.

Confirmation also requires an explicitly declared configuration list.
The protocol must set `confirmation_configuration_ids`.
The executor checks the declared root count, request IDs, and repetition count.
It requires every configuration, root, request, and repetition combination.
It rejects missing or extra primary combinations.

## Process and cache conditions

Each complete comparison starts in a new process.
Each comparison still executes its methods within that process.
Those methods share prepared objects and earlier process history.

The campaign mode is `isolated_comparison_warm_arms_os_cache_uncontrolled`.
The comparison mode remains `warm_sequential_os_cache_uncontrolled`.

A new process does not clear operating-system caches.
This implementation does not establish independent cold execution for each method.
It therefore cannot support a claim about cold method latency.
The inventory fixes and saves counterbalanced method orders.
Method order does not remove every shared-state effect.

The worker timer covers dispatch through process cleanup.
It excludes later controller log summaries and the final controller commit.
The parent must remain active to enforce its wall deadline.
The runner separately records its existing method boundaries.
Do not treat the worker timer as one method's request latency.
Do not add nested method times to the complete worker time.

## Outcomes and restart

Each worker has a durable control record.
The control record seals success, timeout, signal termination, or another failure.
Its top-level `status="complete"` means the controller saved a terminal outcome.
Read `outcome.status` to determine whether the worker succeeded.

The controller retains bounded log summaries.
Each summary includes the full log hash and byte count.
It retains at most the final 32,768 bytes as decoded text.
It does not retain an unbounded in-memory log.

Each campaign keeps every planned entry in its denominator.
An absent worker result becomes `missing_worker_result`.
An incomplete runner result remains a failure.
A successful runner result must pass complete artifact verification.
Its identity, target, protocol, manifest, method order, and cache mode must match the frozen entry.

A completed campaign also seals failed entries.
Its `outcome` field reports whether every entry succeeded.
Restart returns the same terminal records after verification.
Restart does not rerun failed workers automatically.
A new prospective inventory must identify deliberate repetitions.

An interrupted controller preserves attempted and unstarted entries.
Restart creates a new controller attempt.
It reuses sealed workers after verification.
It does not overwrite completed worker artifacts.

The archive uses trusted local storage.
Hashes detect changed artifacts within this scope.
They do not authenticate an adversarial storage service.
The archive retains original states outside the live-state deletion guarantee.

## Remaining execution work

The following items remain open:

- Independent processes and equivalent preparation for each measured method.
- Cumulative limits for each research phase.
- Hardware and cache controls needed for broader latency claims.
- Real checkpoint compatibility and practical resource fit.
- User authorization to resume research experiments.

The correctness tests establish these software behaviors only.
They do not establish useful chart coverage, model quality, or repair speed.

## Revision 7 separate method executor

The original campaign keeps warm methods inside each comparison worker.
The separate executor uses independent setup, repair, indexed-fresh, and direct-fresh workers.
It includes loading and child commitment within each declared worker clock.
Parent verification, post-cleanup accounting, logs, and controller receipts remain outside that clock.
Operating-system caches remain uncontrolled.
Read `docs/ISOLATED_COMPARISON.md` for exact boundaries and restart guarantees.
Isolated confirmation inventory and complete parent-transaction timing remain open.
