#!/usr/bin/env bash
# Archive the metadata of the forecast workflow runs (GitHub deletes run logs after 90 days by default).
# Run at the END of the live test, and in any case by 2027-02-01. Not run automatically.
set -euo pipefail
cd "$(dirname "$0")/.."
# Single end-of-test pass: complete the pending OpenTimestamps proofs in place (needs network; failures tolerated).
ots upgrade forecasts/*.ots || true
mkdir -p audit
# -L 1000, not 200: 3 scheduled runs/day over the test window exceed 200 runs, which would drop the earliest ones.
gh run list --workflow forecast -L 1000 --json databaseId,createdAt,headSha,conclusion,event > audit/runs.json
echo "saved $(jq length audit/runs.json) runs to audit/runs.json"
