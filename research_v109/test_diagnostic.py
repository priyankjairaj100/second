import dataclasses
from fractions import Fraction
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from research_v109 import stage,config,storage_plan
from research_v43 import dispatcher
from src.dyadic_row_target import DyadicRowStage
from src.run_store import canonical_json,digest
from src import fixed_lossless_codec_v29 as codec


class Diagnostic(unittest.TestCase):
    def full_stage(self):
        return DyadicRowStage(config.STAGE,(),((0.,)*768,)*3072,Fraction(1),Fraction(512),(1.,)*3072,4)

    def spec(self):
        return dispatcher.StageSpec('toy','a'*64,1,2,(1.,),Fraction(1),Fraction(512),'b'*64)

    def data(self):
        rows=[dict(id='record'+str(i),tokens=list(range(128))) for i in range(3)]
        payloads={}
        for r in rows:
            d=codec.encode_factor(np.zeros((128,768)),target_sha256='a'*64,anchor_target_sha256='b'*64,
                record_id=r['id'],token_sha256=digest(canonical_json(r['tokens'])),stage_id=config.STAGE)
            payloads[config.STAGE,r['id']]=codec.serialize(d)
        return rows,payloads

    def test_actual_stage_type_without_rows_attribute(self):
        s=self.full_stage();self.assertFalse(hasattr(s,'rows'));self.assertIs(stage.select_stage([s]),s)

    def test_stage_absent(self):
        with self.assertRaises(ValueError):stage.select_stage([])

    def test_stage_duplicate(self):
        s=self.full_stage()
        with self.assertRaises(ValueError):stage.select_stage([s,s])

    def test_stage_wrong_extent(self):
        with self.assertRaises(ValueError):stage.select_stage([dataclasses.replace(self.full_stage(),weights=((0.,)*768,))])

    def test_point_bytes_and_order(self):
        rows,payloads=self.data();p,ids=stage.decode_points(self.full_stage(),rows,payloads,'a'*64,'b'*64)
        self.assertEqual([x.shape for x in p],[(768,128)]*3)
        self.assertTrue(all(x['source_sha256']==x['point_sha256'] for x in ids))

    def test_changed_tokens_refused(self):
        rows,payloads=self.data();rows[0]['tokens'][0]=17
        with self.assertRaises(ValueError):stage.decode_points(self.full_stage(),rows,payloads,'a'*64,'b'*64)

    def test_changed_target_refused(self):
        rows,payloads=self.data()
        with self.assertRaises(ValueError):stage.decode_points(self.full_stage(),rows,payloads,'c'*64,'b'*64)

    def test_missing_retained_source_refused(self):
        rows,payloads=self.data();del payloads[config.STAGE,rows[1]['id']]
        with self.assertRaises(KeyError):stage.decode_points(self.full_stage(),rows,payloads,'a'*64,'b'*64)

    def test_reordered_sources_refused(self):
        rows,payloads=self.data()
        with self.assertRaises(ValueError):stage.decode_points(self.full_stage(),rows[::-1],payloads,'a'*64,'b'*64)

    def test_only_token_point_route_dispatched(self):
        spec=self.spec();points=[np.zeros((2,128)) for _ in range(3)];ad=dict(admitted=True,selected_route='token')
        answer=SimpleNamespace(route='token',admission=ad,codes=np.zeros((1,2)))
        with patch.object(dispatcher,'assess_stage',return_value=ad),patch.object(dispatcher,'solve_blocks',return_value=answer) as call:
            result,code=stage.solve_token(spec,np.zeros((1,2)),points)
        self.assertIs(result,answer);self.assertEqual(code.rows*code.columns,2);call.assert_called_once()
        self.assertEqual(call.call_args.kwargs['kind'],'point');self.assertEqual(call.call_args.kwargs['route'],'token')
        self.assertEqual(call.call_args.kwargs['policy'],dispatcher.ResourcePolicy())

    def test_refusal_not_retried(self):
        ad=dict(admitted=True,selected_route='token')
        with patch.object(dispatcher,'assess_stage',return_value=ad),patch.object(dispatcher,'solve_blocks',side_effect=RuntimeError('refused')) as call:
            with self.assertRaisesRegex(RuntimeError,'refused'):stage.solve_token(self.spec(),np.zeros((1,2)),[np.zeros((2,128))]*3)
        call.assert_called_once()

    def test_failed_admission_no_numerical_call(self):
        with patch.object(dispatcher,'assess_stage',return_value=dict(admitted=False)),patch.object(dispatcher,'solve_blocks') as call:
            with self.assertRaises(ValueError):stage.solve_token(self.spec(),np.zeros((1,2)),[np.zeros((2,128))]*3)
        call.assert_not_called()

    def test_remaining_caps_not_reset(self):
        d=config.design()
        for carry,add,cap in [('carried_numerical_seconds','diagnostic_cpu_reservation','original_numerical_ceiling'),
            ('carried_software_seconds','software_aggregate_seconds','original_software_ceiling'),
            ('carried_checks_controller_seconds','checks_controller_seconds','original_checks_controller_ceiling'),
            ('carried_numerical_controller_seconds','numerical_controller_seconds','original_numerical_controller_ceiling')]:
            self.assertLessEqual(d[carry]+d[add],d[cap])
        self.assertEqual(d['exact_refinement_coordinates'],16)

    def test_no_original_operation_in_new_registry(self):
        self.assertEqual(config.OPERATIONS,('checks','diagnostic'))
        with self.assertRaises(ValueError):config.name('gpt2/reference_compressed-1')

    def test_storage_plan_source_binding(self):
        sources={'x.py':dict(bytes=1,sha256='0'*64)};p=storage_plan.build(sources,10240)
        requests=storage_plan.requests(p,sources,10240,'diagnostic')
        self.assertEqual(requests['temporary']['path'],'/tmp');self.assertGreater(requests['project']['required_bytes'],2**30)
        with self.assertRaises(ValueError):storage_plan.requests(dict(p,diagnostic_output_bytes=1),sources,10240,'diagnostic')

    def test_output_stage_extent(self):
        self.assertEqual(3072*768//2,1179648)
        self.assertLess(3072*768//2+2**20,4*2**20)


if __name__=='__main__':unittest.main()
