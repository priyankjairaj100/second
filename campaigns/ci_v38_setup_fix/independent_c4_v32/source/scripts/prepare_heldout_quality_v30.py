"""Prepare the complete held-out remainder without model inference or registration."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_heldout_quality_v30 import POLICY,validate_selection
from src.run_store import canonical_json,digest


def require(flag,message):
    if not flag:raise ValueError(message)


def descriptor(path):
    path=Path(path).resolve()
    with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
    return dict(path=str(path),sha256=sha,bytes=path.stat().st_size)


def exposure_audit(root,remaining,exclude_dirs=()):
    pattern=re.compile(r'wikitext2:validation:article-row-[0-9]+')
    observed=set();files={};collisions=[]
    for folder in ('pilots','campaigns'):
        for path in sorted((root/folder).rglob('*.json')):
            if {'source','worker'}&set(path.parts) or any(path==parent or parent in path.parents for parent in exclude_dirs):continue
            if path.stat().st_size>64*2**20:raise ValueError('oversized experiment metadata prevents complete exposure audit')
            raw=path.read_bytes();ids=set(pattern.findall(raw.decode('utf-8')))
            if ids:
                observed.update(ids);files[str(path.resolve())]=dict(bytes=len(raw),sha256=digest(raw))
            if ids&set(remaining):collisions.append(dict(path=str(path.resolve()),ids=sorted(ids&set(remaining))))
    return dict(observed_metadata_ids=sorted(observed),metadata_files=files,remaining_id_collisions=collisions,
                scope='identifier audit of archived experiment JSON outside source and worker copies; not a pretraining contamination audit')


def build(root,destination):
    development_path=root/'campaigns/quality_v30/registration.json'
    previous_path=root/'campaigns/quality_extensions_v30/attempts/matched-quality-128/outputs/completion.json'
    development=json.loads(development_path.read_bytes());previous=json.loads(previous_path.read_bytes())
    pool_path=root/'tmp/data/wikitext2/prepared-pools.json';pools=json.loads(pool_path.read_bytes())
    old=development['excluded_from_future_confirmation_ids']
    records=[dict(id=row['id'],tokens=row['tokens'][:128]) for row in pools['evaluation'] if row['id'] not in set(old)]
    remaining=[row['id'] for row in records]
    audit=exposure_audit(root,remaining,(destination,root/'campaigns/heldout_quality_v30'))
    require(not audit['remaining_id_collisions'],'remaining articles have prior metadata exposure')
    require(all(previous.get(key) is True for key in ('matched_quality_gate_pass','development_safety_gate_pass','historical_control_parity_pass')),
            'development gates did not pass')
    fixed_attempt=root/'campaigns/full_service_v30/attempts/repair-001'
    seq_attempt=root/'campaigns/quality_extensions_v30/attempts/sequential-128'
    inputs={key:descriptor(path) for key,path in dict(pools=pool_path,development_registration=development_path,
        development_completion=previous_path,fixed_completion=fixed_attempt/'outputs/completion.json',
        fixed_model=fixed_attempt/'outputs/model.bin',sequential_completion=seq_attempt/'outputs/completion.json',
        sequential_model=seq_attempt/'outputs/model.bin',config=root/'tmp/models/distilgpt2/config.json',
        weights=root/'tmp/models/distilgpt2/model.safetensors',tokenizer=root/'tmp/models/distilgpt2/tokenizer.json').items()}
    frozen=dict(fixed128=inputs['fixed_model']['sha256'],sequential128=inputs['sequential_model']['sha256'])
    require(frozen==dict(fixed128=previous['provenance']['new_model_sha256'],
        sequential128=previous['provenance']['sequential128']['model_sha256']),'frozen outputs differ from development follow-up')
    selection=dict(schema='heldout-quality-selection-v30',status='draft_unregistered',model_inference=False,policy=POLICY,
        records=records,prior_excluded_ids=old,prospective_all_excluded_ids=sorted(set(old)|set(remaining)),
        pools_sha256=inputs['pools']['sha256'],tokenizer_sha256=inputs['tokenizer']['sha256'],frozen_model_sha256=frozen,
        quality_evaluator_sha256=previous['provenance']['shared_evaluator_sha256'],exposure_audit=audit,
        selection='all remaining prepared validation articles in their existing deterministic pool order',
        scope='bounded prepared-pool remainder, not a corpus-uniform sample or pretraining-clean benchmark')
    validate_selection(selection,pools,development)
    selection_raw=canonical_json(selection)
    inputs['selection']=dict(path=str(destination/'selection.json'),bytes=len(selection_raw),sha256=digest(selection_raw))
    specification=dict(schema='heldout-quality-draft-v30',status='draft_unregistered',confirmation=True,
        confirmation_scope=POLICY['confirmation_scope'],phase_cpu_cap_seconds=600,
        external_attempts=dict(development=dict(attempt=str(previous_path.parent.parent),equals=dict(status='complete',
            matched_quality_gate_pass=True,development_safety_gate_pass=True,historical_control_parity_pass=True,
            **{'provenance.new_model_sha256':frozen['fixed128'],
               'provenance.sequential128.model_sha256':frozen['sequential128']}))),
        external_equalities=[],trials=[dict(id='quality-40',script='run_heldout_quality_v30.py',cpu_seconds=540,wall_seconds=720,
            plan=dict(checkpoint=str(root/'tmp/models/distilgpt2'),inputs=inputs,policy=POLICY))],
        model_freeze='exact fixed128 and sequential128 output hashes; byte-preserving certificate or codec optimization remains permitted',
        compression_latency_prerequisite=False,
        stop_rule='no outcome-driven stopping, retuning, retries, article replacement, or alternative primary; preserve incomplete work',
        reporting='all forty article outcomes and all controls; only fixed128/sequential128 is primary',
        interpretation='prospective held-out bounded-pool gate; bootstrap article-mixture guard has no guaranteed population coverage')
    return selection_raw,specification


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'campaigns/heldout_quality_v30_draft')
    args=parser.parse_args();destination=args.output.resolve()
    if destination.exists():raise ValueError('refuse to overwrite a prospective draft')
    selection,spec=build(ROOT,destination);destination.mkdir(parents=True,exist_ok=False)
    (destination/'selection.json').write_bytes(selection)
    (destination/'specification.json').write_bytes(canonical_json(spec))
    print(json.dumps(dict(status='draft_unregistered',articles=40,model_inference=False,
        selection_sha256=digest(selection),specification_sha256=digest(canonical_json(spec)))))
