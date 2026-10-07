"""Portable-content runtime binding for prospective local inventories.

No host name, account identifier, executable path, or environment variables
enter the record. This pins declared software and architecture properties,
not machine load, physical CPU identity, native dynamic dependencies, or OS caches.
"""
from __future__ import annotations

from hashlib import sha256
import importlib
from pathlib import Path
import platform
import re
import sys

from .run_store import canonical_json, strict_json

_MODULES = ('fractions', 'decimal', '_decimal', 'math', 'json', 'struct',
            '_struct', 'fcntl', 'resource', 'hashlib', '_hashlib')
_FIELDS = {'schema', 'implementation', 'python_version', 'cache_tag', 'compiler',
           'build', 'interpreter', 'system', 'kernel', 'machine', 'libc',
           'byteorder', 'pointer_bits', 'float_model', 'modules', 'execution_flags'}
_FLAG_NAMES = ('optimize', 'dont_write_bytecode', 'no_user_site', 'no_site',
               'ignore_environment', 'isolated', 'dev_mode', 'utf8_mode',
               'warn_default_encoding', 'safe_path')


def _file_fingerprint(path):
    p = Path(path).resolve(strict=True)
    if not p.is_file():
        raise ValueError('runtime component is not a regular file')
    h = sha256()
    size = 0
    with p.open('rb') as stream:
        while data := stream.read(1024 * 1024):
            size += len(data)
            h.update(data)
    return {'kind': 'file', 'bytes': size, 'sha256': h.hexdigest()}


def capture_runtime_contract():
    import struct
    modules = {}
    for name in _MODULES:
        module = importlib.import_module(name)
        origin = getattr(getattr(module, '__spec__', None), 'origin', None)
        if origin in ('built-in', 'frozen'):
            modules[name] = {'kind': origin}
        elif type(origin) is str:
            modules[name] = _file_fingerprint(origin)
        else:
            raise ValueError('runtime module has no verifiable origin: ' + name)
    contract = {
        'schema': 'calibration-runtime-v1',
        'implementation': sys.implementation.name,
        'python_version': platform.python_version(),
        'cache_tag': sys.implementation.cache_tag,
        'compiler': platform.python_compiler(),
        'build': list(platform.python_build()),
        'interpreter': _file_fingerprint(sys.executable),
        'system': platform.system(), 'kernel': platform.release(),
        'machine': platform.machine(), 'libc': list(platform.libc_ver()),
        'byteorder': sys.byteorder, 'pointer_bits': struct.calcsize('P') * 8,
        'float_model': {key: getattr(sys.float_info, key)
                        for key in ('radix', 'mant_dig', 'min_exp', 'max_exp', 'rounds')},
        'execution_flags': dict({key: int(getattr(sys.flags, key, 0)) for key in _FLAG_NAMES},
                               integer_string_digit_limit=sys.get_int_max_str_digits(),
                               recursion_limit=sys.getrecursionlimit()),
        'modules': modules,
    }
    return validate_runtime_contract(contract)


def _fingerprint(value):
    if type(value) is not dict or value.get('kind') not in ('file', 'built-in', 'frozen'):
        raise ValueError('invalid runtime component fingerprint')
    if value['kind'] != 'file':
        if set(value) != {'kind'}:
            raise ValueError('invalid built-in runtime component')
        return
    if (set(value) != {'kind', 'bytes', 'sha256'} or type(value['bytes']) is not int
            or value['bytes'] <= 0 or type(value['sha256']) is not str
            or re.fullmatch('[0-9a-f]{64}', value['sha256']) is None):
        raise ValueError('invalid file runtime fingerprint')


def validate_runtime_contract(payload):
    if type(payload) is not dict or set(payload) != _FIELDS or payload.get('schema') != 'calibration-runtime-v1':
        raise ValueError('invalid runtime contract schema or fields')
    for name in ('implementation', 'python_version', 'cache_tag', 'compiler', 'system', 'kernel', 'machine'):
        if type(payload[name]) is not str or not payload[name] or len(payload[name]) > 512:
            raise ValueError('invalid runtime text: ' + name)
    for name in ('build', 'libc'):
        if type(payload[name]) is not list or len(payload[name]) != 2 or any(type(x) is not str or len(x) > 512 for x in payload[name]):
            raise ValueError('invalid runtime pair: ' + name)
    if payload['system'] != 'Linux' or payload['implementation'] != 'cpython':
        raise ValueError('measured execution requires the supported CPython Linux runtime')
    if payload['byteorder'] not in ('little', 'big') or type(payload['pointer_bits']) is not int or payload['pointer_bits'] not in (32, 64):
        raise ValueError('invalid runtime word representation')
    f = payload['float_model']
    if type(f) is not dict or set(f) != {'radix', 'mant_dig', 'min_exp', 'max_exp', 'rounds'} or any(type(x) is not int for x in f.values()):
        raise ValueError('invalid runtime float model')
    if (f['radix'], f['mant_dig'], f['min_exp'], f['max_exp']) != (2, 53, -1021, 1024):
        raise ValueError('finite target requires binary64 floats')
    flags = payload['execution_flags']
    if (type(flags) is not dict or set(flags) != set(_FLAG_NAMES) | {'integer_string_digit_limit', 'recursion_limit'}
            or any(type(value) is not int or value < 0 for value in flags.values())
            or flags['recursion_limit'] < 1):
        raise ValueError('invalid declared Python execution flags')
    _fingerprint(payload['interpreter'])
    if payload['interpreter']['kind'] != 'file':
        raise ValueError('interpreter binary must have a content fingerprint')
    if type(payload['modules']) is not dict or set(payload['modules']) != set(_MODULES):
        raise ValueError('runtime module inventory differs')
    for value in payload['modules'].values():
        _fingerprint(value)
    return strict_json(canonical_json(payload))


def verify_runtime_contract(payload):
    expected = validate_runtime_contract(payload)
    observed = capture_runtime_contract()
    if observed != expected:
        changed = sorted(key for key in _FIELDS if observed[key] != expected[key])
        raise ValueError('runtime contract differs: ' + ', '.join(changed))
    return observed
