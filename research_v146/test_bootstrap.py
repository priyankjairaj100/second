import json,tempfile,unittest,zipfile,sys
from pathlib import Path
from research_v146.bootstrap import install,ident
from research_v146.worker import selected_records

class BootstrapTest(unittest.TestCase):
 def fixture(self,root,name='pkg/value.txt'):
  (root/'wheels').mkdir();wheel=root/'wheels/test.whl'
  with zipfile.ZipFile(wheel,'w') as z:z.writestr(name,b'original')
  return dict(wheels=[dict(file='test.whl',**ident(wheel.read_bytes()))])
 def test_complete_member_rehash(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=self.fixture(root);first=install(root,p,True)
   self.assertEqual(first,install(root,p,False))
   (root/'deps/pkg/value.txt').write_bytes(b'changed')
   with self.assertRaises(AssertionError):install(root,p,False)
 def test_previously_missing_directory_cache(self):
  import importlib
  name='v146_fresh_import_probe'
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);deps=str(root/'deps');sys.path.insert(0,deps)
   try:
    with self.assertRaises(ModuleNotFoundError):importlib.import_module(name)
    self.assertIsNone(sys.path_importer_cache[deps])
    (root/'wheels').mkdir();w=root/'wheels/test.whl'
    with zipfile.ZipFile(w,'w') as z:z.writestr(name+'.py','value=146')
    p=dict(wheels=[dict(file='test.whl',**ident(w.read_bytes()))]);install(root,p,True)
    self.assertEqual(importlib.import_module(name).value,146)
   finally:
    sys.modules.pop(name,None);sys.path[:]=[x for x in sys.path if x!=deps];sys.path_importer_cache.pop(deps,None)
 def test_reject_parent_traversal(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=self.fixture(root,'../escaped')
   with self.assertRaises(AssertionError):install(root,p,True)
   self.assertFalse((root/'escaped').exists())
 def test_reject_changed_wheel(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=self.fixture(root);(root/'wheels/test.whl').write_bytes(b'changed')
   with self.assertRaises(AssertionError):install(root,p,True)
 def test_reject_second_install(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=self.fixture(root);install(root,p,True)
   with self.assertRaises(FileExistsError):install(root,p,True)
 def test_selected_ids_exact(self):
  rows=[dict(id='%02d'%i,tokens=[i]*128) for i in range(13)]
  self.assertEqual(selected_records(rows,['01','03','05','08']),[rows[i] for i in (1,3,5,8)])
  with self.assertRaises(AssertionError):selected_records(rows,['01','03','05','14'])
 def test_duplicate_and_out_of_vocabulary_refused(self):
  rows=[dict(id='%02d'%i,tokens=[i]*128) for i in range(13)]
  rows[0]['tokens'][0]=50257
  with self.assertRaises(AssertionError):selected_records(rows,['01','03','05','08'])
  rows[0]['tokens'][0]=0;rows[0]['id']='01'
  with self.assertRaises(AssertionError):selected_records(rows,['01','03','05','08'])

if __name__=='__main__':unittest.main()
