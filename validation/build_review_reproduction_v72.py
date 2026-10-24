"""Bind the completed quality/recovery component without new empirical execution."""
from pathlib import Path
import json,zipfile
from validation.build_review_reproduction_v71c import R,info,enc,transform

def build():
    out=R/'reports/review-reproduction-v72';archive=R/'reports/development-reproduction-guide-v72.zip';assert not out.exists() and not archive.exists()
    old=R/'reports/review-reproduction-v71c'
    inputs=json.loads((old/'INPUTS.json').read_bytes());env=json.loads((old/'RUNTIME.json').read_bytes())
    names=['development-source-review-v72.zip','development-evidence-v69b.zip','development-audit-receipts-v69.zip','development-service-evidence-v70.zip','development-quality-evidence-v72.zip','development-dependency-notices-v71c.zip','development-selection-metadata-v71.zip']
    inputs.update(schema='review-external-input-commitments-v72',components={n:info((R/'reports'/n).read_bytes()) for n in names},quality_evaluation_complete=True,
        quality_evidence_component='development-quality-evidence-v72.zip',original_quality_closure_failed=True,separate_accounting_recovery_complete=True,
        recovery_source_registration_sha256=info((R/'handoff/registration_v72_accounting.json').read_bytes())['sha256'],
        real_registrations_distributed=False,quality_input_bodies_included=False)
    env['schema']='review-runtime-commitments-v72';env['future_cuda']['empirical_quality_complete']=True
    env['future_cuda']['key_name_historical']=True
    env['separate_accounting_recovery']=dict(complete=True,model_or_likelihood_execution=False,
        resources=json.loads((R/'handoff/registration_v72_accounting.json').read_bytes())['caps'],runtime_unchanged_from_original_cpu=True)
    readme='''Completed service and quality evidence guide,18 October2026

This guide binds seven companion ZIPs and the existing input/runtime commitments.
It acquires no data, installs no dependencies and runs no model or new experiment.
Previous components and guides remain preserved under their original names.

Offline verification
Extract into a fresh directory and use an existing Python3.10+ interpreter:
python3 -I -B verify_inputs.py --components /absolute/path/to/components
The directory must contain the seven ZIP filenames listed in INPUTS.json. The
verifier checks exact bytes/hashes and the guide manifest; missing or unexpected
guide files fail. Check the archive hash separately. Editable manifests are not
authenticity signatures. Optional --model-directory hashes the three preexisting
model/tokenizer files without loading the checkpoint.

Local fixtures
Extract development-source-review-v72.zip and follow its README using an existing
CPython3.12.7/NumPy2.3.5 environment, fresh outputs and an empty temporary directory.
Its unchanged qualification helper runs the same213 generated local fixtures.
The583 source/protocol/helper copies include separately registered accounting
recovery, whose three original tests are outside this portable subset because one
requires a private actual scheduler snapshot. Production constructors, checkpoint,
runtime and Slurm boundaries are mocked in the local subset; tiny CPU fixtures
execute. Python audit hooks are not a full OS sandbox. This is not an empirical
reproduction. The actual Linux103 and generated CUDA24 checks are separate.

Evidence navigation
E01--E15 historical summaries and nine receipt derivatives are preserved.
E16 supplies both actual service audits and ten complete model/state comparisons.
E17 supplies320 paired article loss records across six model roles,24 CPU reference
losses, registered statistics, actual terminal audit, failed accounting receipt
and separate recovery. Its verify_statistics.py recomputes scalar arithmetic from
saved losses; it does not rerun inference or bootstrap. The original cluster
terminal audit checks all1944 actual scalar artifacts and recomputes registered
statistics. Both fixed-teacher endpoints pass frozen tolerances with small
perplexity costs, not gains. The failed original accounting job remains failed;
separate recovery includes that cost and does not repeat models or evaluations.

Input obligations
The ten original quality input groups remain bound in INPUTS.json. The selected
320 articles come from2778 eligible records in a bounded3801-record frame. All
inspected articles, old60 quality IDs and2349 calibration-frame records remain
excluded from future selection. No outcome-dependent replacements are allowed.
The selection metadata companion reproduces saved-hash eligibility, exact union
and fixed sampling order, but does not retokenize corpus text. The original V68
and V70 audits establish saved-token/hash correspondence. The source range does
not verify a full gzip trailer or entire publisher file. This frame is not a
uniform corpus-wide sample. Whole-source SHA is publisher metadata only.

Corpus text, token sequences, model/state binaries and the complete historical
input graph remain external. Original public hashes alone do not reconstruct
those inputs or establish redistribution rights. Do not substitute a new prefix,
current publisher main branch, empty ledger or inferred records. Any empirical
reproduction requires separately admitted inputs/runtime/sources, bounded resources
and one-use registration. Never replay the old jobs or alter their frozen caps.
The original exact target, guards, failed attempts and exclusions remain fixed.

Protocols and runtimes
Read research_v65/PROTOCOL.txt, research_v67/PROTOCOL.txt, research_v68/PROTOCOL.txt,
research_v69/PROTOCOL.txt, research_v70/PROTOCOL.txt, research_v71/PROTOCOL.txt and
research_v72/PROTOCOL.txt in the source component. Runtime commitments refer to
original executed bytes; illustrative host/path replacements are not admitted
runtime identities. Container recreation does not guarantee hash equality.
RUNTIME.json retains its historical future_cuda key with completion now explicit.
No timing replication was performed. Descriptive timings support only the observed
space/source-access/latency tradeoff; stable latency or transfer claims need new
prospective evidence, outside the manuscript's current claim.

Release boundaries
The notices companion includes43 observed notice/attribution texts and preserves
all earlier texts. Later installed RECORD scans do not extend frozen binary
bindings or resolve exact system/driver/container/native-library attribution.
Project release terms are unassigned. Private derivation maps are excluded.
Historical hashes and public source similarity may still reveal identity; full
indirect anonymity is unverified. Author-controlled facts, venue/page category,
rendered layout, release rights and complete external-input closure remain open.
Do not treat these development materials as conference-upload ready.
'''
    payload={'README.txt':readme.encode(),'INPUTS.json':enc(inputs),'RUNTIME.json':enc(env),
        'DEPENDENCIES.txt':(old/'DEPENDENCIES.txt').read_bytes()+b'\nV72 update: actual quality and separately registered accounting recovery are complete; no new dependency/runtime installation. E17 supplies scalar evidence. System/native attribution and project release terms remain unresolved.\n',
        'verify_inputs.py':(old/'verify_inputs.py').read_bytes()}
    assert all(not any(x in raw for x in [b'poonam',b'priyankjairaj',b'/nfs_home',b'/Users/',b'csis.',b'csis_',b'172.24.16.132']) for raw in payload.values())
    payload['MANIFEST.json']=enc({n:info(b) for n,b in payload.items()});out.mkdir()
    for n,b in payload.items():(out/n).write_bytes(b)
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,b in sorted(payload.items()):
            i=zipfile.ZipInfo('reproduction-guide/'+n,(2026,10,18,0,0,0));i.external_attr=0o100644<<16;z.writestr(i,b,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    report=dict(schema='review-reproduction-guide-v72',archive=dict(path=str(archive.relative_to(R)),**info(archive.read_bytes())),component_count=7,
        quality_input_groups=len(inputs['quality_input_groups']),quality_evidence_included=True,original_failure_preserved=True,empirical_execution=False,
        complete_historical_input_closure=False,complete_transitive_notices=False,full_anonymity_verified=False,submission_ready=False)
    with (R/'validation/v72_reproduction_guide_build.json').open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(report))
if __name__=='__main__':build()
