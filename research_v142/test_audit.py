import unittest,json,copy
from research_v142.audit import saved_model_checks,ident
from research_v135.source_state import pack
from research_v61.test_target import bind,fixture
from research_v61.test_state import record,codes
from src.run_store import canonical_json
class AuditChecks(unittest.TestCase):
 def setUp(self):
  t=bind(*fixture(((2,4),(1,2)),original=512));r=(record('a',[1,2]),record('b',[3,4]));c=codes(t)
  events=[dict(event='source_replayed',record_id=x.record_id) for x in r]+[dict(event='stage_certified',stage_id=z.stage_id,code_sha256=ident(z.packed_indices)['sha256'],route='token',fallback=False,admission=dict(kind='point',admitted=True,selected_route='token')) for z in c]
  self.args=[pack(t,r,c),b''.join(z.packed_indices for z in c),b'{}',t.anchor_payload,canonical_json(json.loads(t.fixed_payload)['calibration_target']),['a','b'],'tokens',events]
  self.outer=t.fixed_payload
 def test_valid_nested_contract(self):self.assertEqual(saved_model_checks(*self.args)['stages'],2)
 def test_outer_contract_rejected(self):
  self.args[4]=self.outer
  with self.assertRaises(AssertionError):saved_model_checks(*self.args)
 def test_changed_model_rejected(self):
  self.args[1]=self.args[1][:-1]+bytes([self.args[1][-1]^1])
  with self.assertRaises(AssertionError):saved_model_checks(*self.args)
 def test_wrong_membership_rejected(self):
  self.args[5]=['b']
  with self.assertRaises(AssertionError):saved_model_checks(*self.args)
 def test_missing_stage_rejected(self):
  self.args[-1]=self.args[-1][:-1]
  with self.assertRaises(AssertionError):saved_model_checks(*self.args)
 def test_wrong_source_event_rejected(self):
  self.args[-1][0]['record_id']='deleted'
  with self.assertRaises(AssertionError):saved_model_checks(*self.args)
if __name__=='__main__':unittest.main()
