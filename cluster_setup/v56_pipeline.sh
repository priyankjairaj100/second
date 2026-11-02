#!/bin/bash
# One-use GPU continuation, gated on the V55 valid-result audit, including losses.
set -euo pipefail
launch="local_runs/continuation-v56-20261011-a"
campaign="local_runs/gpu-parity-v56-20261011-a"
checks="local_runs/v56-software-a.json"
test ! -e "$campaign"
test -f "$checks"
test -z "$(git status --porcelain)"
test "$(awk '$1=="audit" {print $2}' local_runs/continuation-v55-20261011-a/jobs.tsv)" = "13327"
mkdir "$launch"
git rev-parse HEAD > "$launch/source-commit.txt"
jid=$(sbatch --parsable --no-requeue --nodelist=csis.cn3 --dependency=afterok:13327 --kill-on-invalid-dep=yes \
    --job-name=second56-parity --output="$launch/parity-%j.log" \
    research_v56/run_gpu.sbatch -m research_v56.campaign "$campaign" "$checks")
[[ "$jid" =~ ^[0-9]+$ ]]
printf 'register-parity-audit\t%s\n' "$jid" > "$launch/jobs.tsv"
cat "$launch/jobs.tsv"
