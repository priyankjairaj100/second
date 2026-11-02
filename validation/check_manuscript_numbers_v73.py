"""Check the concise current paper and keep archived history checks separate.

The V61 table and detailed development costs were removed from the main text,
not from evidence. Their exact checks still run on the immutable V72 snapshot.
New V67 table values are checked directly against the audited comparison rows.
This performs no calibration, inference, bootstrap or original binary audit.
"""
from pathlib import Path
from decimal import Decimal
import datetime, hashlib, json, re
from validation.check_manuscript_numbers_v72 import check as prior
R=Path(__file__).resolve().parents[1]
RETIRED={
 'eight_table_rows_exact_order_labels_units_and_rounding',
 *[f'table_row_{r}_column_{c}' for r in range(1,9) for c in range(3,6)],
 'nearest_anchor_storage_and_latency','nearest_anchor_worker_and_failed_costs',
 'full_precision_and_nearest_ppl','quality_cpu_charge','gpu_cpu_charge',
 'gpu_pair_count','gpu_maximum_deviation','adaptive_article_directions_text',
 'adaptive_over_nearest_anchor_ratio','adaptive_constructor_and_transaction',
 'adaptive_historical_parity_text','service_checkpoint_inclusive_savings',
 'attributed_two_request_costs','numerical_worker_debits','recovery_cpu_cost',
 'recovery_walls','modern_exact_live_bytes','compression_vs_modern',
 'codec_plus_source_footprint',
}

def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def check(text):
    old=(R/'reports/manuscript_v72.tex').read_text()
    assert info(old.encode())['sha256']=='32af6235cb6ab812dd91f08b2d0bf9b23e0ea6a6e71be85686e5a390c13acafd'
    historical=prior(old)
    assert len(historical)==114 and all(c['passed'] for c in historical)
    assert RETIRED<=set(c['name'] for c in historical)
    allprior=prior(text)
    checks=[c for c in allprior if c['name'] not in RETIRED]
    def add(name,passed,**kwargs):checks.append(dict(name=name,passed=bool(passed),**kwargs))
    audit=json.loads((R/'validation/v67_terminal_reconciliation_20261018_a.json').read_bytes())
    assert audit['status']=='verified_terminal_receipt_metadata' and audit['complete_state_comparison_claims']==10
    values={(v['arm'],v['step']):v for v in audit['comparison_rows']}
    names=[('cached','Cached lossless'),('modern','Modern lossless'),('cold','Cold reconstruction'),('hybrid','Hybrid exact Gram'),('compressed','Compressed 48-bit')]
    blocks=re.findall(r'\\begin\{table\*\}(.*?)\\end\{table\*\}',text,re.S)
    tables=[b for b in blocks if r'\label{tab:v67}' in b];observed=[];expected=[]
    if len(tables)==1:
        for line in tables[0].splitlines():
            if '&' in line and re.search(r'\d',line):
                observed.append([v.strip().removesuffix(r'\\').strip() for v in line.split('&')])
    for step in (1,2):
        for i,(arm,label) in enumerate(names):
            x=values[arm,step]
            expected.append([str(x['retained_records']) if i==0 else '',label,
                f"{Decimal(x['request_elapsed_ns'])/10**9:,.3f}",
                f"{Decimal(x['live_state_bytes'])/10**6:,.3f}",
                f"{Decimal(x['checkpoint_inclusive_bytes'])/10**6:,.3f}",str(x['source_stage_record_pairs'])])
    add('v67_ten_rows_order_labels_and_all_values',observed==expected,source='validation/v67_terminal_reconciliation_20261018_a.json')
    for i,row in enumerate(expected):
        for j in range(2,6):
            seen=observed[i][j] if i<len(observed) and j<len(observed[i]) else None
            add(f'v67_row_{i+1}_column_{j+1}',seen==row[j],expected=row[j],observed=seen)
    # Editorial shortening cannot change theory, target, quality, bibliographic
    # statements, or ACL style. The changed areas are identified explicitly.
    for name,start,end in [
        ('abstract',r'\begin{abstract}',r'\end{abstract}'),
        ('target_method_proofs_cost',r'\section{An explicit reconstruction target}',r'\section{Development history}'),
        ('history_relatedwork',r'\section{Development history}',r'\section{Complete-model evidence}'),
        ('untouched_quality_and_limits',r'\paragraph{Untouched two-endpoint quality (V71/V72).}',r'\section{Reproducibility and evidence status}'),
        ('limitations_and_bibliography',r'\label{page:main-end}',r'\end{document}')]:
        block=lambda s:s.split(start,1)[1].split(end,1)[0]
        add('unchanged_'+name,block(old)==block(text))
    add('unchanged_preamble',old.split(r'\begin{document}')[0]==text.split(r'\begin{document}')[0])
    add('no_appendix',r'\appendix' not in text.split(r'\begin{document}',1)[1])
    add('old_table_not_mislabeled_current',r'\label{tab:v61}' not in text)
    return checks

if __name__=='__main__':
    text=(R/'reports/manuscript_v73.tex').read_text();checks=check(text)
    pairs=[('4,419.007 & 368.003','4,419.008 & 368.003'),('4,921.935 & 318.918 & 671.743 & 24','4,921.935 & 318.918 & 671.743 & 0'),('1.005421','1.005422'),('7,588.049','7,588.048'),('9.24\\%','9.25\\%'),('but the overall gate fails.','but the overall gate passes.')]
    probes={a:text.replace(a,b)!=text and any(not c['passed'] for c in check(text.replace(a,b))) for a,b in pairs}
    result=dict(schema='manuscript-number-check-v73',checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='passed' if all(c['passed'] for c in checks) and all(probes.values()) else 'failed',
        manuscript=info(text.encode()),check_count=len(checks),checks=checks,failed_checks=[c['name'] for c in checks if not c['passed']],
        tamper_probes=probes,archived_v72_checks_passed=114,
        checks_retired_from_current_text_only=sorted(RETIRED),retirement_reason='Detailed historical passages/table condensed; full E12-E15 evidence and immutable V72 snapshot remain. Current V67 table replaces V61 table.',
        historical_snapshot=info((R/'reports/manuscript_v72.tex').read_bytes()),
        current_service_rows=10,current_service_numeric_cells=40,
        empirical_execution=False,scope='Selected transcriptions, table arithmetic and unchanged formal/quality text; not every numerical claim, a proof review or independent empirical replication.')
    with (R/'validation/v73_manuscript_numbers.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print({k:result[k] for k in ['status','check_count','failed_checks','tamper_probes']});assert result['status']=='passed'
