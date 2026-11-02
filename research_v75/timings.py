"""Read-only V67 receipt attribution. Nested timers are NOT additive totals."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parent
REPO = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT.parent
ARCHIVE = REPO/'campaigns/csis_v67_terminal_metadata_20261018_a.tar.gz'

def main():
    result = dict(scope='Descriptive reanalysis of one existing observation per arm/endpoint; no new experiment',
        archive=str(ARCHIVE), archive_sha256=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        reporting_commit=subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'],text=True).strip(),
        observations={})
    with tarfile.open(ARCHIVE) as t:
        for arm in ('cached', 'modern', 'compressed', 'hybrid', 'cold'):
            for endpoint in (1, 2):
                name=f'{arm}-{endpoint}'
                receipt=json.load(t.extractfile(name+'/outputs/completion.json'))['request']
                timing=receipt['timing']
                row=dict(request_s=receipt['request_elapsed_ns']/1e9,
                    predecessor_s=0 if arm=='cold' else timing['predecessor_validation_ns']/1e9,
                    serialization_s=timing['serialization_ns']/1e9,
                    extraction_s=timing['source_extraction_ns']/1e9,
                    stages_s=sum(s['elapsed_ns'] for s in timing['stages'])/1e9,
                    groups={})
                for stage in timing['stages']:
                    key=str(stage['admission']['width'])+'-'+stage['route']
                    g=row['groups'].setdefault(key,dict(count=0,elapsed_s=0,
                        gram_including_decode_s=0, coefficient_s=0, rows_s=0,
                        row_fallback_s=0, row_fallback_count=0,
                        token_coefficient_native_s=0, token_feature_bounds_s=0))
                    g['count']+=1
                    g['elapsed_s']+=stage['elapsed_ns']/1e9
                    solver=stage['solver']
                    if stage['route']=='streamed':
                        d=solver['diagnostics']
                        g['gram_including_decode_s']+=d['gram_elapsed_ns']/1e9
                        g['coefficient_s']+=d['coefficient_elapsed_ns']/1e9
                        g['rows_s']+=d['rows']['row_elapsed_ns']/1e9
                        g['row_fallback_s']+=d['rows']['fallback_elapsed_ns']/1e9
                        g['row_fallback_count']+=d['rows']['fallback_rows']
                    elif stage['route']=='token':
                        d=solver if arm=='compressed' else solver['solver_diagnostics']
                        g['coefficient_s']+=d['coefficient_elapsed_ns']/1e9
                        evidence=d['coefficient_evidence'] if arm=='compressed' else d['coefficient_verification']
                        g['token_coefficient_native_s']+=evidence['native_elapsed_ns']/1e9
                        g['token_feature_bounds_s']+=d.get('feature_bounds_elapsed_ns',0)/1e9
                result['observations'][name]=row
    result['comparisons']={}
    for endpoint in (1,2):
        c=result['observations'][f'compressed-{endpoint}']
        m=result['observations'][f'modern-{endpoint}']
        gap=c['request_s']-m['request_s']
        validation_gap=c['predecessor_s']+c['serialization_s']-m['predecessor_s']-m['serialization_s']
        result['comparisons'][str(endpoint)]=dict(request_gap_s=gap,
            validation_serialization_gap_s=validation_gap,
            fraction_gap_in_validation_serialization=validation_gap/gap,
            compressed_request_even_if_its_validation_and_serialization_were_free_s=
                c['request_s']-c['predecessor_s']-c['serialization_s'],
            modern_observed_request_s=m['request_s'])
    (ROOT/'timing-attribution.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['comparisons'],indent=2))

if __name__=='__main__':
    main()
