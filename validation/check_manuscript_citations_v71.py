"""Static citation/link structure for the unchanged current manuscript.

Primary-source and proof-scope reviews are recorded separately; syntax checks do
not prove bibliographic facts, novelty, rendered formatting or external results.
"""
from pathlib import Path
import datetime
import hashlib
import json
import re

R = Path(__file__).resolve().parents[1]
M = R / 'reports/manuscript_v70.tex'
EXPECTED = '65d02e6048156fc1d2270368d8fa7efae192511f79e5aa9d00fc3820a772db0a'

def check():
    raw = M.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == EXPECTED
    text = raw.decode().split('\\begin{document}', 1)[1]
    text = re.sub(r'(?<!\\)%[^\n]*', '', text)
    bibliography = re.findall(r'\\bibitem\[([^\]]+)\]\{([^}]+)\}', text)
    keys = [key for label, key in bibliography]
    assert keys == ['gptq', 'ginart', 'medu', 'qss', 'exactfun', 'qebverif', 'execcert']
    assert len(keys) == len(set(keys)) == 7
    citations = re.findall(r'\\cite(?:t|p|yearpar)?(?:\[[^\]]*\])*\{([^}]+)\}', text)
    cited = {k.strip() for group in citations for k in group.split(',')}
    assert cited == set(keys)
    labels = re.findall(r'\\label\{([^}]+)\}', text)
    refs = re.findall(r'\\(?:eqref|ref|pageref|getpagerefnumber)\{([^}]+)\}', text)
    assert len(labels) == len(set(labels))
    assert set(refs) <= set(labels)
    links = re.findall(r'\\href\{([^}]+)\}', text.split('\\begin{thebibliography}', 1)[1])
    assert len(links) == 8 and all(link.startswith('https://') for link in links)
    return dict(schema='current-manuscript-citation-structure-v71',
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        manuscript=dict(path=str(M.relative_to(R)), bytes=len(raw), sha256=EXPECTED),
        bibliography_keys=keys, citation_groups=len(citations), missing_citations=[], unused_bibliography_keys=[],
        labels=len(labels), reference_uses=len(refs), unresolved_references=[], bibliography_urls=links,
        native_compile_repeated=False, rendered_reference_format_verified=False,
        bibliographic_metadata_verified_by_this_script=False, proof_attribution_verified_by_this_script=False,
        manuscript_edited=False, empirical_result=False)

if __name__ == '__main__':
    result=check()
    with (R / 'validation/v71_manuscript_citation_structure.json').open('x') as output:
        json.dump(result,output,indent=2,sort_keys=True);output.write('\n')
    print(json.dumps({k: result[k] for k in ('bibliography_keys','citation_groups','labels','reference_uses','missing_citations','unresolved_references')}))
