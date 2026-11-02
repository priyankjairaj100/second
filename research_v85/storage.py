"""Read-only storage admission for a future, separately registered recovery.

The observed CSIS quota tool reports unsuffixed blocks in KiB. It can exit1
while returning a valid over-quota row. Filesystem free space is insufficient:
use both the account quota and statvfs. This is an observation, not a reservation
against concurrent account writers, and does not attest to group/project quotas.
"""
import datetime, os, re, subprocess, sys
from pathlib import Path

class StorageAdmissionError(ValueError):
    pass

def require(ok, message):
    if not ok:
        raise StorageAdmissionError(message)

def count(text):
    require(re.fullmatch(r'\d+\*?', text) is not None, 'Expected raw quota integer, not rounded human units')
    return int(text.rstrip('*'))

def parse_quota(raw, source):
    require(isinstance(raw,str) and len(raw)<128*1024, 'Bounded quota output required')
    require(any(line.split()==['Filesystem','blocks','quota','limit','grace','files','quota','limit','grace'] for line in raw.splitlines()), 'Raw blocks/files quota header required')
    rows=[line.split() for line in raw.splitlines() if line.split() and line.split()[0]==source]
    require(len(rows)==1, 'Exactly one quota row for the output filesystem required')
    fields=rows[0];require(len(fields)>=7, 'Incomplete quota row')
    used,soft,hard=map(count,fields[1:4]);tail=fields[4:]
    if re.fullmatch(r'\d+\*?',tail[0]) is None:
        tail=tail[1:]  # Human grace label; never use its deadline to admit work.
    require(len(tail) in (3,4), 'Ambiguous inode quota row')
    files,file_soft,file_hard=map(count,tail[:3])
    require(not tail[3:] or re.fullmatch(r'\d+\*?',tail[3]) is None, 'Unexpected quota columns')
    require(hard>0 and (soft==0 or soft<=hard), 'Known finite block hard limit required')
    require(file_hard==0 or file_soft==0 or file_soft<=file_hard, 'Invalid inode quota limits')
    limit=min(x for x in (soft,hard) if x>0)
    file_limits=[x for x in (file_soft,file_hard) if x>0]
    return dict(source=source,block_unit_bytes=1024,used_bytes=used*1024,
                soft_limit_bytes=soft*1024,hard_limit_bytes=hard*1024,
                headroom_bytes=max(0,limit-used)*1024,used_files=files,
                file_headroom=min(file_limits)-files if file_limits else None,
                refuses_soft_limit_grace=True)

def admit(quota, filesystem_bytes, filesystem_files, required_bytes, required_files):
    for value in (filesystem_bytes,filesystem_files,required_bytes,required_files):
        require(type(value) is int and value>=0, 'Nonnegative integer storage count required')
    require(required_bytes>0 and required_files>0, 'Registered positive storage allowance required')
    available=min(quota['headroom_bytes'],filesystem_bytes)
    files=filesystem_files if quota['file_headroom'] is None else min(quota['file_headroom'],filesystem_files)
    require(available>=required_bytes, 'Insufficient account or filesystem byte headroom')
    require(files>=required_files, 'Insufficient account or filesystem inode headroom')
    return dict(status='admitted_at_observation_only',available_bytes=available,
                available_files=files,required_bytes=required_bytes,required_files=required_files,
                capacity_reserved=False,group_project_quota_attested=False,
                concurrent_writers_can_invalidate=True)

def inspect(path, required_bytes, required_files):
    """Never creates files, changes quotas, launches jobs or retries a command."""
    require(sys.platform=='linux', 'Pinned Linux host inspection required')
    path=Path(path).absolute()
    require(path.is_dir() and not any(x.is_symlink() for x in (path,*path.parents)), 'Existing nonsymbolic output directory required')
    env=dict(os.environ,LC_ALL='C')
    mount=subprocess.run(['findmnt','-n','-o','SOURCE,TARGET','-T',str(path)],capture_output=True,text=True,timeout=10,env=env)
    require(mount.returncode==0 and not mount.stderr.strip() and len(mount.stdout.splitlines())==1, 'Unambiguous mounted filesystem required')
    fields=mount.stdout.split();require(len(fields)==2 and path.is_relative_to(Path(fields[1])), 'Output mount identity differs')
    report=subprocess.run(['quota','-v','-w'],capture_output=True,text=True,timeout=10,env=env)
    require(report.returncode in (0,1) and not report.stderr.strip(), 'Quota query failed; do not assume unlimited capacity')
    quota=parse_quota(report.stdout,fields[0]);stat=os.statvfs(path)
    result=admit(quota,stat.f_bavail*stat.f_frsize,stat.f_favail,required_bytes,required_files)
    return dict(result,quota=quota,path=str(path),observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
