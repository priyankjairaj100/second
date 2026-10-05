"""Bounded real checkpoint feature diagnostic, never a full repair benchmark.

Read only selected embedding rows and one real block. Use the existing finite
schedule without quantization. A stage stop is a prefix of the full model.
"""
import argparse
import hashlib
import json
import struct
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.checkpoint_adapter import _SafeFile, _config, _json
from src.certified_transformer import _execute as _original_execute, _StageWeights, _Finite
from src.transformer_backend import _check_runtime
from types import FunctionType
from ordered_float64 import finite_linear
_execute = FunctionType(_original_execute.__code__, dict(_original_execute.__globals__, _linear=finite_linear), _original_execute.__name__, _original_execute.__defaults__)
from src.run_store import canonical_json, atomic_write, digest
from src.transaction_timing import verify_command_admission


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('plan', type=Path)
    args = parser.parse_args()
    _check_runtime()
    raw = args.plan.read_bytes()
    plan = json.loads(raw)
    for filename, expected in plan['source_sha256'].items():
        if digest(Path(filename).read_bytes()) != expected:
            raise ValueError('diagnostic source changed: ' + filename)
    command = [sys.executable, str(Path(__file__).resolve()), str(args.plan.absolute())]
    verify_command_admission(plan['protocol_sha256'], 'feasibility', command)
    root = Path(plan['checkpoint'])
    records_path = Path(plan['records'])
    if digest(records_path.read_bytes()) != plan['records_sha256']:
        raise ValueError('prepared records changed')
    for file, expected in plan['checkpoint_sha256'].items():
        with (root / file).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise ValueError('checkpoint changed: ' + file)
    records = json.loads(records_path.read_bytes())['records']
    config, tied = _config(_json((root / 'config.json').read_bytes()))
    if config.model_width != 768 or config.block_count != 6:
        raise ValueError('this frozen diagnostic expects DistilGPT2')
    out = Path(plan['output']); out.mkdir(parents=True, exist_ok=True)
    result = dict(schema='real-prefix-feature-pilot-v1', status='running', plan_sha256=digest(raw),
        scope='unquantized block-zero features; exact-order NumPy prototype; no model repair or speed ratio',
        full_model_complete=False, paper_speed_evidence=False, stages=[])
    def save():
        atomic_write(out / 'progress.json', canonical_json(result))
    save()
    start = time.perf_counter_ns()
    with (root / 'model.safetensors').open('rb') as handle:
        reader = _SafeFile(handle, max_header_bytes=16*1024*1024)
        def tensor(name, transpose=False):
            value = reader.values(name); shape = reader.tensors[name].shape
            if len(shape) == 1:
                return value
            rows, cols = shape
            if transpose:
                return tuple(tuple(value[i*cols+j] for i in range(rows)) for j in range(cols))
            return tuple(value[i*cols:(i+1)*cols] for i in range(rows))
        def selected_rows(name, indices):
            entry = reader.tensors[name]
            if entry.dtype != 'F32' or entry.shape[1] != config.model_width:
                raise ValueError('unexpected embedding storage')
            width = entry.shape[1]
            rows = {}
            for index in sorted(set(indices)):
                if not 0 <= index < entry.shape[0]:
                    raise ValueError('embedding index out of range')
                handle.seek(reader.data_offset + entry.begin + index*width*4)
                rows[index] = struct.unpack('<'+'f'*width, handle.read(width*4))
            return rows
        embeddings = selected_rows('transformer.wte.weight', [t for r in records for t in r['tokens']])
        positions = selected_rows('transformer.wpe.weight', range(max(len(r['tokens']) for r in records)))
        block = {}; weights = {}
        for dest, source in [('qkv','attn.c_attn'),('attn_out','attn.c_proj'),('mlp_up','mlp.c_fc'),('mlp_down','mlp.c_proj')]:
            weights['block.0000.'+dest] = tensor('transformer.h.0.'+source+'.weight', True)
            block[dest+'_bias'] = tensor('transformer.h.0.'+source+'.bias')
        for dest, source in [('norm1','ln_1'),('norm2','ln_2')]:
            block[dest+'_scale'] = tensor('transformer.h.0.'+source+'.weight')
            block[dest+'_bias'] = tensor('transformer.h.0.'+source+'.bias')
        base = SimpleNamespace(config=config, _token_embeddings=embeddings,
            _position_embeddings=positions, _blocks=(block,))
        wrapped = _StageWeights(tuple(weights), lambda s:tuple(tuple(_Finite(x) for x in row) for row in weights[s]))
        result['selected_parameter_loading_ns'] = time.perf_counter_ns()-start
        save()
        for stage in plan['stages']:
            for record in records:
                before = time.perf_counter_ns()
                try:
                    rows = _execute(base, tuple(record['tokens']), wrapped, lambda x:_Finite(float(x)), stage)
                    data = b''.join(struct.pack('<d',x.value) for row in rows for x in row)
                    name = stage.replace('.','_')+'-'+digest(record['id'].encode())[:12]+'.bin'
                    atomic_write(out / name,data)
                    row = dict(stage=stage, record_id=record['id'],status='complete',
                        elapsed_ns=time.perf_counter_ns()-before,shape=[len(rows),len(rows[0])],
                        features_sha256=digest(data),features_file=name)
                except Exception as error:
                    row = dict(stage=stage,record_id=record['id'],status='failed',
                        elapsed_ns=time.perf_counter_ns()-before,error_type=type(error).__name__,error=str(error))
                    result['stages'].append(row);result['status']='failed';save();raise
                result['stages'].append(row);save()
                print(json.dumps(row),flush=True)
        result['status']='complete';save()


if __name__ == '__main__':
    main()
