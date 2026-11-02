Current external-input and reproduction guide,18 October2026

This guide binds six companion ZIPs and the inputs/runtimes for the completed
disjoint-root service and active untouched-quality campaign. It does not acquire
data, install dependencies or reproduce numerical results. Original historical
components and the previous guide remain unchanged and separately identifiable.

Offline verification
Extract this guide into a fresh directory. With an existing Python3.10+ interpreter:
python3 -I -B verify_inputs.py --components /absolute/path/to/components
The directory must contain the six ZIP filenames listed in INPUTS.json. The
verifier reads existing files only, validates exact bytes/hashes and this guide's
manifest, and refuses missing or unexpected guide files. The archive hash must
also be checked separately: editable manifests are not authenticity signatures.
Optional --model-directory checks the three already acquired model/tokenizer
files against saved commitments, without parsing or loading the checkpoint.

Local fixture reproduction
Extract development-source-review-v71.zip into a new directory. Use an existing
CPython3.12.7/NumPy2.3.5 environment and empty temporary directory, then invoke:
python -I -B qualify_review_source.py PATH_TO_SOURCE_REVIEW --report REPORT.json
--log TESTS.txt --temporary EMPTY_TEMP_DIRECTORY
The source README defines limits and the213-test subset. It contains577 registered
or legacy-helper files plus README, checker and manifest. Report/log paths must be
new. Network, empirical processes and writes outside the allowed outputs are denied
by Python audit hooks, which are not a full OS sandbox. Expected refusal fixtures
write intentional tracebacks to stderr; use the final unittest/report result.
Linux103 numerical/source fixtures and CUDA24 generated comparisons occurred
separately on the admitted cluster. They are not actual untouched quality results.

Actual input obligations
The model revision and all three files preserve the earlier publisher commitments.
Service inputs and calibration policy remain bound to the training-shard2 prefix.
The untouched sample comes from one bounded8MiB compressed/decoded validation-
shard1 frame,3801 complete articles,2778 eligible and320 selected. All inspected
articles remain reserved. This is not uniform sampling over the corpus. Prefix
verification does not verify a complete gzip trailer or full source bytes.
Whole-source SHA is publisher metadata only. Every historical exclusion, the old
60 quality IDs and2349 calibration-frame records remain protected. The separately
completed saved-frame audit adds complete hashes for short records; exact exclusion
union equality is retained. No sample/threshold/target was changed after outcomes.

INPUTS.json lists each actual quality input commitment by semantic role, including
service audits, candidates, complete-frame audit, exclusions, parameter snapshot,
targets and scheduler evidence. Eleven labelled selection/hash metadata copies
are now supplied in development-selection-metadata-v71.zip, including complete
before/after exclusions and the inspected-frame inventory. Its read-only checker
recomputes saved-hash eligibility, exact exclusion union and fixed sampling order.
It does not retokenize text or establish corpus-to-hash correspondence. Raw corpus,
selected tokens and model/state bodies remain external. Original public hashes
alone do not reconstruct the full historical input graph or establish rights to
redistribute corpus content. Do not substitute a new prefix, current
publisher main branch, an empty ledger or an inferred record list. Exact empirical
reproduction remains blocked until the complete admitted input/receipt graph is
available under appropriate distribution terms. No launch is authorized here.

Runtime and source boundaries
RUNTIME.json preserves CPU/runtime file commitments and the observed CUDA device,
driver/build/package hashes under illustrative host/path replacements. Original
frozen hashes refer to actual executed bytes, not the adapted source copies.
Use research_v65/PROTOCOL.txt, research_v67/PROTOCOL.txt, research_v68/PROTOCOL.txt,
research_v69/PROTOCOL.txt, research_v70/PROTOCOL.txt and research_v71/PROTOCOL.txt.
The failed V69 admission and separate V70 repair audit remain part of the history.
A new environment needs a separate prospective registration, complete source/input/
runtime admission, explicit resources and one-use attempts. Never replay original
jobs or change their caps. Container recreation is not guaranteed to match a hash.

Evidence and release status
Historical E01--E15 summaries and nine receipt derivatives remain unchanged. E16
adds complete disjoint-service audits and ten comparisons, with adverse costs and
fallbacks. Typed fields are preserved under string mappings; derivatives do not
constitute new numerical audits. Original model/corpus/state bytes are excluded.
Quality construction and final loss/cost gates remain pending at this checkpoint.

The expanded notices companion preserves the earlier five texts and adds35
installed CUDA/Python notice texts. Its28-distribution metadata graph,32 active
dependency constraints and34 RECORD notice hashes are checked. This later notice
observation does not extend frozen binary bindings or complete driver/system/
compiler/container/native-library attribution. DEPENDENCIES.txt records both dates.
Three additional NumPy2.3.5 CPU notice texts are now included, bringing the
observed notice/attribution texts to43. They match installed RECORD entries but
do not establish exact native-library source/build identity. All96 earlier
non-index notice-component payloads remain unchanged.
No project license is assigned. Private derivation
maps are excluded. Historical hashes and public source similarity can still reveal
identity; full indirect anonymity is unverified. Author facts, rendered pagination,
rights, complete reproduction and claim-required evidence remain release gates.
