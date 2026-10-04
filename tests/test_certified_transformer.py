"""Correctness fixtures, not empirical datasets or performance benchmarks."""
from fractions import Fraction as Q
import unittest

from src.certified_transformer import AffineChart, AutomaticResponseProvider, CertifiedDecoder
from src.transformer_backend import DecoderConfig, DeterministicDecoder
from src.repair_service import Record, StageSpec
from src.response_moments import ResponseIndex
from src.linear_response import LinearResponseIndex, shifted_linear_response_bound
from tests.test_transformer_backend import decoder_fixture


def small_decoder(activation='gelu'):
    z, a, delta = Q(0), Q(1, 4), Q(1, 4096)
    base = DeterministicDecoder(
        DecoderConfig(3, 2, 1, 2, 1, 4, activation=activation),
        token_embeddings=((1, 0), (0, 1), (1, -1)),
        position_embeddings=((0, 0), (a, -a), (-a, a), (a, a)),
        blocks=({'qkv': ((a,z),(z,a),(a,z),(z,a),(a+delta,z),(z,a)),
                 'attn_out': ((a,z),(z,a)), 'mlp_up': ((1,z),(z,1)),
                 'mlp_down': ((a,z),(z,a))},),
        lm_head=((1,z),(z,1),(1,-1)),
    )
    decoder = CertifiedDecoder(base)
    first = decoder.stage_ids[0]
    direction = tuple(tuple(-delta if (i,j)==(4,0) else z for j in range(2)) for i in range(6))
    chart = AffineChart(({first:direction},), (Q(1),), 'fixed coordinate direction before corpus construction')
    return decoder, chart


def grids(decoder):
    grid = (Q(-1),Q(-1,4),Q(0),Q(1,4),Q(1))
    return {stage: tuple(grid for _ in decoder.stage_weights(stage)[0]) for stage in decoder.stage_ids}


class CertifiedTransformerTests(unittest.TestCase):
    def test_full_program_distinct_identity_and_causality(self):
        base = decoder_fixture()
        decoder = CertifiedDecoder(base)
        self.assertNotEqual(decoder.evaluator_id, base.evaluator_id)
        self.assertEqual(decoder.logits((0,1)), decoder.logits((0,1,2))[:2])
        self.assertEqual(decoder.exact_logits((0,1)), decoder.exact_logits((0,1)))
        with self.assertRaises(AttributeError): decoder.base = decoder_fixture()
        for activation in ('gelu','gelu_new'):
            d,_ = small_decoder(activation)
            self.assertEqual(len(d.logits((0,1))),2)

    def test_automatic_descriptor_bounds_actual_changed_features(self):
        decoder,chart = small_decoder()
        provider = AutomaticResponseProvider(decoder,chart)
        first = decoder.stage_ids[0]
        prefix = {first:tuple(tuple(v+chart.directions[0][first][i][j]
                                  for j,v in enumerate(row)) for i,row in enumerate(decoder.stage_weights(first)))}
        target_stage = decoder.stage_ids[-1]
        self.assertNotEqual(decoder.stage_features(target_stage,(0,1)),decoder.stage_features(target_stage,(0,1),prefix))
        record=Record('proof-record',decoder.record_payload((0,1)))
        stage=StageSpec(target_stage,decoder.dependencies(target_stage),decoder.stage_weights(target_stage),grids(decoder)[target_stage],1,1)
        moments=provider.intrinsic_moments(record,stage)
        self.assertIsNotNone(moments)
        response,error=moments
        bound=shifted_linear_response_bound(LinearResponseIndex.from_records(response.basis,(response,)),
                                            ResponseIndex.from_records(error.basis,(error,)),(Q(1),),1,1)
        x=decoder.stage_features(target_stage,(0,1),prefix)
        true=tuple(tuple(sum(a*b for a,b in zip(xi,xj)) for xj in x) for xi in x)
        # Frobenius controls spectral norm. A direct eigenvalue-free PSD check
        # verifies both Loewner sides for this two-dimensional fixture.
        from src.repair_service import _is_psd
        raw=bound.raw_surrogate_gram
        beta=bound.omitted_psd_trace_normalized
        delta=bound.response_gram_error_normalized
        lower=tuple(tuple(true[i][j]-raw[i][j]+((beta+delta) if i==j else 0) for j in range(2)) for i in range(2))
        upper=tuple(tuple(raw[i][j]-true[i][j]+(delta if i==j else 0) for j in range(2)) for i in range(2))
        self.assertTrue(_is_psd(lower))
        self.assertTrue(_is_psd(upper))

    def test_exact_chart_and_box_rejection(self):
        decoder,chart=small_decoder()
        provider=AutomaticResponseProvider(decoder,chart)
        first,second=decoder.stage_ids[:2]
        base=decoder.stage_weights(first)
        def changed(i,j,amount):
            return {first:tuple(tuple(x+(amount if (r,c)==(i,j) else 0) for c,x in enumerate(row)) for r,row in enumerate(base))}
        self.assertEqual(provider.coefficients(second,changed(4,0,-Q(1,4096))),(Q(1),))
        self.assertIsNone(provider.coefficients(second,changed(4,0,-Q(2,4096))))
        self.assertIsNone(provider.coefficients(second,changed(0,0,Q(1,4096))))
        self.assertEqual(provider.coefficients(first,changed(0,0,Q(1,4096))),(Q(0),))
        with self.assertRaises(TypeError):
            AffineChart(({first:((0.1,0),)*6},),(1,),'bad float direction')

    def test_changed_prefix_compact_repair_avoids_retained_reads(self):
        decoder,chart=small_decoder()
        service=decoder.make_repair_service(grids(decoder),chart,group_count=1)
        records=tuple(Record(str(i),decoder.record_payload(tokens)) for i,tokens in enumerate(((0,1),(1,0),(0,2))))
        old=service.fresh(records)
        first=decoder.stage_ids[0]
        old_codes={output.stage_id:output.codes for output in old.state.model}
        self.assertNotEqual(old_codes[first],decoder.stage_weights(first))
        self.assertNotEqual(decoder.stage_features(decoder.stage_ids[-1],(0,1)),
                            decoder.stage_features(decoder.stage_ids[-1],(0,1),old_codes))
        reads=[]
        def no_reads(rid):
            reads.append(rid)
            raise AssertionError('the certified fixture must not read retained source')
        repaired=service.repair(old.state,(records[0],),no_reads)
        fresh=service.fresh(records[1:])
        self.assertEqual(repaired.state.canonical_bytes(),fresh.state.canonical_bytes())
        self.assertEqual(reads,[])
        self.assertEqual(repaired.ledger.count('retained_replay_evaluator_calls'),0)
        self.assertGreater(repaired.ledger.count('certificate_factorization_calls'),0)
        repeated=service.repair(repaired.state,(records[1],),no_reads)
        self.assertEqual(repeated.state.canonical_bytes(),service.fresh(records[2:]).state.canonical_bytes())
        self.assertEqual(decoder.exact_logits((0,1),{x.stage_id:x.codes for x in repaired.state.model}),
                         decoder.exact_logits((0,1),{x.stage_id:x.codes for x in fresh.state.model}))
        for group in repaired.state.groups:
            for stage in group.stages:
                if stage.response is not None: self.assertEqual(stage.response.records,())
                if stage.error is not None: self.assertEqual(stage.error.records,())

    def test_deletion_changes_first_stage_with_zero_retained_replay(self):
        decoder,_=small_decoder()
        base=decoder.base
        delta=Q(1,4096)
        block=dict(base._blocks[0])
        qkv=[list(row) for row in block['qkv']]
        qkv[4][1]=17*delta/6
        block['qkv']=qkv
        changed=CertifiedDecoder(DeterministicDecoder(base.config,
            token_embeddings=base._token_embeddings,position_embeddings=base._position_embeddings,
            blocks=(block,),lm_head=base._lm_head))
        first=changed.stage_ids[0]
        base_second=Q.from_float(float(qkv[4][1]))
        d0=tuple(tuple(-delta if (i,j)==(4,0) else (-base_second if (i,j)==(4,1) else Q(0))
                       for j in range(2)) for i in range(6))
        d1=tuple(tuple(4*delta if (i,j)==(4,1) else Q(0) for j in range(2)) for i in range(6))
        chart=AffineChart(({first:d0},{first:d1}),(Q(1),Q(1)),'fixed two-coordinate chart before records')
        grid=(Q(-1),Q(-1,4),Q(0),4*delta,Q(1,4),Q(1))
        configured={stage:tuple(grid for _ in changed.stage_weights(stage)[0]) for stage in changed.stage_ids}
        service=changed.make_repair_service(configured,chart,group_count=1)
        records=tuple(Record(str(i),changed.record_payload(tokens))
                      for i,tokens in enumerate(((0,1),(1,0),(0,2))))
        old=service.fresh(records)
        def forbid(rid): raise AssertionError('unexpected retained replay')
        repaired=service.repair(old.state,(records[0],),forbid)
        fresh=service.fresh(records[1:])
        self.assertNotEqual(old.state.model[0].codes,repaired.state.model[0].codes)
        self.assertEqual(old.state.model[0].codes[4][1],Q(0))
        self.assertEqual(repaired.state.model[0].codes[4][1],4*delta)
        self.assertEqual(repaired.state.canonical_bytes(),fresh.state.canonical_bytes())
        self.assertEqual(repaired.ledger.count('retained_replay_evaluator_calls'),0)
        old_prefix={x.stage_id:x.codes for x in old.state.model}
        new_prefix={x.stage_id:x.codes for x in repaired.state.model}
        self.assertNotEqual(changed.stage_features(changed.stage_ids[-1],(1,0),old_prefix),
                            changed.stage_features(changed.stage_ids[-1],(1,0),new_prefix))

    def test_out_of_chart_replays_and_matches_fresh(self):
        decoder,chart=small_decoder()
        empty=AffineChart((),(),'fixed empty chart')
        service=decoder.make_repair_service(grids(decoder),empty,group_count=1)
        records=(Record('a',decoder.record_payload((0,1))),Record('b',decoder.record_payload((1,0))))
        old=service.fresh(records)
        repaired=service.repair(old.state,(records[0],),lambda rid:records[1])
        self.assertGreater(repaired.ledger.count('retained_replay_evaluator_calls'),0)
        self.assertEqual(repaired.state.canonical_bytes(),service.fresh(records[1:]).state.canonical_bytes())


if __name__=='__main__': unittest.main()
