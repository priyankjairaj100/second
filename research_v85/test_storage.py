"""Pure quota fixtures; no cluster admission or model evidence."""
import unittest
from research_v85.storage import parse_quota,admit,StorageAdmissionError
HEADER='Filesystem blocks quota limit grace files quota limit grace\n'
class StorageGate(unittest.TestCase):
    def test_observed_hard_quota_refuses_despite_terabytes_free(self):
        q=parse_quota(HEADER+'/dev/sdb1 1048576004* 1047527424 1048576000 3days 3306263 0 0\n','/dev/sdb1')
        self.assertEqual(q['used_bytes']-q['hard_limit_bytes'],4096)
        with self.assertRaises(StorageAdmissionError):admit(q,15*2**40,1000000,1,1)
    def test_does_not_rely_on_soft_quota_grace(self):
        q=parse_quota(HEADER+'/dev/sdb1 950* 900 1000 3days 12 0 0\n','/dev/sdb1')
        with self.assertRaises(StorageAdmissionError):admit(q,2**40,100,1,1)
    def test_exact_positive_headroom_and_inode_limit(self):
        q=parse_quota(HEADER+'/dev/sdb1 100 900 1000 12 20 30\n','/dev/sdb1')
        result=admit(q,800*1024,100,800*1024,8)
        self.assertFalse(result['capacity_reserved'])
        with self.assertRaises(StorageAdmissionError):admit(q,2**40,100,1,9)
    def test_filesystem_bytes_and_inodes_can_be_tighter(self):
        q=parse_quota(HEADER+'/dev/sdb1 100 900 1000 12 0 0\n','/dev/sdb1')
        for available_bytes,available_files in [(4,100),(100,4)]:
            with self.assertRaises(StorageAdmissionError):admit(q,available_bytes,available_files,5,5)
    def test_missing_duplicate_rounded_unlimited_and_malformed_rows_refuse(self):
        rows=['/dev/other 100 900 1000 12 0 0\n',
              '/dev/sdb1 100 900 1000 12 0 0\n'*2,
              '/dev/sdb1 100G 900G 1000G 12 0 0\n',
              '/dev/sdb1 100 0 0 12 0 0\n',
              '/dev/sdb1 100 1100 1000 12 0 0\n',
              '/dev/sdb1 100 900 1000 12 0\n']
        for row in rows:
            with self.subTest(row=row):
                with self.assertRaises(StorageAdmissionError):parse_quota(HEADER+row,'/dev/sdb1')
    def test_positive_registered_requirements_are_mandatory(self):
        q=parse_quota(HEADER+'/dev/sdb1 100 900 1000 12 0 0\n','/dev/sdb1')
        for byte_count,file_count in [(0,1),(1,0),(-1,1),(True,1)]:
            with self.assertRaises(StorageAdmissionError):admit(q,2**40,100,byte_count,file_count)
if __name__=='__main__':unittest.main()
