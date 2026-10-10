"""Software fixtures only: no checkpoint load, calibration, or inference."""
import copy
import json
import math
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from research_v44 import campaign, diagnostic
from research_v42.test_resource_plan import bind, fixture
from research_v43.state import build_state
from research_v43.test_state import record, artifacts
from src.compact_state import StageCodes
from src.run_store import canonical_json, digest
from src.transaction_timing import verify_command_admission


def quality(delta=0.):
    result = {label:[dict(id=rid,predictions=127,nll_sum=127*4.) for rid in diagnostic.ARTICLE_IDS]
              for label in diagnostic.LABELS}
    for row in result['fixed_feature']:
        row['nll_sum'] += 127*delta
    return result


def audits():
    rows = [dict(trial=trial,step=step,actual_bytes_equal=True,actual_model_bytes_equal=True,
        exact_retained_membership_verified=True,code_count=42_467_328,stages=24,
        complete_model_sha256='m',state_sha256='s',retained_records=3-step,retained_tokens=32*(3-step),
        model_export_matches_state_codes=True,registered_record_binding_verified=True,
        cross_representation_target_and_model_verified=True)
        for trial in ('cached','compressed','hybrid','cold') for step in (1,2)]
    first=dict(schema='complete-service-artifact-audit-v43',status='verified',program_sha256='p',
        campaign='/fixture',all_declared_artifacts_rehashed=True,complete_model=True,
        original_tokens=96,retained_tokens=[64,32],comparisons=copy.deepcopy(rows))
    second=dict(schema='complete-service-additive-artifact-audit-v43',status='verified',program_sha256='p',
        campaign='/fixture',frozen_audit_sha256='a',evidence=dict(comparisons=copy.deepcopy(rows)))
    return first,second


class DiagnosticTests(unittest.TestCase):
    def test_actual_historical_payload_and_source_are_available_without_model_files(self):
        reg=json.loads((campaign.ROOT/'campaigns/quality_v30/registration.json').read_bytes())
        history=json.loads((campaign.ROOT/'campaigns/research_v30/attempts/quality-001/outputs/completion.json').read_bytes())
        rows=diagnostic.validate_exposed(reg,history)
        self.assertEqual(sum(len(r['tokens'])-1 for r in rows),1016)
        self.assertEqual(digest(canonical_json(reg)),campaign.REGISTRATION_SHA256)
        self.assertEqual(campaign.sha(campaign.ROOT/'scripts/run_quality_v30.py'),campaign.EVALUATOR_SHA256)
        bad=copy.deepcopy(reg);bad['records'][0]['id']='unexposed'
        with self.assertRaises(ValueError):diagnostic.validate_exposed(bad,history)

    def test_both_linked_actual_audits_required(self):
        first,second=audits()
        check=lambda a,b:campaign.check_audits({'directory':'/fixture'},'p',a,b,'a','m','s')
        check(first,second)
        for location,key,value in [('first','program_sha256','other'),('second','frozen_audit_sha256','other')]:
            a,b=copy.deepcopy(first),copy.deepcopy(second)
            (a if location=='first' else b)[key]=value
            with self.assertRaises(ValueError):check(a,b)
        for key in ('actual_bytes_equal','actual_model_bytes_equal','model_export_matches_state_codes',
                    'registered_record_binding_verified','cross_representation_target_and_model_verified'):
            b=copy.deepcopy(second);b['evidence']['comparisons'][0][key]=False
            with self.assertRaises(ValueError):check(first,b)
        b=copy.deepcopy(second);b['evidence']['comparisons'].pop()
        with self.assertRaises(ValueError):check(first,b)
        b=copy.deepcopy(second)
        next(r for r in b['evidence']['comparisons'] if (r['trial'],r['step'])==('compressed',2))['state_sha256']='changed'
        with self.assertRaises(ValueError):check(first,b)

    def test_bound_input_detects_same_size_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'input';p.write_bytes(b'first')
            binding=campaign.bind(p)
            self.assertEqual(campaign.bound(binding),p.resolve())
            p.write_bytes(b'other')
            with self.assertRaises(ValueError):campaign.bound(binding)

    def test_parity_requires_all_sixteen_finite_controls(self):
        q=quality();history={'quality':copy.deepcopy(q)}
        report=diagnostic.parity(q,history)
        self.assertTrue(report['passed']);self.assertEqual(len(report['checks']),16)
        q['nearest_rounding'][0]['nll_sum']+=127*2e-8
        self.assertFalse(diagnostic.parity(q,history)['passed'])
        q['nearest_rounding'].pop()
        with self.assertRaises(ValueError):diagnostic.parity(q,history)

    def test_pooled_and_adverse_article_guards_are_distinct(self):
        self.assertTrue(diagnostic.summarize(quality())['development_guards_pass'])
        pooled=diagnostic.summarize(quality(math.log(1.06)))
        self.assertFalse(pooled['guards']['pooled_pass'])
        self.assertTrue(pooled['guards']['every_article_pass'])
        q=quality();q['fixed_feature'][0]['nll_sum']+=127*math.log(1.21)
        article=diagnostic.summarize(q)
        self.assertTrue(article['guards']['pooled_pass'])
        self.assertFalse(article['guards']['every_article_pass'])
        self.assertIsNone(article['inferential_interval'])
        self.assertFalse(article['confirmation'])
        self.assertAlmostEqual(article['fixed_feature_comparisons']['full_precision']['pooled_perplexity_ratio'],1.21**(1/8))
        q['sequential'][0]['predictions']=126
        with self.assertRaises(ValueError):diagnostic.summarize(q)
        enormous=diagnostic.summarize(quality(1000.))
        self.assertFalse(enormous['development_guards_pass'])
        self.assertIsNone(enormous['fixed_feature_comparisons']['sequential']['pooled_perplexity_ratio'])

    def test_real_complete_synthetic_codes_reconstruct_and_reject_export_mutation(self):
        # Actual 24-stage shapes and packing, but synthetic constant codes and
        # tiny synthetic calibration factors; no model/evaluator executes.
        shapes=((2304,768),(768,768),(3072,768),(768,3072))*6
        target=bind(*fixture(shapes,original=96))
        source=record('synthetic',(1,2))
        codes=tuple(StageCodes(s.stage_id,s.rows,s.width,'dyadic_row',4,(),
            b'\x88'*(s.rows*s.width//2),(1.,)*s.rows) for s in target.stages)
        payload=artifacts(target,(source,),'compressed40')
        blob=build_state(target,(source,),codes,'compressed40',**payload)
        model=b''.join(s.packed_indices for s in codes)
        kwargs=dict(bound_target=target,records=[{'id':'synthetic','tokens':[1,2]}],
            provenance={'synthetic':json.loads(source.provenance)})
        restored=diagnostic.reconstruct_fixed(blob,model,**kwargs)
        self.assertEqual(restored,codes)
        self.assertTrue(np.all(restored[0].array()==0.))
        with self.assertRaisesRegex(ValueError,'export differs'):
            diagnostic.reconstruct_fixed(blob,model[:-1]+b'\x78',**kwargs)
        kwargs['records'][0]['tokens']=[1,3]
        with self.assertRaises(ValueError):diagnostic.reconstruct_fixed(blob,model,**kwargs)

    def test_new_phase_binds_literal_command_and_does_not_reuse_old_allowance(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'program.json').write_bytes(canonical_json({'fixture':True}))
            p={'directory':str(root)}
            command=[campaign.sys.executable,'-B','-m','research_v44.worker',str(root/'plan.json')]
            with patch.object(campaign,'source_hashes',return_value={'fixture.py':'1'*64}),\
                    patch('src.experiment_inventory.source_hashes',return_value={'fixture.py':'1'*64}):
                budget=campaign.budget(p);budget.reserve('development','one',1202)
                admission=dict(phase_budget_root=str(budget.root),phase_budget_binding_sha256=budget.identity_digest,
                    attempt_id='one',phase='development',command=command,cwd=str(campaign.ROOT))
                with patch.dict(os.environ,CALIBRATION_PHASE_CPU_ADMISSION=canonical_json(admission).decode()):
                    verify_command_admission(campaign.sha(root/'program.json'),'development',command)
                    with self.assertRaises(ValueError):
                        verify_command_admission(campaign.sha(root/'program.json'),'development',command[1:])
                self.assertEqual(budget.snapshot()['charged_cpu_seconds']['development'],1202)

    def test_failed_worker_is_charged_recorded_and_never_automatically_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'program.json').write_bytes(canonical_json({'fixture':True}))
            p=dict(directory=str(root),file_size_bytes=2*2**30)
            def failed(command,worker,limits,**kwargs):
                self.assertEqual(limits.cpu_seconds,1200)
                ledger=kwargs['phase_budget'];ledger.reserve('development','failed-fixture',1202)
                ledger.settle('failed-fixture',1_200_000_000)
                return {'outcome':{'status':'failed','returncode':1}}
            with patch.object(campaign,'verify',return_value=p),\
                    patch.object(campaign,'run_limited',side_effect=failed),\
                    patch.object(campaign,'source_hashes',return_value={'fixture.py':'1'*64}),\
                    patch.object(os,'sched_getaffinity',return_value={0},create=True),\
                    patch.dict(os.environ,SLURM_JOB_ID='fixture'):
                self.assertEqual(campaign.run(root),'failed')
                result=json.loads((root/'quality/transaction.json').read_bytes())
                self.assertEqual(result['budget']['charged_cpu_seconds']['development'],2)
                with self.assertRaisesRegex(ValueError,'already attempted'):campaign.run(root)


class RuntimeDependencyTests(unittest.TestCase):
    def test_absent_optional_scipy_is_recorded_but_required_or_broken_packages_refuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            modules={}
            for name in ('numpy','gmpy2'):
                path=root/name/'__init__.py';path.parent.mkdir();path.write_text('# fixture\n')
                modules[name]=SimpleNamespace(__file__=str(path),__version__='fixture')
            compiler=root/'cc';compiler.write_text('fixture compiler')
            def imported(name):
                if name=='scipy':
                    raise ModuleNotFoundError("No module named 'scipy'",name='scipy')
                return modules[name]
            with patch.object(campaign,'capture_runtime_contract',return_value={'fixture':True}), \
                    patch.object(campaign.importlib,'import_module',side_effect=imported), \
                    patch.object(campaign.shutil,'which',return_value=str(compiler)), \
                    patch.object(campaign.subprocess,'check_output',return_value='fixture compiler'), \
                    patch.object(np,'show_config',side_effect=lambda:print('fixture')):
                runtime=campaign.runtime()
                self.assertEqual(runtime['packages']['scipy'],dict(installed=False,
                    required_for_pinned_gelu_new_route=False))
                self.assertEqual(runtime['packages']['numpy']['version'],'fixture')
                with patch.object(campaign.importlib,'import_module',
                        side_effect=ModuleNotFoundError('numpy missing',name='numpy')):
                    with self.assertRaises(ModuleNotFoundError):campaign.runtime()
                def broken(name):
                    if name=='scipy':
                        raise ModuleNotFoundError('broken dependency',name='broken_dependency')
                    return modules[name]
                with patch.object(campaign.importlib,'import_module',side_effect=broken):
                    with self.assertRaises(ModuleNotFoundError):campaign.runtime()


if __name__=='__main__':
    unittest.main()
