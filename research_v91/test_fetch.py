"""New finite fetch receipts retain failed partials and redact redirect errors."""
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from research_v80.io import info,json_read
from research_v91 import fetch
class Response(io.BytesIO):
    url='https://huggingface.co/fixture'
class Opener:
    def __init__(self,blobs):self.blobs=iter(blobs)
    def open(self,*args,**kwargs):return Response(next(self.blobs))
class Fetch(unittest.TestCase):
    def test_exact_stream_receipt_and_directory_reuse(self):
        with TemporaryDirectory() as d,patch.object(fetch,'EXPECTED',{'config.json':info(b'ab')}),patch.object(fetch.urllib.request,'build_opener',return_value=Opener([b'ab'])):
            root=Path(d).resolve()/'input';r=fetch.fetch_checkpoint(root)
            self.assertEqual(fetch.verify_fetch(root),r)
            with self.assertRaises(FileExistsError):fetch.fetch_checkpoint(root)
    def test_failed_hash_retains_bytes_and_only_error_type(self):
        with TemporaryDirectory() as d,patch.object(fetch,'EXPECTED',{'config.json':info(b'ab')}),patch.object(fetch.urllib.request,'build_opener',return_value=Opener([b'ac'])):
            root=Path(d).resolve()/'input'
            with self.assertRaises(ValueError):fetch.fetch_checkpoint(root)
            self.assertEqual((root/'config.json').read_bytes(),b'ac');r=json_read(root/'fetch-receipt.json')
            self.assertEqual(r['status'],'failed');self.assertEqual(r['error_type'],'ValueError');self.assertNotIn('error',r)
            with self.assertRaises(ValueError):fetch.verify_fetch(root)
    def test_signed_url_in_transport_error_is_not_serialized(self):
        with TemporaryDirectory() as d,patch.object(fetch.urllib.request,'build_opener') as factory:
            factory.return_value.open.side_effect=RuntimeError('https://secret?signature=private')
            root=Path(d).resolve()/'input'
            with self.assertRaises(RuntimeError):fetch.fetch_checkpoint(root)
            self.assertNotIn(b'private',(root/'fetch-receipt.json').read_bytes())
    def test_unexpected_output_prevents_completed_fetch_admission(self):
        with TemporaryDirectory() as d,patch.object(fetch,'EXPECTED',{'config.json':info(b'ab')}),patch.object(fetch.urllib.request,'build_opener',return_value=Opener([b'ab'])):
            root=Path(d).resolve()/'input';fetch.fetch_checkpoint(root);(root/'extra').write_bytes(b'x')
            with self.assertRaises(ValueError):fetch.verify_fetch(root)
if __name__=='__main__':unittest.main()
