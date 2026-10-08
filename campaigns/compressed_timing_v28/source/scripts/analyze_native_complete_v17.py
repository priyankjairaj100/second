"""Validate archived v17 transactions. Never launches research workers.

Missing ignored binaries permit digest comparison only. Existing bytes are checked.
"""
import json,os,subprocess,sys,time,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from src.run_store import atomic_write,canonical_json,digest
from src.pilot_budget import inherited_allowance
from src.experiment_inventory import source_hashes
archive=root/'pilots/v17'
program_raw=(archive/'complete-program.json').read_bytes();program=json.loads(program_raw)
reference_original=json.loads((root/'pilots/v15/attempt-001/outputs/progress.json').read_bytes())
reference_retained=json.loads((root/'pilots/v15/attempt-002/outputs/progress.json').read_bytes())
source=json.loads((archive/'attempt-002/plan.json').read_bytes())['source_sha256']
rows=[]
import argparse
parser=argparse.ArgumentParser(description='Read-only validation of completed v17 evidence.')
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if args.output.exists():raise ValueError('Output exists; choose a new analysis path.')
def check(slot,wait=False):
 attempt=archive/slot['id']
 while True:
  path=attempt/'worker/result.json'
  receipt=json.loads(path.read_bytes()) if path.exists() else {}
  if receipt.get('budget_debit',{}).get('state')=='settled':break
  if not wait:raise RuntimeError('unsettled worker')
  time.sleep(1)
 if receipt['outcome']['status']!='complete':raise RuntimeError('worker failed: '+slot['id'])
 plan_raw=(attempt/'plan.json').read_bytes();plan=json.loads(plan_raw)
 result=json.loads((attempt/'outputs/progress.json').read_bytes())
 if source_hashes(attempt/'source')!=plan['source_sha256']:raise RuntimeError('snapshot changed')
 if digest((attempt/'protocol.json').read_bytes())!=plan['protocol_sha256']:raise RuntimeError('protocol changed')
 if (attempt/'complete-program.json').read_bytes()!=program_raw:raise RuntimeError('program copy changed')
 if plan['method']!=slot['method'] or plan['solver_backend']!=slot['backend']:raise RuntimeError('slot changed')
 if (plan['source_sha256']!=source or plan['complete_program_sha256']!=digest(program_raw)
   or receipt['worker_identity']['plan_sha256']!=digest(plan_raw)
   or result['plan_sha256']!=digest(plan_raw) or result['status']!='complete'):
  raise RuntimeError('source, plan, or status mismatch')
 expected=reference_original if not slot['delete'] else reference_retained
 for name in ('target_sha256','model_sha256','model_artifact'):
  if result[name]!=expected[name]:raise RuntimeError('exact reference mismatch: '+name)
 if result['complete_state'] and result['state_artifact']!=expected['state_artifact']:
  raise RuntimeError('canonical state mismatch')
 verified_bytes=True
 for field in ('model_artifact','state_artifact'):
  if field in result:
   artifact=result[field];path=attempt/'outputs'/artifact['file']
   if not path.exists():
    verified_bytes=False
    continue
   with path.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
   if path.stat().st_size!=artifact['bytes'] or actual!=artifact['sha256']:raise RuntimeError('output bytes changed')
 row=dict(artifact_bytes_verified=verified_bytes,id=slot['id'],method=slot['method'],backend=slot['backend'],initial_model=slot.get('initial_model'),
  worker_elapsed_ns=receipt['outcome']['elapsed_wall_ns'],charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],
  reference_model_equal=True,reference_state_equal=True if result['complete_state'] else None,
  model_sha256=result['model_sha256'],target_sha256=result['target_sha256'],diagnostics=result['diagnostics'])
 rows.append(row)
 print(json.dumps({k:v for k,v in row.items() if k!='diagnostics'}),flush=True)
for slot in program['sequence']:
 check(slot)
used,left=inherited_allowance(root)
output=dict(schema='native-complete-analysis-v17',program_sha256=digest(program_raw),status='complete',
 scientific_promotion=False,confirmation=False,timing_scope='bounded child worker; source snapshot/controller work excluded',
 rows=rows,worker_cpu_debit_seconds=used,worker_cpu_remaining_seconds=left,
 repair_over_warm_elapsed=rows[1]['worker_elapsed_ns']/rows[4]['worker_elapsed_ns'],
 repair_over_cold_elapsed=rows[1]['worker_elapsed_ns']/rows[2]['worker_elapsed_ns'],
 repair_over_direct_elapsed=rows[1]['worker_elapsed_ns']/rows[5]['worker_elapsed_ns'],
 reference_over_native_cold_elapsed=rows[3]['worker_elapsed_ns']/rows[2]['worker_elapsed_ns'])
atomic_write(args.output,canonical_json(output))
