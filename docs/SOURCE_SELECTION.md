# Source selection and acquisition gate

Date: 4 October 2026.
Status: metadata selection only.

The machine-readable catalog is `configs/source_catalog_v1.json`.
No selected checkpoint or corpus has been downloaded or evaluated.
Repository metadata does not establish adapter compatibility or practical execution.

## Checkpoint candidates

| Candidate | Intended role | Observed source evidence | Remaining gate |
| --- | --- | --- | --- |
| `distilbert/distilgpt2` | First supported architecture candidate | GPT-2 configuration, six layers, safetensors, Apache-2.0 tag | Tensor inspection, local hashes, resource fit |
| `openai-community/gpt2` | Larger architecture control | GPT-2 architecture, safetensors, MIT tag, full revision available | Local hashes, tensor inspection, resource fit |

Official DistilGPT2 metadata includes the historical `_num_labels` field.
The adapter now accepts this field without changing language-model computations.
One regression test checks this behavior.
This metadata fix does not validate an actual public checkpoint.

Safetensors may contain legacy buffers beyond trainable parameters.
The current adapter rejects unsupported tensors.
Inspect actual tensor headers before deciding whether another adapter change is necessary.
Do not silently ignore unexplained tensors.

Both candidates can exceed the reference implementation's default planning limits.
They are architecture candidates, not approved executable configurations.
The config-only preflight checks counts before loading tensor values.
Its byte estimate is a planning heuristic, not a measured peak or proved upper bound.
Passing that check does not guarantee allocation or useful runtime.
Failing it blocks the declared execution plan.

## Real text candidates

| Source | Intended use | Required preparation |
| --- | --- | --- |
| WikiText-2 raw | First real calibration and held-out text | Reconstruct article boundaries; pin splits and source rows |
| C4 English | Reserve domain and source-deletion workload | Select bounded shards; declare the sampling frame |
| English LAMBADA | Reserve NLP task evaluation | Implement verified last-word scoring and confirm underlying text permissions |

WikiText rows do not automatically identify independent documents.
Preserve complete article identity through tokenization and deletion.
Never create independence by treating article lines as separate research roots.
WikiText-2 and WikiText-103 share evaluation material.
Do not count their evaluation splits as independent domains.

The WikiText card has inconsistent license metadata.
Its tags name CC-BY-SA-3.0 and GFDL; its prose names CC-BY-SA-4.0.
Resolve the applicable source terms before publishing redistributed text.
Record the resolution and attribution in acquisition metadata.

C4's repository tag names ODC-BY.
A selected shard prefix is a bounded sampling frame.
It does not establish corpus-uniform sampling.
Do not download the complete corpus for a bounded pilot.

The LAMBADA repository tag names MIT.
This tag alone does not resolve underlying book-text permissions.
Use its English material only for this initial real-text protocol.
The runner currently provides language-model NLL, not a complete LAMBADA task evaluator.

Synthetic empirical datasets remain deferred.
Small algebraic software fixtures remain correctness tests.
They do not supply paper performance or NLP evidence.

## Inputs required before any research run

1. Pin complete repository revisions and every acquired file hash.
2. Record tokenizer files, revisions, special-token policy, and resulting token hashes.
3. Record licenses, provenance, document identities, and permitted redistribution.
4. Freeze development, confirmation, and held-out evaluation identities without overlap.
5. Freeze request selectors, seeds, family definitions, and a complete planned run inventory.
6. Pass architecture validation and the declared resource policy.
7. Obtain the user's instruction to resume experiments.

The current catalog deliberately leaves unavailable pins null.
It is not a runnable experiment manifest.
Later acquisition must replace every required null with observed evidence.

## Local execution scope

The observed environment uses Python 3.12.14 on Linux x86_64.
The container reports an eight-CPU quota and an eight-GiB memory limit.
The proposed reference-process planning budget is six GiB.
No GPU interface or installed PyTorch package was observed.
These observations describe this session, not guaranteed future hardware.

All work remains local to this project.
No cloud job, external compute budget, or unrelated hardware is authorized.
The protocol states additional staged runtime budgets.
Those budgets are planning decisions, not measured feasibility results.

## Primary sources inspected

- DistilGPT2 files: https://huggingface.co/distilbert/distilgpt2/tree/main
- DistilGPT2 configuration: https://huggingface.co/distilbert/distilgpt2/blob/main/config.json
- DistilGPT2 weight metadata: https://huggingface.co/distilbert/distilgpt2/blob/main/model.safetensors
- GPT-2 repository API: https://huggingface.co/api/models/openai-community/gpt2
- WikiText card: https://huggingface.co/datasets/Salesforce/wikitext
- WikiText revisions: https://huggingface.co/datasets/Salesforce/wikitext/commits/main
- C4 card: https://huggingface.co/datasets/allenai/c4
- C4 revisions: https://huggingface.co/datasets/allenai/c4/commits/main
- LAMBADA card: https://huggingface.co/datasets/EleutherAI/lambada_openai
- LAMBADA revisions: https://huggingface.co/datasets/EleutherAI/lambada_openai/commits/main

## Revision 6 pin audit

Primary Hub pages now identify complete DistilGPT2 and WikiText repository revisions.
The catalog records those revisions and their source URLs.
These are repository pins, not verified local file hashes.
Tokenizer files, token records, and actual checkpoint imports remain unverified.
C4 and LAMBADA remain reserve sources with unresolved acquisition fields.
No model or corpus payload was downloaded.
