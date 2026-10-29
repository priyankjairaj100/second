from pathlib import Path
import json,hashlib,zipfile,datetime,io
R=Path('/Users/priyankjairaj/Downloads/ACL/Second');W=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2');O=W/'outputs'
def ident(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def enc(v):return (json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
def put(p,b):
 if p.exists():
  assert p.read_bytes()==b,p
  return
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
def zipped(items,prefix):
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for n,b in sorted(items.items()):
   a=zipfile.ZipInfo(prefix+'/'+n,(2026,10,29,0,0,0));a.compress_type=zipfile.ZIP_DEFLATED;a.external_attr=0o100644<<16;z.writestr(a,b)
 with zipfile.ZipFile(io.BytesIO(out.getvalue())) as z:assert {n[len(prefix)+1:]:z.read(n) for n in z.namelist()}==items
 return out.getvalue()
source=(O/'second-research-draft.tex').read_bytes();pdf=(W/'work/quality-revision-v136/final/second-research-draft.pdf').read_bytes();v=json.loads((R/'validation/v136_manuscript_verification.json').read_bytes());assert ident(source)==v['manuscript'] and ident(pdf)==v['pdf']
v['visual_review']='all eleven final rendered pages inspected; no clipping, overlap or missing content';v['visual_review_date']='2026-10-29';(R/'validation/v136_manuscript_verification.json').write_bytes(enc(v))
put(R/'reports/manuscript_v137.tex',source);put(R/'reports/second_tacl_v137.pdf',pdf);put(O/'second-tacl-review-v137.pdf',pdf)
text='''# Second V137: matched predictive-quality study closed; minimal cold baseline next

29 October 2026. All fourteen saved model roles completed evaluation on the frozen
320-article V124 frame: 4,480 audited article losses. Three of four primary
fixed/sequential guards pass. GPT2 with three retained records fails the unchanged
observed-article limit (1.402707 > 1.20, shard2 line816). Every pooled ratio and
multiplicity-adjusted upper bound passes. No article removal, retuning or new seed.
Fixed targets have 7.7--11.5% lower perplexity than the frozen practical GPTQ
controls, and 11.8--15.4% higher perplexity than their original checkpoints.
Read RESEARCH_DECISION_V136.txt for exact scope and numbers.

V136 jobs16725--16728 all COMPLETED0:0. Slurm rechecked29October09:24UTC; no active
Second job. Other-project jobs16645/16646 remain untouched. Account quota945G of
999G soft. Capacity is observed, not reserved. Distinct allocation CPU for the new
quality/control campaign is9084.405seconds, including failures, excluding launcher
CPU. Sources and full actual receipts are published under pilots/. No experiment
may be inferred from generated tests. All staged/submit/collector attempts through
V136 are consumed. V132 constructors remain FAILED after complete model writes;
V133 independent saved-output audits qualify those binaries without recalibration.
Original runtime sidecars remain missing. V134 pre-loss schema failures remain.

Same open manuscript updated and natively compiled. Independent PDF export,
all-page visual review, numeric/reference checks pass:10content pages,1references,
noappendices,15unchanged verified bibliography entries,three retained proofs.
New versioned review PDF and source/evidence archives are author checkpoints,
not a completed scientific revision or TACL review supplement. Old V123 author
archive is preserved byte-for-byte, including all14 historical scientific ZIPs.

Ordered next work:
1. Minimal source-only cold comparison on all four exact targets. Distinguish the
   three quality-qualified settings from the GPT2/three-record failure boundary.
   research_v135 format has10generated tests; unregistered, not an empirical result.
   Retained tokens are self-contained; immutable references require source access.
   Neither retains features/Grams or reads deleted records during repair.
2. Shape admission and justified operating-range/precision measurements, actual
   margins/replay telemetry, native arithmetic and transaction fault qualification.
3. Repeated timings only after the minimal baseline supports a useful regime;
   clean external-input preparation/deletion/oracle/audit reproduction.
4. Final writing/package and author release/declaration decisions. No submission.

SchedulerPAUSED; no restart, subagents, paid compute, GPU substitution, third-party
messages or repeat jobs. Preserve all caps, exclusions, originals and negative
findings. OneCPU/16GiB; solver caps unchanged; GPT2grid allowance1,327,104.
Before any launch reconcile current Slurm/receipts and freeze a new finite protocol.
'''
put(R/'docs/ACTIVE_SESSION_V137.md',text.encode())
put(R/'handoff/program_v137.json',enc({'schema':'second-handoff-v137','updated_utc':json.loads((R/'handoff/program_v137.json').read_bytes())['updated_utc'],'status':'matched_quality_closed_minimal_cold_next','handoff':'docs/ACTIVE_SESSION_V137.md','scheduler':'PAUSED','primary_quality_gate':{'passed':3,'total':4,'failed':'gpt2_retained3_observed_max_article'},'article_losses':4480,'actual_allocation_cpu_seconds':9084.405,'manuscript':'reports/manuscript_v137.tex','pdf':'reports/second_tacl_v137.pdf','scientific_revision_complete':False,'submission_ready':False}))
header='Current checkpoint 29 October 2026: **V137 matched quality CLOSED: three of four primary guards pass.** Read docs/ACTIVE_SESSION_V137.md and handoff/program_v137.json. All4480 article losses audited. GPT2/three-record observed-article ratio1.402707 fails1.20; preserve boundary. Fixed/GPTQ PPL7.7--11.5%lower under frozen settings. Allqualityjobscomplete;9084.405actual allocationCPUseconds including failures. Same manuscript updated/native compiled/visually verified10+1pages. Minimal source-only baseline next, V135format10tests only. Operating range, native faults, justified repeated timing and clean reproduction pending. SchedulerPAUSED; old attempts consumed. Earlier snapshots below are historical.\n\n'
for rel in ['AGENTS.md','docs/CONTINUOUS_RESEARCH_QUEUE.md']:
 p=R/rel
 if not p.read_text().startswith(header):p.write_text(header+p.read_text())
old=(O/'second-author-review-v123.zip').read_bytes();assert ident(old)['sha256']=='d416395d2cf196f8599cdb55fcfcc5d6fa78294f0150d0317ca31a37c7d6b06a'
with zipfile.ZipFile(io.BytesIO(old)) as z:
 hist={Path(n).name:ident(z.read(n)) for n in z.namelist() if n.endswith('.zip')};assert len(hist)==14
with zipfile.ZipFile(O/'second-tacl-source-v123.zip') as z:style=next(z.read(n) for n in z.namelist() if n.endswith('/tacl2021v1.sty'))
readme=b'''Second TACL revision checkpoint V137. The matched quality study is complete,
with three of four guards passing. This is not the completed empirical revision.
The main source embeds the unchanged official TACL style and fifteen references.
Native and independent compilation and all-page visual checks pass: ten main pages,
one references page, no appendix. No submission was made.

The nested V123 archive is immutable historical evidence, including fourteen
scientific ZIPs. Its old status statements are historical. The separate new
quality-evidence archive includes frozen execution source, protocols, actual
losses, receipts, failures, analysis and accounting. It excludes model weights,
corpus, runtime binaries and credentials. V135 is clearly labeled preparation.
Inventory verification does not constitute clean empirical reproduction.
Minimal cold, range/precision, native fault qualification, justified repeated
timing and clean reproduction remain. Author declarations/release terms remain.
These archives are author-side files, not external TACL review supplements.
'''
items={}
for p in sorted((R/'pilots').iterdir()):
 if any(('v'+str(n)+'-') in p.name for n in range(124,137)):
  for f in sorted(p.rglob('*')):
   if f.is_file() and '__pycache__' not in f.parts:items[str(f.relative_to(R))]=f.read_bytes()
# Merge exactly the bound source inventories, failing on any old-source mutation.
for n,b in list(items.items()):
 if n.endswith('/program.json'):
  p=json.loads(b)
  for rel,h in p.get('sources',{}).items():
   f=R/rel
   if not f.is_file():f=W/'work/practical-gptq-v129'/rel
   raw=f.read_bytes();assert ident(raw)==h,rel
   if rel.startswith('wheels/'):
    items['external_dependency_bindings/'+Path(rel).name+'.json']=enc(h)
    continue
   key='execution_sources/'+rel
   if key in items:assert items[key]==raw
   items[key]=raw
for rel in ['docs/RESEARCH_DECISION_V136.txt','docs/ACTIVE_SESSION_V137.md','handoff/program_v137.json','validation/v136_manuscript_verification.json']:
 items[rel]=(R/rel).read_bytes()
for directory in ['research_v135','reporting_v136']:
 for f in (R/directory).rglob('*'):
  if f.is_file() and '__pycache__' not in f.parts:items[('unregistered_preparation/' if directory=='research_v135' else '')+str(f.relative_to(R))]=f.read_bytes()
items['README.txt']=readme;items['MANIFEST.json']=enc({n:ident(b) for n,b in items.items()})
evidence=zipped(items,'quality-evidence-v137')
src={'main.tex':source,'tacl2021v1.sty':style,'README.txt':readme,'ACTIVE_SESSION_V137.md':text.encode(),'RESEARCH_DECISION_V136.txt':(R/'docs/RESEARCH_DECISION_V136.txt').read_bytes(),'REFERENCE_AUDIT.json':(R/'validation/v123_reference_audit.json').read_bytes()};src['MANIFEST.json']=enc({n:ident(b) for n,b in src.items()})
srczip=zipped(src,'second-tacl-source-v137');put(O/'second-tacl-source-v137.zip',srczip)
author={'second-tacl-review-v137.pdf':pdf,'second-research-draft.tex':source,'README.txt':readme,'second-author-review-v123.zip':old,'quality-evidence-v137.zip':evidence,'HISTORICAL_COMPONENTS.json':enc(hist),'ACTIVE_SESSION_V137.md':text.encode()};author['MANIFEST.json']=enc({n:ident(b) for n,b in author.items()})
authzip=zipped(author,'second-author-review-v137');put(O/'second-author-review-v137.zip',authzip)
report={'schema':'second-packages-v137','pdf':ident(pdf),'source':ident(source),'source_zip':ident(srczip),'author_zip':ident(authzip),'new_evidence_zip':ident(evidence),'new_evidence_files':len(items),'unchanged_nested_historical_components':hist,'old_v123_archive':ident(old),'byte_roundtrip_verified':True,'clean_empirical_reproduction':False,'submission_ready':False};put(R/'validation/v137_packages.json',enc(report));print(json.dumps({k:v for k,v in report.items() if k!='unchanged_nested_historical_components'},indent=2))
