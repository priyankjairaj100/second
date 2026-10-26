"""Preparation must succeed without importing container-only numerical packages."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
from research_v110 import prepare,dispatch_failure
from research_v110.records import writer
from research_v104 import campaign as parent
from research_v80.io import info,json_read
from src.run_store import canonical_json


class Boundary(unittest.TestCase):
    def test_actual_host_prepare_defers_numerical_runtime_to_container(self):
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            root=Path(directory).resolve();sources={'x.py':info(b'x')};sha=info(canonical_json(sources))['sha256']
            old=dict(checkpoint_paths={'gpt2':'fixed-checkpoint'},admitted_targets={'gpt2':{'fixed':'target'}})
            stack.enter_context(patch.object(prepare,'RUN',root))
            stack.enter_context(patch.object(prepare,'__file__',str(root/'research_v110/prepare.py')))
            stack.enter_context(patch.object(dispatch_failure,'verify',return_value={'actual_fixture':True}))
            def verify(*,prerequisite):
                if prerequisite:raise ModuleNotFoundError('Host intentionally lacks gmpy2')
                return old
            called=stack.enter_context(patch.object(parent,'verify',side_effect=verify))
            stack.enter_context(patch.object(parent,'sha',return_value=prepare.PARENT_SHA))
            stack.enter_context(patch.object(prepare,'json_read',return_value=sources))
            stack.enter_context(patch.object(prepare,'read',return_value=dict(bytes=10240,sha256='a'*64)))
            stack.enter_context(patch.object(prepare,'inspect',return_value={'fixture_only':True}))
            stack.enter_context(patch.object(prepare,'writer',side_effect=lambda:writer(root)))
            prepare.main(sha,'a'*64)
            called.assert_called_once_with(prerequisite=False)
            self.assertEqual(json_read(root/'program.json')['checkpoint_path'],'fixed-checkpoint')


if __name__=='__main__':unittest.main()
