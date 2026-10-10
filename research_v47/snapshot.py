"""Non-executable NumPy parameter archive with every float64 word committed."""
from types import SimpleNamespace
from pathlib import Path
import hashlib
import json
import numpy as np
from scripts.run_quality_v30 import NumpyQualityDecoder


def word_sha(array):return hashlib.sha256(array.astype('<f8',copy=False).tobytes(order='C')).hexdigest()


class SnapshotBase:
    def __init__(self,config,weights):self.config,self._float_weights=config,weights
    def _tokens(self,tokens):
        values=tuple(tokens)
        if not 1<=len(values)<=self.config.max_sequence_length:
            raise ValueError('Invalid sequence extent')
        if any(type(t) is not int or not 0<=t<self.config.vocabulary_size for t in values):
            raise ValueError('Invalid token ID')
        return values


def write_snapshot(reference,directory):
    directory=Path(directory);directory.mkdir(exist_ok=False)
    fields={name:getattr(reference,name) for name in
        ('embeddings','positions','head','head_bias','final_scale','final_bias')}
    fields.update({'weights/'+name:array for name,array in reference.weights.items()})
    fields.update({f'blocks/{index}/{name}':array for index,block in enumerate(reference.blocks) for name,array in block.items()})
    manifest=dict(schema='numpy-quality-parameter-words-v47',config=vars(reference.config),arrays={})
    arrays={}
    for index,(name,array) in enumerate(sorted(fields.items())):
        if type(array) is not np.ndarray or array.dtype!=np.float64 or not np.isfinite(array).all():
            raise ValueError('Finite float64 source arrays required')
        key=f'array_{index:04d}';arrays[key]=array
        manifest['arrays'][name]=dict(key=key,shape=list(array.shape),dtype='<f8',word_sha256=word_sha(array))
    # Uncompressed .npz avoids pickle, lossy conversion and a codec dependency.
    np.savez(directory/'parameters.npz',**arrays)
    from src.run_store import canonical_json
    (directory/'manifest.json').write_bytes(canonical_json(manifest))
    restored=load_snapshot(directory/'manifest.json',directory/'parameters.npz')
    if set(restored.weights)!=set(reference.weights):raise ValueError('Snapshot stage extent differs')
    return manifest


def load_snapshot(manifest_path,archive_path):
    manifest=json.loads(Path(manifest_path).read_bytes())
    if manifest['schema']!='numpy-quality-parameter-words-v47':raise ValueError('Snapshot schema differs')
    config=SimpleNamespace(**manifest['config']);fields={}
    with np.load(archive_path,allow_pickle=False) as archive:
        if len(archive.files)!=len(manifest['arrays']) or set(archive.files)!={v['key'] for v in manifest['arrays'].values()}:
            raise ValueError('Archive array extent differs')
        for name,entry in manifest['arrays'].items():
            array=archive[entry['key']]
            if (array.dtype!=np.float64 or list(array.shape)!=entry['shape'] or entry['dtype']!='<f8'
                    or not np.isfinite(array).all() or word_sha(array)!=entry['word_sha256']):
                raise ValueError('Parameter words changed: '+name)
            fields[name]=array
    obj=NumpyQualityDecoder.__new__(NumpyQualityDecoder);obj.np=np;obj.config=config
    for name in ('embeddings','positions','head','head_bias','final_scale','final_bias'):setattr(obj,name,fields[name])
    obj.weights={name.split('/',1)[1]:v for name,v in fields.items() if name.startswith('weights/')}
    obj.blocks=[{name.split('/',2)[2]:v for name,v in fields.items() if name.startswith(f'blocks/{i}/')}
        for i in range(config.block_count)]
    obj.base=SnapshotBase(config,obj.weights)
    if (obj.embeddings.shape!=(config.vocabulary_size,config.model_width)
            or obj.positions.shape!=(config.max_sequence_length,config.model_width)
            or obj.head.shape!=(config.vocabulary_size,config.model_width)
            or len(obj.weights)!=4*config.block_count):raise ValueError('Decoder geometry differs')
    return obj
