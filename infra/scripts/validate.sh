#!/usr/bin/env bash
# Aegis - validate CloudFormation templates.
#   cfn-lint  : offline, NO AWS creds required.
#   validate-template : calls AWS, REQUIRES creds (skipped if none/usable).
set -euo pipefail

REGION="${REGION:-us-east-1}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFN_DIR="$(cd "${HERE}/../cloudformation" && pwd)"

echo "==> cfn-lint (offline, no creds needed)"
if ! command -v cfn-lint >/dev/null 2>&1; then
  echo "cfn-lint not found. Install with: pip install cfn-lint" >&2
  exit 1
fi
cfn-lint "${CFN_DIR}/governance-core.yaml" "${CFN_DIR}/sample-agent.yaml"
echo "    cfn-lint: PASS"

echo "==> aws cloudformation validate-template (requires AWS creds)"
if aws sts get-caller-identity >/dev/null 2>&1; then
  for tpl in governance-core.yaml sample-agent.yaml; do
    echo "    validating ${tpl} ..."
    aws cloudformation validate-template \
      --region "${REGION}" \
      --template-body "file://${CFN_DIR}/${tpl}" >/dev/null
    echo "    ${tpl}: VALID"
  done
else
  echo "    No usable AWS credentials -> skipping validate-template (cfn-lint already passed)."
fi

echo "All validations complete."
