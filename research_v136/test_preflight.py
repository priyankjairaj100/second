import unittest
from research_v136.preflight import validate
class Preflight(unittest.TestCase):
 def fixture(self):return dict(path='/actual/file',bytes=1,sha256='a'*64)
 def test_exact_valid_binding(self):self.assertEqual(validate([self.fixture()]),1)
 def test_registration_string_rejected(self):
  with self.assertRaises(ValueError):validate([self.fixture(),'a'*64])
 def test_invalid_fields_rejected(self):
  for change in [dict(bytes=True),dict(path='../bad'),dict(sha256='bad'),dict(extra='value')]:
   x=self.fixture();x.update(change)
   with self.assertRaises(ValueError):validate([x])
 def test_conflicting_same_path_rejected(self):
  x=self.fixture();x['sha256']='b'*64
  with self.assertRaises(ValueError):validate([self.fixture(),x])
