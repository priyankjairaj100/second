#!/usr/bin/env python3
"""Compare genuine old and new runtime facts on a compatible Linux host.

This gate uses no model, dataset, worker ledger, or historical prepared state.
The old and new schemas keep distinct identities after a successful comparison.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True


class CrosscheckRefusal(RuntimeError):
    pass


_UNSUPPORTED_PORTABLE_PREFIXES = (
    "live runtime schema supports Linux x86_64 only",
    "gcc is required for the bound live helper",
    "required live loader API is absent:",
    "bounded child refused CPUID or XGETBV",
    "live CPUID is unavailable",
    "OS-enabled XCR0 is unavailable",
    "required auxiliary-vector entry is unavailable:",
    "NumPy live CPU dispatch evidence is unavailable",
)


def refusal_class(exc, original_admitted):
    from research_v38.live_runtime import RuntimeEvidenceError
    if (original_admitted and isinstance(exc, RuntimeEvidenceError)
            and any(str(exc).startswith(prefix) for prefix in _UNSUPPORTED_PORTABLE_PREFIXES)):
        return "unsupported_portable_interface", True
    if isinstance(exc, CrosscheckRefusal):
        return "contradictory_runtime_facts", False
    return "unexpected_error", False


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def bounded_proc(path, limit=2 * 1024 * 1024):
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    if not raw or len(raw) > limit:
        raise CrosscheckRefusal(f"proc evidence is empty or exceeds its bound: {path}")
    return raw.decode("utf-8", errors="strict")


def cpu_records(text):
    records = []
    for paragraph in text.strip().split("\n\n"):
        fields = {}
        for line in paragraph.splitlines():
            if ":" not in line:
                raise CrosscheckRefusal("CPU record contains an unparsed line")
            key, value = (part.strip() for part in line.split(":", 1))
            if key in fields:
                raise CrosscheckRefusal("CPU record contains a duplicate field")
            fields[key] = value
        if "processor" not in fields:
            raise CrosscheckRefusal("CPU record lacks its logical processor number")
        try:
            processor = int(fields["processor"])
        except ValueError as exc:
            raise CrosscheckRefusal("CPU processor number is invalid") from exc
        if any(item["processor"] == processor for item in records):
            raise CrosscheckRefusal("CPU processor numbers are ambiguous")
        records.append({"processor": processor, "fields": fields, "raw": paragraph + "\n"})
    if not records:
        raise CrosscheckRefusal("CPU records are unavailable")
    return records


def cpuid_identity(raw):
    def leaf(number):
        value = raw.get(f"{number:08x}:00000000")
        if not isinstance(value, list) or len(value) != 4 or any(not isinstance(x, int) or not 0 <= x < 2**32 for x in value):
            raise CrosscheckRefusal("required CPUID identity registers are unavailable")
        return value
    zero, one = leaf(0), leaf(1)
    vendor = struct.pack("<III", zero[1], zero[3], zero[2]).decode("ascii", errors="strict").rstrip("\0")
    eax = one[0]
    base_family, base_model = (eax >> 8) & 15, (eax >> 4) & 15
    family = base_family + ((eax >> 20) & 255) if base_family == 15 else base_family
    model = base_model | (((eax >> 16) & 15) << 4) if base_family in (6, 15) else base_model
    brand = b"".join(struct.pack("<IIII", *leaf(n)) for n in (0x80000002, 0x80000003, 0x80000004))
    return {"vendor_id": vendor, "cpu family": str(family), "model": str(model),
            "stepping": str(eax & 15), "model name": brand.decode("ascii", errors="strict").strip("\0 ")}


def compare_old_cpu_records(old, text, selected_cpu):
    records = cpu_records(text)
    matches = [item for item in records if item["processor"] == selected_cpu]
    if len(matches) != 1:
        raise CrosscheckRefusal("selected CPU lacks one proc record")
    first, selected = records[0], matches[0]
    fields = old["cpu_dispatch_fields"]
    required = {"vendor_id", "cpu family", "model", "model name", "stepping", "flags"}
    if not required.issubset(fields):
        raise CrosscheckRefusal("old CPU identity lacks required x86 fields")
    for key, value in fields.items():
        old_value = set(value.split()) if key == "flags" else value
        first_value = first["fields"].get(key)
        selected_value = selected["fields"].get(key)
        if key == "flags":
            first_value = set(first_value.split()) if first_value is not None else None
            selected_value = set(selected_value.split()) if selected_value is not None else None
        if first_value != old_value or selected_value != old_value:
            raise CrosscheckRefusal(f"old first-record CPU facts differ from the selected CPU: {key}")
    return {"status": "passed", "first_record_cpu": first["processor"], "selected_cpu": selected_cpu,
            "first_record_is_selected": first["processor"] == selected_cpu,
            "first_record": first, "selected_record": selected,
            "scope": "The old collector's first record agrees with the selected CPU for every recorded identity field."}


_FLAG_MAP = {
    "fpu": (1, 3, 0), "cmov": (1, 3, 15), "mmx": (1, 3, 23),
    "sse": (1, 3, 25), "sse2": (1, 3, 26), "pni": (1, 2, 0),
    "ssse3": (1, 2, 9), "sse4_1": (1, 2, 19), "sse4_2": (1, 2, 20),
    "popcnt": (1, 2, 23), "aes": (1, 2, 25), "xsave": (1, 2, 26),
    "avx": (1, 2, 28), "avx2": (7, 1, 5), "avx512f": (7, 1, 16),
}


def compare_cpu(old, new, text, selected_cpu):
    records = cpu_records(text)
    matches = [item for item in records if item["processor"] == selected_cpu]
    if len(matches) != 1:
        raise CrosscheckRefusal("selected CPU lacks one proc record")
    first, selected = records[0], matches[0]
    actual = cpuid_identity(new["cpu"]["cpuid"])
    comparisons = {}
    old_fields = old["cpu_dispatch_fields"]
    for key, value in actual.items():
        if selected["fields"].get(key) != value:
            raise CrosscheckRefusal(f"selected CPU contradicts live CPUID: {key}")
        if first["fields"].get(key) != value or old_fields.get(key) != value:
            raise CrosscheckRefusal(f"old first-record CPU facts differ from the selected CPU: {key}")
        comparisons[key] = {"cpuid": value, "selected_proc": selected["fields"][key],
                            "first_proc": first["fields"][key], "old_manifest": old_fields[key]}
    if "flags" not in selected["fields"] or "flags" not in first["fields"] or "flags" not in old_fields:
        raise CrosscheckRefusal("required proc CPU flags are unavailable")
    flags = set(selected["fields"]["flags"].split())
    if set(first["fields"]["flags"].split()) != flags or set(old_fields["flags"].split()) != flags:
        raise CrosscheckRefusal("old first-record flags differ from the selected CPU flags")
    mapped = []
    raw = new["cpu"]["cpuid"]
    xcr0 = new["cpu"]["xcr0"]
    for flag, (leaf, register, bit) in sorted(_FLAG_MAP.items()):
        word = raw[f"{leaf:08x}:00000000"][register]
        hardware = bool(word & (1 << bit))
        os_state = True
        if flag in ("avx", "avx2"):
            os_state = xcr0 is not None and xcr0 & 6 == 6
        elif flag == "avx512f":
            os_state = xcr0 is not None and xcr0 & 0xe6 == 0xe6
        if flag in flags and (not hardware or not os_state):
            raise CrosscheckRefusal(f"proc feature contradicts CPUID or enabled XSTATE: {flag}")
        mapped.append({"flag": flag, "cpuid_leaf": leaf, "register": register, "bit": bit,
                       "proc_present": flag in flags, "hardware_present": hardware,
                       "required_os_state_enabled": os_state})
    return {"status": "passed", "record_count": len(records), "selected_cpu": selected_cpu,
            "first_record_cpu": first["processor"], "first_record_is_selected": first["processor"] == selected_cpu,
            "identity_comparisons": comparisons, "first_record": first, "selected_record": selected,
            "mapped_flags": mapped, "unmapped_proc_flags": sorted(flags - _FLAG_MAP.keys()),
            "cpuinfo_sha256": digest(text.encode()), "cpuinfo_bytes": len(text.encode()),
            "scope": "Shared identity fields agree. Proc flags and raw CPUID remain different representations.",
            "mapping_note": "Logical CPU numbers come from affinity and proc records. APIC numbers are not logical CPU numbers."}


def mapped_paths(text):
    result = set()
    for line in text.splitlines():
        fields = line.split(None, 5)
        if len(fields) == 6 and fields[5].startswith("/"):
            path = fields[5]
            if path.endswith(" (deleted)"):
                continue
            result.add(str(Path(path).resolve(strict=True)))
    return result


def compare_libraries(old_transformer, old_primitive, new_transformer, new_primitive, maps_text):
    files = new_transformer["files"]
    if old_transformer["loaded_libm_sha256"] != [files["libm"]["sha256"]]:
        raise CrosscheckRefusal("old and new loaded libm hashes differ")
    embedded = files["libpython"]["path"] == new_transformer["python_executable"]["path"]
    python_hashes = [] if embedded else [files["libpython"]["sha256"]]
    if old_transformer["loaded_python_libraries_sha256"] != python_hashes:
        raise CrosscheckRefusal("old and new Python library hashes differ")
    if old_transformer["python_executable_sha256"] != new_transformer["python_executable"]["sha256"]:
        raise CrosscheckRefusal("old and new Python executable hashes differ")
    old_math = old_transformer["math_extension_sha256"]
    if old_math == "built-in; bound by Python binaries":
        if files["math"]["path"] != files["libpython"]["path"]:
            raise CrosscheckRefusal("built-in math has an unexpected new owner")
    elif old_math != files["math"]["sha256"]:
        raise CrosscheckRefusal("old and new math extension hashes differ")
    if old_transformer["libc"][1] != new_transformer["libc_version"]:
        raise CrosscheckRefusal("old and new libc versions differ")
    for key in ("python", "implementation", "system", "machine", "byteorder", "binary64"):
        if old_transformer[key] != new_transformer[key]:
            raise CrosscheckRefusal(f"old and new basic runtime facts differ: {key}")
    new_primitive_files = new_primitive["files"]
    expected = {Path(new_primitive_files[key]["path"]).name: new_primitive_files[key]["sha256"]
                for key in ("gmp", "mpfr", "mpc", "gmpy2")}
    if len(expected) != 4 or old_primitive["binary_sha256"] != expected:
        raise CrosscheckRefusal("old and new MPFR dependency hashes differ")
    for key in ("gmpy2", "mpfr", "gmp"):
        if old_primitive[key] != new_primitive["versions"][key]:
            raise CrosscheckRefusal(f"old and new primitive versions differ: {key}")
    paths = mapped_paths(maps_text)
    bound_files = {entry["path"]: entry for manifest in (new_transformer, new_primitive)
                   for entry in manifest["files"].values()}
    if not set(bound_files).issubset(paths):
        raise CrosscheckRefusal("a new required binary is absent from genuine proc maps")
    from research_v38.live_runtime import _file_evidence
    for path, evidence in bound_files.items():
        if _file_evidence(path) != evidence:
            raise CrosscheckRefusal("a loaded file changed during the cross-check")
    return {"status": "passed", "old_libm_hashes": old_transformer["loaded_libm_sha256"],
            "old_python_library_hashes": python_hashes, "python_is_embedded": embedded,
            "primitive_hashes": expected, "required_mapped_files": sorted(bound_files),
            "additional_new_facts": ["ELF dependency closure", "resolved symbol owners", "native NumPy identities",
                                     "CPU register and OS state evidence", "compiler and helper identities"],
            "scope": "Shared loaded-file identities agree. New-only facts have no old-schema counterpart."}


def crosscheck(cpu=None):
    start_wall, start_cpu = time.perf_counter(), time.process_time()
    start_children = resource.getrusage(resource.RUSAGE_CHILDREN)
    output = {"schema": "runtime-portability-crosscheck-v38", "status": "unexpected_error",
              "c4_original_backend_admitted": False, "portable_gate_7_passed": False,
              "model_loaded": False, "dataset_loaded": False, "model_inference_performed": False,
              "ledger_written": False, "historical_identity_compatibility_claimed": False,
              "raw_manifests": {}, "proc": {}, "checks": {}, "source_sha256": {}}
    original_affinity = None
    original_admitted = False
    try:
        for name in ("scripts/check_runtime_portability_v38.py", "research_v38/live_runtime.py",
                     "research_v38/runtime_probe.c", "src/transformer_backend.py", "src/finite_primitives.py"):
            output["source_sha256"][name] = digest((ROOT / name).read_bytes())
        original_affinity = os.sched_getaffinity(0)
        selected = min(original_affinity) if cpu is None else cpu
        if selected not in original_affinity:
            raise CrosscheckRefusal("requested CPU is outside the allowed affinity")
        os.sched_setaffinity(0, {selected})
        output["affinity"] = {"original": sorted(original_affinity), "selected": selected}
        # Load the same numerical dependencies before either manifest is captured.
        import numpy
        import gmpy2
        from research_v38.live_runtime import collect_runtime
        from src.transformer_backend import _runtime_manifest
        from src.finite_primitives import _primitive_manifest_bytes, primitive_manifest
        if _runtime_manifest.cache_info().currsize or _primitive_manifest_bytes.cache_info().currsize:
            raise CrosscheckRefusal("old manifests were already cached before the live cross-check")
        cpuinfo = bounded_proc("/proc/cpuinfo")
        output["proc"]["cpuinfo_before"] = {"raw": cpuinfo, "sha256": digest(cpuinfo.encode())}
        maps_initial = bounded_proc("/proc/self/maps")
        output["proc"]["maps_before"] = {"raw": maps_initial, "sha256": digest(maps_initial.encode())}
        old_transformer, old_primitive = _runtime_manifest(), primitive_manifest("mpfr_enclosure")
        output["raw_manifests"].update(old_transformer=old_transformer, old_primitive=old_primitive)
        output["checks"]["old_cpu_record_mapping"] = compare_old_cpu_records(old_transformer, cpuinfo, selected)
        original_admitted = True
        before = {domain: collect_runtime(domain) for domain in ("transformer", "mpfr")}
        maps_before = bounded_proc("/proc/self/maps")
        output["proc"]["maps_after_portable_capture"] = {"raw": maps_before, "sha256": digest(maps_before.encode())}
        output["raw_manifests"]["new_before"] = before
        output["checks"]["cpu"] = compare_cpu(old_transformer, before["transformer"], cpuinfo, selected)
        output["checks"]["libraries"] = compare_libraries(old_transformer, old_primitive,
                                                          before["transformer"], before["mpfr"], maps_before)
        after = {domain: collect_runtime(domain) for domain in ("transformer", "mpfr")}
        output["raw_manifests"]["new_after"] = after
        if before != after:
            raise CrosscheckRefusal("new runtime evidence changed during the cross-check")
        maps_after = bounded_proc("/proc/self/maps")
        output["proc"]["maps_after"] = {"raw": maps_after, "sha256": digest(maps_after.encode())}
        compare_libraries(old_transformer, old_primitive, after["transformer"], after["mpfr"], maps_after)
        cpuinfo_after = bounded_proc("/proc/cpuinfo")
        output["proc"]["cpuinfo_after"] = {"raw": cpuinfo_after, "sha256": digest(cpuinfo_after.encode())}
        later_cpu = compare_cpu(old_transformer, after["transformer"], cpuinfo_after, selected)
        if later_cpu["identity_comparisons"] != output["checks"]["cpu"]["identity_comparisons"]:
            raise CrosscheckRefusal("shared CPU identities changed across collection")
        if os.sched_getaffinity(0) != {selected}:
            raise CrosscheckRefusal("affinity changed during the cross-check")
        if any(digest((ROOT / name).read_bytes()) != sha for name, sha in output["source_sha256"].items()):
            raise CrosscheckRefusal("a cross-check source changed during collection")
        output["status"] = "passed"
        output["c4_original_backend_admitted"] = True
        output["portable_gate_7_passed"] = True
        output["checks"]["stable_live_evidence"] = True
        output["scope"] = "One genuine process on this host. Common facts agree; schemas and target identities remain distinct."
        output["manifest_sha256"] = {name: digest(canonical(value)) for name, value in output["raw_manifests"].items()}
    except Exception as exc:
        output["error"] = {"type": type(exc).__name__, "reason": str(exc)}
        status, admitted = refusal_class(exc, original_admitted)
        if admitted:
            try:
                # Force fresh observations. No cached old facts can authorize this branch.
                _runtime_manifest.cache_clear()
                _primitive_manifest_bytes.cache_clear()
                fresh_old = _runtime_manifest()
                fresh_primitive = primitive_manifest("mpfr_enclosure")
                output["raw_manifests"].update(old_transformer_after=fresh_old, old_primitive_after=fresh_primitive)
                fresh_cpuinfo = bounded_proc("/proc/cpuinfo")
                fresh_maps = bounded_proc("/proc/self/maps")
                output["proc"]["cpuinfo_after"] = {"raw": fresh_cpuinfo, "sha256": digest(fresh_cpuinfo.encode())}
                output["proc"]["maps_after"] = {"raw": fresh_maps, "sha256": digest(fresh_maps.encode())}
                output["checks"]["old_cpu_record_mapping_after"] = compare_old_cpu_records(fresh_old, fresh_cpuinfo, selected)
                stable_sources = all(digest((ROOT / name).read_bytes()) == sha for name, sha in output["source_sha256"].items())
                stable_affinity = os.sched_getaffinity(0) == {selected}
                if (not stable_sources or not stable_affinity or fresh_old != old_transformer
                        or fresh_primitive != old_primitive):
                    raise CrosscheckRefusal("original runtime evidence changed across portable interface refusal")
                output["checks"]["stable_original_runtime_evidence"] = True
            except Exception as secondary:
                status, admitted = "contradictory_runtime_facts" if isinstance(secondary, CrosscheckRefusal) else "unexpected_error", False
                output["secondary_error"] = {"type": type(secondary).__name__, "reason": str(secondary)}
        output["status"], output["c4_original_backend_admitted"] = status, admitted
        output["portable_gate_7_passed"] = False
    finally:
        if original_affinity is not None:
            try:
                os.sched_setaffinity(0, original_affinity)
            except OSError as exc:
                output["status"] = "unexpected_error"
                output["c4_original_backend_admitted"] = False
                output["portable_gate_7_passed"] = False
                output["affinity_restore_error"] = str(exc)
        children = resource.getrusage(resource.RUSAGE_CHILDREN)
        output["cost"] = {"wall_seconds": time.perf_counter() - start_wall,
                          "process_cpu_seconds": time.process_time() - start_cpu,
                          "child_cpu_seconds": children.ru_utime + children.ru_stime - start_children.ru_utime - start_children.ru_stime}
        output["manifest_sha256"] = {name: digest(canonical(value)) for name, value in output["raw_manifests"].items()}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cpu", type=int)
    args = parser.parse_args()
    result = crosscheck(args.cpu)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Preserve any prior observation. A retry needs a new output path.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "output": str(args.output), "cost": result["cost"]}, sort_keys=True))
    return 0 if result["c4_original_backend_admitted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
