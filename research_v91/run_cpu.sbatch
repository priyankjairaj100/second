#!/bin/bash
set -euo pipefail
# All substantial bootstrap work is inside the measured host envelope.
exec python3 -B /nfs_home/users/poonam/second-20261010/local_runs/matched-transfer-admission-v91-20261024-a/research_v91/host.py "$@"
