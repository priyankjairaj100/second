# Runtime restoration and evidence boundaries

The checkpoint, tokenizer, and archived model artifacts survived the session transition.
The current processor differs from the processor used for revision 17.
The old processor was Intel Xeon Platinum 8573C.
The current processor is AMD EPYC 9V74.

The first revision 20 screen correctly rejected the stale runtime-bound target.
It charged eleven CPU seconds before method execution.
Its receipt remains in `pilots/v20/attempt-001`.
The second screen built a new current-runtime target and recomputed its checked oracle values.
It did not bypass the runtime guard.

The first-stage codes, second-stage factors, and second-stage codes matched the checked archived values.
Those equalities establish a value bridge for those objects only.
They do not equate the old and current complete target identities.
All revision 17 comparison workers used the same old runtime.
The later processor change therefore does not explain their recorded relative performance.

Restored dependencies match `requirements-local.txt`:

- `gmpy2==2.3.2`
- `pyarrow==25.0.1`
- `tokenizers==0.23.2`
- `huggingface_hub==1.33.0`

The preparation script rebuilt the pinned WikiText token pools.
Their digest matches the previously archived revision 14 pool digest:
`20f6dcf2893b157d4064f43c8b4c92ff96b370d350e53affaa8075b989178c5b`.
The restored pools contain 500 development, 110 confirmation, and 60 evaluation articles.
Rebuilding token pools ran no model.

All previously evaluated articles remain excluded from future confirmation.
Revision 21 adds its two articles to those exclusions.
Its comparator is explicitly the archived sequential model evaluated under the current decoder.
It is not a newly measured sequential requantization transaction.

Dependency restoration, software fixtures, and archive analysis do not debit empirical worker time.
Every admitted model worker retains its receipt and inherited CPU debit.
No budget was reset.
Revision 21 ended with 10,775 charged seconds and 25 seconds remaining.
