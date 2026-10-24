"""Check unchanged science plus the current asset/disclosure edits; no experiment."""
from pathlib import Path
import datetime,hashlib,json,re
from validation.check_manuscript_numbers_v73 import check as prior
R=Path(__file__).resolve().parents[1]
REPLACED={'unchanged_history_relatedwork','unchanged_limitations_and_bibliography','unchanged_preamble'}

def check(text):
    old=(R/'reports/manuscript_v73.tex').read_text()
    assert hashlib.sha256(old.encode()).hexdigest()=='2fb9e3fe2b682fe2400a34b88fa3a276473112c25869f8545bace54f2022e63b'
    archived=prior(old);assert len(archived)==119 and all(c['passed'] for c in archived)
    checks=[c for c in prior(text) if c['name'] not in REPLACED]
    def add(name,ok):checks.append(dict(name=name,passed=bool(ok)))
    part=lambda s,a,b:s.split(a,1)[1].split(b,1)[0]
    for name,a,b in [('related_work',r'\section{Related work and contribution boundary}',r'\section{Complete-model evidence}'),('limitations',r'\section*{Limitations}',r'\section*{'),('acknowledgements',r'\section*{Acknowledgements}',r'\begin{thebibliography}')]:
        add('unchanged_'+name,part(old,a,b)==part(text,a,b))
    expected=old.split(r'\begin{document}')[0].replace(r'\author{Author and affiliation details pending}',r'\author{Anonymous submission}')
    add('preamble_only_anonymous_author_replaced',expected==text.split(r'\begin{document}')[0])
    add('draft_banner_removed','Working draft:' not in text)
    add('model_parameter_count_is_publisher_approximation','approximately 82 million total parameters' in text)
    add('model_and_dataset_creators_cited',r'\cite{distilgpt2,c4}' in text)
    add('historical_dataset_cited',r'\cite{wikitext}' in text)
    add('language_and_domain','English C4 web text' in text)
    add('source_license_unassigned','no general public\nlicense has been assigned to the project source' in text)
    ethics=part(text,r'\section*{Ethical considerations}',r'\section*{Acknowledgements}')
    for name,phrase in [('no_privacy_guarantee','not a privacy or pretraining-unlearning guarantee'),('no_content_audit_claim','do not claim a\ncontent-level privacy/offensive-text audit'),('no_demographic_characterization','a demographic characterization'),('no_raw_text_release','Raw text, token sequences and model binaries are excluded'),('hashes_not_anonymization','not proof of anonymization')]:
        add(name,phrase in ethics)
    # Every old bibliography entry remains exact; additions do not revise old work.
    # V73 had seven entries; split on the environment without depending on its width.
    old_body=re.split(r'\\begin\{thebibliography\}\{\d+\}',old)[1].split(r'\end{thebibliography}')[0]
    add('all_old_bibliography_entries_unchanged',old_body==re.split(r'\\begin\{thebibliography\}\{\d+\}',text)[1].split(r'\bibitem[Hugging Face')[0])
    return checks
if __name__=='__main__':
    text=(R/'reports/manuscript_v74.tex').read_text();checks=check(text)
    mutations=[('approximately 82 million','approximately 83 million'),('1.005421','1.005422'),('4,419.007 & 368.003','4,419.008 & 368.003'),('do not claim a\ncontent-level','claim a\ncontent-level')]
    probes={a:text.replace(a,b)!=text and any(not c['passed'] for c in check(text.replace(a,b))) for a,b in mutations}
    result=dict(schema='manuscript-selected-checks-v74',checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      status='passed' if all(c['passed'] for c in checks) and all(probes.values()) else 'failed',check_count=len(checks),checks=checks,
      failed_checks=[c['name'] for c in checks if not c['passed']],tamper_probes=probes,
      manuscript_sha256=hashlib.sha256(text.encode()).hexdigest(),replaced_section_identity_checks=sorted(REPLACED),
      archived_v73_checks=119,archived_v72_checks=114,empirical_execution=False,
      scope='Selected numerical transcriptions, unchanged theory/results, and explicit asset/disclosure text; not a proof or legal review.')
    with (R/'validation/v74_manuscript_numbers.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print({k:result[k] for k in ['status','check_count','failed_checks','tamper_probes']});assert result['status']=='passed'
