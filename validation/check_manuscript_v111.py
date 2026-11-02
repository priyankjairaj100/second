"""Source structure check after successful native compile; not rendered-layout QA."""
from pathlib import Path
import datetime,re,json
from validation.build_review_source_v69 import info,enc
R=Path(__file__).resolve().parents[1]
W=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2')
source=(W/'outputs/second-research-draft.tex').read_bytes();text=source.decode();body=text.split('\\begin{document}',1)[1]
labels=re.findall(r'\\label\{([^}]+)\}',body);refs=re.findall(r'\\(?:ref|eqref|pageref)\{([^}]+)\}',body)
bib=re.findall(r'\\bibitem(?:\[[^]]*\])?\{([^}]+)\}',body)
cites=[k for keys in re.findall(r'\\cite\w*\{([^}]+)\}',body) for k in keys.split(',')]
assert len(labels)==len(set(labels)) and not(set(refs)-set(labels)) and not(set(cites)-set(bib))
assert text.count('\\evidence{E19}')==1 and 'full-model transfer evidence' in text
(R/'reports/manuscript_v111.tex').write_bytes(source)
report=dict(schema='manuscript-checks-v111',captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),manuscript=info(source),
    native_compile_success=True,native_compile=dict(tool='compile_latex_document',kind='success',source=info(source)),
    labels=len(labels),bibliography_keys=bib,unresolved_citations=[],unresolved_references=[],rendered_layout_verified=False,
    full_model_transfer_claim=False,new_scientific_scope='V104 failed screen and V110 selected-stage-only diagnostic')
(R/'validation/v111_manuscript_checks.json').write_bytes(enc(report));print(json.dumps(report,sort_keys=True))
