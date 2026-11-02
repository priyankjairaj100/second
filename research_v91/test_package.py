"""Exact uncompressed tar extent including long-name PAX overhead."""
import io,tarfile,unittest
from research_v91.package import tar_extent
class Package(unittest.TestCase):
    def test_exact_header_padding_for_small_and_long_names(self):
        for files in ({'a.py':b'a'}, {'a'*120+'.py':b'x'*513,'unicode-α.txt':b'x'*1024}):
            stream=io.BytesIO()
            with tarfile.open(fileobj=stream,mode='w|') as archive:
                for name,data in sorted(files.items()):
                    member=tarfile.TarInfo(name);member.size=len(data);member.mode=0o600;archive.addfile(member,io.BytesIO(data))
            self.assertEqual(tar_extent(files),len(stream.getvalue()))
    def test_header_overhead_can_refuse_otherwise_allowed_payload_before_write(self):
        class Extent:
            def __len__(self):return 64*2**20
        with self.assertRaisesRegex(ValueError,'before writing'):tar_extent({'large.py':Extent()})
if __name__=='__main__':unittest.main()
