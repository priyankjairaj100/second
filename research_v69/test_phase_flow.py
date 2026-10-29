"""Production wiring tests with checkpoint/calibration/inference mocked."""
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import copy,unittest
from research_v69 import phase_flow as f,execution_gate,quality_flow


def prerequisite(phase):
    previous={k:{'result':{}} for k in list(execution_gate.CAPS)[:list(execution_gate.CAPS).index(phase)]}
    if 'cpu_checks' in previous:previous['cpu_checks']['result']=dict(tests=80,failures=0,errors=0,skips=0)
    if 'cuda_checks' in previous:previous['cuda_checks']['result']=dict(status='complete',error=None,comparisons=[{'passed':True}]*24)
    return previous


class PhaseFlowTests(unittest.TestCase):
    def test_parameter_reuse_requires_checkpoint_derived_all_array_audit(self):
        s={n:dict(path='/generated/'+n,bytes=10,sha256='b'*64) for n in ['manifest','archive']}
        p={'inputs':{'snapshot':s,'checkpoint':{'generated':True}}}
        audit=dict(status='verified',actual_all_parameter_words_equal=True,arrays=78,
            includes_embeddings_positions_norm_bias_head_and_stage_weights=True,
            manifest={'bytes':10,'sha256':'b'*64},archive={'bytes':10,'sha256':'b'*64})
        r=dict(schema='checkpoint-parameter-audit-v69',status='verified',registration_sha256='a'*64,
            checkpoint=p['inputs']['checkpoint'],actual_checkpoint_reference_compared=True,parameters=audit)
        previous={'parameters':{'result':r}}
        self.assertEqual(f.parameter_binding(p,previous,'a'*64),r)
        for key,value in [('arrays',77),('actual_all_parameter_words_equal',False),
            ('archive',{'bytes':11,'sha256':'b'*64})]:
            bad=copy.deepcopy(previous);bad['parameters']['result']['parameters'][key]=value
            with self.assertRaises(ValueError):f.parameter_binding(p,bad,'a'*64)
        r['actual_checkpoint_reference_compared']=False
        with patch('research_v47.snapshot.load_snapshot') as load,self.assertRaises(ValueError):
            f.saved_reference(p,previous,'a'*64)
        load.assert_not_called()

    def test_failed_cuda_or_linux_gate_prevents_checkpoint_load(self):
        with TemporaryDirectory() as tmp,patch.object(f,'context') as load:
            p={'expected_tests':80};previous=prerequisite('parameters')
            previous['cuda_checks']['result']['comparisons'][-1]={'passed':False}
            with self.assertRaisesRegex(ValueError,'actual generated CUDA'):
                f.run('parameters',p,{},previous,tmp,tmp,'a'*64)
            previous=prerequisite('parameters');previous['cpu_checks']['result']['skips']=1
            with self.assertRaisesRegex(ValueError,'complete Linux'):
                f.run('parameters',p,{},previous,tmp,tmp,'a'*64)
            load.assert_not_called()

    def test_both_sequential_dispatches_use_correct_retained_endpoint_and_exact_kernel(self):
        from research_v50 import neighbors
        @contextmanager
        def enabled():yield {'generated':'kernel'}
        with TemporaryDirectory() as tmp:
            x=dict(root=['generated'],candidates={'candidate_12':b'a','candidate_6':b'b'})
            p={'expected_tests':80};ctx=SimpleNamespace(decoder='decoder',base='base')
            for n in [12,6]:
                phase='sequential_'+str(n)
                with patch.object(f,'parameter_binding'),patch.object(f,'context',return_value=ctx),\
                    patch.object(neighbors,'enabled',enabled),patch.object(f.construction,'construct',return_value={'saved':n}) as construct,\
                    patch.object(f.construction,'audit',return_value={'audit':n}) as audit:
                    result=f.run(phase,p,x,prerequisite(phase),tmp,tmp,'a'*64)
                self.assertEqual(construct.call_args.kwargs['endpoint'],n)
                self.assertEqual(construct.call_args.kwargs['candidate_blob'],x['candidates']['candidate_'+str(n)])
                self.assertEqual(audit.call_args.kwargs['endpoint'],n)
                self.assertEqual(result['kernel'],{'generated':'kernel'})

    def test_incomplete_chain_is_rejected_before_dispatch(self):
        with patch.object(f,'context') as load,self.assertRaisesRegex(ValueError,'Exactly'):
            f.run('parameters',{'expected_tests':80},{},{},'/missing','/missing','a'*64)
        load.assert_not_called()

    def test_gpu_transfer_report_is_checked_after_context_exit_and_negative_quality_completes(self):
        from research_v69 import model_backend,loss_audit
        previous=prerequisite('gpu_quality');previous['cpu_parity']['result']={'cpu':'reference'}
        report=dict(dtype='float64',tf32=False,amp=False,deterministic_algorithms=True,
            allocator_limit_bytes=execution_gate.GPU_ALLOCATOR)
        @contextmanager
        def device(*args,**kwargs):
            yield 'factory',report
            report.update(copied_arrays_with_bitwise_roundtrip=318,peak_cuda_allocated_bytes=100,
                peak_cuda_reserved_bytes=200)
        with TemporaryDirectory() as tmp,patch.object(f,'parameter_binding'),\
            patch.object(f,'model_set',return_value=SimpleNamespace(bindings={'models':'generated'})),\
            patch.object(loss_audit,'audit'),patch.object(f,'json_read',return_value=previous['cpu_parity']['result']),\
            patch.object(model_backend,'cuda',device),\
            patch.object(quality_flow,'collect',return_value={'status':'complete','summary':{'all_endpoint_gates_pass':False}}):
            directory=Path(tmp).resolve()
            result=f.run('gpu_quality',{'expected_tests':80},{'records':[]},previous,directory,directory,'a'*64)
            self.assertEqual(result['gpu']['copied_arrays_with_bitwise_roundtrip'],318)
            self.assertFalse(result['collection']['summary']['all_endpoint_gates_pass'])
            self.assertTrue((Path(tmp)/'gpu.json').exists())


if __name__=='__main__':unittest.main()
