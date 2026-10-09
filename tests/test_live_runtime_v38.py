"""Software fixtures for live evidence and explicit refusal paths."""
import copy
import ctypes
import errno
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research_v38 import live_runtime as live


class LiveRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_affinity = os.sched_getaffinity(0)
        cls.cpu = min(cls.previous_affinity)
        os.sched_setaffinity(0, {cls.cpu})

    @classmethod
    def tearDownClass(cls):
        os.sched_setaffinity(0, cls.previous_affinity)

    def test_live_domains_and_loading_order(self):
        transformer = live.collect_runtime("transformer")
        primitive = live.collect_runtime("mpfr")
        live.assert_runtime_unchanged(transformer)
        live.assert_runtime_unchanged(primitive)
        self.assertEqual(transformer["affinity"], [self.cpu])
        self.assertIsInstance(transformer["cpu"]["xcr0"], int)
        self.assertTrue(transformer["versions"]["numpy_cpu_features"])
        self.assertTrue(any(k.startswith("numpy:") for k in transformer["files"]))
        self.assertEqual({"gmp", "mpfr", "mpc", "gmpy2"} & primitive["files"].keys(),
                         {"gmp", "mpfr", "mpc", "gmpy2"})
        self.assertFalse(transformer["historical_manifest_equivalence"])

    def test_returned_manifest_cannot_mutate_cache(self):
        first = live.collect_runtime("transformer")
        saved = copy.deepcopy(first)
        first["native_helper"]["source"]["sha256"] = "0" * 64
        self.assertEqual(live.collect_runtime("transformer"), saved)

    def test_mutated_expected_manifest_is_refused(self):
        value = live.collect_runtime("transformer")
        value["cpu"]["xcr0"] ^= 1
        with self.assertRaises(live.RuntimeEvidenceError):
            live.assert_runtime_unchanged(value)

    def test_domain_and_schema_refusal(self):
        with self.assertRaises(ValueError):
            live.collect_runtime("made-up")
        with self.assertRaises(live.RuntimeEvidenceError):
            live.assert_runtime_unchanged({"schema": "old-runtime"})

    def test_non_linux_refusal(self):
        with patch.object(live.platform, "system", return_value="Darwin"):
            with self.assertRaises(live.RuntimeEvidenceError):
                live.collect_runtime()

    def test_unsupported_architecture_refusal(self):
        with patch.object(live.platform, "machine", return_value="aarch64"):
            with self.assertRaises(live.RuntimeEvidenceError):
                live.collect_runtime()

    def test_multiple_cpu_refusal(self):
        with patch.object(live.os, "sched_getaffinity", return_value={0, 1}):
            with self.assertRaises(live.RuntimeEvidenceError):
                live.collect_runtime()

    def test_missing_loader_api_refusal(self):
        with patch.object(live.ctypes, "CDLL", return_value=object()):
            with self.assertRaises(live.RuntimeEvidenceError):
                live._libc()

    def test_interposition_refusal(self):
        for key in ("LD_PRELOAD", "LD_AUDIT"):
            with patch.dict(os.environ, {key: "untrusted.so"}):
                with self.assertRaises(live.RuntimeEvidenceError):
                    live.collect_runtime()

    def test_duplicate_library_refusal(self):
        with self.assertRaises(live.RuntimeEvidenceError):
            live._select({"/one/libm.so.6": 0, "/two/libm.so.6": 1}, "libm", lambda n: n.startswith("libm"))

    def test_wrong_symbol_owner_refusal(self):
        libc = live._libc()
        objects = live._loaded_objects(libc)
        wrong = live._select(objects, "libm", lambda n: n.startswith("libm.so"))
        with self.assertRaises(live.RuntimeEvidenceError):
            live._symbol(libc, libc, "memcpy", wrong, objects)

    def test_cpuid_refusal(self):
        class Unavailable:
            def v38_cpuid(self, leaf, sub, out):
                return -1
        with self.assertRaises(live.RuntimeEvidenceError):
            live._cpu_evidence(Unavailable(), live._libc())

    def test_xgetbv_refusal(self):
        helper, _ = live._helper()
        class Unavailable:
            v38_cpuid = helper.v38_cpuid
            v38_fenv = helper.v38_fenv
            def v38_xcr0(self, out):
                return -1
        with self.assertRaisesRegex(live.RuntimeEvidenceError, "XCR0"):
            live._cpu_evidence(Unavailable(), live._libc())

    def test_missing_auxv_refusal(self):
        helper, _ = live._helper()
        class MissingAuxv:
            @staticmethod
            def getauxval(key):
                ctypes.set_errno(errno.ENOENT)
                return 0
        with self.assertRaisesRegex(live.RuntimeEvidenceError, "auxiliary-vector"):
            live._cpu_evidence(helper, MissingAuxv())

    def test_missing_required_library_refusal(self):
        with self.assertRaises(live.RuntimeEvidenceError):
            live._select({"/one/libc.so.6": 0}, "libm", lambda n: n.startswith("libm"))

    def test_changed_helper_hash_refusal(self):
        _, identity = live._helper()
        original = live._file_evidence
        def changed(path):
            result = original(path)
            if result["path"] == identity["shared"]["path"]:
                result["sha256"] = "0" * 64
            return result
        with patch.object(live, "_file_evidence", side_effect=changed):
            with self.assertRaises(live.RuntimeEvidenceError):
                live.collect_runtime()

    def test_changed_affinity_refusal(self):
        with patch.object(live, "_affinity", side_effect=[(self.cpu,), (self.cpu + 1,)]):
            with self.assertRaises(live.RuntimeEvidenceError):
                live.collect_runtime()

    def test_non_nearest_rounding_refusal(self):
        libc = ctypes.CDLL(None)
        libc.fesetround.argtypes = [ctypes.c_int]
        libc.fesetround.restype = ctypes.c_int
        try:
            self.assertEqual(libc.fesetround(0x400), 0)
            with self.assertRaises(live.RuntimeEvidenceError):
                live.collect_runtime()
        finally:
            self.assertEqual(libc.fesetround(0), 0)

    def test_malformed_elf_refusal(self):
        with tempfile.TemporaryDirectory(dir=live._ROOT / "tmp") as directory:
            path = Path(directory) / "bad.so"
            path.write_bytes(b"not-an-elf")
            with self.assertRaises(live.RuntimeEvidenceError):
                live._elf_metadata(str(path))


if __name__ == "__main__":
    unittest.main()
