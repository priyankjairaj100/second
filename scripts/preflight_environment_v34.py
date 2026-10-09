#!/usr/bin/env python3
"""Read-only admission screen for the unchanged finite numerical environment.

This checks the actual decoder and finite-primitive runtime manifests before
any expensive checkpoint load or worker reservation. It never supplies missing
/proc data, changes a runtime contract, starts a worker, or writes a ledger.
A passing screen does not authorize retrying a failed registered trial.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

# Imported modules must not create cache files during this read-only screen.
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def preflight(campaign=None):
    checks=[]
    def check(name,operation):
        try:
            value=operation()
            checks.append({'check':name,'status':'passed','evidence':value})
            return value
        except (OSError,ValueError,RuntimeError,ImportError,KeyError,TypeError,AttributeError) as exc:
            checks.append({'check':name,'status':'blocked','error_type':type(exc).__name__,'reason':str(exc)})
            return None
    def readable(path):
        raw=Path(path).read_bytes()
        if not raw:raise ValueError('required runtime file is empty: '+path)
        return {'path':path,'readable':True,'bytes':len(raw)}
    # Enumerate both files even if the first full manifest fails immediately.
    check('proc_self_maps_readable',lambda:readable('/proc/self/maps'))
    check('proc_cpuinfo_readable',lambda:readable('/proc/cpuinfo'))
    def decoder_manifest():
        from src.transformer_backend import _runtime_manifest
        # A fresh CLI process avoids any earlier cached runtime manifest.
        value=_runtime_manifest()
        return {'manifest_sha256':hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest(),
                'loaded_libm_count':len(value['loaded_libm_sha256']),
                'cpu_dispatch_field_count':len(value['cpu_dispatch_fields'])}
    check('actual_transformer_backend_runtime_manifest',decoder_manifest)
    def primitive_manifest(backend):
        from src.finite_primitives import primitive_manifest
        value=primitive_manifest(backend)
        return {'backend':backend,'manifest_sha256':hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest(),
                'bound_binary_count':len(value.get('binary_sha256',{}))}
    for backend in ('rational','mpfr_enclosure'):
        check('actual_finite_primitive_manifest_'+backend,lambda backend=backend:primitive_manifest(backend))
    def software_runtime():
        from src.runtime_contract import capture_runtime_contract
        return capture_runtime_contract()
    runtime=check('portable_software_runtime_contract',software_runtime)
    if campaign is not None:
        campaign=Path(campaign).absolute()
        def registered_contract():
            from src.run_store import digest
            from src.experiment_inventory import source_hashes
            raw=(campaign/'program.json').read_bytes()
            protocol=(campaign/'protocol.json').read_bytes()
            program=json.loads(raw);policy=json.loads(protocol)
            registration=json.loads((campaign/'registration.json').read_bytes())
            if registration['program_sha256']!=digest(raw) or registration['protocol_sha256']!=digest(protocol) or policy['program_sha256']!=digest(raw):
                raise ValueError('original registration hashes do not agree')
            if runtime is None or runtime!=registration['runtime']:
                raise ValueError('current software runtime differs from original registration')
            if source_hashes(ROOT)!=program['source_sha256'] or source_hashes(campaign/'source')!=program['source_sha256']:
                raise ValueError('current or frozen numerical source differs from original registration')
            return {'program_sha256':digest(raw),'protocol_sha256':digest(protocol),'runtime_matches':True,'numerical_sources_match':True}
        check('registered_software_and_source_contract',registered_contract)
        def worker_limits():
            from src.worker_control import WorkerLimits
            program=json.loads((campaign/'program.json').read_bytes())
            for trial in program['trials']:
                WorkerLimits(trial['wall_seconds'],trial['cpu_seconds'],program['address_space_bytes'],1,
                    tuple(program['affinity_cpus'])).check_host()
            return {'trial_limit_sets_checked':len(program['trials'])}
        check('registered_worker_host_limits',worker_limits)
    blocked=[entry['check'] for entry in checks if entry['status']=='blocked']
    return {'schema':'finite-environment-preflight-v34','status':'blocked' if blocked else 'passed',
            'blocked_checks':blocked,'checks':checks,
            'campaign':str(campaign) if campaign is not None else None,
            'worker_launched':False,'model_loaded':False,'model_inference_performed':False,
            'ledger_written':False,'runtime_contract_relaxed':False,'missing_runtime_data_substituted':False,
            'passing_preflight_authorizes_retry':False,
            'limit':'Environment checks only. Original controller, registration, source, artifact, and failed-attempt guards still apply. A changed execution surface requires this screen again.',
            'next_action':'Do not start experiments on this environment; restore a compatible environment without altering the target contract.' if blocked else 'Use the original controller guards; never retry an already failed trial automatically.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,help='Optional existing campaign for exact registered runtime, source, and resource checks')
    args=parser.parse_args()
    result=preflight(args.campaign)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 2 if result['status']=='blocked' else 0


if __name__=='__main__':raise SystemExit(main())
