#!/bin/bash
set -euo pipefail
# All substantial bootstrap work is inside the measured host envelope.
exec python3 -B /nfs_home/users/poonam/second-20261010/local_runs/matched-complete-recovery-v92-20261024-a/research_v92/host.py "$@"
