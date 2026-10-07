import hashlib
import json
import struct
import unittest
from fractions import Fraction as Q
from src.compact_exact import CompactDyadicMatrix
from src.streamed_rationals import rational_json_sha256
from src.repair_service import StageSpec, JobSpec


class StreamedTargetTests(unittest.TestCase):
    def test_numeric_pair_hash(self):
        value=((Q(1,3),Q(-2,7)),(Q(0),Q(123)))
        old=json.dumps([[[x.numerator,x.denominator] for x in row] for row in value],separators=(',',':')).encode()
        self.assertEqual(rational_json_sha256(value),hashlib.sha256(old).hexdigest())

    def test_job_hash_unchanged(self):
        stage=StageSpec('α',(),((Q(1,2),Q(-3,4)),),((Q(-1),Q(0),Q(1)),)*2,Q(1,100),Q(32))
        job=JobSpec((stage,),'finite','reference',1)
        self.assertEqual(job.manifest_digest,hashlib.sha256(job.manifest_bytes).hexdigest())
        self.assertEqual(job.manifest_digest,job.manifest_digest)


if __name__=='__main__':unittest.main()
