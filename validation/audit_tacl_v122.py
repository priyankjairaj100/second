from pathlib import Path
import json,re,hashlib,csv,math
from fractions import Fraction as F
from pypdf import PdfReader
import pdfplumber
W=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2');D=W/'work/tacl-review-response-v122';R=Path(__file__).resolve().parents[1]
M=W/'outputs/second-research-draft.tex';P=D/'final/second-research-draft.pdf'
ident=lambda b:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
s=M.read_text();body=s[s.index('\\title{Lossy Calibration Archives'):s.index('\\begin{thebibliography}')]
style=s.split('\\begin{filecontents*}[overwrite]{tacl2021v1.sty}\n',1)[1].split('\n\\end{filecontents*}',1)[0]
assert style==(D/'tacl2021v1.sty').read_text()
assert '\\appendix' not in body and '\\section*{Acknowledg' not in body
assert '\u2014' not in body and '---' not in body
assert '\\begin{proof}' in body and body.count('\\begin{proof}')==3
assert all(x not in body.lower() for x in ['priyank','poonam','/users/','github.com/priyank'])
labels=re.findall(r'\\label\{([^}]+)\}',s);assert len(labels)==len(set(labels))
refs=re.findall(r'\\(?:eqref|ref)\{([^}]+)\}',body);assert set(refs)<=set(labels)
cites=set(k.strip() for part in re.findall(r'\\cite\w*\{([^}]+)\}',body) for k in part.split(','))
bib=set(re.findall(r'\\bibitem\[[^\n]+?\]\{([^}]+)\}',s));assert cites==bib
native=json.loads((R/'validation/v122_native_compile.json').read_text())
assert not native.get('isError')
assert any(json.loads(c['text']).get('kind')=='success' for c in native['content'] if c['type']=='text')
assert len(bib)==15
refaudit=json.loads((R/'validation/v122_reference_audit.json').read_text())
assert {e['key'] for e in refaudit['references']}==bib
assert 'Alon Helvits' in s and 'Helvitz' not in s
assert len(list((D/'final/render').glob('page-*.png')))==11
log=(D/'final/second-research-draft.log').read_text()
assert 'Overfull' not in log and not re.search(r'(?:Reference|Citation).*undefined',log)
aux=(D/'final/second-research-draft.aux').read_text()
assert re.search(r'\\newlabel\{page:main-end\}\{\{10\}\{10\}',aux)
pdf=PdfReader(P);assert len(pdf.pages)==11
assert all(abs(float(pg.mediabox.width)-595.28)<1 and abs(float(pg.mediabox.height)-841.89)<1 for pg in pdf.pages)
assert not pdf.metadata.get('/Author')
assert 'References' in pdf.pages[10].extract_text() and all('References\n' not in pdf.pages[i].extract_text() for i in range(10))
assert 'Anonymous TACL submission' in pdf.pages[0].extract_text()
assert 'Table 1:' not in pdf.pages[0].extract_text()
# Verify embedded font programs, including descendant CID fonts if present.
fonts={}
for pg in pdf.pages:
 for font in pg['/Resources']['/Font'].get_object().values():
  f=font.get_object()
  for ff in f.get('/DescendantFonts',[f]):
   ff=ff.get_object();desc=ff.get('/FontDescriptor');assert desc
   desc=desc.get_object();assert any(k in desc for k in ['/FontFile','/FontFile2','/FontFile3'])
   fonts[str(ff.get('/BaseFont'))]=True
# Every citation's intended destination must occur in the actual final PDF.
uris={str(a.get_object().get('/A',{}).get('/URI','')) for pg in pdf.pages for a in pg.get('/Annots',[])}
for e in refaudit['references']:
 for url in e['manuscript_links']:assert url in uris,url
# Exact toy interval enclosure; mathematical illustration only.
lo=F(9801,10000)/F(20201,10000);hi=F(10201,10000)/F(19801,10000)
assert F(59,100)<F(2,5)*(1+lo)<=F(2,5)*(1+hi)<F(61,100)
assert F(2,5)<F(1,2)<F(2,5)*(1+F(1,2))
# Table 1: every time, storage and access value at the proper arm/endpoint.
e16=json.loads((R/'reports/review-service-v70/E16_comparison_and_costs.json').read_bytes())
armnames={'cached':'Cached lossless','modern':'Modern lossless','cold':'Cold reconstruction','hybrid':'Hybrid exact Gram','compressed':'Compressed'}
block=body[body.index('Records & Service arm'):body.index('\\label{tab:service}')]
for row in e16['rows']:
 arm=armnames[row['arm']]
 expected=f"{arm} & {row['request_elapsed_ns']/1e9:,.3f} & {row['live_state_bytes']/1e6:.3f} & {row['checkpoint_inclusive_bytes']/1e6:.3f} & {row['source_stage_record_pairs']}"
 assert expected in block,expected
# Table 2: preserve all eight request values.
e18=json.loads((R/'reports/review-optimization-v98/results.json').read_bytes())
block=body[body.index('Records & Archive'):body.index('\\label{tab:optimization}')]
for row in e18['rows']:assert f"{row['host_elapsed_ns']/1e9:,.3f}" in block
# Table 3 and 4: exact mapping from all sixteen matched rows.
rows=list(csv.DictReader((R/'pilots/matched-closure-v119-20261027/v119-closed-report/all-requests.tsv').open(),delimiter='\t'))
by={(r['profile'],int(r['step']),r['cell']):r for r in rows}
block=body[body.index('Checkpoint & Records & Ref. comp.'):body.index('\\label{tab:matched}')]
for p in ['distilgpt2','gpt2']:
 for st in [1,2]:
  rr=[by[p,st,c] for c in ['reference_compressed','optimized_compressed','reference_modern','optimized_modern']]
  fields=' & '.join(f"{int(r['host_elapsed_ns'])/1e9:,.3f}" for r in rr)
  ratio=int(rr[1]['host_elapsed_ns'])/int(rr[3]['host_elapsed_ns'])
  assert fields+f' & {ratio:.4f}' in block
  for field in ['live_state_bytes','checkpoint_inclusive_bytes']:
   saving=100*(1-int(rr[1][field])/int(rr[3][field]));assert f'{saving:.2f}' in body
q=json.loads((R/'reports/review-quality-v72/E17_statistics.json').read_bytes())
for endpoint in q['endpoints'].values():
 vals=[endpoint[k] for k in ['pooled_ratio','one_sided_97_5_upper','maximum_article_ratio']]
 assert ' & '.join(f'{v:.6f}' for v in vals) in body
# The new generated checks are separate from empirical observations.
generated=json.loads((R/'validation/v122_generated_checks.json').read_text())
assert generated['enumerated_feature_realizations']==39366
assert generated['feature_boxes']==486 and generated['reference_primitive_exact_containment_checks']==316
assert generated['nonfinite_cases_requiring_refusal']==26 and not generated['new_empirical_execution']
assert all(v in body for v in ['6.89','10.089','6.873','10.124'])
# Frozen originals: resolve existing repository or campaign source counterpart only.
old=json.loads((R/'validation/v119_final_verification.json').read_bytes());checks={}
for name,expected in old['original_source_inventory'].items():
 matches=[p for p in [R/name,W/'work/second-speed-campaign'/name] if p.is_file() and ident(p.read_bytes())==expected]
 assert matches,name
 checks[name]=expected
bounds=[]
with pdfplumber.open(P) as doc:
 for i,pg in enumerate(doc.pages):
  bb=[]
  for a,b in [(72,292),(305,525)]:
   chars=[c for c in pg.chars if a<c['x0']<b and 80<c['top']<780]
   bb.append(max((c['bottom'] for c in chars),default=None))
  bounds.append(dict(page=i+1,column_bottom_points=bb))
result=dict(schema='second-tacl-manuscript-v122',manuscript=ident(M.read_bytes()),pdf=ident(P.read_bytes()),
 title='Lossy Calibration Archives for Exact Model Repair',content_pages=10,reference_pages=1,total_pages=11,
 appendices=0,style=ident((D/'tacl2021v1.sty').read_bytes()),official_style_unmodified=True,
 labels=len(labels),citation_keys=len(cites),all_references_resolved=True,overfull_boxes=0,
 first_page_no_tables_or_figures=True,pdf_author_metadata_empty=True,embedded_fonts=sorted(fonts),
 source_author_identifier_scan_pass=True,no_em_dashes=True,core_proofs_in_main=3,
 baseline_rows_checked=10,optimization_times_checked=8,matched_times_checked=16,quality_endpoints_checked=2,
 original_source_files_verified=len(checks),original_research_sources_changed=False,
 toy_exact_rational_check=True,toy_is_not_empirical_evidence=True,new_empirical_execution=False,
 native_compile_success=True,native_compiler_message='The current source compiled successfully with the desktop editor\'s compiler.',
 export_engine='Official portable Tectonic 0.17.0; independent PDF export of the same source',
 column_bottoms=bounds,visual_review_status='passed_all_11_pages',
 rendered_page_hashes={f.name:ident(f.read_bytes()) for f in sorted((D/'final/render').glob('page-*.png'))},
 full_indirect_anonymity_verified=False,author_attestations_completed=False,submission_performed=False)
(R/'validation/v122_manuscript_checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['content_pages','reference_pages','overfull_boxes','citation_keys','original_source_files_verified','pdf']},indent=2))
