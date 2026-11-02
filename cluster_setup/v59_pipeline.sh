#!/bin/bash
# One use only. Partial submission is preserved for inspection, never rerun.
set -euo pipefail
launch="local_runs/continuation-v59-20261014-a"
campaign="local_runs/full-precision-anchor-v59-20261014-a"
prior="local_runs/exposed-quality-v55-20261011-a"
checks="local_runs/v59-software-a.json"
manifest="local_runs/cluster-setup-20261010/container-13155.sha256"
test ! -e "$launch"
test ! -e "$campaign"
test ! -e "$checks"
test -z "$(git status --porcelain)"
test -f "$prior/artifact-audit.json"
test "$(sha256sum "$prior/artifact-audit.json" | cut -d ' ' -f 1)" = "fa4a762a2ca6389968a503c0e224d1bd3f0d1bf0bb0aedb7acd24dd9d251b042"
test -z "$(squeue -h -u poonam -n second59-checks,second59-register,second59-quality,second59-audit)"
mkdir "$launch"
git rev-parse HEAD > "$launch/source-commit.txt"
previous=""
submit() {
    local label="$1" limit="$2" jid
    shift 2
    local deps=()
    if test -n "$previous"; then deps=(--dependency="afterok:$previous" --kill-on-invalid-dep=yes); fi
    jid=$(sbatch --parsable --no-requeue --nodelist=csis.mn1 --mem=16G --time="$limit" \
        "${deps[@]}" --job-name="second59-$label" --output="$launch/$label-%j.log" \
        cluster_setup/run_cpu.sbatch "$manifest" "$@")
    [[ "$jid" =~ ^[0-9]+$ ]]
    printf '%s\t%s\n' "$label" "$jid" >> "$launch/jobs.tsv"
    previous="$jid"
}
submit checks 00:20:00 -m research_v59.checks "$checks"
submit register 00:15:00 -m research_v59.campaign register "$campaign" "$prior" "$checks"
submit quality 05:10:00 -m research_v59.campaign run "$campaign"
submit audit 00:30:00 -m research_v59.audit "$campaign" "$campaign/artifact-audit.json"
cat "$launch/jobs.tsv"
