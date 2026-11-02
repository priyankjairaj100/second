"""Current input/runtime guide from actual registrations; no input acquisition."""
from pathlib import Path
import datetime,hashlib,json,zipfile
from validation.build_review_source_v69 import MAPPING,replace
R=Path(__file__).resolve().parents[1]
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def enc(d):return (json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def read(n):return json.loads((R/n).read_bytes())
def transform(x):
    if isinstance(x,str):return replace(x,MAPPING)
    if isinstance(x,list):return [transform(v) for v in x]
    if isinstance(x,dict):return {replace(k,MAPPING):transform(v) for k,v in x.items()}
    return x
def commitments(x):
    if isinstance(x,dict) and set(x)=={'path','bytes','sha256'}:return {k:x[k] for k in ['bytes','sha256']}
    assert isinstance(x,dict)
    return {k:commitments(v) for k,v in x.items()}
def build():
    out=R/'reports/review-reproduction-v71c';archive=R/'reports/development-reproduction-guide-v71c.zip'
    assert not out.exists() and not archive.exists()
    p=read('handoff/registration_v71_quality.json');data=read('handoff/registration_v68.json')
    old=read('reports/review-reproduction-v69/INPUTS.json');env=read('reports/review-reproduction-v69/RUNTIME.json')
    names=['development-source-review-v71.zip','development-evidence-v69b.zip','development-audit-receipts-v69.zip',
           'development-service-evidence-v70.zip','development-dependency-notices-v71c.zip','development-selection-metadata-v71.zip']
    inputs=dict(old,schema='review-external-input-commitments-v71',components={n:info((R/'reports'/n).read_bytes()) for n in names},
        quality_input_groups=commitments(p['inputs']),quality_sample_policy=data['policy'],
        quality_data_url='https://huggingface.co/datasets/allenai/c4/resolve/'+data['policy']['revision']+'/'+data['policy']['filename'],
        quality_frame_complete_records=3801,quality_eligible_articles=2778,quality_selected_articles=320,
        entire_inspected_frame_reserved=True,additional_complete_token_hash_audit=True,
        quality_evaluation_complete=False,quality_source_registration_sha256=info((R/'handoff/registration_v71_quality.json').read_bytes())['sha256'],
        real_registrations_distributed=False,quality_input_bodies_included=False,quality_selection_metadata_component='development-selection-metadata-v71.zip',quality_selection_metadata_roles=['registration','checks','data','audit','selection','inventory','before','after','acquisition','frame_audit','historical-quality-exclusions'])
    env['schema']='review-runtime-commitments-v71'
    env['local_fixture_environment'].update(tests=213)
    env['future_cuda']=dict(admission_complete=True,actual_generated_comparisons=24,empirical_quality_complete=False,
        actual_runtime_bindings=transform(p['runtimes']['cuda']),device_policy=dict(one_a100=True,allocator_limit_bytes=8589934592,physical_reservation_bytes=17179869184),
        placeholder_host_and_path_strings=True,numerical_runtime_not_installed_by_this_guide=True)
    env['cpu_runtime_and_limits']=dict(host='reviewcluster.mn1',resources=p['resources'],actual_linux_tests=103,
        registration_covers_original_paths_only=True,derived_placeholders_not_admitted_runtime=True)
    readme='''Current external-input and reproduction guide,18 October2026

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
'''
    verifier=(R/'validation/verify_review_inputs_v69.py').read_text().replace('Directory holding the three named ZIPs','Directory holding the named companion ZIPs')
    payload={'README.txt':readme.encode(),'INPUTS.json':enc(inputs),'RUNTIME.json':enc(env),
        'DEPENDENCIES.txt':(R/'reports/review-reproduction-v69/DEPENDENCIES.txt').read_bytes()+b'\nUpdate18 October2026: development-dependency-notices-v71c.zip preserves the five earlier texts and adds35 observed installed CUDA/Python notices. All28 selected distribution notice sets and32 active declared dependency constraints were checked;34 distribution notice files match their RECORD entries. This is later metadata/notice observation, not a retroactive frozen binary binding. Full GPU-node/system/native attribution and project release terms remain open.\n','verify_inputs.py':verifier.encode()}
    forbidden=[b'poonam',b'priyankjairaj',b'/nfs_home',b'/Users/',b'csis.',b'csis_',b'172.24.16.132']
    for name,b in payload.items():assert not any(s in b for s in forbidden),name
    payload['MANIFEST.json']=enc({k:info(v) for k,v in payload.items()});out.mkdir()
    for name,b in payload.items():(out/name).write_bytes(b)
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,b in sorted(payload.items()):
            i=zipfile.ZipInfo('reproduction-guide/'+name,date_time=(2026,10,18,0,0,0));i.external_attr=0o100644<<16;z.writestr(i,b,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    report=dict(schema='review-reproduction-guide-v71',archive=dict(path=str(archive.relative_to(R)),**info(archive.read_bytes())),
        payload={k:info(v) for k,v in payload.items()},quality_input_groups=len(p['inputs']),component_count=6,
        model_or_data_acquired=False,actual_runtime_installed=False,quality_result_inferred=False,
        complete_historical_input_closure=False,complete_transitive_notices=False,full_anonymity_verified=False,
        additional_cpu_notice_texts=3,source_bindings={n:info((R/n).read_bytes()) for n in ['handoff/registration_v71_quality.json','handoff/registration_v68.json','reports/review-reproduction-v69/INPUTS.json','reports/review-reproduction-v69/RUNTIME.json']})
    (R/'validation/v71c_reproduction_guide_build.json').write_bytes(enc(report));print(json.dumps(report['archive']))
if __name__=='__main__':build()
