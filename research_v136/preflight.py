from pathlib import PurePosixPath

def validate(entries):
    if not isinstance(entries,list) or not entries:raise ValueError('Nonempty binding list required')
    seen={}
    for e in entries:
        if not isinstance(e,dict) or set(e)!={'path','bytes','sha256'}:raise ValueError('Exact file binding schema required')
        if not isinstance(e['path'],str) or not PurePosixPath(e['path']).is_absolute() or '..' in PurePosixPath(e['path']).parts:raise ValueError('Absolute normalized path required')
        if type(e['bytes'])is not int or e['bytes']<0:raise ValueError('Nonnegative byte count required')
        h=e['sha256']
        if type(h)is not str or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):raise ValueError('SHA256 required')
        if e['path'] in seen and seen[e['path']]!=e:raise ValueError('Conflicting bindings')
        seen[e['path']]=e
    return len(seen)
