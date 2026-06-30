#!/usr/bin/env bash
# Aegis - teardown. COST-SAFETY: removes ALL Aegis stacks so nothing keeps
# billing. Empties the WORM bucket (all versions + delete markers) first, since
# CloudFormation cannot delete a non-empty bucket. Object Lock is enabled on the
# bucket but NO default retention rule is set, so versions delete cleanly.
set -uo pipefail

REGION="${REGION:-us-east-1}"
CORE_STACK="${CORE_STACK:-aegis-governance-core}"
AGENT_STACK="${AGENT_STACK:-aegis-sample-agent}"

echo "=========================================================="
echo " Aegis teardown (region ${REGION}) - removing all aegis-* stacks"
echo "=========================================================="

output() {
  aws cloudformation describe-stacks --region "${REGION}" \
    --stack-name "$1" \
    --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" --output text 2>/dev/null
}

WORM_BUCKET="$(output "${CORE_STACK}" WormEvidenceBucketName)"

echo "==> [1/4] Deleting sample-agent stack ..."
if aws cloudformation describe-stacks --region "${REGION}" --stack-name "${AGENT_STACK}" >/dev/null 2>&1; then
  aws cloudformation delete-stack --region "${REGION}" --stack-name "${AGENT_STACK}"
  aws cloudformation wait stack-delete-complete --region "${REGION}" --stack-name "${AGENT_STACK}" || true
  echo "    sample-agent: deleted"
else
  echo "    sample-agent: not present, skipping"
fi

echo "==> [2/4] Emptying WORM bucket ${WORM_BUCKET:-<none>} ..."
if [[ -n "${WORM_BUCKET}" && "${WORM_BUCKET}" != "None" ]] && \
   aws s3api head-bucket --bucket "${WORM_BUCKET}" >/dev/null 2>&1; then
  # Delete all object versions and delete markers.
  while true; do
    VERS="$(aws s3api list-object-versions --region "${REGION}" --bucket "${WORM_BUCKET}" \
      --output json --max-items 1000 2>/dev/null)"
    PAYLOAD="$(echo "${VERS}" | python3 - <<'PY'
import json, sys
d = json.load(sys.stdin) or {}
items = []
for k in ("Versions", "DeleteMarkers"):
    for o in d.get(k, []) or []:
        items.append({"Key": o["Key"], "VersionId": o["VersionId"]})
print(json.dumps({"Objects": items, "Quiet": True}) if items else "")
PY
)"
    [[ -z "${PAYLOAD}" ]] && break
    echo "${PAYLOAD}" | aws s3api delete-objects --region "${REGION}" \
      --bucket "${WORM_BUCKET}" --delete "file:///dev/stdin" >/dev/null 2>&1 || true
  done
  echo "    WORM bucket emptied"
else
  echo "    WORM bucket not found / already gone, skipping"
fi

echo "==> [3/4] Deleting governance-core stack ..."
if aws cloudformation describe-stacks --region "${REGION}" --stack-name "${CORE_STACK}" >/dev/null 2>&1; then
  aws cloudformation delete-stack --region "${REGION}" --stack-name "${CORE_STACK}"
  aws cloudformation wait stack-delete-complete --region "${REGION}" --stack-name "${CORE_STACK}" || true
  echo "    governance-core: deleted"
else
  echo "    governance-core: not present, skipping"
fi

echo "==> [4/4] Verifying zero aegis-* stacks remain ..."
REMAIN="$(aws cloudformation list-stacks --region "${REGION}" \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE ROLLBACK_COMPLETE \
    UPDATE_ROLLBACK_COMPLETE DELETE_FAILED CREATE_IN_PROGRESS DELETE_IN_PROGRESS \
  --query "StackSummaries[?starts_with(StackName, 'aegis-')].StackName" \
  --output text 2>/dev/null)"
if [[ -z "${REMAIN}" ]]; then
  echo "    OK - no aegis-* stacks remain. Billing stopped."
  echo "=========================================================="
  echo " TEARDOWN COMPLETE - clean."
  echo "=========================================================="
  exit 0
else
  echo "    WARNING - these aegis-* stacks still exist: ${REMAIN}"
  echo "    (A DELETE_FAILED stack usually means the bucket still has objects."
  echo "     Re-run this script, or check the stack events in the console.)"
  exit 1
fi
