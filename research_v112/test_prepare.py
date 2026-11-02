"""Host preparation and old-output reuse guards; synthetic files only."""
from contextlib import ExitStack,redirect_stdout
from pathlib import Path
import io,tempfile,unittest
from unittest.mock import patch
from research_v112 import prepare,dispatch_failure,preparations,config
from research_v112.records import writer
from research_v80.io import info,json_read,write
from src.run_store import canonical_json

class Prepare(unittest.TestCase):
    def test_actual_host_preparation_uses_bound_old_preparations_without_runtime_import(self):
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            root=Path(directory).resolve();sources={'x.py':info(b'x'),'gates/target-admission-terminal.json':info(b'{}')}
            archive=dict(bytes=10240,sha256='a'*64)
            admission=dict(checkpoint_paths={p:'fixed/'+p for p in config.PROFILES},profiles={p:dict(checkpoint_files=['model.bin']) for p in config.PROFILES})
            close=dict(seal_audit=dict(models={p:dict(artifacts={'target.json':info(b'fixed')}) for p in config.PROFILES}))
            stack.enter_context(patch.object(prepare,'RUN',root));stack.enter_context(patch.object(prepare,'__file__',str(root/'research_v112/prepare.py')))
            stack.enter_context(patch.object(dispatch_failure,'verify',return_value={'synthetic':True}))
            stack.enter_context(patch.object(prepare,'json_read',return_value=sources))
            stack.enter_context(patch.object(prepare,'read',return_value=archive))
            stack.enter_context(patch.object(prepare,'verify_gate',return_value=({'synthetic':True},admission,close)))
            stack.enter_context(patch.object(prepare,'inspect',return_value={'synthetic':True}))
            stack.enter_context(patch.object(prepare,'writer',side_effect=lambda:writer(root)))
            stack.enter_context(patch.object(preparations,'bindings',return_value={'synthetic':'preparation'}))
            with redirect_stdout(io.StringIO()):prepare.main(info(canonical_json(sources))['sha256'],'a'*64)
            p=json_read(root/'program.json');self.assertEqual(p['reused_preparations'],{'synthetic':'preparation'})
            self.assertEqual(len(p['trial_order']),18);self.assertEqual(p['phase_cpu_seconds']+p['carried_numerical_seconds'],78340)
            with self.assertRaisesRegex(ValueError,'consumed'):prepare.main(info(canonical_json(sources))['sha256'],'a'*64)
    def test_old_preparations_require_original_program_and_complete_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            for profile in config.PROFILES:
                write(root/profile/'prepare/outputs/completion.json',dict(status='complete',complete_model=True,program_sha256=config.PARENT_SHA,trial=profile+'/prepare'))
            with patch.object(preparations,'PARENT',root):
                self.assertEqual(set(preparations.bindings()),set(config.PROFILES))
                q=root/'gpt2/prepare/outputs/completion.json';q.write_bytes(canonical_json(dict(json_read(q),complete_model=False)))
                with self.assertRaises(ValueError):preparations.bindings()
    def test_reused_output_path_is_fixed_by_step_and_preparation_cannot_launch(self):
        for cell in config.CELLS:
            for profile in config.PROFILES:
                self.assertEqual(config.predecessor_directory(profile+'/'+cell+'-1'),config.PARENT/profile/'prepare/outputs')
                self.assertEqual(config.predecessor_directory(profile+'/'+cell+'-2'),config.RUN/profile/(cell+'-1')/'outputs')
        self.assertFalse(any(t.endswith('/prepare') for t in config.ORDER))
        for profile in config.PROFILES:
            with self.assertRaises(ValueError):config.trial_parts(profile+'/prepare')
