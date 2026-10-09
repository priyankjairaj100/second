"""Small software fixtures for CPU mappings and cross-check refusals."""
import copy
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from scripts import check_runtime_portability_v38 as check


def fixture_cpu():
    vendor = struct.unpack("<III", b"GenuineIntel")
    brand = b"Fixture CPU".ljust(48, b"\0")
    raw = {"00000000:00000000": [7, vendor[0], vendor[2], vendor[1]],
           "00000001:00000000": [0x000906e9, 0, (1 << 26) | (1 << 28), 1],
           "00000007:00000000": [0, 1 << 5, 0, 0]}
    for i, leaf in enumerate((0x80000002, 0x80000003, 0x80000004)):
        raw[f"{leaf:08x}:00000000"] = list(struct.unpack("<IIII", brand[i * 16:(i + 1) * 16]))
    identity = check.cpuid_identity(raw)
    def record(cpu):
        return "\n".join(f"{k}: {v}" for k, v in {"processor": str(cpu), **identity, "flags": "fpu xsave avx avx2"}.items())
    text = record(0) + "\n\n" + record(3) + "\n"
    old = {"cpu_dispatch_fields": {**identity, "flags": "fpu xsave avx avx2"}}
    new = {"cpu": {"cpuid": raw, "xcr0": 7}}
    return old, new, text


class RuntimeCrosscheckTests(unittest.TestCase):
    def test_extended_model_mapping(self):
        _, new, _ = fixture_cpu()
        facts = check.cpuid_identity(new["cpu"]["cpuid"])
        self.assertEqual((facts["cpu family"], facts["model"], facts["stepping"]), ("6", "158", "9"))

    def test_extended_family_mapping(self):
        _, new, _ = fixture_cpu()
        new["cpu"]["cpuid"]["00000001:00000000"][0] = 0x00830f12
        facts = check.cpuid_identity(new["cpu"]["cpuid"])
        self.assertEqual((facts["cpu family"], facts["model"], facts["stepping"]), ("23", "49", "2"))

    def test_first_and_selected_record_mapping(self):
        old, new, text = fixture_cpu()
        result = check.compare_cpu(old, new, text, 3)
        self.assertEqual(result["first_record_cpu"], 0)
        self.assertEqual(result["selected_cpu"], 3)
        self.assertFalse(result["first_record_is_selected"])
        self.assertEqual(check.compare_old_cpu_records(old, text, 3)["status"], "passed")

    def test_unsupported_portable_requires_original_success(self):
        from research_v38.live_runtime import RuntimeEvidenceError
        error = RuntimeEvidenceError("required live loader API is absent: getauxval")
        self.assertEqual(check.refusal_class(error, True), ("unsupported_portable_interface", True))
        self.assertEqual(check.refusal_class(error, False), ("unexpected_error", False))

    def test_ownership_and_hash_errors_block_original_backend(self):
        from research_v38.live_runtime import RuntimeEvidenceError
        for message in ("live symbol has an unexpected owner: exp", "bound native helper identity changed"):
            self.assertEqual(check.refusal_class(RuntimeEvidenceError(message), True), ("unexpected_error", False))

    def test_common_contradictions_block_original_backend(self):
        self.assertEqual(check.refusal_class(check.CrosscheckRefusal("hashes differ"), True),
                         ("contradictory_runtime_facts", False))

    def test_missing_selected_cpu_refusal(self):
        old, new, text = fixture_cpu()
        with self.assertRaises(check.CrosscheckRefusal):
            check.compare_cpu(old, new, text, 9)

    def test_different_first_cpu_refusal(self):
        old, new, text = fixture_cpu()
        text = text.replace("stepping: 9", "stepping: 8", 1)
        with self.assertRaisesRegex(check.CrosscheckRefusal, "first-record"):
            check.compare_cpu(old, new, text, 3)

    def test_duplicate_cpu_refusal(self):
        _, _, text = fixture_cpu()
        with self.assertRaises(check.CrosscheckRefusal):
            check.cpu_records(text.replace("processor: 3", "processor: 0"))

    def test_hardware_flag_contradiction_refusal(self):
        old, new, text = fixture_cpu()
        new["cpu"]["cpuid"]["00000001:00000000"][3] = 0
        with self.assertRaisesRegex(check.CrosscheckRefusal, "proc feature"):
            check.compare_cpu(old, new, text, 3)

    def test_avx_os_state_refusal(self):
        old, new, text = fixture_cpu()
        new["cpu"]["xcr0"] = 3
        with self.assertRaisesRegex(check.CrosscheckRefusal, "XSTATE"):
            check.compare_cpu(old, new, text, 3)

    def test_missing_cpuid_leaf_refusal(self):
        _, new, _ = fixture_cpu()
        del new["cpu"]["cpuid"]["80000003:00000000"]
        with self.assertRaises(check.CrosscheckRefusal):
            check.cpuid_identity(new["cpu"]["cpuid"])

    def test_library_mapping_and_hash_refusal(self):
        with tempfile.TemporaryDirectory(dir=check.ROOT / "tmp") as directory:
            evidence = {}
            for name in ("libm.so.6", "libpython.so", "python", "math.so", "gmp.so", "mpfr.so", "mpc.so", "gmpy2.so"):
                path = Path(directory) / name
                path.write_bytes(name.encode())
                evidence[name] = {"path": str(path), "size": len(name), "sha256": hashlib.sha256(name.encode()).hexdigest()}
            common = {"python": "fixture", "implementation": "cpython", "system": "Linux", "machine": "x86_64",
                      "byteorder": "little", "binary64": [2, 53, 1024]}
            new = {**common, "libc_version": "fixture", "python_executable": evidence["python"],
                   "files": {"libm": evidence["libm.so.6"], "libpython": evidence["libpython.so"], "math": evidence["math.so"]}}
            old = {**common, "libc": ["glibc", "fixture"], "loaded_libm_sha256": [evidence["libm.so.6"]["sha256"]],
                   "loaded_python_libraries_sha256": [evidence["libpython.so"]["sha256"]],
                   "python_executable_sha256": evidence["python"]["sha256"], "math_extension_sha256": evidence["math.so"]["sha256"]}
            primitive = {"files": {key: evidence[key + ".so"] for key in ("gmp", "mpfr", "mpc", "gmpy2")},
                         "versions": {key: "fixture" for key in ("gmp", "mpfr", "gmpy2")}}
            old_primitive = {**primitive["versions"], "binary_sha256": {key + ".so": evidence[key + ".so"]["sha256"] for key in primitive["files"]}}
            maps = "\n".join("0000-ffff r-xp 0000 00:00 0 " + entry["path"] for entry in evidence.values())
            self.assertEqual(check.compare_libraries(old, old_primitive, new, primitive, maps)["status"], "passed")
            changed = copy.deepcopy(old_primitive)
            changed["binary_sha256"]["mpc.so"] = "0" * 64
            with self.assertRaisesRegex(check.CrosscheckRefusal, "dependency hashes"):
                check.compare_libraries(old, changed, new, primitive, maps)
            with self.assertRaisesRegex(check.CrosscheckRefusal, "proc maps"):
                check.compare_libraries(old, old_primitive, new, primitive, "")

    def test_bounded_proc_refusal(self):
        with tempfile.TemporaryDirectory(dir=check.ROOT / "tmp") as directory:
            path = Path(directory) / "record"
            path.write_text("too large")
            with self.assertRaises(check.CrosscheckRefusal):
                check.bounded_proc(path, 3)


if __name__ == "__main__":
    unittest.main()
