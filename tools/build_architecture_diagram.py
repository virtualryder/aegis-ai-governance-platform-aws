#!/usr/bin/env python3
"""Generate docs/ARCHITECTURE-DEPLOYED.drawio — the governance platform as ACTUALLY deployed and
live-validated (benefits v0.3.0-pilot-rc1 + kill switch on main 2026-09-03, governed-core 1.8.0, platform reference stack).

Every element carries one of three status tags, rendered as a colored pill:
  LIVE      deployed + exercised with real requests, evidence file cited
  OFFLINE   implemented + unit-tested in platform_core, not wired into a deployed path
  NOT BUILT named in docs/design only
Nothing aspirational is drawn as if it existed."""
import html
import xml.sax.saxutils as su

# ---- AWS category colours (Architecture Icons 2024) ------------------------------------------
C_COMPUTE = "#ED7100"; C_STORAGE = "#7AA116"; C_DB = "#C925D1"; C_SEC = "#DD344C"; C_MGMT = "#E7157B"
C_ML = "#01A88D"; C_APPINT = "#E7157B"; C_ANALYTICS = "#8C4FFF"; C_BUS = "#01A88D"
LIVE = "#1D8102"; OFFLINE = "#B7791F"; NOTBUILT = "#8B8B8B"

cells = []
_id = [10]


def nid():
    _id[0] += 1
    return "c%d" % _id[0]


def esc(s):
    return su.escape(s, {'"': "&quot;"})


GEOM = {"1": (0, 0)}   # absolute origin of each container: children use RELATIVE coordinates in draw.io


def cell(value, style, x, y, w, h, parent="1", vertex=True, cid=None):
    c = cid or nid()
    ox, oy = GEOM.get(parent, (0, 0))
    GEOM[c] = (x, y)               # remember absolute origin for nested children
    x, y = x - ox, y - oy
    cells.append('<mxCell id="%s" value="%s" style="%s" vertex="1" parent="%s"><mxGeometry x="%d" y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
                 % (c, esc(value), style, parent, x, y, w, h))
    return c


def edge(src, dst, label="", style="", parent="1", points=(), lx=None, ly=None):
    c = nid()
    base = "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;fontSize=10;fontColor=#232F3E;strokeColor=#232F3E;endArrow=block;endFill=1;jettySize=auto;orthogonalLoop=1;labelBackgroundColor=#FFFFFF;"
    geo = '<mxGeometry relative="1" as="geometry"%s%s>' % ('' if lx is None else ' x="%s"' % lx, '' if ly is None else ' y="%s"' % ly)
    if points:
        geo += '<Array as="points">' + "".join('<mxPoint x="%d" y="%d"/>' % p for p in points) + '</Array>'
    geo += '</mxGeometry>'
    cells.append('<mxCell id="%s" value="%s" style="%s%s" edge="1" parent="%s" source="%s" target="%s">%s</mxCell>'
                 % (c, esc(label), base, style, parent, src, dst, geo))
    return c


def icon(res, label, color, x, y, w=64, h=64, parent="1", lw=150):
    st = ("sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=%s;strokeColor=none;dashed=0;verticalLabelPosition=bottom;"
          "verticalAlign=top;align=center;html=1;fontSize=10;fontStyle=0;aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.%s;labelWidth=%d;whiteSpace=wrap;" % (color, res, lw))
    return cell(label, st, x, y, w, h, parent)


def group(label, gricon, color, x, y, w, h, parent="1", dashed=0):
    st = ("points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],[1,1],[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];"
          "outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;fontStyle=1;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;"
          "shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.%s;strokeColor=%s;fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor=%s;dashed=%d;"
          % (gricon, color, color, dashed))
    return cell(label, st, x, y, w, h, parent)


def box(label, x, y, w, h, fill="#FFFFFF", stroke="#232F3E", parent="1", fs=10, align="left", bold=0):
    st = ("rounded=1;whiteSpace=wrap;html=1;fillColor=%s;strokeColor=%s;fontSize=%d;align=%s;verticalAlign=top;spacing=6;fontColor=#232F3E;fontStyle=%d;"
          % (fill, stroke, fs, align, bold))
    return cell(label, st, x, y, w, h, parent)


def pill(status, x, y, parent="1"):
    color = {"LIVE": LIVE, "OFFLINE": OFFLINE, "NOT BUILT": NOTBUILT}[status]
    st = "rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor=%s;strokeColor=none;fontColor=#FFFFFF;fontSize=9;fontStyle=1;align=center;verticalAlign=middle;" % color
    return cell(status, st, x, y, 64 if status != "NOT BUILT" else 74, 16, parent)


def text(label, x, y, w, h, fs=11, bold=0, color="#232F3E", parent="1", align="left"):
    st = "text;html=1;strokeColor=none;fillColor=none;align=%s;verticalAlign=top;whiteSpace=wrap;fontSize=%d;fontStyle=%d;fontColor=%s;spacing=2;" % (align, fs, bold, color)
    return cell(label, st, x, y, w, h, parent)


W = 2360
# ---------------------------------------------------------------- title ----------------------------
text("<b>AEGIS Governance Platform on Amazon Bedrock AgentCore — as DEPLOYED and LIVE-VALIDATED (2026-09-03)</b>", 20, 10, 1500, 30, fs=20)
text("Benefits Eligibility pack <b>v0.3.0-pilot-rc1</b> + kill switch (main, 2026-09-03) · governed-core <b>1.8.0</b> (hash-pinned) · AWS account-agnostic, us-east-1 · Every element is tagged "
     "<font color='#1D8102'><b>LIVE</b></font> (deployed + exercised with real requests; evidence file cited) · "
     "<font color='#B7791F'><b>OFFLINE</b></font> (implemented + unit-tested in platform_core, not wired into a deployed path) · "
     "<font color='#8B8B8B'><b>NOT BUILT</b></font> (design only). Nothing aspirational is drawn as if it existed. Sources: "
     "benefits/evidence/AGENTCORE-*-2026-09-02.md, AGENTCORE-111-GATE-2026-09-02.md, AGENTCORE-KILL-SWITCH-2026-09-03.md, EP1-VALIDATION.md; platform DEPLOYED-AND-VALIDATED.md, MATURITY.yaml.",
     20, 42, 2300, 44, fs=11)

# ---------------------------------------------------------------- AWS cloud ------------------------
cloud = group("AWS Cloud — one shared control plane per deployment (hybrid multi-tenant: -c tenants=a,b) or one silo per customer (default)",
              "group_aws_cloud_alt", "#232F3E", 20, 100, 2320, 1575)

# ===== Layer 1: Identity ===========================================================================
L1 = group("LAYER 1 · IDENTITY — who is acting.  Protects: every call is bound to a verified human; the tenant is DERIVED from the identity, never typed.  Tracks: sub, groups, tenant, session.",
           "group_security_identity_compliance", C_SEC, 40, 140, 2280, 170, parent=cloud)
u = icon("user", "Caseworker / Approver (different humans: SoD)", "#232F3E", 70, 182, parent=L1, lw=130)
cog = icon("cognito", "Amazon Cognito user pool — groups benefits_caseworker + tenant_<id>; MFA REQUIRED in pilot mode", C_SEC, 260, 172, parent=L1, lw=200)
pill("LIVE", 278, 290, parent=L1)
jwt = box("<b>JWT flow (SRP → access token)</b><br>1. Human authenticates to Cognito (SRP; MFA in pilot mode) → <b>access token</b> (RS256, iss / client_id / exp, <code>cognito:groups</code>).<br>"
          "2. The SAME token is (a) the bearer for the AgentCore <b>Runtime</b> (customJWTAuthorizer: discoveryUrl + allowedClients) and (b) the bearer the runtime forwards to the "
          "<b>Gateway</b> (CUSTOM_JWT) — Cedar evaluates the real human principal, never a service role.<br>"
          "3. <code>approve_signoff</code>, <code>request_signoff</code> and multi-tenant <code>ingest</code> re-verify the token themselves (RS256 vs JWKS, client id, reviewer group) — P0-5: no 'requester' field is ever trusted.<br>"
          "4. Tenant = the <code>tenant_&lt;id&gt;</code> group → gateway interceptor → HMAC-signed pair (Layer 3). An un-tenanted identity gets 0 tools + 403 (require_tenant).",
          520, 165, 1100, 135, parent=L1)
pill("LIVE", 1556, 170, parent=L1)
box("<b>Evidence</b>: cw-a / cw-b / cw-none live runs — AGENTCORE-MULTITENANT-E2E-2026-09-02.md · approval-path verification (a raw send-task-success is refused) — governed-core 1.5.0, DEPLOYMENT-GUIDE · MFA pool ON — EP1-VALIDATION.md",
    1640, 165, 660, 135, fill="#F7F7F7", parent=L1)

# ===== Layer 2: Runtime + model ====================================================================
L2 = group("LAYER 2 · AGENT RUNTIME + MODEL — the reasoning.  Protects: session isolation, tenant-bound session, guardrailed generation, masked-before-model.  Tracks: every span + every model call, tagged per tenant / session / case.",
           "group_ai_ml", C_ML, 40, 355, 1120, 330, parent=cloud)
rt = icon("bedrock", "Amazon Bedrock AgentCore RUNTIME — Strands agent, ADOT, microVM per session", C_ML, 100, 420, parent=L2, lw=140)
pill("LIVE", 100, 538, parent=L2)
model = icon("bedrock", "Amazon Bedrock model — Claude Sonnet 4.5 (ConverseStream)", C_ML, 300, 420, parent=L2, lw=170)
pill("LIVE", 300, 538, parent=L2)
gr = icon("bedrock", "Bedrock Guardrail on draft_notice (-c guardrail_id); intervention ⇒ ManualReview", C_ML, 500, 420, parent=L2, lw=170)
pill("LIVE", 500, 538, parent=L2)
box("<b>What the runtime does on every invocation</b><br>• binds <code>session.id</code> (X-Amzn-Bedrock-AgentCore-Runtime-Session-Id) + derived tenant + case as Strands <code>trace_attributes</code> and OTEL baggage<br>"
    "• injects <code>requestMetadata</code> {tenant, session_id, case_id, requester} on EVERY Converse call → model-invocation log rows are per-tenant filterable<br>"
    "• MULTITENANT=1: refuses an identity with no tenant; the human's JWT is the bearer for every gateway tool call<br>"
    "• never commits: consequential actions end at the human sign-off gate (Cedar forbids finalize / refer_fraud to the agent)",
    690, 375, 450, 160, parent=L2)
box("<b>Evidence</b>: real Runtime, 2 tenants, 13/13 checks each — AGENTCORE-OBSERVABILITY-2026-09-02.md; repeated on the release tag — AGENTCORE-111-GATE-2026-09-02.md; masked_before_model = true on every model invocation. "
    "Guardrail G1 wired + validated 2026-08-29 (ben-demo); the multi-tenant runs used the sandbox (unguarded) switch.",
    690, 545, 450, 130, fill="#F7F7F7", parent=L2)
box("<b>TOKEN BUDGETS / COST CEILING — honest status</b><br>"
    "<font color='#1D8102'><b>LIVE</b></font> tracked: inputTokenCount / outputTokenCount per invocation (model log) + gen_ai.usage on every span, tagged per tenant / session / case.<br>"
    "<font color='#B7791F'><b>OFFLINE</b></font> capped: platform_core/token_budget.py hard/soft meter (preflight denies) + manifest <code>budget:</code> 5M tokens/month hard — read by NO deployed component today.<br>"
    "<font color='#8B8B8B'><b>NOT BUILT</b></font>: AWS Budgets $ ceiling with an action → kill switch; per-tenant live meter. Design + build list B1–B5: docs/TOKEN-BUDGETS-AND-COST-CEILINGS.md",
    70, 562, 600, 113, fill="#FFF8E7", stroke=OFFLINE, parent=L2)

# ===== Layer 3: Gateway + policy ===================================================================
L3 = group("LAYER 3 · GOVERNED TOOL GATEWAY — every tool call is authorized.  Protects: deny-by-default, mask-before-use, no self-commit, tenant scope.  Tracks: every request row (initialize / tools/list / tools/call) with trace + request ids.",
           "group_security_identity_compliance", C_SEC, 1180, 355, 1140, 330, parent=cloud)
gw = icon("bedrock", "AgentCore GATEWAY (MCP, CUSTOM_JWT) — 10 tools over 8 Lambda targets", C_ML, 1730, 420, parent=L3, lw=170)
pill("LIVE", 1730, 538, parent=L3)
pe = icon("identity_and_access_management", "AgentCore POLICY engine — Cedar, ENFORCE (AWS preview); platform_core engine = fail-closed oracle", C_SEC, 1940, 420, parent=L3, lw=170)
pill("LIVE", 1940, 538, parent=L3)
ic = icon("lambda", "REQUEST interceptor (Lambda) — after auth, before the target", C_COMPUTE, 2150, 420, parent=L3, lw=170)
pill("LIVE", 2150, 538, parent=L3)
box("<b>Cedar policies (deny-by-default)</b>: caseworker_permit · mask_before_assess / redetermine / overpayment / draft (forbid unless deidentified) · no_self_commit · no_self_fraud_referral · require_tenant (multi-tenant only).<br>"
    "<b>Interceptor on every tools/call</b>: derives the tenant from the validated JWT → injects <code>__aegis_tenant</code> + HMAC <code>__aegis_tenant_sig</code> (per-deploy Secrets Manager key) + <code>__aegis_trace</code> {trace_id, span_id, session_id, case_id} "
    "from the MCP _meta context; un-tenanted ⇒ 403 verbatim. Caller-supplied values are overwritten; targets trust ONLY a verifying signature.",
    1210, 395, 480, 115, parent=L3)
box("<b>Evidence</b>: ENFORCE from zero — AGENTCORE-E2E-FROMZERO-2026-09-02.md · cross-tenant deny (cw-none: 0 tools, 403) — AGENTCORE-MULTITENANT-E2E · 33 gateway request rows per session joined by trace id — AGENTCORE-OBSERVABILITY · "
    "kill switch 29/29, 13.9 s to effect — AGENTCORE-KILL-SWITCH-2026-09-03.md · red-team + 29-check demo — README.",
    1730, 562, 360, 113, fill="#F7F7F7", parent=L3)
box("<b>KILL SWITCH — one command stops everything</b> &nbsp;<font color='#1D8102'><b>LIVE 2026-09-03 · 29/29 · 13.9 s to effect</b></font><br>"
    "SSM <code>/ben-&lt;env&gt;-eligibility/kill-switch</code> (+ optional platform-wide <code>/aegis/kill-switch</code>) is read FIRST — before tenancy, Cedar, masking, sign-off — by the REQUEST interceptor "
    "(tools/list + tools/call ⇒ 403 + DENIED record in the tenant's WORM ledger), by EVERY tool Lambda (<code>KillSwitchEngaged</code> before the handler; a running workflow fails at its next state) and by the Runtime "
    "(new invocation refused; a RUNNING session stopped at its next model call). Fail-closed if unreadable; 15 s TTL cache.<br>"
    "<b>Engage / disengage</b> = two Lambda function URLs (AuthType AWS_IAM, SigV4), one IAM policy each (SoD) + in-code same-identity refusal; the actor is the IAM-verified caller ARN; "
    "every state change = COMMITTED row in the base ledger's hash-chained KILL-SWITCH case, WORM copy. Platform reference gateway: same design, LIVE (Run 11).",
    1210, 520, 480, 155, fill="#EAF7EA", stroke=LIVE, parent=L3)
ssm_ks = icon("systems_manager", "SSM Parameter Store — the kill-switch flag (read by every Lambda + the Runtime; written only by the controller)", C_MGMT, 2160, 578, w=44, h=44, parent=L3, lw=110)

# ===== Layer 4: governed tools =====================================================================
L4 = group("LAYER 4 · GOVERNED TOOLS — one Lambda per manifest target, least-privilege IAM, X-Ray.  Protects: fail-closed masking, signed de-identification proof, pass-by-reference, exactly-once commit.  Tracks: one structured aegis.call line per invocation (keys, outcome, arg digest — never values).",
           "group_compute", C_COMPUTE, 40, 730, 2280, 270, parent=cloud)
tools = ["ingest-application", "intake-application", "mask-pii", "assess-eligibility", "redetermine", "overpayment", "ben-core", "write-audit",
         "request-signoff", "signoff-register", "finalize", "approve-signoff", "workflow-guards", "tenant-interceptor",
         "kill-switch-engage (AWS_IAM URL)", "kill-switch-disengage (AWS_IAM URL)"]
x = 70
for name in tools:
    icon("lambda", name, C_COMPUTE, x, 775, w=48, h=48, parent=L4, lw=100)
    x += 106
pill("LIVE", 70, 850, parent=L4)
comp = icon("comprehend", "Amazon Comprehend DetectPiiEntities", C_ML, 1810, 775, w=48, h=48, parent=L4, lw=110)
sm = icon("secrets_manager", "Secrets Manager — per-deploy HMAC key (sanitized_ref + tenant pair)", C_SEC, 1960, 775, w=48, h=48, parent=L4, lw=140)
box("<b>Roles</b>: ingest = the only door for raw content (R3-2; multi-tenant: token-verified tenant) · intake = decision fields · mask_pii → Comprehend, mints the signed sanitized_ref · assess / redetermine / overpayment = deterministic rules (FPL-pinned; due-process classification) · "
    "ben-core = draft_notice (guardrailed) / finalize / refer_fraud (Cedar-forbidden to the agent) · write_audit = canonical evidence · request_signoff / signoff_register / approve_signoff / finalize = the SoD sign-off gate · workflow_guards = state-transition guards · tenant-interceptor = Layer 3 · kill-switch-engage / -disengage = the containment controller (function URLs, IAM SoD).",
    70, 875, 1100, 112, parent=L4)
box("<b>Controls in code</b> (governed-core 1.8.0 = the shared, hash-pinned control plane; benefits overrides mask_pii + provenance, declared): fail-closed masking (no proof ⇒ refuse) · sanitized_ref HMAC bound to content + tenant · R3-2 pass-by-reference (raw text never in workflow state; strict PII canary PASS) · "
    "evidence.record_event hash chain + WORM copy + correlation block · finalize FINAL# exactly-once + approval-path verification · tenancy.route_store to the tenant's physical stores, fail-closed · telemetry.instrument = one aegis.call line per call + the kill-switch gate before every handler.",
    1190, 875, 700, 112, parent=L4)
box("<b>Evidence</b>: EP1-VALIDATION.md (canary 0 leaks, AdverseNoticeHold) · AGENTCORE-MULTITENANT-AUDIT (routing 12/12) · 111 gate (0 unexpected errors, 20 log groups) · governed-core tests + 46-file lock.",
    1910, 875, 390, 112, fill="#F7F7F7", parent=L4)

# ===== Layer 5: workflow ===========================================================================
L5 = group("LAYER 5 · DETERMINISTIC WORKFLOW — the human gate.  Protects: the model cannot skip a guard or commit; adverse actions hold for due-process notice.  Tracks: every state with the execution ARN; execution data OFF (refs only).",
           "group_application_integration", C_APPINT, 40, 1060, 1120, 250, parent=cloud)
sfn = icon("step_functions", "AWS Step Functions controller — X-Ray on, execution logging without data", C_APPINT, 100, 1110, parent=L5, lw=150)
pill("LIVE", 100, 1228, parent=L5)
box("Extract → GuardExtracted → MaskPii → GuardDeidentified → AssessEligibility → GuardRulesExecuted → CheckAdverseNotice (<b>AdverseNoticeHold</b> = terminal due-process hold) → DraftNotice → <b>DraftOk</b> (guardrail-blocked ⇒ ManualReview) → "
    "AuditIntent → <b>HumanSignoff</b> (waitForTaskToken, 24 h) → Finalize → <b>FinalizeOk</b> (refused ⇒ ManualReview) → Committed.<br>"
    "Every Lambda payload carries <code>__aegis_execution</code> = $$.Execution.Id; multi-tenant payloads carry the signed tenant pair — an execution started without it FAILS at the first state (fail-closed, proven).",
    280, 1095, 860, 125, parent=L5)
box("<b>Evidence</b>: EP1-VALIDATION.md · DEMO-DEPLOY-2026-08-24.md · AGENTCORE-MULTITENANT-AUDIT (workflow hop with / without the pair) · 111 gate.", 280, 1230, 860, 60, fill="#F7F7F7", parent=L5)

# ===== Layer 6: per-tenant data ====================================================================
L6 = group("LAYER 6 · PER-TENANT DATA + WORM EVIDENCE — physically separate per tenant.  Protects: isolation, tamper-evidence, retention.  Tracks: hash-chained ledger rows (correlation keys hashed), Object-Lock copies, CloudTrail data events.",
           "group_storage", C_STORAGE, 1180, 1060, 1140, 250, parent=cloud)
ddb = icon("dynamodb", "DynamoDB per tenant — case-store · sanitized-artifacts · audit-ledger (hash chain, PITR) · pending-approvals", C_DB, 1250, 1110, parent=L6, lw=190)
pill("LIVE", 1250, 1228, parent=L6)
s3 = icon("s3", "S3 Object Lock WORM vault per tenant — &lt;prefix&gt;-&lt;tenant&gt;-worm-&lt;acct&gt;", C_STORAGE, 1470, 1110, parent=L6, lw=170)
pill("LIVE", 1470, 1228, parent=L6)
kms = icon("key_management_service", "AWS KMS CMK (-c kms=customer-managed)", C_SEC, 1680, 1110, parent=L6, lw=150)
pill("LIVE", 1680, 1228, parent=L6)
box("Base silo stack + ONE DataStack per tenant (<code>-c tenants=pha-a,pha-b</code>). Mirror IAM grants scoped to <code>&lt;prefix&gt;-*-&lt;logical&gt;</code>; the audit writer has an explicit DENY on Update / Delete / retention bypass. "
    "Retention: GOVERNANCE 1d sandbox → COMPLIANCE 7y production-reference.<br><b>Proven</b>: base ledger + base vault received 0 writes across whole runs; the other tenant's ledger was empty for every case (MULTITENANT-AUDIT 12/12; 111 gate). "
    "EP1 Gate-B switches (CMK, zero egress, MFA) validated 2026-07-27 on v0.1.2-pilot-rc1 — not re-walked on this tag.",
    1830, 1090, 470, 200, parent=L6)

# ===== Layer 7: observability ======================================================================
L7 = group("LAYER 7 · TRANSPARENCY — every API call, the model's reasoning and the evidence, joined by ONE correlation set (tenant · session · trace · request · case).  Protects: auditability, per-tenant filtering, masked-before-model measured.",
           "group_management_governance", C_MGMT, 40, 1355, 2280, 300, parent=cloud)
cw = icon("cloudwatch", "CloudWatch Logs — Lambda · Step Functions · gateway vended request log · runtime logs", C_MGMT, 100, 1405, parent=L7, lw=150)
xr = icon("xray", "X-Ray + Transaction Search — aws/spans: agent, model, tool + Lambda segments under ONE trace id", C_MGMT, 300, 1405, parent=L7, lw=190)
ml = icon("bedrock", "Bedrock model-invocation log (-c model_logging=1) — exact bodies, requestMetadata per tenant / session", C_ML, 540, 1405, parent=L7, lw=190)
ct = icon("cloudtrail", "CloudTrail data events on the WORM vault", C_MGMT, 780, 1405, parent=L7, lw=150)
dash = icon("cloudwatch", "Dashboard + alarms → SNS (workflow failed / timed out, guard failures, governance Lambda errors)", C_MGMT, 980, 1405, parent=L7, lw=190)
for xx in (100, 300, 540, 780, 980):
    pill("LIVE", xx, 1525, parent=L7)
box("<b>trace_case.py</b> — one auditor timeline per case: WORM rows → correlation keys → runtime spans + reasoning events (session.id) → gateway rows (trace id) → Lambda aegis.call lines → model-invocation rows (requestMetadata.case_id; requestId = the span's aws.request_id) → Step Functions history; "
    "verdict per tenant incl. <b>masked_before_model</b> against PII canaries.<br>Live: 1 agent / 10–14 model / 12 tool spans, 33 gateway rows, 7 Lambda calls, 5–7 model invocations per tenant — all joined; the other tenant's timeline empty.",
    1200, 1390, 720, 125, parent=L7)
box("<b>Evidence</b>: AGENTCORE-OBSERVABILITY-2026-09-02.md (+ per-tenant timelines) · AGENTCORE-111-GATE-2026-09-02.md (repeat on the tag + 0-unexpected-errors sweep) · OBSERVABILITY-VALIDATION-2026-08-29.md (X-Ray / SFN / model log / CloudTrail four-way capture) · design: docs/OBSERVABILITY-CORRELATION.md",
    1200, 1525, 720, 100, fill="#F7F7F7", parent=L7)
box("<b>Governance core</b>: governed-core wheel pinned by URL + sha256 (<code>--require-hashes</code>); intra-repo lock (verify_core) + cross-repo parity; MATURITY.yaml drift-checked in CI; account-id scan; security CI (hash-pinned lock + pip-audit, detect-secrets baseline, Bandit, Semgrep, Checkov) — all green 2026-09-03.",
    1940, 1390, 360, 235, fill="#F7F7F7", parent=L7)

# ---------------------------------------------------------------- edges ----------------------------
# Absolute coordinates (edges live on the root layer). Inter-layer edges are routed through the
# 60 px gaps between layers so their labels never sit on a layer title or a box.
edge(u, cog, "SRP + MFA", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
edge(cog, L2, "access token (JWT)", "exitX=1;exitY=0.5;entryX=0.073;entryY=0;", points=[(380, 204), (380, 325), (122, 325)], lx=0.2)
edge(rt, model, "ConverseStream<br>+ requestMetadata", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
edge(L2, L3, "MCP tools/call (runtime → gateway) · Bearer = the human's JWT · _meta: traceparent + baggage", "exitX=0.102;exitY=0;entryX=0.51;entryY=0;", points=[(154, 343), (1762, 343)])
edge(gw, pe, "authorize (Cedar)", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
edge(pe, ic, "permit → interceptor", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
edge(ic, L4, "invoke the target with the signed<br>tenant pair + trace context (or 403)", "exitX=1;exitY=0.5;entryX=0.987;entryY=0;", points=[(2290, 452)], lx=0.86, ly=-110)
edge(L4, sfn, "controller ⇄ Lambdas:<br>guards / tools invoked with $$.Execution.Id + signed pair;<br>request_signoff / finalize run inside the controller",
     "startArrow=block;startFill=1;exitX=0.14;exitY=1;entryX=0;entryY=0.5;", points=[(359, 1018), (30, 1018), (30, 1142)], lx=-0.35)
edge(L4, L6, "route_store → the tenant's tables", "exitX=0.5447;exitY=1;entryX=0.0895;entryY=0;")
edge(L4, L6, "WORM copy (route_bucket)", "exitX=0.6368;exitY=1;entryX=0.2737;entryY=0;")

# ---------------------------------------------------------------- issue → control table ------------
T = group("ISSUE → CONTROL → PROOF (each row is something a buyer will ask; status is today's truth)", "group_aws_cloud_alt", "#232F3E", 20, 1700, 2320, 470)
rows = [
    ("Raw PII reaching the model / the logs", "mask_pii (Comprehend) fail-closed + signed sanitized_ref; R3-2 pass-by-reference (raw text only via ingest, refs in workflow state); masked-before-model measured on every model row",
     "Ingest → case_ref → mask → sanitized_ref → tools accept only a verifying ref", "LIVE", "EP1 canary 0 leaks; 111 gate canary; OBSERVABILITY masked_before_model = true"),
    ("The agent commits a consequential action by itself", "Cedar no_self_commit / no_self_fraud_referral; HumanSignoff (waitForTaskToken) with SoD; approve_signoff single-use; finalize verifies the approval PATH + exactly-once FINAL#",
     "Agent → request_signoff → human approves (different identity) → finalize → FinalizeOk", "LIVE", "governed-core 1.5.0 live (raw send-task-success refused); demo 29 checks; EP1"),
    ("One tenant sees another tenant's data", "Tenant derived from the verified identity (interceptor, HMAC pair); per-tenant DataStacks + WORM vaults; route_store fail-closed; require_tenant; mirror IAM scoped to prefix",
     "JWT group → interceptor → signed pair → every Lambda verifies → tenant's physical stores", "LIVE", "MULTITENANT-E2E 5/5; MULTITENANT-AUDIT 12/12; 111 gate"),
    ("Someone edits or deletes the audit trail", "DynamoDB hash chain (HEAD# CAS transact) + S3 Object Lock copy + IAM DENY on Update/Delete/retention bypass + CloudTrail data events; correlation keys inside the hash",
     "record_event → transact append + WORM put → verify_chain", "LIVE", "EP1; OBSERVABILITY-VALIDATION-2026-08-29; MULTITENANT-AUDIT"),
    ("\"Show me everything that touched this case\"", "One correlation set on every span, gateway row, Lambda line, model row and WORM record; trace_case.py builds the timeline per tenant",
     "runtime → gateway → tool → WORM, joined by session/trace/request ids", "LIVE", "OBSERVABILITY 13/13 per tenant; 111 gate"),
    ("Runaway spend / \"never exceed $X\"", "Per-tenant token usage TRACKED live (model log + spans); hard/soft cap meter exists OFFLINE (platform_core); AWS Budgets $ action NOT BUILT",
     "today: measure per tenant, alert manually; build B1–B5: preflight deny + Budgets action → kill switch", "OFFLINE", "docs/TOKEN-BUDGETS-AND-COST-CEILINGS.md"),
    ("\"Stop everything, now, and prove you did\"", "One SSM flag read FIRST by the interceptor, every tool Lambda and the Runtime (fail-closed, 15 s TTL); engage/disengage via AWS_IAM function URLs — IAM + in-code separation of duties, IAM-verified actor, every change a COMMITTED WORM row, every refusal a DENIED row",
     "engage → 403 at the gateway within one TTL, workflow fails at its next state, running session stops → security lead (different identity) releases", "LIVE", "AGENTCORE-KILL-SWITCH-2026-09-03 (29/29, 13.9 s); platform Run 11"),
    ("The IaC drifts from the claims", "MATURITY.yaml single source of truth + drift-checker in CI; hash-pinned governed-core; doc-count gates; account-id scan; release tag = validated tree",
     "commit → CI gates → tag → live gate → evidence → MATURITY", "LIVE", "all three repos' CI green 2026-09-03; VALIDATED_RELEASE.md"),
]
hdr_y = 1735
for i, (hx, hw, ht) in enumerate([(40, 330, "Issue"), (380, 760, "Control that solves it (as deployed)"), (1150, 560, "High-level workflow"), (1720, 90, "Status"), (1820, 500, "Proof (evidence file)")]):
    box("<b>%s</b>" % ht, hx, hdr_y, hw, 26, fill="#232F3E", stroke="#232F3E", parent=T, fs=11)
    cells[-1] = cells[-1].replace("fontColor=#232F3E", "fontColor=#FFFFFF")
y = hdr_y + 30
for issue, ctrl, wf, status, proof in rows:
    box(issue, 40, y, 330, 48, parent=T, fs=10)
    box(ctrl, 380, y, 760, 48, parent=T, fs=10)
    box(wf, 1150, y, 560, 48, parent=T, fs=10)
    pill(status, 1728, y + 16, parent=T)
    box(proof, 1820, y, 500, 48, fill="#F7F7F7", parent=T, fs=10)
    y += 52

xml = ('<mxfile host="aegis" modified="2026-09-03T00:00:00Z" agent="build_arch.py" version="24.7.17">'
       '<diagram id="deployed" name="Deployed + validated"><mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="2380" pageHeight="2200" math="0" shadow="0">'
       '<root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(cells) + '</root></mxGraphModel></diagram></mxfile>')
open(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "docs", "ARCHITECTURE-DEPLOYED.drawio"), "w", encoding="utf-8").write(xml)
print("cells", len(cells))
