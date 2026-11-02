"""Bounded actual-byte comparison of every saved evaluator parameter.

The reference must be constructed from the prospectively bound checkpoint by the
admitted worker. This function does not itself authenticate that checkpoint.
"""
import math,zipfile
import numpy as np
from research_v67.io import read,require
from src.run_store import canonical_json,strict_json,digest

MAX_ARCHIVE=2*2**30
MAX_ARRAY=512*2**20
MAX_ARRAYS=128


def fields(reference):
    result={name:getattr(reference,name) for name in ['embeddings','positions','head','head_bias','final_scale','final_bias']}
    result.update({'weights/'+name:a for name,a in reference.weights.items()})
    result.update({f'blocks/{i}/{name}':a for i,b in enumerate(reference.blocks) for name,a in b.items()})
    require(0<len(result)<=MAX_ARRAYS,'Bounded complete parameter census required')
    for a in result.values():
        require(type(a) is np.ndarray and a.dtype==np.float64 and a.nbytes<=MAX_ARRAY
            and a.size>0 and np.isfinite(a).all(),'Bounded finite binary64 reference arrays required')
    require(sum(a.nbytes for a in result.values())<=MAX_ARCHIVE,'Reference parameter extent exceeds bound')
    return result


def verify(reference,manifest_path,archive_path,*,expected_manifest,expected_archive):
    raw=read(manifest_path,expected_manifest,maximum=2*2**20);manifest=strict_json(raw)
    require(canonical_json(manifest)==raw and set(manifest)=={'schema','config','arrays'}
        and manifest['schema']=='numpy-quality-parameter-words-v47'
        and manifest['config']==vars(reference.config),'Canonical complete parameter manifest/config required')
    before=read(archive_path,expected_archive,maximum=MAX_ARCHIVE,retain=False)
    expected=fields(reference);require(set(manifest['arrays'])==set(expected),'Complete actual parameter fields required')
    names={}
    for index,(name,a) in enumerate(sorted(expected.items())):
        entry=manifest['arrays'][name];key=f'array_{index:04d}'
        require(entry==dict(key=key,shape=list(a.shape),dtype='<f8',word_sha256=digest(a.astype('<f8',copy=False).tobytes(order='C'))),
            'Reference parameter words or declared array entry differ: '+name)
        names[key+'.npy']=(name,a)
    with zipfile.ZipFile(archive_path) as archive:
        members=archive.infolist()
        require(len(members)==len(names) and {m.filename for m in members}==set(names),'Exact unique non-executable archive members required')
        for member in members:
            name,a=names[member.filename]
            require(member.compress_type==zipfile.ZIP_STORED and member.file_size==member.compress_size
                and member.file_size<=MAX_ARRAY+65536 and not member.is_dir(),'Uncompressed bounded parameter arrays required')
            # Validate headers before NumPy can allocate a claimed oversized shape.
            with archive.open(member) as stream:
                version=np.lib.format.read_magic(stream)
                require(version in [(1,0),(2,0)],'Only bounded NPY1/2 headers admitted')
                reader=np.lib.format.read_array_header_1_0 if version==(1,0) else np.lib.format.read_array_header_2_0
                shape,fortran,dtype=reader(stream,max_header_size=65536)
                require(shape==a.shape and dtype.str=='<f8' and type(fortran) is bool
                    and stream.tell()+math.prod(shape)*8==member.file_size,'Actual NPY extent/dtype differs from admitted array')
    checked={}
    with np.load(archive_path,allow_pickle=False) as archive:
        for name,a in sorted(expected.items()):
            key=manifest['arrays'][name]['key'];actual=archive[key]
            require(actual.dtype==np.float64 and actual.shape==a.shape and np.isfinite(actual).all()
                and actual.astype('<f8',copy=False).tobytes(order='C')==a.astype('<f8',copy=False).tobytes(order='C'),
                'Actual saved parameter words differ: '+name)
            checked[name]=manifest['arrays'][name]
            del actual
    require(read(archive_path,before,maximum=MAX_ARCHIVE,retain=False)==before
        and read(manifest_path,expected_manifest,maximum=2*2**20)==raw,'Parameter artifacts changed during audit')
    return dict(status='verified',actual_all_parameter_words_equal=True,arrays=len(checked),
        parameter_word_bytes=sum(a.nbytes for a in expected.values()),manifest=expected_manifest,archive=before,
        includes_embeddings_positions_norm_bias_head_and_stage_weights=True,
        checkpoint_identity_validation_required_of_caller=True,gpu_transfer_checked=False,
        quality_evaluation=False,shared_reference_export_semantics=True)
