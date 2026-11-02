"""Verify the existing default container paths, without redirecting any output."""
import os
from pathlib import Path
import tempfile
from research_v88.storage import _identity
from research_v110.config import RUN
from research_v80.io import require


def verify(start, expected, operation, arguments):
    require(start['program_sha256'] == expected and start['operation'] == operation
            and start['arguments'] == list(arguments)
            and start['job_id'] == os.environ.get('SLURM_JOB_ID'),
            'Host observation is not from this registered allocation')
    require(start['admission']['status'] == 'admitted_at_observation_only',
            'Fresh host capacity admission is required')
    # tempfile performs its ordinary small write/delete usability check here;
    # that cost and space belong to this registered software/entry allowance.
    temporary = Path(tempfile.gettempdir()).resolve()
    require(temporary == Path('/tmp'), 'Default temporary path differs; no redirect permitted')
    paths = {'project': RUN, 'temporary': temporary}
    observed = {}
    for scope, path in paths.items():
        dev, inode, gid, mode = _identity(str(path))
        host = start['snapshot']['observations'][scope]
        require(dev == host['device'] and gid == host['write_group'],
                'Container filesystem or new-file group differs from admitted host scope')
        observed[scope] = dict(path=str(path), device=dev, write_group=gid)
    return dict(status='matched_host_devices_and_new_file_groups', observations=observed,
                paths_redirected=False, capacity_reserved=False)
