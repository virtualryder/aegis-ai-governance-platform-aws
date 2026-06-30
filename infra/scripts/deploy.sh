#!/usr/bin/env bash
# Aegis - deploy governance-core then sample-agent. Idempotent (uses
# `aws cloudformation deploy`, which creates or updates). Low-cost, serverless.
set -euo pipefail

REGION="${REGION:-us-east-1}"
APP_NAME="${APP_NAME:-aegis}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
CORE_STACK="${CORE_STACK:-aegis-governance-core}"
AGENT_STACK="${AGENT_STACK:-aegis-sample-agent}"
PARAM_FILE="${PARAM_FILE:-}"   # optional path to a params/*.json file

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFN_DIR="$(cd "${HERE}/../cloudformation" && pwd)"

# Convert a CloudFormation params JSON ([{ParameterKey,ParameterValue}]) into
# the Key=Value pairs that `deploy --parameter-overrides` expects.
overrides_from_file() {
  local f="$1"
  python3 - "$f" <<'PY'
import json, sys
with open(sys.argv[1]) as fh:
    data = json.load(fh)
print(" ".join(f'{p["ParameterKey"]}={p["ParameterValue"]}' for p in data))
PY
}

CORE_OVERRIDES="Environment=${ENVIRONMENT} AppName=${APP_NAME}"
if [[ -n "${PARAM_FILE}" ]]; then
  echo "==> Using parameter file: ${PARAM_FILE}"
  CORE_OVERRIDES="$(overrides_from_file "${PARAM_FILE}")"
fi

echo "=========================================================="
echo " Aegis deploy"
echo "   region      : ${REGION}"
echo "   core stack  : ${CORE_STACK}"
echo "   agent stack : ${AGENT_STACK}"
echo "=========================================================="

echo "==> [1/2] Deploying governance-core ..."
# shellcheck disable=SC2086
aws cloudformation deploy \
  --region "${REGION}" \
  --stack-name "${CORE_STACK}" \
  --template-file "${CFN_DIR}/governance-core.yaml" \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides ${CORE_OVERRIDES}
echo "    governance-core: DONE"

echo "==> [2/2] Deploying sample-agent ..."
aws cloudformation deploy \
  --region "${REGION}" \
  --stack-name "${AGENT_STACK}" \
  --template-file "${CFN_DIR}/sample-agent.yaml" \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    "CoreStackName=${CORE_STACK}" \
    "Environment=${ENVIRONMENT}" \
    "AppName=${APP_NAME}"
echo "    sample-agent: DONE"

echo "=========================================================="
echo " Deploy complete. Run smoke_test.sh next, then teardown.sh."
echo " Cost note: these are pay-per-use resources; tear down when done."
echo "=========================================================="
