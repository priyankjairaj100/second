"""Production phase operations, called only by the admitted bounded worker.

Every later phase consumes outputs bound by completed predecessor seals. The
terminal phase checks actual artifacts; its own final cost requires post-exit
closure. No function here submits jobs or acquires data.
"""
from pathlib import Path
import unittest
from research_v67.io import read,write,json_read,require,info
from research_v67.config import RECORDS_SHA,BASE_TARGET
from research_v69 import production_gate as production,construction_flow as construction
from src.run_store import canonical_json,digest


def context(p,x):return production.cpu_context(p['inputs']['checkpoint'],x['base'],x['calibration'])


def parameter_binding(p,previous,registration):
    c=previous['parameters']['result'];s=p['inputs']['snapshot']
    require(c['schema']=='checkpoint-parameter-audit-v69' and c['status']=='verified'
        and c['registration_sha256']==registration and c['checkpoint']==p['inputs']['checkpoint']
        and c['actual_checkpoint_reference_compared'] is True,
        'Fresh completed checkpoint-derived parameter audit required before reuse')
    r=c['parameters']
    require(r['status']=='verified' and r['actual_all_parameter_words_equal'] is True
        and r['arrays']==78 and r['includes_embeddings_positions_norm_bias_head_and_stage_weights'] is True
        and r['manifest']=={k:s['manifest'][k] for k in ['bytes','sha256']}
        and r['archive']=={k:s['archive'][k] for k in ['bytes','sha256']},
        'Fresh all-array audit must bind these actual original export bytes')
    return c


def saved_reference(p,previous,registration):
    from research_v47.snapshot import load_snapshot
    from research_v69.parameter_audit import verify
    c=parameter_binding(p,previous,registration);s=p['inputs']['snapshot']
    for name in ['manifest','archive']:
        read(s[name]['path'],{k:s[name][k] for k in ['bytes','sha256']},maximum=2*2**30,retain=False)
    reference=load_snapshot(s['manifest']['path'],s['archive']['path'])
    require(production.reference_geometry(reference)==c['geometry'],'Reused actual parameter geometry differs')
    # This second comparison is a transfer-integrity check. Checkpoint provenance
    # comes from the earlier completed parameter worker, not self-consistency.
    r=verify(reference,s['manifest']['path'],s['archive']['path'],
        expected_manifest=c['parameters']['manifest'],expected_archive=c['parameters']['archive'])
    require(r==c['parameters'],'Reused parameter words differ from fresh reference audit')
    return reference


def construction_arguments(p,x,n,registration):
    return dict(endpoint=n,expected_root_sha256=RECORDS_SHA,
        expected_candidate=info(x['candidates']['candidate_'+str(n)]),
        expected_target_sha256=BASE_TARGET,registration_sha256=registration)


def model_set(p,x,previous,run,registration,*,base=None):
    from research_v69.model_backend import ModelSet
    reference=saved_reference(p,previous,registration);models={}
    for n in [12,6]:
        label='candidate_'+str(n);candidate=x['candidates'][label]
        _,retained=construction.membership(x['root'],n,RECORDS_SHA)
        models[label]=dict(blob=candidate,expected=info(candidate),retained_records_sha256=retained)
        name='sequential_'+str(n);prior=previous[name]['result']
        require(set(prior)=={'construction','saved_code_audit','kernel'},'Complete sequential phase result required')
        complete=prior['construction'];audit=prior['saved_code_audit']
        require(complete['schema']=='matched-sequential-construction-v69' and complete['status']=='complete'
            and complete['error'] is None and complete['endpoint']==n and complete['registration_sha256']==registration
            and complete['root_records_sha256']==RECORDS_SHA and complete['retained_records_sha256']==retained
            and complete['base_target_sha256']==BASE_TARGET and complete['candidate']==info(candidate)
            and audit['status']=='verified' and audit['endpoint']==n and audit['stages']==24
            and audit['actual_model_codes_compared']==42467328 and audit['first_stage_equal'] is True,
            'Actual complete matched construction and saved-code audit required')
        directory=Path(run)/name/'outputs/construction'
        require(json_read(directory/'completion.json')==complete,'Actual saved construction receipt differs')
        expected={k:complete['artifacts']['model.bin'][k] for k in ['bytes','sha256']}
        require(expected==audit['artifacts']['model.bin'],'Saved model audit commitment differs')
        blob=read(directory/'model.bin',expected,maximum=21233664)
        if base is not None:
            repeated=construction.audit(directory,base,x['root'],candidate,**construction_arguments(p,x,n,registration))
            require(repeated==audit,'Actual saved sequential audit differs on terminal read')
        models[name]=dict(blob=blob,expected=expected,retained_records_sha256=retained)
    return ModelSet(reference,x['bound'],models,expected_base=info(x['base']),expected_service=info(x['bound'].fixed_payload))


def run(phase,p,x,previous,out,run_directory,registration):
    """Dispatch actual numerical work; caller supplies verified immutable inputs."""
    from research_v69 import execution_gate,quality_flow,loss_audit,cost_accounting
    require(phase in execution_gate.CAPS and set(previous)==set(list(execution_gate.CAPS)[:list(execution_gate.CAPS).index(phase)]),
        'Exactly the completed earlier phase chain is required')
    out=Path(out);run_directory=Path(run_directory)
    if phase=='cpu_checks':
        suite=unittest.defaultTestLoader.loadTestsFromNames(p['software_modules'])
        tests=unittest.TextTestRunner(verbosity=2).run(suite)
        r=dict(tests=tests.testsRun,failures=len(tests.failures),errors=len(tests.errors),skips=len(tests.skipped),
            includes_unchanged_v55_numerical_fixtures=True,empirical_quality=False)
        write(out/'checks.json',r)
        require(tests.wasSuccessful() and tests.testsRun==p['expected_tests'] and not tests.skipped,
            'Exact complete registered Linux check suite required')
        return r
    tests=previous['cpu_checks']['result']
    require(tests['tests']==p['expected_tests'] and tests['failures']==tests['errors']==tests['skips']==0,
        'Passed complete Linux qualification required')
    if phase=='cuda_checks':
        from research_v69.cuda_qualification import run as qualify
        return qualify(out/'cuda',registration_sha256=registration,allocator_bytes=execution_gate.GPU_ALLOCATOR)
    cuda=previous['cuda_checks']['result']
    require(cuda['status']=='complete' and cuda['error'] is None and len(cuda['comparisons'])==24
        and all(r['passed'] is True for r in cuda['comparisons']), 'Passed actual generated CUDA qualification required')
    if phase=='parameters':
        ctx=context(p,x);s=p['inputs']['snapshot']
        return production.parameter_receipt(ctx,s['manifest']['path'],s['archive']['path'],
            expected_manifest={k:s['manifest'][k] for k in ['bytes','sha256']},
            expected_archive={k:s['archive'][k] for k in ['bytes','sha256']},
            registration_sha256=registration,checkpoint_entries=p['inputs']['checkpoint'])
    parameter_binding(p,previous,registration)
    if phase.startswith('sequential_'):
        from research_v50.neighbors import enabled
        n=int(phase.split('_')[1]);ctx=context(p,x);candidate=x['candidates']['candidate_'+str(n)]
        args=construction_arguments(p,x,n,registration)
        with enabled() as kernel:
            result=construction.construct(decoder=ctx.decoder,base=ctx.base,records=x['root'],candidate_blob=candidate,
                out=out/'construction',**args)
        audit=construction.audit(out/'construction',ctx.base,x['root'],candidate,**args)
        return dict(construction=result,saved_code_audit=audit,kernel=kernel)
    ctx=context(p,x) if phase=='terminal' else None
    models=model_set(p,x,previous,run_directory,registration,base=ctx.base if ctx else None)
    if phase=='cpu_parity':
        return quality_flow.collect(phase,x['records'],models.cpu,models.bindings,out/'losses',registration_sha256=registration)
    if phase=='gpu_quality':
        from research_v69.model_backend import cuda as device
        cpu_directory=run_directory/'cpu_parity/outputs/losses'
        loss_audit.audit(cpu_directory,x['records'],models.bindings,registration_sha256=registration)
        cpu=json_read(cpu_directory/'completion.json')
        require(cpu==previous['cpu_parity']['result'],'Sealed actual CPU reference differs')
        with device(models,allocator_bytes=execution_gate.GPU_ALLOCATOR) as (factory,gpu):
            result=quality_flow.collect(phase,x['records'],factory,models.bindings,out/'losses',
                registration_sha256=registration,cpu_reference=cpu)
        write(out/'gpu.json',gpu);cost_accounting.gpu_memory(gpu)
        require(gpu['copied_arrays_with_bitwise_roundtrip']==318,'Complete actual model transfer census differs')
        return dict(collection=result,gpu=gpu)
    require(phase=='terminal','Unknown terminal phase')
    s=p['inputs']['snapshot']
    parameter_audit=production.parameter_receipt(ctx,s['manifest']['path'],s['archive']['path'],
        expected_manifest={k:s['manifest'][k] for k in ['bytes','sha256']},
        expected_archive={k:s['archive'][k] for k in ['bytes','sha256']},
        registration_sha256=registration,checkpoint_entries=p['inputs']['checkpoint'])
    # Decoder provenance includes measurements such as construction timing; only
    # immutable parameter words, geometry and checkpoint identities must match.
    original=previous['parameters']['result']
    require(all(parameter_audit[k]==original[k] for k in ['parameters','geometry','checkpoint']),
        'Repeated actual checkpoint parameter comparison differs')
    gpu_phase=previous['gpu_quality'];gpu=gpu_phase['result']['gpu']
    require(gpu==json_read(run_directory/'gpu_quality/outputs/gpu.json'),'Actual allocator receipt differs')
    allocator=cost_accounting.gpu_memory(gpu)
    require(gpu['copied_arrays_with_bitwise_roundtrip']==318,'Every declared model transfer required')
    # Runtime version is taken from the prospectively registered actual GPU host.
    version=p['runtimes']['cuda'][gpu_phase['hostname']]['numpy']
    audit=loss_audit.audit(run_directory/'gpu_quality/outputs/losses',x['records'],models.bindings,
        registration_sha256=registration,cpu_directory=run_directory/'cpu_parity/outputs/losses',
        expected_statistics_numpy_version=version)
    require(json_read(run_directory/'gpu_quality/outputs/losses/completion.json')==gpu_phase['result']['collection'],
        'Actual full GPU collection differs from completed worker')
    return dict(status='verified_actual_artifacts',loss_audit=audit,allocator=allocator,
        actual_checkpoint_parameter_audit=parameter_audit,
        model_bindings=models.bindings,sequential_actual_saved_codes_reaudited=True,
        quality_guard_pass=audit['all_endpoint_gates_pass'],
        numerical_constructor_and_likelihood_not_independently_reexecuted=True,
        final_scheduler_and_terminal_process_costs_require_post_exit_closure=True)
