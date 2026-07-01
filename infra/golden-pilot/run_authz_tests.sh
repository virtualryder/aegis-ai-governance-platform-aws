#!/usr/bin/env bash
# Aegis Golden Pilot - deploy the AVP Cedar policy store, run three live
# authorization decisions (1 ALLOW, 2 DENY), then tear down.
# Prereq: AWS creds + region. NOTE: the is-authorized request MUST be passed as
# explicit --principal/--action/--resource/--context/--entities file:// flags
# (some CLI proxies drop --cli-input-json).
set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"
STACK="aegis-golden-pilot-avp"
cd "$(dirname "$0")"

aws cloudformation deploy --stack-name "$STACK" --template-file avp-cedar.yaml --region "$REGION"
PSID=$(aws cloudformation describe-stacks --stack-name "$STACK" --query "Stacks[0].Outputs[?OutputKey=='PolicyStoreId'].OutputValue" --output text --region "$REGION")
echo "PolicyStoreId=$PSID"

run () { aws verifiedpermissions is-authorized --policy-store-id "$PSID" \
  --principal file://authz/principal.json --action file://authz/action.json \
  --resource "file://authz/$1" --context "file://authz/$2" --entities "file://authz/$3" \
  --query decision --output text --region "$REGION"; }

echo -n "1 legit read (expect ALLOW):        "; run resource_kb.json      context_allow.json     entities_allow.json
echo -n "2 unpermitted tool (expect DENY):   "; run resource_ticket.json  context_deny_tool.json entities_deny_tool.json
echo -n "3 wrong data class (expect DENY):   "; run resource_kb.json      context_allow.json     entities_deny_dataclass.json

# Optional: real Bedrock call through an inference profile (chargeback path)
# aws bedrock-runtime converse --model-id us.anthropic.claude-haiku-4-5-20251001-v1:0 \
#   --messages '[{"role":"user","content":[{"text":"ping"}]}]' --inference-config maxTokens=20 --region "$REGION"

aws cloudformation delete-stack --stack-name "$STACK" --region "$REGION"
echo "teardown requested."
