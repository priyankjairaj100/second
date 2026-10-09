#!/usr/bin/env python3
"""Prepare a text-only GitHub checkpoint from the reviewed Git index.

This does not contact GitHub or move a ref. Upload new_blobs, create the tree,
require expected_tree equality, then use a non-force expected-head update.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(*args, data=None):
    return subprocess.check_output(['git', *args], cwd=ROOT, input=data)


def index_entries():
    result = {}
    for row in git('ls-files', '--stage', '-z').split(b'\0'):
        if not row:
            continue
        meta, path = row.split(b'\t', 1)
        mode, sha, stage = meta.decode().split()
        if stage != '0' or mode not in ('100644', '100755'):
            raise ValueError('Unsupported index entry')
        result[path.decode()] = (mode, sha)
    return result


def blobs(shas):
    names = sorted(set(shas))
    raw = git('cat-file', '--batch', data=('\n'.join(names)+'\n').encode())
    found = {}
    offset = 0
    for expected in names:
        end = raw.index(b'\n', offset)
        sha, kind, size = raw[offset:end].decode().split()
        if sha != expected or kind != 'blob':
            raise ValueError('Unexpected Git object')
        size = int(size)
        found[sha] = raw[end+1:end+1+size]
        offset = end+size+2
    if offset != len(raw):
        raise ValueError('Unexpected batch suffix')
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'tmp/github-checkpoint-v34.json')
    args = parser.parse_args()
    entries = index_entries()
    content = blobs(sha for _, sha in entries.values())
    lines = [hashlib.sha256(content[sha]).hexdigest()+'  '+name+'\n'
             for name, (_, sha) in sorted(entries.items()) if name != 'MANIFEST.sha256']
    (ROOT/'MANIFEST.sha256').write_text(''.join(lines))
    git('add', 'MANIFEST.sha256')
    entries = index_entries()
    names = [p.decode() for p in git('diff', '--cached', '--name-only', '-z', 'HEAD').split(b'\0') if p]
    if any(name not in entries for name in names):
        raise ValueError('Deletion requires separate review')
    content.update(blobs(entries[name][1] for name in names))
    reachable = {row.split()[0].decode() for row in git('rev-list', '--objects', 'HEAD').splitlines()}
    new = {}
    changes = []
    for name in names:
        mode, sha = entries[name]
        changes.append(dict(path=name, mode=mode, type='blob', sha=sha))
        if sha in reachable:
            continue
        raw = content[sha]
        if b'\0' in raw:
            raise ValueError('Binary publication refused: '+name)
        text = raw.decode('utf-8')
        if re.search(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|hf_[A-Za-z0-9]{30,})', text):
            raise ValueError('Possible credential refused: '+name)
        new[sha] = text
    payload = dict(repository='priyankjairaj100/second', parent=git('rev-parse','HEAD').decode().strip(),
                   base_tree=git('rev-parse','HEAD^{tree}').decode().strip(),
                   expected_tree=git('write-tree').decode().strip(), changes=changes, new_blobs=new)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False))
    print(json.dumps(dict(output=str(args.output), parent=payload['parent'], expected_tree=payload['expected_tree'],
                          changes=len(changes), new_blobs=len(new), characters=len(args.output.read_text()))))


if __name__ == '__main__':
    main()
