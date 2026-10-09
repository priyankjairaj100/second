"""Protocol fixtures only; no real-data Gram or quantization outcomes are read."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import execute_gram_ball_stage_v37 as worker
from scripts import launch_gram_ball_stage_v37 as controller

class BallStageProtocolTests(unittest.TestCase):
    def test_narrow_fallback_refusal_is_scientific(self):
        from research_v37.direct_gram_ball import DirectGramBallUnresolved
        self.assertTrue(worker.scientific_refusal(DirectGramBallUnresolved('primal native row verification failed: status=3, row=4, coordinate=123')))
        self.assertFalse(worker.scientific_refusal(DirectGramBallUnresolved('primal native row verification failed: status=2, row=4, coordinate=123')))
        self.assertFalse(worker.scientific_refusal(DirectGramBallUnresolved('ball row runtime or allocation failure')))

    def test_coefficient_and_token_budget_refusals_preserved(self):
        from research_v35.direct_gram import DirectGramUnresolved
        from src.low_rank_certified import LowRankUnresolved
        self.assertTrue(worker.scientific_refusal(DirectGramUnresolved('direct Gram coefficient enclosure failed at coordinate 7: status=2')))
        self.assertTrue(worker.scientific_refusal(LowRankUnresolved('exact fallback budget exceeded at coordinate 7; no codes committed')))
        self.assertFalse(worker.scientific_refusal(ValueError('exact fallback budget exceeded at coordinate 7; no codes committed')))

    def test_unrecognized_refusal_stops(self):
        from research_v37.direct_gram_ball import DirectGramBallUnresolved
        for message in ('direct Gram ball row verification unresolved: row=3, coordinate=8','compiler failed','nonfinite runtime','primal native row verification failed: status=1, row=3, coordinate=8'):
            self.assertFalse(worker.scientific_refusal(DirectGramBallUnresolved(message)))

    def test_full_stage_admits_charged_fallback(self):
        from research_v37.direct_gram_ball import assess_direct_gram_ball_budget
        from src.primal_certificate_v30 import PrimalBudget
        result=assess_direct_gram_ball_budget(rows=2304,width=768,budget=PrimalBudget(max_workspace_bytes=512*2**20,max_work_units=6_000_000_000))
        self.assertTrue(result['admitted']);self.assertEqual(result['rows']*result['width'],1_769_472)
        self.assertGreater(result['work_units'],1_812_013_056)
        self.assertGreaterEqual(result['explicit_array_bytes'],333_250_560)

    def test_existing_campaign_prevents_registration(self):
        with tempfile.TemporaryDirectory() as d,patch.object(controller,'bind_inputs',side_effect=AssertionError('must not load')):
            with self.assertRaises(ValueError):controller.register(Path(d),Path(d)/'capsule.json')

    def test_existing_attempt_prevents_retry(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'attempt').mkdir()
            with patch.object(controller,'verified_program',return_value={}),patch.object(controller,'run_limited',side_effect=AssertionError('must not launch')):
                with self.assertRaises(ValueError):controller.execute(p)

    def test_registered_worker_plan_cannot_be_substituted(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);attempt=p/'attempt';attempt.mkdir()
            program=dict(inputs={},source_sha256={},runtime={},arm_order=controller.ARM_ORDER)
            (p/'program.json').write_bytes(worker.canonical_json(program))
            plan=dict(schema='archive-gram-ball-stage-plan-v37',program_sha256=worker.hashed(p/'program.json'),inputs={},source_sha256={'unregistered':'source'},runtime={},arm_order=controller.ARM_ORDER,output=str(attempt/'outputs'))
            (attempt/'plan.json').write_bytes(worker.canonical_json(plan))
            with self.assertRaisesRegex(ValueError,'plan differs'):controller.verify_terminal(p,program)

    def test_prior_ledgers_are_checked_without_blocking_future_ledgers(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);program=dict(source_sha256={},runtime={},historical_ledgers_sha256={'v36':'sealed'},inputs={})
            (p/'program.json').write_bytes(worker.canonical_json(program));(p/'registration.json').write_text(json.dumps({'program_sha256':worker.hashed(p/'program.json')}))
            with patch.object(controller,'current_sources',return_value={}),patch.object(controller,'capture_runtime_contract',return_value={}),patch.object(controller,'verify_inputs'),patch.object(controller,'historical_ledgers',return_value={'v36':'sealed','future':'new'}):
                self.assertEqual(controller.verified_program(p),program)
            with patch.object(controller,'current_sources',return_value={}),patch.object(controller,'capture_runtime_contract',return_value={}),patch.object(controller,'verify_inputs'),patch.object(controller,'historical_ledgers',return_value={'v36':'changed'}):
                with self.assertRaisesRegex(ValueError,'bound historical'):controller.verified_program(p)

if __name__=='__main__':unittest.main()
