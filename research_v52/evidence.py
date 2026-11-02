"""Read-only separation of V51 point success from its preserved box failure."""
from pathlib import Path
from research_v51_postrun.audit import inspect,ROOT,PROGRAM
from research_v48.report import read,require,sha
from research_v51.stage import STAGE_ID,HISTORICAL_CODE
from src.run_store import digest


def validate_v51():
    d=ROOT/'local_runs/real-wide-stage-v51-20261011-a'
    result=inspect(d,ROOT/'campaigns/csis_wide_stage_v51_terminal/accounting.txt')
    require(result['status']=='verified_terminal_stage_failure' and result['failure']['trial']=='compressed',
        'Preserved V51 compressed failure required')
    codes={name:(d/name/'outputs/codes.bin').read_bytes() for name in ('candidate','reference')}
    require(codes['candidate']==codes['reference'] and len(codes['candidate'])==1179648 and
        digest(codes['candidate'])==HISTORICAL_CODE,'Complete point codes differ')
    manifest=read(d/'prepare/outputs/inputs.json');p=read(d/'program.json')
    require(manifest['stage_id']==STAGE_ID and manifest['normalization']==1664 and manifest['total_tokens']==1664 and
        [r['record_id'] for r in manifest['records']]==[r['id'] for r in p['records']] and
        [r['full_traversal_compared'] for r in manifest['records']]==[True]+[False]*12,
        'Source membership or validation differs')
    rows={}
    for name in ('candidate','reference'):
        m=read(d/name/'outputs/completion.json')['measurement']
        require(m['code_sha256']==HISTORICAL_CODE and m['code_count']==2359296 and
            m['source_manifest_sha256']==sha(d/'prepare/outputs/inputs.json') and m['route']=='streamed' and
            m['diagnostics']['diagnostics']['rows']['native_certified_rows']==768 and
            m['diagnostics']['diagnostics']['rows']['fallback_rows']==0,'Point result scope differs')
        if name=='candidate':
            from research_v50.neighbors import source
            require(m['backend']['source_sha256']==digest(source().encode()) and
                m['diagnostics']['diagnostics']['coefficient_build']['source_sha256']==digest(source().encode()),
                'Optimized kernel identity differs')
        else:require(m['backend'] is None,'Historical point unexpectedly selected an override')
        rows[name]=dict(solve_seconds=m['solve_and_write_elapsed_ns']/1e9,
            max_coefficient_radius=m['diagnostics']['diagnostics']['rows']['max_euclidean_coefficient_radius'])
    c=read(d/'compressed/outputs/completion.json')
    require(c['status']=='failed' and c['error_type']=='DispatchRefused' and c['artifacts']=={} and
        not (d/'compressed/outputs/codes.bin').exists(),'Failure scope differs')
    diag=c['refusal_diagnostics']['solver_diagnostics']
    prep=read(d/'prepare/outputs/completion.json')['artifacts']
    sizes={rep:sum(e['bytes'] for n,e in prep.items() if n.startswith(rep)) for rep in ('lossless','compressed40')}
    return dict(schema='wide-stage-separated-evidence-v52',status='verified_point_pair_and_box_refusal',
        prior_audit_status=result['status'],program_sha256=PROGRAM,all_point_code_bytes_equal=True,
        code_sha256=HISTORICAL_CODE,code_count=2359296,point_measurements=rows,
        candidate_over_reference_solve_time=rows['candidate']['solve_seconds']/rows['reference']['solve_seconds'],
        feature_descriptor_bytes=sizes,compressed40_feature_saving=1-sizes['compressed40']/sizes['lossless'],
        failure=dict(error=c['error'],native_certified_rows=diag['native_certified_rows'],
            interval_fallback_rows=diag['fallback_rows'],failed_subset_row=41,
            failed_stage_row=diag['fallback_row_indices'][41],failed_coordinate=1591,
            max_coefficient_radius=diag['max_euclidean_coefficient_radius']),
        charged_cpu_seconds=result['budget']['charged_cpu_seconds'],total_charged_cpu_seconds=sum(result['budget']['charged_cpu_seconds'].values()),
        gate_passed=False,complete_model=False,quality_evaluation=False,confirmation=False,acl_ready=False,
        scope='Single fixed-order adaptive development stage. Actual new point bytes match; historical V45 comparison remains hash-only. Certificate refusal does not prove incorrect codes or a mathematical impossibility.')
