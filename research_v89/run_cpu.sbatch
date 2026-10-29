#!/bin/bash
set -euo pipefail
# All substantial bootstrap work is inside the measured host envelope.
exec python3 -B /nfs_home/users/poonam/second-20261010/local_runs/four-cell-recovery-v89-20261023-a/research_v89/host.py "$@"
