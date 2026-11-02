import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import check_v63_metadata as c
import collect_v63_metadata as collect


class MetadataTests(unittest.TestCase):
    def test_safe_paths_refuse_escape_and_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();(root/'a').write_bytes(b'{}');(root/'link').symlink_to(root/'a')
            self.assertEqual(c.safe(root,'a'),root/'a')
            for n in ('../a',str(root/'a'),'link'):
                with self.assertRaises(ValueError):c.safe(root,n)
    def test_collector_requires_all_terminal_jobs(self):
        with patch.object(collect,'command',side_effect=['15245|RUNNING|node']):
            with self.assertRaises(ValueError):collect.scheduler()
        raw='\n'.join(j+'|name|COMPLETED|0:0|20|00:00:19|1K|start|end|' for j in collect.JOBS.values())
        with patch.object(collect,'command',side_effect=['',raw]):self.assertTrue(collect.scheduler()['successful'])
        with patch.object(collect,'command',side_effect=['',raw.replace('COMPLETED','TIMEOUT',1)]):self.assertFalse(collect.scheduler()['successful'])
        with patch.object(collect,'command',side_effect=['','\n'.join(raw.splitlines()[:-1])]):
            with self.assertRaises(ValueError):collect.scheduler()


if __name__=='__main__':unittest.main()
