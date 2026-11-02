"""Preserve historical numerical checks; update the abstract to actual V67 evidence."""
from pathlib import Path
from decimal import Decimal
import json,hashlib,datetime,copy
from validation import check_manuscript_numbers_v69 as old
R=Path(__file__).resolve().parents[1]
def norm(s):return ' '.join(s.split())
def check(text):
 evidence={k:json.loads((R/n).read_bytes()) for k,n in old.INPUTS.items()}
 checks=old.check(text,evidence)
 # V70 replaces exactly one old abstract claim with the current modern-control
 # comparison. All historical body/table/adverse-result checks remain unchanged.
 assert sum(c['name']=='abstract_service_tradeoff' for c in checks)==1
 checks=[c for c in checks if c['name']!='abstract_service_tradeoff']
 r=json.loads((R/'validation/v67_terminal_reconciliation_20261018_a.json').read_bytes())
 assert r['status']=='verified_terminal_receipt_metadata' and r['complete_state_comparison_claims']==10
 rows={(x['arm'],x['step']):x for x in r['comparison_rows']}
 fmt=lambda x:format(x,'.2f')
 def percent(arm,key,saving=False):
  out=[]
  for step in [1,2]:
   x=Decimal(rows['compressed',step][key])/rows[arm,step][key]
   out.append(fmt(100*(1-x if saving else x-1)))
  return out
 def passage(name,s,scope):checks.append(dict(name=name,expected_text=s,passed=norm(s) in norm(scope),sources=['v67_terminal_reconciliation_20261018_a.json']))
 abstract=text.split(r'\begin{abstract}')[1].split(r'\end{abstract}')[0]
 body=text.split(r'\paragraph{Disjoint-root complete service (V67).}')[1].split(r'\paragraph{Research decision.}')[0]
 cs=percent('cached','live_state_bytes',True);ct=percent('cached','request_elapsed_ns');ms=percent('modern','live_state_bytes',True);mt=percent('modern','request_elapsed_ns');md=percent('modern','checkpoint_inclusive_bytes',True)
 passage('abstract_modern_storage',f'compression saves {ms[0]}\\% and {ms[1]}\\% of live state against a Zstandard-augmented lossless cache',abstract)
 passage('abstract_modern_latency',f'requests take {mt[0]}\\% and {mt[1]}\\% longer',abstract)
 passage('disjoint_cached_tradeoff',f'compression saves {cs[0]}\\% and {cs[1]}\\% of live state but requests take {ct[0]}\\% and {ct[1]}\\% longer',body)
 passage('disjoint_modern_tradeoff',f'savings are {ms[0]}\\% and {ms[1]}\\%, with requests {mt[0]}\\% and {mt[1]}\\% longer',body)
 passage('disjoint_deployment_savings',f'savings fall to {md[0]}\\% and {md[1]}\\%',body)
 passage('disjoint_installation',f"installation occupies {r['added_codec_installation_bytes']:,} bytes",body)
 passage('disjoint_worker_cpu',f"workers charge {r['numerical_worker_charged_cpu_seconds']:,} CPU seconds",body)
 passage('disjoint_scheduler_cpu',f"consume {Decimal(r['scheduler_allocation_cpu_seconds']):,.3f} CPU seconds",body)
 passage('disjoint_fallback_rows',f"fallbacks on {rows['compressed',1]['numerical_solver_fallback_rows']} and {rows['compressed',2]['numerical_solver_fallback_rows']} rows",body)
 passage('untouched_quality_not_inferred','Quality on this new root is not yet known.',body)
 checks.append(dict(name='hybrid_access_and_tradeoff_direction',passed=all(rows['compressed',i]['source_stage_record_pairs']==0 for i in [1,2]) and rows['hybrid',1]['source_stage_record_pairs']>0 and all(rows['hybrid',1][k]<rows['compressed',1][k] for k in ['live_state_bytes','request_elapsed_ns']) and all(rows['hybrid',2][k]>rows['compressed',2][k] for k in ['live_state_bytes','request_elapsed_ns']),sources=['v67_terminal_reconciliation_20261018_a.json']))
 return checks
if __name__=='__main__':
 p=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2/outputs/second-research-draft.tex');text=p.read_text();checks=check(text)
 probes={}
 for a,b in [('9.24\\%','9.25\\%'),('50.48\\%','50.47\\%'),('47,767','47,768'),('4,083.951 & 368.133','4,083.950 & 368.133')]:
  bad=text.replace(a,b);probes[a]=bad!=text and any(not x['passed'] for x in check(bad))
 result=dict(status='passed' if all(x['passed'] for x in checks) and all(probes.values()) else 'failed',check_count=len(checks),checks=checks,failed_checks=[x['name'] for x in checks if not x['passed']],tamper_probes=probes,manuscript_sha256=hashlib.sha256(text.encode()).hexdigest(),local_numerical_execution=False,legacy_abstract_check_replaced_explicitly=True)
 with (R/'validation/v70_manuscript_numbers.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True)
 print(json.dumps({k:result[k] for k in ['status','check_count','failed_checks','tamper_probes']}));assert result['status']=='passed'
