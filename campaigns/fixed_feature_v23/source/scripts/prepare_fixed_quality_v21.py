"""Freeze one new-target quality screen before any model evaluation."""
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.run_store import canonical_json,digest
root=Path(__file__).resolve().parents[1]
raw=(root/'tmp/data/wikitext2/prepared-pools.json').read_bytes();pools=json.loads(raw)
old=json.loads((root/'pilots/v14/quality-records.json').read_bytes())
if digest(raw)!=old['pool_sha256']:raise ValueError('restored token pool differs')
excluded=set(old['excluded_from_future_confirmation_ids'])
selected=[r for r in pools['evaluation'] if r['id'] not in excluded][:2]
records=[dict(id=r['id'],tokens=r['tokens'][:16]) for r in selected]
payload=dict(schema='fixed-anchor-quality-input-v21',records=records,selection='next two eligible articles in fixed pilot-order-v1 after all prior exclusions',pool_sha256=old['pool_sha256'],prior_exclusions=sorted(excluded),excluded_from_future_confirmation_ids=sorted(excluded|{r['id'] for r in selected}),tokenizer_sha256=old['tokenizer_sha256'],source_files=old['source_files'],scope='30 new development predictions; no population or confirmation claim')
archive=root/'pilots/v21';archive.mkdir(exist_ok=True)
def save(path,payload):
 raw=canonical_json(payload)
 if path.exists() and path.read_bytes()!=raw:raise ValueError('registered file cannot be overwritten')
 path.write_bytes(raw)
save(archive/'quality-records.json',payload)
paths=dict(records='pilots/v10/wikitext2/preflight-records.json',evaluation='pilots/v21/quality-records.json',previous_evaluation='pilots/v14/quality-records.json',anchor='pilots/v20/attempt-002/outputs/anchor.bin',anchor_progress='pilots/v20/attempt-002/outputs/progress.json',anchor_receipt='pilots/v20/attempt-002/worker/result.json',anchor_plan='pilots/v20/attempt-002/plan.json',sequential_model='pilots/v17/attempt-003/outputs/model.bin',sequential_progress='pilots/v17/attempt-003/outputs/progress.json',sequential_receipt='pilots/v17/attempt-003/worker/result.json',sequential_plan='pilots/v17/attempt-003/plan.json',config='tmp/models/distilgpt2/config.json',weights='tmp/models/distilgpt2/model.safetensors')
program=dict(schema='fixed-anchor-quality-program-v21',status='prospectively_registered',attempt_id='attempt-001',scope='explicit_new_target_quality_screen',cpu_seconds=240,wall_seconds=240,record_id='wikitext2:train:article-row-5326',inputs={n:dict(path=p,sha256=digest((root/p).read_bytes())) for n,p in paths.items()},gate=dict(max_aggregate_perplexity_ratio_to_sequential=1.05,max_each_article_ratio=1.20),stop_rule='stop after this single variant; no retuning on the selected records; any partial run is incomplete',numerical_target='NEW corpus-independent nearest-anchor features; not sequential retained-prefix features',evaluation_model_labels=['fixed_anchor_calibrated','archived_sequential_calibrated'],quality_order=[['archived_sequential_calibrated','fixed_anchor_calibrated'],['fixed_anchor_calibrated','archived_sequential_calibrated']],inherited_budget_before=245,no_budget_reset=True,scientific_promotion=False,confirmation=False,repair_timing=False,auxiliary_preparation='reuse previously verified canonical anchor; include its22.458859389s original preparation separately; no free preparation claim')
save(archive/'program.json',program)
print(json.dumps(dict(records=[r['id'] for r in records],predictions=30)))
