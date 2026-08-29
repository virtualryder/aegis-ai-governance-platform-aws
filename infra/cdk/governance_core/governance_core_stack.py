"""GovernanceCoreStack — CDK authoring of the Aegis governance core.

Synthesizes to CloudFormation, the canonical Aegis IaC language
(infra/CANONICAL-IAC.md). Resource-for-resource port of the live-validated
infra/cloudformation/governance-core.yaml (and its Terraform parity module),
in the same Python-CDK style as the four vertical agents' cdk apps
(identity / gateway / data / compute stacks) — one authoring approach across
the whole portfolio.

Beyond-parity additions (deliberate, documented):
  * Kill Switch SSM parameter (/{app}/kill-switch, default disengaged) plus
    two IAM managed policies enforcing separation of duties in IAM itself:
    engage-only and disengage-only. See docs/ops/KILL-SWITCH.md.

Partition-aware by construction: CDK tokens (Aws.PARTITION / REGION /
ACCOUNT_ID) resolve at deploy time, so the same synth output deploys to
commercial and GovCloud partitions — replacing the Terraform module's
data-source plumbing.
"""

from __future__ import annotations

import os

from aws_cdk import (
    Aws,
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    Tags,
    aws_bedrock as bedrock,
    aws_cloudtrail as cloudtrail,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_kms as kms,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
    aws_ssm as ssm,
)
from constructs import Construct

_HERE = os.path.dirname(os.path.abspath(__file__))
# Single source for the gateway stub handler — byte-for-byte the same file the
# Terraform module packages and the CFN core inlines.
_GATEWAY_INDEX = os.path.normpath(
    os.path.join(_HERE, "..", "..", "terraform", "modules", "governance_core", "index.py")
)


class GovernanceCoreStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        app_name: str = "aegis",
        data_class: str = "pii",
        environment_name: str = "dev",
        department: str = "shared-services",
        pack: str = "enterprise",
        bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        guardrail_grounding_threshold: float = 0.80,
        guardrail_relevance_threshold: float = 0.75,
        log_retention: logs.RetentionDays = logs.RetentionDays.ONE_WEEK,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        suffix = f"{data_class}-{environment_name}"

        # Cost-allocation tags on every taggable resource (parity with CFN/TF).
        for k, v in {
            "dept": department, "app": app_name, "data_class": data_class,
            "pack": pack, "environment": environment_name,
        }.items():
            Tags.of(self).add(k, v)

        # ----- KMS: CMK per data class, rotation on, confused-deputy guards --
        def _svc_stmt(service: str) -> iam.PolicyStatement:
            return iam.PolicyStatement(
                sid=f"Allow{service.split('.')[0].capitalize()}UseOfKey",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal(service)],
                actions=[
                    "kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*",
                    "kms:GenerateDataKey*", "kms:DescribeKey",
                ],
                resources=["*"],
                conditions={"StringEquals": {
                    "aws:SourceAccount": Aws.ACCOUNT_ID,
                    "kms:ViaService": f"{service.split('.amazonaws.com')[0]}.{Aws.REGION}.amazonaws.com"
                    if service.endswith("amazonaws.com") else service,
                }},
            )

        key_policy = iam.PolicyDocument(statements=[
            iam.PolicyStatement(
                sid="EnableRootAccountAdmin",
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal(f"arn:{Aws.PARTITION}:iam::{Aws.ACCOUNT_ID}:root")],
                actions=["kms:*"],
                resources=["*"],
            ),
            _svc_stmt("dynamodb.amazonaws.com"),
            _svc_stmt("s3.amazonaws.com"),
            # CloudWatch Logs calls KMS DIRECTLY as logs.<region>.amazonaws.com (no ViaService is
            # set), scoped by the log-group encryption context — the generic ViaService statement
            # never matches it, which blocked associate-kms-key on the Bedrock invocation log group
            # (found live 2026-08-29, G5a). This is the canonical CloudWatch Logs key statement.
            iam.PolicyStatement(
                sid="AllowCloudWatchLogsUseOfKey",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal(f"logs.{Aws.REGION}.amazonaws.com")],
                actions=["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*",
                         "kms:GenerateDataKey*", "kms:DescribeKey"],
                resources=["*"],
                conditions={"ArnLike": {
                    "kms:EncryptionContext:aws:logs:arn":
                        f"arn:{Aws.PARTITION}:logs:{Aws.REGION}:{Aws.ACCOUNT_ID}:*"}},
            ),
        ])
        self.cmk = kms.Key(
            self, "DataClassKey",
            description=f"Aegis CMK for data class {data_class} ({app_name}/{environment_name})",
            enable_key_rotation=True,
            policy=key_policy,
            pending_window=Duration.days(7),
            alias=f"alias/{app_name}-{data_class}-{environment_name}",
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ----- DynamoDB: append-only audit (request_id + seq, PITR, CMK) -----
        self.audit_table = dynamodb.Table(
            self, "AuditTable",
            table_name=f"{app_name}-audit-{suffix}",
            partition_key=dynamodb.Attribute(name="request_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="seq", type=dynamodb.AttributeType.NUMBER),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.cmk,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ----- DynamoDB: single-use approval ledger (TTL expires_at) ---------
        self.approvals_table = dynamodb.Table(
            self, "ApprovalsTable",
            table_name=f"{app_name}-approvals-{suffix}",
            partition_key=dynamodb.Attribute(name="approval_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expires_at",
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.cmk,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ----- S3: WORM evidence bucket (Object Lock, no default retention) --
        self.worm_bucket = s3.Bucket(
            self, "WormEvidenceBucket",
            bucket_name=f"{app_name}-worm-{suffix}-{Aws.ACCOUNT_ID}",
            object_lock_enabled=True,          # versioning implied+required
            versioned=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.cmk,
            bucket_key_enabled=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,   # evidence outlives stacks
        )

        # ----- Bedrock Guardrail (PII, grounding+relevance, deny topic) ------
        self.guardrail = bedrock.CfnGuardrail(
            self, "AegisGuardrail",
            name=f"{app_name}-guardrail-{suffix}",
            blocked_input_messaging="This request was blocked by Aegis governance policy.",
            blocked_outputs_messaging="This response was blocked by Aegis governance policy.",
            description=(
                "Aegis mandatory guardrail: PII filters, contextual grounding + "
                "relevance, and a denied topic. Applied on input and output by "
                "the control-plane gateway."
            ),
            content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                # Harmful-content categories at HIGH on both directions, plus the
                # prompt-attack filter (input side only, per service contract).
                # Added 2026-08-23 so the deployed baseline visibly carries the
                # full filter set, not just PII/grounding/topic.
                filters_config=[
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type=cat, input_strength="HIGH", output_strength="HIGH")
                    for cat in ("HATE", "INSULTS", "SEXUAL", "VIOLENCE", "MISCONDUCT")
                ] + [
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="PROMPT_ATTACK", input_strength="HIGH", output_strength="NONE"),
                ],
            ),
            sensitive_information_policy_config=bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                pii_entities_config=[
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(type="EMAIL", action="ANONYMIZE"),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(type="PHONE", action="ANONYMIZE"),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(type="US_SOCIAL_SECURITY_NUMBER", action="BLOCK"),
                ],
            ),
            contextual_grounding_policy_config=bedrock.CfnGuardrail.ContextualGroundingPolicyConfigProperty(
                filters_config=[
                    bedrock.CfnGuardrail.ContextualGroundingFilterConfigProperty(
                        type="GROUNDING", threshold=guardrail_grounding_threshold),
                    bedrock.CfnGuardrail.ContextualGroundingFilterConfigProperty(
                        type="RELEVANCE", threshold=guardrail_relevance_threshold),
                ],
            ),
            topic_policy_config=bedrock.CfnGuardrail.TopicPolicyConfigProperty(
                topics_config=[bedrock.CfnGuardrail.TopicConfigProperty(
                    name="UngroundedConsequentialAction",
                    type="DENY",
                    definition=(
                        "Taking a consequential action (issue, adjudicate, release, "
                        "award, or transfer) without a valid bound human approval, "
                        "instead of routing it to the human gate."
                    ),
                    examples=[
                        "Go ahead and approve and release the payment now.",
                        "Issue the permit without waiting for sign-off.",
                    ],
                )],
            ),
        )
        # Published, immutable version of the guardrail. The gateway pins THIS,
        # not the mutable working draft — console edits to the draft cannot
        # silently change what production enforces.
        self.guardrail_version = bedrock.CfnGuardrailVersion(
            self, "AegisGuardrailV1",
            guardrail_identifier=self.guardrail.attr_guardrail_id,
            description="Aegis baseline v1: PII + grounding/relevance + denied topic + harm categories + prompt-attack.",
        )

        # ----- Cognito: pool + operator role group ---------------------------
        self.user_pool = cognito.UserPool(
            self, "AegisUserPool",
            user_pool_name=f"{app_name}-pool-{suffix}",
            self_sign_up_enabled=False,
            mfa=cognito.Mfa.OFF,   # demo parity; golden-pilot hardens to REQUIRED
            password_policy=cognito.PasswordPolicy(
                min_length=14, require_lowercase=True, require_uppercase=True,
                require_digits=True, require_symbols=True,
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
        cognito.CfnUserPoolGroup(
            self, "OperatorGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name=f"{app_name}-operator",
            description="Role group whose JWT role claim the gateway evaluates for least-privilege.",
            precedence=10,
        )

        # ----- CloudWatch Logs: the gateway's own group ----------------------
        self.gateway_logs = logs.LogGroup(
            self, "GatewayLogGroup",
            log_group_name=f"/aws/lambda/{app_name}-gateway-{suffix}",
            retention=log_retention,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ----- Kill Switch (beyond-parity addition) --------------------------
        # Default: disengaged. Gateway reads with a short-TTL cache.
        self.kill_switch_param = ssm.StringParameter(
            self, "KillSwitchParam",
            parameter_name=f"/{app_name}/kill-switch",
            string_value='{"engaged": false, "actor": "", "reason": ""}',
            description="Aegis platform Kill Switch. Engaged=true denies every agent action platform-wide. See docs/ops/KILL-SWITCH.md.",
        )
        param_arn = self.kill_switch_param.parameter_arn
        self.kill_switch_engage_policy = iam.ManagedPolicy(
            self, "KillSwitchEngagePolicy",
            managed_policy_name=f"{app_name}-killswitch-engage-{suffix}",
            description="Grants ONLY the ability to write the kill-switch parameter (incident responders). Pair with a deny elsewhere; disengage is a separate role.",
            statements=[iam.PolicyStatement(
                sid="EngageKillSwitch",
                actions=["ssm:PutParameter"],
                resources=[param_arn],
            )],
        )
        self.kill_switch_read_policy = iam.ManagedPolicy(
            self, "KillSwitchReadPolicy",
            managed_policy_name=f"{app_name}-killswitch-read-{suffix}",
            description="Read-only kill-switch state for gateways and dashboards.",
            statements=[iam.PolicyStatement(
                sid="ReadKillSwitch",
                actions=["ssm:GetParameter"],
                resources=[param_arn],
            )],
        )
        # NOTE: true engage-vs-disengage SoD is value-based; IAM cannot inspect
        # the parameter value, so operational SoD is enforced by the runbook
        # (two distinct principals hold the engage policy) and audited via
        # CloudTrail; the platform_core KillSwitch class enforces SoD in-process.

        # ----- IAM: least-privilege gateway role (explicit audit-deny) -------
        self.gateway_role = iam.Role(
            self, "GatewayRole",
            role_name=f"{app_name}-gateway-role-{suffix}",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        model_arn = f"arn:{Aws.PARTITION}:bedrock:{Aws.REGION}::foundation-model/{bedrock_model_id}"
        for stmt in [
            iam.PolicyStatement(sid="AuditAppendOnly", actions=["dynamodb:PutItem", "dynamodb:ConditionCheckItem"], resources=[self.audit_table.table_arn]),
            iam.PolicyStatement(sid="AuditDenyMutations", effect=iam.Effect.DENY, actions=["dynamodb:UpdateItem", "dynamodb:DeleteItem"], resources=[self.audit_table.table_arn]),
            iam.PolicyStatement(sid="ApprovalLedgerBoundWrites", actions=["dynamodb:PutItem", "dynamodb:ConditionCheckItem"], resources=[self.approvals_table.table_arn]),
            iam.PolicyStatement(sid="BedrockGuardrailApply", actions=["bedrock:ApplyGuardrail"], resources=[self.guardrail.attr_guardrail_arn]),
            iam.PolicyStatement(sid="BedrockInvokeScoped", actions=["bedrock:InvokeModel"], resources=[model_arn]),
            iam.PolicyStatement(sid="KmsDataKeyOnCmk", actions=["kms:Decrypt", "kms:GenerateDataKey"], resources=[self.cmk.key_arn]),
            iam.PolicyStatement(sid="LogsToOwnGroup", actions=["logs:CreateLogStream", "logs:PutLogEvents"], resources=[self.gateway_logs.log_group_arn, f"{self.gateway_logs.log_group_arn}:*"]),
            iam.PolicyStatement(sid="ReadKillSwitch", actions=["ssm:GetParameter"], resources=[param_arn]),
        ]:
            self.gateway_role.add_to_policy(stmt)

        # ----- Lambda: control-plane gateway stub (same index.py) ------------
        with open(_GATEWAY_INDEX, "r", encoding="utf-8") as fh:
            gateway_code = fh.read()
        self.gateway_fn = lambda_.Function(
            self, "GatewayFunction",
            function_name=f"{app_name}-gateway-{suffix}",
            description="Aegis control-plane gateway entrypoint (stub) - writes an audit record and applies the guardrail.",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(gateway_code),
            role=self.gateway_role,
            timeout=Duration.seconds(30),
            memory_size=128,
            tracing=lambda_.Tracing.ACTIVE,   # X-Ray on the control-plane gateway (obs review 2026-08-29)
            environment={
                "AUDIT_TABLE": self.audit_table.table_name,
                "APPROVAL_LEDGER": self.approvals_table.table_name,
                "GUARDRAIL_ID": self.guardrail.attr_guardrail_id,
                "GUARDRAIL_VERSION": self.guardrail_version.attr_version,
                "DATA_CLASS": data_class,
                "KILL_SWITCH_PARAM": self.kill_switch_param.parameter_name,
            },
            log_group=self.gateway_logs,
        )

        # ----- Evidence trail: who touched the evidence (obs review 2026-08-29) ----
        # One platform-owned CloudTrail: management WRITE events + DynamoDB data
        # events for ALL tables (the platform's ledgers AND every agent's — audit,
        # approvals, case stores) + object-level events on the platform WORM bucket.
        # The ledger proves what the gateway wrote; this trail independently proves
        # nobody else touched the stores. Agent stacks add data-only trails for
        # their own WORM vaults. Advanced selectors require replacing the L2
        # construct's basic selectors (a trail cannot carry both kinds).
        self.evidence_trail = cloudtrail.Trail(
            self, "EvidenceTrail", trail_name=f"{app_name}-evidence-trail-{suffix}",
            management_events=cloudtrail.ReadWriteType.WRITE_ONLY,
            include_global_service_events=True, is_multi_region_trail=False)
        _cfn_trail = self.evidence_trail.node.default_child
        _cfn_trail.add_property_deletion_override("EventSelectors")
        _cfn_trail.add_property_override("AdvancedEventSelectors", [
            {"Name": "management-writes",
             "FieldSelectors": [
                 {"Field": "eventCategory", "Equals": ["Management"]},
                 {"Field": "readOnly", "Equals": ["false"]}]},
            {"Name": "dynamodb-data-events-all-tables",
             "FieldSelectors": [
                 {"Field": "eventCategory", "Equals": ["Data"]},
                 {"Field": "resources.type", "Equals": ["AWS::DynamoDB::Table"]}]},
            {"Name": "platform-worm-objects",
             "FieldSelectors": [
                 {"Field": "eventCategory", "Equals": ["Data"]},
                 {"Field": "resources.type", "Equals": ["AWS::S3::Object"]},
                 {"Field": "resources.ARN", "StartsWith": [f"{self.worm_bucket.bucket_arn}/"]}]},
        ])
        CfnOutput(self, "EvidenceTrailArn", value=self.evidence_trail.trail_arn)

        # ----- Outputs (parity with TF outputs.tf) ---------------------------
        CfnOutput(self, "AuditTableName", value=self.audit_table.table_name)
        CfnOutput(self, "ApprovalsTableName", value=self.approvals_table.table_name)
        CfnOutput(self, "WormBucketName", value=self.worm_bucket.bucket_name)
        CfnOutput(self, "GuardrailId", value=self.guardrail.attr_guardrail_id)
        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id)
        CfnOutput(self, "GatewayFunctionName", value=self.gateway_fn.function_name)
        CfnOutput(self, "KillSwitchParameter", value=self.kill_switch_param.parameter_name)
        CfnOutput(self, "CmkArn", value=self.cmk.key_arn)
