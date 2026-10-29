#!/bin/bash
set -euo pipefail
# All substantial bootstrap work is inside the measured host envelope.
exec python3 -B /nfs_home/users/poonam/second-20261010/local_runs/matched-complete-recovery-v112-20261026-a/research_v112/host.py "$@"
