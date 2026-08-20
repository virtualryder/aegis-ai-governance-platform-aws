"""Synth-level assertions for the governance-core CDK stack.

Synthesizes in-process (aws_cdk.assertions) - no CDK CLI, no AWS account -
and asserts the control-plane resources exist with their governing settings.
Run:  python3 -m pytest infra/cdk/tests -q   (from infra/cdk/)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aws_cdk as cdk
from aws_cdk.assertions import Match, Template
from governance_core import GovernanceCoreStack


def _template():
    app = cdk.App()
    stack = GovernanceCoreStack(app, "test-governance-core")
    return Template.from_stack(stack)


def test_kms_key_rotation_enabled():
    t = _template()
    t.has_resource_properties("AWS::KMS::Key", {"EnableKeyRotation": True})


def test_audit_table_append_only_shape():
    t = _template()
    t.has_resource_properties("AWS::DynamoDB::Table", Match.object_like({
        "KeySchema": [
            {"AttributeName": "request_id", "KeyType": "HASH"},
            {"AttributeName": "seq", "KeyType": "RANGE"},
        ],
        "PointInTimeRecoverySpecification": {"PointInTimeRecoveryEnabled": True},
    }))


def test_approvals_table_has_ttl():
    t = _template()
    t.has_resource_properties("AWS::DynamoDB::Table", Match.object_like({
        "TimeToLiveSpecification": {"AttributeName": "expires_at", "Enabled": True},
    }))


def test_worm_bucket_object_lock_enabled():
    t = _template()
    t.has_resource_properties("AWS::S3::Bucket", Match.object_like({
        "ObjectLockEnabled": True,
        "VersioningConfiguration": {"Status": "Enabled"},
    }))


def test_guardrail_blocks_ssn_and_grounds():
    t = _template()
    t.has_resource_properties("AWS::Bedrock::Guardrail", Match.object_like({
        "SensitiveInformationPolicyConfig": Match.object_like({
            "PiiEntitiesConfig": Match.array_with([
                {"Type": "US_SOCIAL_SECURITY_NUMBER", "Action": "BLOCK"},
            ]),
        }),
    }))


def test_gateway_role_explicitly_denies_audit_mutation():
    t = _template()
    t.has_resource_properties("AWS::IAM::Policy", Match.object_like({
        "PolicyDocument": Match.object_like({
            "Statement": Match.array_with([Match.object_like({
                "Effect": "Deny",
                "Action": ["dynamodb:UpdateItem", "dynamodb:DeleteItem"],
            })]),
        }),
    }))


def test_kill_switch_parameter_defaults_disengaged():
    t = _template()
    t.has_resource_properties("AWS::SSM::Parameter", Match.object_like({
        "Value": Match.string_like_regexp('.*"engaged": false.*'),
    }))


def test_gateway_lambda_wired_to_tables_and_switch():
    t = _template()
    t.has_resource_properties("AWS::Lambda::Function", Match.object_like({
        "Runtime": "python3.12",
        "Environment": {"Variables": Match.object_like({
            "KILL_SWITCH_PARAM": Match.any_value(),
            "AUDIT_TABLE": Match.any_value(),
        })},
    }))
