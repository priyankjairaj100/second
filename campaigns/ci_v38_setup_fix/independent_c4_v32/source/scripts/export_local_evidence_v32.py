#!/usr/bin/env python3
"""Copy local V32 text evidence for publication, without moving live campaigns.

Omit --output for an inventory. A new archives/local-* destination creates a
metadata-only snapshot. It is not runnable and does not include binary outputs.
This exporter performs no scientific validation and never filters by outcome.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.pilot_budget import research_worker_lock
from src.run_store import canonical_json

MAX_FILE_BYTES=32*2**20
MAX_TOTAL_BYTES=256*2**20
CAMPAIGNS=('independent_wikitext_v32','independent_c4_v32')


def require(condition,message):
    if not condition:raise ValueError(message)


def relative_path(value,kind):
    path=Path(value)
    require(not path.is_absolute() and str(path)==value and '..' not in path.parts and '.' not in path.parts,
        kind+' must be a normalized relative path')
    if kind=='workspace':
        require(len(path.parts)>=2 and path.parts[0]=='local_runs','workspace must be below local_runs')
    else:
        require(len(path.parts)==2 and path.parts[0]=='archives' and path.parts[1].startswith('local-')
            and len(path.parts[1])>6,'output must be a new archives/local-* directory')
    absolute=ROOT/path
    require(not any(p.is_symlink() for p in (absolute,*absolute.parents)),'symbolic paths are refused')
    return absolute


def collect(workspace):
    """Return every allowed text file from both roots, including failed attempts."""
    root=relative_path(workspace,'workspace')
    require(root.is_dir(),'workspace does not exist')
    files={};omitted=[];total=0;roots=[]
    for name in CAMPAIGNS:
        campaign=root/name
        if not campaign.exists():continue
        require(campaign.is_dir() and not campaign.is_symlink(),'invalid campaign directory')
        roots.append(name)
        for path in sorted(campaign.rglob('*')):
            require(not path.is_symlink(),'symbolic evidence paths are refused')
            mode=path.stat().st_mode
            if stat.S_ISDIR(mode):continue
            require(stat.S_ISREG(mode),'evidence must be a regular file')
            relative=path.relative_to(root).as_posix()
            if path.suffix not in ('.json','.py'):
                omitted.append(dict(original_workspace_relative=relative,bytes=path.stat().st_size,
                    reason='binary, cache, lock, or unsupported text extension'))
                continue
            require(path.stat().st_size<=MAX_FILE_BYTES,'text evidence exceeds file limit')
            raw=path.read_bytes()
            require(len(raw)<=MAX_FILE_BYTES,'text evidence grew beyond file limit')
            raw.decode('utf-8');require(b'\0' not in raw,'NUL-containing evidence is not text')
            total+=len(raw);require(total<=MAX_TOTAL_BYTES,'text evidence exceeds total limit')
            files[relative]=raw
    require(roots,'workspace has no V32 campaign roots')
    # Complete analyses are optional. Their absence never hides failed roots.
    for path in sorted(root.glob('*-analysis.json')):
        require(not path.is_symlink() and path.is_file(),'unsafe analysis file')
        require(path.stat().st_size<=MAX_FILE_BYTES,'analysis exceeds file limit')
        raw=path.read_bytes();raw.decode('utf-8')
        require(len(raw)<=MAX_FILE_BYTES and b'\0' not in raw,'invalid analysis text')
        total+=len(raw);require(total<=MAX_TOTAL_BYTES,'text evidence exceeds total limit')
        files[path.name]=raw
    require(files,'workspace contains no publishable text evidence')
    return root,files,omitted,roots,total


def snapshot(workspace,output=None):
    """Read-only inventory, or a new byte-preserving publication copy."""
    destination=relative_path(output,'output') if output is not None else None
    if destination is not None:require(not destination.exists(),'output already exists; snapshots are never overwritten')
    root,files,omitted,roots,total=collect(workspace)
    entries=[]
    for name,raw in sorted(files.items()):
        entries.append(dict(original_repository_relative=(root/ name).relative_to(ROOT).as_posix(),
            original_workspace_relative=name,archive_relative='files/'+name,
            sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
    manifest=dict(schema='v32-local-metadata-export-v1',original_workspace=workspace,
        original_workspace_absolute=str(root),included_roots=roots,files=entries,omitted_files=omitted,
        metadata_only=True,runnable=False,binary_outputs_included=False,scientific_validation_performed=False,
        outcome_filter_applied=False,live_workspace_modified=False,metadata_paths_rewritten=False,
        scope='Publication copy only. Original plans retain their original absolute paths. Preserve live binary outputs separately.',
        future_reproduction='Use a new local_runs namespace with scripts/continue_empirical_v32.py --workspace local_runs/replay-002 --execute.',
        files_count=len(entries),text_bytes=total)
    if destination is None:return dict(exported=False,inventory=manifest)
    destination.mkdir(parents=True,exist_ok=False)
    for entry in entries:
        target=destination/entry['archive_relative'];target.parent.mkdir(parents=True,exist_ok=True)
        raw=files[entry['original_workspace_relative']]
        with target.open('xb') as stream:stream.write(raw)
        require(hashlib.sha256(target.read_bytes()).hexdigest()==entry['sha256'],'copied evidence differs')
    # Detect external edits despite the shared research-launcher lock.
    for entry in entries:
        source=root/entry['original_workspace_relative']
        require(not source.is_symlink() and hashlib.sha256(source.read_bytes()).hexdigest()==entry['sha256'],
            'source changed during export; preserve this incomplete export and use a new destination')
    with (destination/'EXPORT_MANIFEST.json').open('xb') as stream:stream.write(canonical_json(manifest))
    return dict(exported=True,destination=str(destination),files=len(entries),text_bytes=total,
        metadata_only=True,runnable=False,scientific_validation_performed=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',required=True,help='Existing local_runs workspace')
    parser.add_argument('--output',help='New archives/local-* publication snapshot; omit for inventory')
    args=parser.parse_args()
    with research_worker_lock(ROOT):result=snapshot(args.workspace,args.output)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,UnicodeError) as exc:
        print(str(exc),file=sys.stderr);raise SystemExit(1)
