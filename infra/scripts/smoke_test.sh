#!/usr/bin/env bash
# Aegis - smoke test. Verifies the deployed governance core works AND that the
# append-only guarantee actually holds (an UpdateItem on an audit record must be
# DENIED). Prints PASS/FAIL per check. Requires AWS creds.
set -uo pipefail

REGION="${REGION:-us-east-1}"
CORE_STACK="${CORE_STACK:-aegis-governance-core}"
AGENT_STACK="${AGENT_STACK:-aegis-sample-agent}"

PASS=0
FAIL=0
ok()   { echo "PASS - $1"; PASS=$((PASS+1)); }
bad()  { echo "FAIL - $1"; FAIL=$((FAIL+1)); }

stack_status() {
  aws cloudformation describe-stacks --region "${REGION}" \
    --stack-name "$1" --query 'Stacks[0].StackStatus' --output text 2>/dev/null
}
output() {
  aws cloudformation describe-stacks --region "${REGION}" \
    --stack-name "$1" \
    --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" --output text 2>/dev/null
}

echo "==> Check 1: stack statuses"
for s in "${CORE_STACK}" "${AGENT_STACK}"; do
  st="$(stack_status "$s")"
  case "$st" in
    CREATE_COMPLETE|UPDATE_COMPLETE) ok "${s} is ${st}" ;;
    *) bad "${s} is '${st}' (expected CREATE/UPDATE_COMPLETE)" ;;
  esac
done

GUARDRAIL_ID="$(output "${CORE_STACK}" GuardrailId)"
AUDIT_TABLE="$(output "${CORE_STACK}" AuditTableName)"
GATEWAY_FN="$(output "${CORE_STACK}" GatewayFnName)"
WORM_BUCKET="$(output "${CORE_STACK}" WormEvidenceBucketName)"

echo "==> Check 2: guardrail exists"
if [[ -n "${GUARDRAIL_ID}" ]] && \
   aws bedrock get-guardrail --region "${REGION}" \
     --guardrail-identifier "${GUARDRAIL_ID}" >/dev/null 2>&1; then
  ok "guardrail ${GUARDRAIL_ID} exists"
else
  bad "guardrail ${GUARDRAIL_ID:-<none>} not found (is Bedrock enabled in ${REGION}?)"
fi

echo "==> Check 3: invoke GatewayFn and confirm an audit item lands"
REQ_ID="smoke-$(date +%s)-$$"
OUT_FILE="$(mktemp)"
if aws lambda invoke --region "${REGION}" \
     --function-name "${GATEWAY_FN}" \
     --payload "$(printf '{"request_id":"%s","prompt":"smoke test"}' "${REQ_ID}")" \
     --cli-binary-format raw-in-base64-out \
     "${OUT_FILE}" >/dev/null 2>&1; then
  sleep 2
  if aws dynamodb get-item --region "${REGION}" \
       --table-name "${AUDIT_TABLE}" \
       --key "$(printf '{"request_id":{"S":"%s"},"seq":{"N":"0"}}' "${REQ_ID}")" \
       --query 'Item.request_id.S' --output text 2>/dev/null | grep -q "${REQ_ID}"; then
    ok "audit record ${REQ_ID} written by GatewayFn"
  else
    bad "audit record ${REQ_ID} not found after invoke"
  fi
else
  bad "GatewayFn invoke failed"
fi
rm -f "${OUT_FILE}"

echo "==> Check 4: append-only enforcement (UpdateItem must be DENIED)"
# The GatewayLambdaRole has an explicit Deny on UpdateItem. We assume this caller
# has its own perms, so we assume the gateway role to prove the deny is real.
ROLE_ARN="$(aws iam get-role --role-name "$(aws cloudformation describe-stack-resources \
  --region "${REGION}" --stack-name "${CORE_STACK}" \
  --query "StackResources[?ResourceType=='AWS::IAM::Role'].PhysicalResourceId" \
  --output text 2>/dev/null)" --query 'Role.Arn' --output text 2>/dev/null)"

if [[ -n "${ROLE_ARN}" && "${ROLE_ARN}" != "None" ]]; then
  CREDS_JSON="$(aws sts assume-role --role-arn "${ROLE_ARN}" \
    --role-session-name aegis-smoke-deny-test \
    --duration-seconds 900 --output json 2>/dev/null)"
  if [[ -n "${CREDS_JSON}" ]]; then
    export AWS_ACCESS_KEY_ID="$(echo "${CREDS_JSON}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["Credentials"]["AccessKeyId"])')"
    export AWS_SECRET_ACCESS_KEY="$(echo "${CREDS_JSON}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["Credentials"]["SecretAccessKey"])')"
    export AWS_SESSION_TOKEN="$(echo "${CREDS_JSON}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["Credentials"]["SessionToken"])')"
    ERR="$(aws dynamodb update-item --region "${REGION}" \
      --table-name "${AUDIT_TABLE}" \
      --key "$(printf '{"request_id":{"S":"%s"},"seq":{"N":"0"}}' "${REQ_ID}")" \
      --update-expression "SET tampered = :t" \
      --expression-attribute-values '{":t":{"S":"yes"}}' 2>&1 || true)"
    unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
    if echo "${ERR}" | grep -qi "AccessDenied\|not authorized\|explicit deny"; then
      ok "UpdateItem on audit record was DENIED (append-only proven)"
    else
      bad "UpdateItem was NOT denied -> append-only guarantee broken: ${ERR}"
    fi
  else
    bad "could not assume gateway role to test append-only deny"
  fi
else
  bad "could not resolve gateway role ARN for append-only test"
fi

echo "==> Check 5: put an object in the WORM bucket"
TMP_OBJ="$(mktemp)"
echo "aegis-evidence-${REQ_ID}" > "${TMP_OBJ}"
if aws s3api put-object --region "${REGION}" \
     --bucket "${WORM_BUCKET}" \
     --key "smoke/${REQ_ID}.txt" \
     --body "${TMP_OBJ}" >/dev/null 2>&1; then
  ok "object written to WORM bucket ${WORM_BUCKET}"
else
  bad "could not write object to WORM bucket ${WORM_BUCKET}"
fi
rm -f "${TMP_OBJ}"

echo "=========================================================="
echo " SMOKE TEST RESULT: ${PASS} passed, ${FAIL} failed"
echo "=========================================================="
[[ "${FAIL}" -eq 0 ]] && exit 0 || exit 1
