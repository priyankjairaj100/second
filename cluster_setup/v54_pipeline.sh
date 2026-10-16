#!/bin/bash
# One-use sequential full-model pipeline. Run from the clean cluster checkout.
# A failed submission is never automatically retried; inspect jobs.tsv first.
set -euo pipefail
launch="local_runs/continuation-v54-20261011-a"
campaign="local_runs/full-model48-v54-20261011-a"
checks="local_runs/v54-software-a.json"
manifest="local_runs/cluster-setup-20261010/container-13155.sha256"
test ! -e "$campaign"
test -f "$checks"
test -z "$(git status --porcelain)"
mkdir "$launch"
git rev-parse HEAD > "$launch/source-commit.txt"
previous=""
submit() {
    label="$1"; limit="$2"; shift 2
    dependency=()
    if test -n "$previous"; then dependency=(--dependency="afterok:$previous" --kill-on-invalid-dep=yes); fi
    jid=$(sbatch --parsable --no-requeue --nodelist=csis.mn1 --mem=16G --time="$limit" \
        --job-name="second54-$label" --output="$launch/$label-%j.log" "${dependency[@]}" \
        cluster_setup/run_cpu.sbatch "$manifest" "$@")
    [[ "$jid" =~ ^[0-9]+$ ]]
    printf '%s\t%s\n' "$label" "$jid" >> "$launch/jobs.tsv"
    previous="$jid"
}
submit register 00:10:00 -m research_v54.campaign register "$campaign" local_runs/c4-data-v45-20261010-a "$checks"
submit prepare 04:10:00 -m research_v54.campaign run "$campaign" prepare
submit cached 04:10:00 -m research_v54.campaign run "$campaign" cached
submit cold 04:40:00 -m research_v54.campaign run "$campaign" cold
submit hybrid 05:10:00 -m research_v54.campaign run "$campaign" hybrid
submit compressed 06:10:00 -m research_v54.campaign run "$campaign" compressed
submit oracle 05:10:00 -m research_v54.campaign run "$campaign" oracle
submit audit 00:30:00 -m research_v54.audit "$campaign" "$campaign/artifact-audit.json"
submit postrun 00:30:00 -m research_v54.postrun "$campaign" "$campaign/artifact-audit.json" "$campaign/postrun-audit.json"
cat "$launch/jobs.tsv"
