#!/bin/bash
# One-use conditional quality chain. Never rerun after a partial submission.
set -euo pipefail
launch="local_runs/continuation-v55-20261011-a"
campaign="local_runs/exposed-quality-v55-20261011-a"
v54="local_runs/full-model48-v54-20261011-a"
checks="local_runs/v55-software-a.json"
manifest="local_runs/cluster-setup-20261010/container-13155.sha256"
test ! -e "$campaign"
test -f "$checks"
test -z "$(git status --porcelain)"
# Bind the known prerequisite job to the archived V54 launch, before submission.
test "$(awk '$1=="postrun" {print $2}' local_runs/continuation-v54-20261011-a/jobs.tsv)" = "13317"
mkdir "$launch"
git rev-parse HEAD > "$launch/source-commit.txt"
previous="13317"
submit() {
    label="$1"; limit="$2"; shift 2
    jid=$(sbatch --parsable --no-requeue --nodelist=csis.mn1 --mem=16G --time="$limit" \
        --dependency="afterok:$previous" --kill-on-invalid-dep=yes \
        --job-name="second55-$label" --output="$launch/$label-%j.log" \
        cluster_setup/run_cpu.sbatch "$manifest" "$@")
    [[ "$jid" =~ ^[0-9]+$ ]]
    printf '%s\t%s\n' "$label" "$jid" >> "$launch/jobs.tsv"
    previous="$jid"
}
submit register 00:15:00 -m research_v55.campaign register "$campaign" "$v54" "$v54/artifact-audit.json" "$v54/postrun-audit.json" "$checks"
submit quality 05:10:00 -m research_v55.campaign run "$campaign"
submit audit 00:30:00 -m research_v55.audit "$campaign" "$campaign/artifact-audit.json"
cat "$launch/jobs.tsv"
