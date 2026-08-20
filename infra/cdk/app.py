#!/usr/bin/env python3
"""Aegis governance core - CDK app. Synthesizes to CloudFormation (the
canonical Aegis IaC language, infra/CANONICAL-IAC.md). Context keys mirror the
Terraform module's variables: app_name, data_class, environment, department,
pack, bedrock_model_id."""
import aws_cdk as cdk
from governance_core import GovernanceCoreStack

app = cdk.App()
ctx = lambda k, d: app.node.try_get_context(k) or d  # noqa: E731
GovernanceCoreStack(
    app, "aegis-governance-core",
    app_name=ctx("app_name", "aegis"),
    data_class=ctx("data_class", "pii"),
    environment_name=ctx("environment", "dev"),
    department=ctx("department", "shared-services"),
    pack=ctx("pack", "enterprise"),
    bedrock_model_id=ctx("bedrock_model_id", "anthropic.claude-3-haiku-20240307-v1:0"),
)
app.synth()
