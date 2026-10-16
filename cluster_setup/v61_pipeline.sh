#!/bin/bash
# One use only. Inspect a passing Linux software receipt before invoking.
# Preserve partial submissions; never rerun this script or extend the allowance.
set -euo pipefail
launch="local_runs/continuation-v61-20261014-a"
campaign="local_runs/full-precision-service-v61-20261014-a"
prior="local_runs/full-precision-anchor-v59-20261014-a"
checks="local_runs/v61-software-a.json"
manifest="local_runs/cluster-setup-20261010/container-13155.sha256"
test ! -e "$launch"
test ! -e "$campaign"
test -f "$checks"
test -z "$(git status --porcelain)"
test "$(sha256sum "$prior/artifact-audit.json" | cut -d ' ' -f 1)" = "286a2c74b676e55ff4d463d31545ca8138eb7dce36e515112fb697575a89f6e6"
test -z "$(squeue -h -u poonam -n second61-register,second61-prepare,second61-cached,second61-cold,second61-hybrid,second61-compressed,second61-oracle,second61-audit,second61-postrun)"
mkdir "$launch"
git rev-parse HEAD > "$launch/source-commit.txt"
previous=""
submit() {
    local label="$1" limit="$2" jid
    shift 2
    local deps=()
    if test -n "$previous"; then deps=(--dependency="afterok:$previous" --kill-on-invalid-dep=yes); fi
    jid=$(sbatch --parsable --no-requeue --nodelist=csis.mn1 --mem=16G --time="$limit" \
        "${deps[@]}" --job-name="second61-$label" --output="$launch/$label-%j.log" \
        cluster_setup/run_cpu.sbatch "$manifest" "$@")
    [[ "$jid" =~ ^[0-9]+$ ]]
    printf '%s\t%s\n' "$label" "$jid" >> "$launch/jobs.tsv"
    previous="$jid"
}
submit register 00:15:00 -m research_v61.campaign register "$campaign" "$prior" "$checks"
submit prepare 04:10:00 -m research_v61.campaign run "$campaign" prepare
submit cached 04:10:00 -m research_v61.campaign run "$campaign" cached
submit cold 04:40:00 -m research_v61.campaign run "$campaign" cold
submit hybrid 05:10:00 -m research_v61.campaign run "$campaign" hybrid
submit compressed 06:10:00 -m research_v61.campaign run "$campaign" compressed
submit oracle 05:10:00 -m research_v61.campaign run "$campaign" oracle
submit audit 00:30:00 -m research_v61.audit "$campaign" "$campaign/artifact-audit.json"
submit postrun 00:30:00 -m research_v61.postrun "$campaign" "$campaign/artifact-audit.json" "$campaign/postrun-audit.json"
cat "$launch/jobs.tsv"
