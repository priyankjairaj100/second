# Calibration-data unlearning for quantized language models

Last checkpoint: 4 October 2026. Target venue: ACL 2027.
Repository: https://github.com/priyankjairaj100/second

## Instructions for the next chat

Read this file first, then `docs/STATUS.md`, `docs/PROJECT_CONTEXT.md`, the latest report and `docs/ALGORITHM_SPEC.md`. The theory/design revision is complete at its stated contracts; full transformer integration and empirical validation remain. Preserve distinctions between proved theorems, implemented algorithms, reported prior measurements and untested proposals. Do not infer empirical success from a conditional theorem. Experiments remain PAUSED pending the user's instruction to resume. The user authorized saving all project files and context to this repository and wants work to continue here without repeated permission requests.

The active request is: "attack the remaining points theoritically and algorithmically. when everything is closed we will resume experiments." During that work the user added: "use this repo to push all your files ... chatgpt chats may freeze run out anytime. so to be sagfe drop full context here so that we may be able to resume in another chat if we have to."

## Scientific goal

Fix a full-precision model W. A sequential quantizer Q uses calibration documents C. On withdrawal F, return exactly the result of Q(W,C\\F), including downstream changes caused by earlier quantized layers. This is calibration-source removal, not removal of knowledge learned in W. Primary aim: meaningful full-model repair savings, with precisely declared state, numerical oracle, storage, and correctness guarantees.

## Most important current facts

1. A prior scalar deletion-score certificate proves equality to full retained-data requantization when all quantized codes stay unchanged. An unchanged-prefix/checkpoint version also permits changed suffix weights. Conditional full-model work savings are proved; reliable wall-clock savings have NOT been established.
2. The recorded pilot's first layer changes codes even after one-record deletion. Thus the old unchanged-prefix route cannot explain those targets. The remaining bottleneck is retained activation/statistic recomputation after changed early layers.
3. The completed theoretical improvement is candidate-prefix transport certification: permit new codes, bound retained activation/covariance drift from independent references, and certify against the true sequential target. The 17-page report proves exactness, finite adaptive replay fallback and a conditional full-model cost bound. It is not an implemented or measured full-model service.
4. Further results: sharp shape bound `(b-a)/(2 sqrt(ab)) K`; operator rather than trace scores; sparse coordinate repair; canonical independent-reference state; weighted fallback with explicit cancellation cost; feature-query limits; and a separate deletion-native alternative. `docs/THEOREM_LEDGER.md` records scope. `src/exact_core.py` implements the local rational oracle/verifier only, with static/manual validation and no numerical experiments.
5. Workspace maintenance removed all earlier local artifacts before this turn. Their contents were not recovered. Historical results below are reconstructed from visible conversation context; original raw logs/source/PDFs are absent. Do not cite the new repository as containing the old experiment payloads unless those files are later recovered and verified.

## Restart protocol

- Check `docs/STATUS.md`, `docs/NUMERICAL_CONTRACT.md` and the most recent commit before doing work. The consolidated report supersedes less-qualified statements in working notes.
- Keep theorem assumptions and numerical target explicit. Exact rational/statistical oracle V differs from pinned floating-point executable E.
- Do not silently change the sequential quantizer to fixed-teacher calibration and still claim the original target.
- Do not launch benchmarks, synthetic datasets, external GPU jobs, or data downloads while experiments remain paused.
- Save meaningful progress to GitHub regularly. Preserve existing files and do not force-push.
- If old artifacts are needed, ask the user to attach the previously downloaded ZIPs/PDFs. Library access in the originating chat was restricted and its last upload failed authentication.
- Never place credentials, account tokens, unrelated user history, private messages, model caches, or environment secrets in this repository.

This checkpoint deliberately stores scientific/project context rather than a transcript of unrelated conversations or internal reasoning.
