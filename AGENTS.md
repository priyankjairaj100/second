> Current instruction, 5 October 2026: The user resumed local empirical pilots.
> Use protocol v6. Keep prior results and failures. Confirmation remains blocked.
> The earlier experiment pause below is historical.

# Project working guidance

Read RESUME.md, docs/PROJECT_CONTEXT.md, and docs/STATUS.md before continuing.

Preserve the user's current constraint: experiments are paused until the theoretical and algorithmic revision is complete. Do not launch benchmarks or synthetic dataset studies without the user's next instruction to resume. Mathematical derivation, source inspection, implementation design, and static code checking are allowed.

Save substantive progress and a self-contained resume checkpoint to the authorized repository, priyankjairaj100/second. Do not force-push or delete unrelated files. Do not commit credentials, private account data, environments, or model caches.

Keep precise labels for proved results, reviewed results, implementation status, measurements, and hypotheses. Historical measurements copied from chat are not recovered raw evidence. Fixed floating-point program E and exact-statistic oracle V are different targets. A fixed-teacher or reset-calibration quantizer is an alternative target, not a repair shortcut for the original sequential target.

Correctness and complete state semantics take priority over reporting a speedup. Include setup, verification, retained replay, checkpoint reads, canonical state maintenance, output, and fallback costs in the appropriate ledger. Make probability laws and hardware/work models explicit.
