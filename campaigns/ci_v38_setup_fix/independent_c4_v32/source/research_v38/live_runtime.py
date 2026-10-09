"""Live Linux x86-64 runtime evidence without procfs.

This schema defines a new identity. It never reproduces an old manifest.
Library hashes assume trusted, stable files and an unchanged process loader.
They do not attest every mapped memory byte.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import tempfile
from functools import lru_cache


class RuntimeEvidenceError(RuntimeError):
    """Required live evidence is absent, inconsistent, or unsupported."""


SCHEMA = "live-elf-cpuid-runtime-v38"
_ROOT = Path(__file__).resolve().parents[1]
_FLAGS = ["-std=c11", "-O2", "-fno-fast-math", "-ffp-contract=off",
          "-frounding-math", "-fexcess-precision=standard", "-Wall", "-Wextra", "-Werror"]
_ENV_KEYS = ("GLIBC_TUNABLES", "LD_HWCAP_MASK", "LD_LIBRARY_PATH", "LD_PRELOAD", "LD_AUDIT",
             "LD_BIND_NOW", "LD_ASSUME_KERNEL", "LD_DYNAMIC_WEAK", "LD_POINTER_GUARD",
             "NPY_DISABLE_CPU_FEATURES", "OPENBLAS_CORETYPE", "OPENBLAS_NUM_THREADS",
             "GOTO_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "MKL_DEBUG_CPU_TYPE")


def _file_evidence(path: str | Path) -> dict:
    p = Path(path).resolve(strict=True)
    if not p.is_file():
        raise RuntimeEvidenceError(f"library path is not a regular file: {p}")
    try:
        with p.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if before.st_size > 256 * 1024 * 1024:
                raise RuntimeEvidenceError("runtime file exceeds the hash budget")
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
            after = os.fstat(stream.fileno())
        current = p.stat()
    except OSError as exc:
        raise RuntimeEvidenceError(f"cannot hash live runtime file: {p}") from exc
    stable = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if stable(before) != stable(after) or stable(after) != stable(current):
        raise RuntimeEvidenceError("runtime file changed during hashing")
    return {"path": str(p), "size": before.st_size, "sha256": digest.hexdigest()}


def _require_host() -> None:
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeEvidenceError("live runtime schema supports Linux x86_64 only")
    if sys.implementation.name != "cpython" or sys.byteorder != "little":
        raise RuntimeEvidenceError("live runtime schema requires little-endian CPython")
    if (sys.float_info.radix, sys.float_info.mant_dig, sys.float_info.max_exp) != (2, 53, 1024):
        raise RuntimeEvidenceError("live runtime schema requires IEEE binary64")
    if ctypes.sizeof(ctypes.c_void_p) != 8:
        raise RuntimeEvidenceError("live runtime schema requires 64-bit pointers")


def _affinity() -> tuple[int, ...]:
    try:
        value = tuple(sorted(os.sched_getaffinity(0)))
    except (AttributeError, OSError) as exc:
        raise RuntimeEvidenceError("live CPU affinity is unavailable") from exc
    if len(value) != 1:
        raise RuntimeEvidenceError("runtime collection requires one allowed CPU")
    return value


def _libc():
    lib = ctypes.CDLL(None, use_errno=True)
    for name in ("dl_iterate_phdr", "dladdr", "getauxval", "sched_getcpu", "gnu_get_libc_version"):
        if not hasattr(lib, name):
            raise RuntimeEvidenceError(f"required live loader API is absent: {name}")
    lib.sched_getcpu.argtypes = []
    lib.sched_getcpu.restype = ctypes.c_int
    return lib


@lru_cache(maxsize=1)
def _helper() -> tuple[ctypes.CDLL, dict]:
    _require_host()
    compiler = shutil.which("gcc")
    if compiler is None:
        raise RuntimeEvidenceError("gcc is required for the bound live helper")
    source = Path(__file__).with_name("runtime_probe.c")
    source_info, compiler_info = _file_evidence(source), _file_evidence(compiler)
    version = subprocess.run([compiler, "--version"], capture_output=True, check=True, text=True, timeout=15).stdout
    identity = {"source": source_info, "compiler": compiler_info, "compiler_version": version,
                "flags": _FLAGS, "shared_flags": ["-fPIC", "-shared"],
                "probe_flags": ["-DV38_PROBE_MAIN"], "link_flags": ["-lm"]}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    directory = _ROOT / "tmp" / "runtime_v38" / key
    directory.mkdir(parents=True, exist_ok=True)
    shared, executable = directory / "runtime_probe.so", directory / "runtime_probe"
    with tempfile.TemporaryDirectory(prefix="build-", dir=directory) as staging:
        for output, extra in ((shared, ["-fPIC", "-shared"]), (executable, ["-DV38_PROBE_MAIN"])):
            # Compare a fresh build with any cache file. Never overwrite a loaded helper.
            temporary = Path(staging) / output.name
            command = [compiler, *_FLAGS, *extra, str(source), "-o", str(temporary), "-lm"]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise RuntimeEvidenceError(f"live helper compilation failed: {result.stderr[:2000]}")
            expected_hash = _file_evidence(temporary)["sha256"]
            try:
                os.link(temporary, output)
            except FileExistsError:
                if _file_evidence(output)["sha256"] != expected_hash:
                    raise RuntimeEvidenceError("cached helper differs from its fresh build")
    if _file_evidence(source) != source_info or _file_evidence(compiler) != compiler_info:
        raise RuntimeEvidenceError("helper source or compiler changed during compilation")
    probe = subprocess.run([str(executable)], capture_output=True, text=True, timeout=15)
    if probe.returncode or probe.stdout != "live-cpuid-probe-v38-ok\n":
        raise RuntimeEvidenceError("bounded child refused CPUID or XGETBV")
    identity.update(shared=_file_evidence(shared), child_probe=_file_evidence(executable))
    lib = ctypes.CDLL(str(shared), mode=os.RTLD_NOW | os.RTLD_LOCAL)
    lib.v38_cpuid.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)]
    lib.v38_cpuid.restype = ctypes.c_int
    lib.v38_xcr0.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
    lib.v38_xcr0.restype = ctypes.c_int
    lib.v38_fenv.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint16)]
    lib.v38_fenv.restype = ctypes.c_int
    return lib, identity


def _cpu_evidence(helper, libc) -> dict:
    records = {}

    def cpuid(leaf, sub=0):
        out = (ctypes.c_uint32 * 4)()
        if helper.v38_cpuid(leaf, sub, out):
            raise RuntimeEvidenceError("live CPUID is unavailable")
        values = list(out)
        records[f"{leaf:08x}:{sub:08x}"] = values
        return values

    basic = cpuid(0)[0]
    if basic < 7 or basic > 0x40:
        raise RuntimeEvidenceError("unsupported basic CPUID leaf range")
    one = cpuid(1)
    for leaf in (2, 6, 0x15, 0x16, 0x19, 0x1a, 0x1c, 0x1e):
        if leaf <= basic:
            cpuid(leaf)
    structured = cpuid(7)
    if structured[0] > 32:
        raise RuntimeEvidenceError("structured CPUID subleaf budget exceeded")
    for sub in range(1, structured[0] + 1):
        cpuid(7, sub)
    # Cache and topology records use explicit architectural terminators.
    for leaf, register, mask in ((4, 0, 31), (0xb, 1, 0xffff), (0x1f, 1, 0xffff)):
        if leaf <= basic:
            for sub in range(32):
                if cpuid(leaf, sub)[register] & mask == 0:
                    break
            else:
                raise RuntimeEvidenceError("CPUID topology or cache budget exceeded")
    xcr0 = None
    if one[2] & (1 << 26):
        if basic < 0xd:
            raise RuntimeEvidenceError("XSAVE lacks its required CPUID leaf")
        xstate = cpuid(0xd)
        xsuper = cpuid(0xd, 1)
        bitmap = xstate[0] | (xstate[3] << 32) | xsuper[2] | (xsuper[3] << 32)
        for sub in range(2, 64):
            if bitmap & (1 << sub):
                cpuid(0xd, sub)
    if one[2] & (1 << 27):
        if not one[2] & (1 << 26):
            raise RuntimeEvidenceError("OSXSAVE contradicts XSAVE")
        value = ctypes.c_uint64()
        if helper.v38_xcr0(ctypes.byref(value)):
            raise RuntimeEvidenceError("OS-enabled XCR0 is unavailable")
        xcr0 = value.value
        if not xcr0 & 1:
            raise RuntimeEvidenceError("XCR0 omits mandatory x87 state")
    extended = cpuid(0x80000000)[0]
    if extended < 0x80000008 or extended > 0x80000040:
        raise RuntimeEvidenceError("unsupported extended CPUID leaf range")
    for leaf in range(0x80000001, min(extended, 0x80000008) + 1):
        cpuid(leaf)
    for leaf in (0x8000001e, 0x8000001f, 0x80000021, 0x80000022):
        if leaf <= extended:
            cpuid(leaf)
    if one[2] & (1 << 31):
        hyper = cpuid(0x40000000)[0]
        if not 0x40000000 <= hyper <= 0x40000020:
            raise RuntimeEvidenceError("unsupported hypervisor CPUID leaf range")
        for leaf in range(0x40000001, hyper + 1):
            cpuid(leaf)
    libc.getauxval.argtypes = [ctypes.c_ulong]
    libc.getauxval.restype = ctypes.c_ulong
    auxv = {}
    for key, number in (("AT_HWCAP", 16), ("AT_HWCAP2", 26), ("AT_PAGESZ", 6), ("AT_SECURE", 23), ("AT_PLATFORM", 15)):
        ctypes.set_errno(0)
        value = libc.getauxval(number)
        if ctypes.get_errno():
            raise RuntimeEvidenceError(f"required auxiliary-vector entry is unavailable: {key}")
        if key == "AT_PLATFORM":
            if not value:
                raise RuntimeEvidenceError("AT_PLATFORM is null")
            text = ctypes.string_at(value, 64).split(b"\0", 1)[0]
            if not text or len(text) == 64:
                raise RuntimeEvidenceError("AT_PLATFORM exceeds its bound")
            value = text.decode("ascii", errors="strict")
        auxv[key] = value
    if auxv["AT_SECURE"] != 0:
        raise RuntimeEvidenceError("secure loader mode is unsupported")
    mxcsr, x87 = ctypes.c_uint32(), ctypes.c_uint16()
    rounding = helper.v38_fenv(ctypes.byref(mxcsr), ctypes.byref(x87))
    # Exception status bits may change. Control bits must remain stable.
    mxcsr_control = mxcsr.value & ~0x3f
    if rounding != 0 or mxcsr_control & ((3 << 13) | (1 << 15) | (1 << 6)) or x87.value & (3 << 10):
        raise RuntimeEvidenceError("rounding or subnormal controls violate the finite target")
    tiny = float.fromhex("0x0.0000000000001p-1022")
    if sys.float_info.min * 0.5 != float.fromhex("0x0.8000000000000p-1022") or tiny * 1.0 != tiny:
        raise RuntimeEvidenceError("binary64 gradual underflow probe failed")
    return {"cpuid": records, "xcr0": xcr0, "auxv": auxv,
            "mxcsr_control": mxcsr_control, "x87_control": x87.value,
            "rounding": "nearest-even", "subnormals": "gradual-underflow"}


class _PhdrInfo(ctypes.Structure):
    _fields_ = [("addr", ctypes.c_void_p), ("name", ctypes.c_char_p),
                ("phdr", ctypes.c_void_p), ("phnum", ctypes.c_ushort)]


class _Phdr(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint32), ("flags", ctypes.c_uint32),
                ("offset", ctypes.c_uint64), ("vaddr", ctypes.c_uint64),
                ("paddr", ctypes.c_uint64), ("filesz", ctypes.c_uint64),
                ("memsz", ctypes.c_uint64), ("align", ctypes.c_uint64)]


class _DlInfo(ctypes.Structure):
    _fields_ = [("fname", ctypes.c_char_p), ("fbase", ctypes.c_void_p),
                ("sname", ctypes.c_char_p), ("saddr", ctypes.c_void_p)]


def _loaded_objects(libc) -> dict[str, int]:
    paths, failures = {}, []
    callback_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(_PhdrInfo), ctypes.c_size_t, ctypes.c_void_p)

    def receive(pointer, size, unused):
        try:
            if size < ctypes.sizeof(_PhdrInfo):
                raise RuntimeEvidenceError("ELF loader returned an incomplete program header")
            record = pointer.contents
            name = record.name.decode("utf-8", errors="strict") if record.name else str(Path(sys.executable).resolve())
            if name.startswith("linux-vdso"):
                return 0
            if not name.startswith("/"):
                raise RuntimeEvidenceError("ELF loader returned a nonabsolute object path")
            path = str(Path(name).resolve(strict=True))
            if not record.phdr or not 0 < record.phnum <= 512:
                raise RuntimeEvidenceError("ELF loader returned invalid program headers")
            headers = ctypes.cast(record.phdr, ctypes.POINTER(_Phdr))
            loads = [headers[i].vaddr for i in range(record.phnum) if headers[i].type == 1]
            if not loads:
                raise RuntimeEvidenceError("ELF object has no loadable segment")
            page = os.sysconf("SC_PAGESIZE")
            base = int(record.addr or 0) + (min(loads) // page) * page
            if path in paths and paths[path] != base:
                raise RuntimeEvidenceError("ELF object has multiple load addresses")
            paths[path] = base
            if len(paths) > 512:
                raise RuntimeEvidenceError("ELF object budget exceeded")
            return 0
        except Exception as exc:
            failures.append(exc)
            return 1

    callback = callback_type(receive)
    libc.dl_iterate_phdr.argtypes = [callback_type, ctypes.c_void_p]
    libc.dl_iterate_phdr.restype = ctypes.c_int
    status = libc.dl_iterate_phdr(callback, None)
    if failures:
        raise RuntimeEvidenceError(str(failures[0])) from failures[0]
    if status or not paths:
        raise RuntimeEvidenceError("ELF library discovery failed")
    return paths


def _select(objects, label, predicate) -> str:
    hits = sorted(path for path in objects if predicate(Path(path).name))
    if len(hits) != 1:
        raise RuntimeEvidenceError(f"expected one loaded {label}; observed {len(hits)}")
    return hits[0]


def _elf_metadata(path: str) -> tuple[list[str], str | None]:
    """Read bounded ELF64 DT_NEEDED entries from a verified live file."""
    before = _file_evidence(path)
    blob = Path(path).read_bytes()
    if hashlib.sha256(blob).hexdigest() != before["sha256"] or _file_evidence(path) != before:
        raise RuntimeEvidenceError("ELF file changed during dependency parsing")
    if len(blob) < 64 or blob[:6] != b"\x7fELF\x02\x01":
        raise RuntimeEvidenceError("loaded binary is not little-endian ELF64")
    offset = struct.unpack_from("<Q", blob, 32)[0]
    size, count = struct.unpack_from("<HH", blob, 54)
    if size != 56 or count > 512 or offset + size * count > len(blob):
        raise RuntimeEvidenceError("ELF program-header bounds are invalid")
    headers = [struct.unpack_from("<IIQQQQQQ", blob, offset + i * size) for i in range(count)]
    dynamics = [h for h in headers if h[0] == 2]
    if len(dynamics) != 1:
        raise RuntimeEvidenceError("expected one ELF dynamic section")
    dynamic = dynamics[0]
    if dynamic[5] > 1024 * 1024 or dynamic[2] + dynamic[5] > len(blob):
        raise RuntimeEvidenceError("ELF dynamic section exceeds its bounds")
    entries = []
    for pos in range(dynamic[2], dynamic[2] + dynamic[5], 16):
        key, value = struct.unpack_from("<QQ", blob, pos)
        if key == 0:
            break
        entries.append((key, value))
    else:
        raise RuntimeEvidenceError("ELF dynamic section lacks a terminator")
    strings = [value for key, value in entries if key == 5]
    lengths = [value for key, value in entries if key == 10]
    if len(strings) != 1 or len(lengths) != 1 or lengths[0] > 16 * 1024 * 1024:
        raise RuntimeEvidenceError("ELF string-table bounds are invalid")
    loads = [h for h in headers if h[0] == 1 and h[3] <= strings[0] < h[3] + h[5]]
    if len(loads) != 1:
        raise RuntimeEvidenceError("ELF string table has no unique file mapping")
    start = loads[0][2] + strings[0] - loads[0][3]
    end = start + lengths[0]
    if end > len(blob):
        raise RuntimeEvidenceError("ELF string table exceeds the file")
    result, soname = [], None
    for key, value in entries:
        if key in (1, 14):
            if value >= lengths[0]:
                raise RuntimeEvidenceError("ELF dependency index exceeds its table")
            stop = blob.find(b"\0", start + value, end)
            if stop < 0 or stop - start - value > 4096:
                raise RuntimeEvidenceError("ELF dependency name lacks a bounded terminator")
            name = blob[start + value:stop].decode("utf-8", errors="strict")
            if key == 1:
                result.append(name)
            elif soname is None:
                soname = name
            else:
                raise RuntimeEvidenceError("ELF binary declares multiple SONAME entries")
    return result, soname


def _dependency_closure(files: dict, objects: dict) -> dict:
    result = dict(files)
    seen = set()
    pending = list(files.values())
    metadata = {path: _elf_metadata(path) for path in objects}
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        for name in metadata[path][0]:
            matches = [p for p in objects if Path(p).name == name or metadata[p][1] == name]
            if len(matches) != 1:
                raise RuntimeEvidenceError(f"ELF dependency lacks one loaded owner: {name}")
            dependency = matches[0]
            result.setdefault("dependency:" + name, dependency)
            if dependency not in seen:
                pending.append(dependency)
        if len(seen) > 128:
            raise RuntimeEvidenceError("ELF dependency closure exceeds its budget")
    return result


def _symbol(libc, handle, name, expected_path, objects) -> dict:
    try:
        address = ctypes.cast(getattr(handle, name), ctypes.c_void_p).value
    except AttributeError as exc:
        raise RuntimeEvidenceError(f"required live symbol is unavailable: {name}") from exc
    info = _DlInfo()
    libc.dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(_DlInfo)]
    libc.dladdr.restype = ctypes.c_int
    if not address or libc.dladdr(address, ctypes.byref(info)) != 1 or not info.fname:
        raise RuntimeEvidenceError(f"live symbol owner is unavailable: {name}")
    owner = str(Path(info.fname.decode("utf-8", errors="strict")).resolve(strict=True))
    base = int(info.fbase or 0)
    if owner != expected_path or owner not in objects or objects[owner] != base:
        raise RuntimeEvidenceError(f"live symbol has an unexpected owner: {name}")
    return {"name": name, "owner": owner, "relative_address": int(address) - base,
            "reported_symbol": info.sname.decode("utf-8", errors="strict") if info.sname else None}


def collect_runtime(domain: str = "transformer") -> dict:
    """Collect current evidence under one fixed CPU affinity.

    Call again at transaction boundaries. Changes cause explicit refusal.
    The caller must prohibit fenv, loader, environment, and affinity mutation.
    """
    if domain not in ("transformer", "mpfr"):
        raise ValueError("unsupported live runtime domain")
    _require_host()
    affinity = _affinity()
    env = {key: os.environ.get(key) for key in _ENV_KEYS}
    if env["LD_PRELOAD"] or env["LD_AUDIT"]:
        raise RuntimeEvidenceError("loader interposition and audit modules are unsupported")
    extension = None
    versions = None
    if domain == "transformer":
        import numpy as np
    if domain == "mpfr":
        import gmpy2 as g
        extensions = sorted({str(Path(module.__file__).resolve()) for name, module in tuple(sys.modules.items())
                             if name.startswith("gmpy2") and getattr(module, "__file__", "").endswith(".so")})
        if len(extensions) != 1:
            raise RuntimeEvidenceError("expected one loaded gmpy2 extension")
        extension = extensions[0]
        versions = {"gmpy2": g.version(), "gmp": g.mp_version(), "mpfr": g.mpfr_version(), "mpc": g.mpc_version()}
    libc = _libc()
    if libc.sched_getcpu() != affinity[0]:
        raise RuntimeEvidenceError("current CPU contradicts allowed affinity")
    helper, helper_identity = _helper()
    for key in ("source", "compiler", "shared", "child_probe"):
        if _file_evidence(helper_identity[key]["path"]) != helper_identity[key]:
            raise RuntimeEvidenceError("bound native helper identity changed")
    cpu = _cpu_evidence(helper, libc)
    objects = _loaded_objects(libc)
    files = {"libc": _select(objects, "libc", lambda n: n.startswith("libc.so")),
             "loader": _select(objects, "ELF loader", lambda n: n.startswith("ld-linux-x86-64.so"))}
    specifications = [("libc", "memcpy"), ("libc", "memmove"), ("libc", "memset"),
                      ("libc", "getauxval"), ("libc", "sched_getcpu"), ("libc", "dl_iterate_phdr")]
    if domain == "transformer":
        python_libraries = [path for path in objects if Path(path).name.startswith("libpython")]
        if len(python_libraries) > 1:
            raise RuntimeEvidenceError("multiple Python libraries are loaded")
        # Static CPython exposes its symbols from the main executable.
        python_owner = python_libraries[0] if python_libraries else str(Path(sys.executable).resolve(strict=True))
        files.update(libm=_select(objects, "libm", lambda n: n.startswith("libm.so")), libpython=python_owner)
        files["math"] = str(Path(math.__file__).resolve(strict=True)) if getattr(math, "__file__", None) else python_owner
        numpy_extensions = sorted({str(Path(module.__file__).resolve()) for name, module in tuple(sys.modules.items())
                                   if name.startswith("numpy") and str(getattr(module, "__file__", "")).endswith(".so")})
        if not numpy_extensions:
            raise RuntimeEvidenceError("loaded NumPy extensions are unavailable")
        for path in numpy_extensions:
            label = "numpy:" + Path(path).name
            files[label] = path
            specifications.append((label, "PyInit_" + Path(path).name.split(".", 1)[0]))
        versions = {"numpy": np.__version__}
        numpy_core = np._core._multiarray_umath
        feature_map = getattr(numpy_core, "__cpu_features__", None)
        baseline = getattr(numpy_core, "__cpu_baseline__", None)
        dispatch = getattr(numpy_core, "__cpu_dispatch__", None)
        if not isinstance(feature_map, dict) or not feature_map or baseline is None or dispatch is None:
            raise RuntimeEvidenceError("NumPy live CPU dispatch evidence is unavailable")
        versions["numpy_cpu_features"] = {str(key): bool(value) for key, value in sorted(feature_map.items())}
        versions["numpy_cpu_baseline"] = list(baseline)
        versions["numpy_cpu_dispatch"] = list(dispatch)
        specifications += [("libm", name) for name in ("exp", "sqrt", "erf", "tanh", "fegetround")]
        specifications += [("libpython", "PyFloat_FromDouble"), ("libpython", "PyLong_FromLong"), ("math", "PyInit_math")]
    else:
        files.update(gmp=_select(objects, "GMP", lambda n: n.startswith("libgmp") and not n.startswith("libgmpxx")),
                     mpfr=_select(objects, "MPFR", lambda n: n.startswith("libmpfr")),
                     mpc=_select(objects, "MPC", lambda n: n.startswith("libmpc")), gmpy2=extension)
        specifications += [("gmp", "__gmpz_init"), ("gmp", "__gmpn_add_n"),
                           ("mpfr", "mpfr_exp"), ("mpfr", "mpfr_sqrt"), ("mpfr", "mpfr_erf"), ("mpfr", "mpfr_tanh"),
                           ("mpc", "mpc_init2"), ("gmpy2", "PyInit_gmpy2")]
    if any(path not in objects for path in files.values()):
        raise RuntimeEvidenceError("required binary is absent from the live ELF inventory")
    files = _dependency_closure(files, objects)
    # RTLD_NOLOAD prevents library discovery from becoming library substitution.
    main_path = str(Path(sys.executable).resolve(strict=True))
    handles = {label: (libc if files[label] == main_path else
                      ctypes.CDLL(files[label], mode=os.RTLD_NOW | os.RTLD_NOLOAD | os.RTLD_LOCAL))
               for label, _ in specifications}
    symbols = [_symbol(libc, handles[label], name, files[label], objects) for label, name in specifications]
    for label, name in specifications:
        if label in ("libc", "libm", "libpython"):
            global_symbol = _symbol(libc, libc, name, files[label], objects)
            if global_symbol != symbols[specifications.index((label, name))]:
                raise RuntimeEvidenceError("global and library symbol resolution disagree")
    evidence = {label: _file_evidence(path) for label, path in files.items()}
    libc.gnu_get_libc_version.argtypes = []
    libc.gnu_get_libc_version.restype = ctypes.c_char_p
    result = {"schema": SCHEMA, "domain": domain, "collector_source": _file_evidence(__file__),
              "python": sys.version, "implementation": sys.implementation.name,
              "python_executable": _file_evidence(sys.executable), "machine": platform.machine(),
              "system": platform.system(), "kernel": platform.release(), "byteorder": sys.byteorder,
              "binary64": [sys.float_info.radix, sys.float_info.mant_dig, sys.float_info.max_exp],
              "libc_version": libc.gnu_get_libc_version().decode("ascii"), "affinity": list(affinity),
              "dispatch_environment": env, "cpu": cpu, "files": evidence, "symbols": symbols,
              "native_helper": helper_identity, "versions": versions,
              "assumption": "trusted stable files; unchanged loader, affinity, dispatch environment, and fenv during evaluation",
              "mapped_memory_attestation": False, "historical_manifest_equivalence": False}
    # Collect twice to reject migration, mutable controls, and loader changes during collection.
    if _affinity() != affinity or libc.sched_getcpu() != affinity[0] or _cpu_evidence(helper, libc) != cpu:
        raise RuntimeEvidenceError("live CPU evidence changed during collection")
    after_objects = _loaded_objects(libc)
    if any(after_objects.get(path) != objects[path] for path in files.values()):
        raise RuntimeEvidenceError("required loaded objects changed during collection")
    if {key: os.environ.get(key) for key in _ENV_KEYS} != env:
        raise RuntimeEvidenceError("dispatch environment changed during collection")
    return json.loads(json.dumps(result, sort_keys=True, allow_nan=False))


def assert_runtime_unchanged(manifest: dict) -> None:
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise RuntimeEvidenceError("unsupported runtime manifest")
    if collect_runtime(manifest.get("domain")) != manifest:
        raise RuntimeEvidenceError("live runtime no longer matches the bound identity")
