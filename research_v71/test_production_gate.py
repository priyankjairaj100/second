"""Generated production-shaped metadata; no checkpoint/MPFR/CUDA execution."""
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
import copy,tempfile,unittest
from unittest.mock import patch
from research_v61.test_target import fixture,service_for
from research_v71 import production_gate as g
from src.run_store import canonical_json,digest


def target_fixture():
    base,_=fixture(tuple(map(tuple,g.SHAPES.values())),original=1664)
    for i,(name,entry) in enumerate(zip(g.SHAPES,base['stages'])):
        entry.update(stage_id=name,dependencies=sorted(list(g.SHAPES)[:i]))
    service=service_for(base);b=canonical_json(base);c=canonical_json(service['calibration_target'])
    return b,c,canonical_json(service)


def pins(b,c,s):
    stack=ExitStack()
    for name,raw in [('BASE_TARGET',b),('CALIBRATION_TARGET',c),('SERVICE_TARGET',s)]:
        stack.enter_context(patch.object(g,name,digest(raw)))
    return stack


def fake_fields():
    shapes=dict(embeddings=(50257,768),positions=(1024,768),head=(50257,768),
        head_bias=(50257,),final_scale=(768,),final_bias=(768,))
    shapes.update({'weights/'+n:tuple(s) for n,s in g.SHAPES.items()})
    for i in range(6):
        for name,n in [('norm1_scale',768),('norm1_bias',768),('norm2_scale',768),('norm2_bias',768),
            ('qkv_bias',2304),('attn_out_bias',768),('mlp_up_bias',3072),('mlp_down_bias',768)]:
            shapes[f'blocks/{i}/{name}']=(n,)
    import math
    return {name:SimpleNamespace(shape=shape,nbytes=math.prod(shape)*8) for name,shape in shapes.items()}


class ProductionGateTests(unittest.TestCase):
    def test_production_target_and_complete_structural_resource_formula(self):
        b,c,s=target_fixture()
        with pins(b,c,s):
            target=g.targets(b,c);result=g.resources(target)
        self.assertEqual(target.original_tokens,1664)
        self.assertEqual([result['requests'][str(n)]['reserved_work_units'] for n in [12,6]],
            [419270639616,321015398400])
        self.assertTrue(all(len(r['stages'])==24 for r in result['requests'].values()))
        self.assertFalse(result['measured_fit'])

    def test_other_target_or_rebound_smaller_geometry_cannot_pass_production_gate(self):
        b,c,s=target_fixture()
        with self.assertRaisesRegex(ValueError,'commitments'):g.targets(b,c)
        for variant in ['shape','normalization','order','missing']:
            x=copy.deepcopy(g.strict_json(b))
            if variant=='shape':x['stages'][0]['shape'][1]-=1
            elif variant=='normalization':
                x['recipe']['original_token_count']=768
                for row in x['stages']:row['normalization']=[768,1]
            elif variant=='order':x['stages'][0]['stage_id']='other.stage'
            else:x['stages'].pop()
            y=service_for(x);xx=canonical_json(x);cc=canonical_json(y['calibration_target']);ss=canonical_json(y)
            with self.subTest(variant=variant),pins(xx,cc,ss),self.assertRaises(ValueError):g.targets(xx,cc)

    def test_actual_checkpoint_files_hash_extent_census_and_directory_are_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp).resolve();entries={}
            for name,raw in [('config.json',b'config'),('model.safetensors',b'weights')]:
                (d/name).write_bytes(raw);entries[name]=dict(path=str(d/name),**g.info(raw))
            with patch.object(g,'CHECKPOINT_HASHES',{n:e['sha256'] for n,e in entries.items()}):
                self.assertTrue(g.checkpoint(entries)['actual_checkpoint_bytes_verified'])
                with self.assertRaises(ValueError):g.checkpoint({'config.json':entries['config.json']})
                (d/'model.safetensors').write_bytes(b'changed')
                with self.assertRaises(ValueError):g.checkpoint(entries)
                (d/'model.safetensors').write_bytes(b'weights')
                other=d/'other';other.mkdir();(other/'model.safetensors').write_bytes(b'weights')
                wrong=copy.deepcopy(entries);wrong['model.safetensors']['path']=str(other/'model.safetensors')
                with self.assertRaisesRegex(ValueError,'share'):g.checkpoint(wrong)
                (d/'model.safetensors').unlink();(d/'model.safetensors').symlink_to(other/'model.safetensors')
                with self.assertRaisesRegex(ValueError,'nonsymbolic'):g.checkpoint(entries)

    def test_configuration_rejects_dtype_equivalence_extra_fields_and_wrong_activation(self):
        g.configuration(g.CONFIG.copy())
        for key,value in [('block_count',6.),('activation','gelu'),('layernorm_epsilon',1e-6),('extra',0)]:
            with self.subTest(key=key),self.assertRaises(ValueError):g.configuration(dict(g.CONFIG,**{key:value}))

    def test_all78_parameter_shapes_including_nonstage_arrays_are_required(self):
        ref=SimpleNamespace(config=SimpleNamespace(**g.CONFIG),blocks=[{} for _ in range(6)])
        arrays=fake_fields()
        with patch.object(g,'fields',return_value=arrays):
            result=g.reference_geometry(ref)
            self.assertEqual(result['arrays'],78);self.assertEqual(result['packed_model_bytes'],21233664)
        for key in ['head_bias','positions','blocks/5/norm2_scale','weights/block.0005.mlp_down']:
            x=fake_fields();x[key]=SimpleNamespace(shape=(1,),nbytes=8)
            with self.subTest(key=key),patch.object(g,'fields',return_value=x),self.assertRaises(ValueError):g.reference_geometry(ref)
        arrays['foreign']=arrays['head_bias']
        with patch.object(g,'fields',return_value=arrays),self.assertRaises(ValueError):g.reference_geometry(ref)

    def test_mocked_context_uses_original_decoder_and_exact_rebuilt_target(self):
        b,c,s=target_fixture();reference=SimpleNamespace();base=SimpleNamespace(payload=lambda:g.strict_json(b))
        loaded=SimpleNamespace(decoder=SimpleNamespace(config=SimpleNamespace(**g.CONFIG)),
            provenance=dict(files_sha256=g.CHECKPOINT_HASHES))
        ordered=SimpleNamespace(kernel_manifest={'fixture':1},implementation_manifest={'fixture':2})
        with pins(b,c,s),patch.object(g,'checkpoint',return_value={'directory':'/fixture'}) as check,\
            patch('src.checkpoint_adapter.load_gpt2_checkpoint',return_value=loaded) as load,\
            patch('src.ordered_finite_decoder_v30.OrderedFiniteDecoder',return_value=ordered),\
            patch('src.dyadic_row_target.build_dyadic_row_target',return_value=base) as build,\
            patch('scripts.run_quality_v30.NumpyQualityDecoder',return_value=reference) as numpy,\
            patch.object(g,'reference_geometry',return_value={'fixture':True}):
            result=g.cpu_context({},b,c)
            self.assertIs(result.decoder,ordered);self.assertIs(result.reference,reference)
            numpy.assert_called_once_with(loaded.decoder)
            self.assertEqual(build.call_args.args[1].original_token_count,1664)
            self.assertEqual(build.call_args.args[1].group_count,1)
            self.assertEqual(load.call_args.kwargs['identity_encoding'],'binary64_tree_v2')
            self.assertEqual(check.call_count,2)
            base.payload=lambda:{'wrong':'reconstruction'}
            with self.assertRaisesRegex(ValueError,'Reconstructed'):g.cpu_context({},b,c)

    def test_target_failure_happens_before_checkpoint_load(self):
        b,c,s=target_fixture()
        with patch('src.checkpoint_adapter.load_gpt2_checkpoint') as load:
            with self.assertRaises(ValueError):g.cpu_context({},b,c)
            load.assert_not_called()


if __name__=='__main__':unittest.main()
