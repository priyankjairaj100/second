# Independent timing evidence review

Reviewed 8 October 2026, UTC.

The review verified eleven sealed transactions and one controller-incomplete warm attempt.
Every sealed receipt artifact hash, plan binding, transaction clock, and ledger debit matched.
Ten retained model artifacts and six retained state artifacts matched byte-for-byte.
Independent decoding counted 1,906,485 changed model codes.

The gate uses min(cold 49.446 seconds, warm 52.441 seconds).
The three matched speedups are 1.330757, 1.298191, and 1.328236.
Their geometric mean is 1.318978.
Equally indexed reconstruction ties repair, with ratio 0.998806.

Accounting preserves 517 recorded CPU seconds and 122 seconds of unknown reserved usage.
The separate phase retains 261 seconds.
The legacy allowance remains unchanged.
No unavailable CPU usage or full transaction timing was reconstructed.

Release scope: repeatable development speedup on one explicit fixed-feature DistilGPT2 request.
Not established: population reliability, measured lifetime superiority, general quality, or novelty.

The controller now preserves reservation and exit evidence before settlement.
The recovery is explicit and prospective; raw failed evidence remains intact.
