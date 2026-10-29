"""Pure filesystem/refusal checks; no numerical imports or Linux qualification."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research_v87 import outputs as o


class OutputLimits(unittest.TestCase):
    def root(self, folder):
        return Path(folder).resolve()/'outputs'

    def test_complete_oracle_writes_distinct_models_and_all_artifacts(self):
        names={'step-1/model.bin','step-2/model.bin','step-1/state.bin','admission.json'}
        with tempfile.TemporaryDirectory() as d:
            root=self.root(d);w=o.Outputs(root,names,4)
            for name in names:w.artifact(name,b'1234' if name.endswith('model.bin') else b'{}')
            w.progress({'phase':'fixture'})
            w.finish({'status':'complete','complete_model':True})
            self.assertEqual(json.loads((root/'completion.json').read_bytes())['status'],'complete')
            self.assertLessEqual(sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),o.allowance(names,4)['output_bytes'])

    def test_wrong_model_size_refuses_before_file_creation_and_keeps_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.root(d);w=o.Outputs(root,{'model.bin'},4)
            with self.assertRaisesRegex(ValueError,'extent differs'):w.artifact('model.bin',b'123')
            self.assertFalse((root/'model.bin').exists())
            with self.assertRaisesRegex(ValueError,'promoted'):w.finish({'status':'complete','complete_model':True})
            w.finish({'status':'failed','complete_model':False})

    def test_binary_and_metadata_limits_are_checked_before_writing(self):
        for name,limit in [('state.bin','STATE_BYTES'),('trust.json','METADATA_BYTES')]:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d,patch.object(o,limit,8):
                root=self.root(d);w=o.Outputs(root,{name},4)
                with self.assertRaisesRegex(ValueError,'allowance'):w.artifact(name,b'x'*9)
                self.assertFalse((root/name).exists())

    def test_unknown_traversal_and_reserved_names_refuse(self):
        for name in ('../model.bin','/model.bin','a//state.bin','a/./state.bin','completion.json','progress-0000.json','blob.xyz'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
                root=self.root(d)
                with self.assertRaises(ValueError):o.Outputs(root,{name},4)
                self.assertFalse(root.exists())
        with tempfile.TemporaryDirectory() as d:
            w=o.Outputs(self.root(d),{'state.bin'},4)
            with self.assertRaisesRegex(ValueError,'Unknown'):w.artifact('other.json',b'{}')

    def test_progress_count_and_extent_are_bounded(self):
        with tempfile.TemporaryDirectory() as d,patch.object(o,'PROGRESS_FILES',2):
            root=self.root(d);w=o.Outputs(root,{'state.bin'},4)
            w.progress({});w.progress({})
            with self.assertRaisesRegex(ValueError,'count'):w.progress({})
            self.assertEqual(len(list(root.glob('progress-*.json'))),2)
            w.finish({'status':'failed','complete_model':False})
        with tempfile.TemporaryDirectory() as d,patch.object(o,'PROGRESS_BYTES',8):
            root=self.root(d);w=o.Outputs(root,{'state.bin'},4)
            with self.assertRaisesRegex(ValueError,'allowance'):w.progress({'large':'value'})
            self.assertFalse(list(root.glob('progress-*.json')))

    def test_existing_output_directory_or_artifact_is_never_retried(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.root(d);w=o.Outputs(root,{'state.bin'},4);w.artifact('state.bin',b'old')
            with self.assertRaises(ValueError):w.artifact('state.bin',b'new')
            with self.assertRaises(FileExistsError):o.Outputs(root,{'state.bin'},4)
            self.assertEqual((root/'state.bin').read_bytes(),b'old')

    def test_symlink_parent_cannot_redirect_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.root(d);w=o.Outputs(root,{'step-1/state.bin'},4)
            elsewhere=root.parent/'elsewhere';elsewhere.mkdir();(root/'step-1').symlink_to(elsewhere,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'Symlink'):w.artifact('step-1/state.bin',b'bad')
            self.assertEqual(list(elsewhere.iterdir()),[])

    def test_partial_io_failure_preserves_bytes_and_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.root(d);w=o.Outputs(root,{'state.bin'},4);original=o.os.write;calls=[]
            def interrupted(fd,data):
                calls.append(1)
                if len(calls)==1:return original(fd,data[:2])
                raise OSError('fixture quota failure')
            with patch.object(o.os,'write',side_effect=interrupted):
                with self.assertRaisesRegex(OSError,'quota failure'):w.artifact('state.bin',b'partial')
            self.assertEqual((root/'state.bin').read_bytes(),b'pa')
            with self.assertRaisesRegex(ValueError,'promoted'):w.finish({'status':'complete','complete_model':True})
            w.finish({'status':'failed','complete_model':False})

    def test_incomplete_and_mislabeled_completions_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            w=o.Outputs(self.root(d),{'model.bin','state.bin'},4);w.artifact('model.bin',b'1234')
            for result in ({'status':'complete','complete_model':True},{'status':'failed','complete_model':True},{'status':'running','complete_model':False}):
                with self.assertRaises(ValueError):w.finish(result)
            w.finish({'status':'failed','complete_model':False})
            with self.assertRaises(ValueError):w.finish({'status':'failed','complete_model':False})

    def test_failed_completion_is_consumed_without_rewriting(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.root(d);w=o.Outputs(root,{'state.bin'},4)
            with patch.object(o.os,'fsync',side_effect=OSError('fixture sync failure')):
                with self.assertRaises(OSError):w.finish({'status':'failed','complete_model':False})
            before=(root/'completion.json').read_bytes()
            with self.assertRaises(ValueError):w.finish({'status':'failed','complete_model':False})
            self.assertEqual((root/'completion.json').read_bytes(),before)

    def test_completion_retains_existing_canonical_json_tuple_semantics(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.root(d);w=o.Outputs(root,{'state.bin'},4);w.artifact('state.bin',b'fixture')
            w.finish({'status':'complete','complete_model':True,'metadata':('a','b')})
            self.assertEqual(json.loads((root/'completion.json').read_bytes())['metadata'],['a','b'])

    def test_saved_census_refuses_extra_files_and_progress_gaps(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.root(d);names={'state.bin'};w=o.Outputs(root,names,4)
            w.artifact('state.bin',b'fixture');w.progress({});w.finish({'status':'complete','complete_model':True})
            report=o.inspect_outputs(root,names,4)
            self.assertEqual(report['output_files'],3);self.assertFalse(report['scientific_correctness_checked'])
            extra=root/'unexpected.bin';extra.write_bytes(b'extra')
            with self.assertRaisesRegex(ValueError,'Unknown output file'):o.inspect_outputs(root,names,4)
            extra.unlink();(root/'progress-0000.json').rename(root/'progress-0001.json')
            with self.assertRaisesRegex(ValueError,'Progress sequence'):o.inspect_outputs(root,names,4)

    def test_saved_census_refuses_oversize_and_missing_files(self):
        with tempfile.TemporaryDirectory() as d,patch.object(o,'STATE_BYTES',8):
            root=self.root(d);names={'state.bin'};w=o.Outputs(root,names,4)
            w.artifact('state.bin',b'fixture');w.finish({'status':'complete','complete_model':True})
            (root/'state.bin').write_bytes(b'x'*9)
            with self.assertRaisesRegex(ValueError,'exceeds allowance'):o.inspect_outputs(root,names,4)
            (root/'state.bin').unlink()
            with self.assertRaisesRegex(ValueError,'Missing complete'):o.inspect_outputs(root,names,4)


if __name__=='__main__':unittest.main()
