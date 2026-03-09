# Google Workspace CLI Integration Plan for War Room
**Research Agent: Debrah 🔍**  
**Date: 2026-03-08**  
**Status: Design Phase - Ready for Implementation**  
**Updated: 2026-03-08 — Corrected to use `@googleworkspace/cli` (gws)**

---

## Executive Summary

This plan outlines the complete integration of Google Workspace capabilities into the War Room platform, creating a unified client lifecycle management system. The integration leverages **`@googleworkspace/cli` (`gws`)** — a real, open-source CLI tool that dynamically builds its command surface from Google's Discovery Service.

**Key tool:** [github.com/googleworkspace/cli](https://github.com/googleworkspace/cli)  
**npm:** `npm install -g @googleworkspace/cli`  
**What it does:** One CLI for Drive, Gmail, Calendar, Sheets, Docs, Chat, Admin — structured JSON output, 100+ agent skills included.

This provides:
- **Automated client onboarding workflows** (Drive folder creation, contract generation)
- **Native e-signature capabilities** with legal compliance tracking
- **Real-time document collaboration** between War Room and Google Docs/Sheets
- **Client-specific knowledge engines** powered by NotebookLM
- **Automated proposal/pitch deck generation** from templates

**Business Impact:** Reduces client onboarding time from 2-3 days to 30 minutes, eliminates manual document management, and creates a complete audit trail of all client interactions.

---

## 1. The Tool: `@googleworkspace/cli` (gws)

### What It Is
`gws` is a real, production CLI tool built in Rust that wraps **all** Google Workspace APIs:

- **Dynamically built** from Google's Discovery Service — when Google adds an API endpoint, gws picks it up automatically
- **Structured JSON output** — perfect for programmatic use and AI agent integration
- **100+ Agent Skills** (SKILL.md files) — one per API + higher-level workflow helpers + 50 curated recipes
- **Auth:** OAuth 2.0, service accounts, or token env vars — credentials encrypted at rest (AES-256-GCM)
- **Pre-built binaries** for all platforms via npm or GitHub Releases
- **Not an officially supported Google product** but open-source and actively maintained

### Installation
```bash
npm install -g @googleworkspace/cli
```

### Quick Start
```bash
gws auth setup    # Walks through Google Cloud project config
gws auth login    # OAuth login
gws drive files list --params '{"pageSize": 5}'
```

### Key Commands
```bash
# List the 10 most recent files
gws drive files list --params '{"pageSize": 10}'

# Create a spreadsheet
gws sheets spreadsheets create --json '{"properties": {"title": "Q1 Budget"}}'

# Send a Chat message
gws chat spaces messages create \
  --params '{"parent": "spaces/xyz"}' \
  --json '{"text": "Deploy complete."}'

# Introspect any method's request/response schema
gws schema drive.files.list

# Stream paginated results as NDJSON
gws drive files list --params '{"pageSize": 100}' --page-all | jq -r '.files[].name'
```

### Authentication Architecture
- **OAuth 2.0 Flow** for user authorization
- **Service Account with Domain-Wide Delegation** for automated operations
- **Scoped permissions** — `gws auth login -s drive,gmail,sheets`
- **Credentials encrypted at rest** (AES-256-GCM, key in OS keyring)
- **Headless mode:** Export credentials from authenticated machine, use `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` env var on server

**Auth Priority Order:**
1. Access token (`GOOGLE_WORKSPACE_CLI_TOKEN`)
2. Credentials file (`GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE`)
3. Encrypted credentials (`gws auth login`)
4. Plaintext credentials (`~/.config/gws/credentials.json`)

### Agent Skills (Built-In)
The repo ships 100+ skills — installable individually or all at once:
```bash
# Install all skills
npx skills add https://github.com/googleworkspace/cli

# Or pick only what you need
npx skills add https://github.com/googleworkspace/cli/tree/main/skills/gws-drive
npx skills add https://github.com/googleworkspace/cli/tree/main/skills/gws-gmail
```

### Rate Limits & Quotas
- **Drive API:** 1,000 requests/100 seconds/user
- **Docs API:** 100 requests/100 seconds/user  
- **Sheets API:** 300 requests/100 seconds/user
- **Slides API:** 300 requests/100 seconds/user
- **Gmail API:** 1,000,000,000 quota units/day

### Google e-Signature Capabilities
- **Native integration** in Google Docs and Drive
- **Legal compliance:** ESIGN Act (US), eIDAS (EU) compliant
- **Audit trail:** Automatic time/date/location stamping
- **Available on:** Business Standard+, Enterprise plans (FREE feature)

---

## 2. Integration Architecture — gws CLI as Backend Service

### How We Use gws in War Room

Instead of writing raw Python API clients for every Google service, we shell out to `gws` from the FastAPI backend. This gives us:

- **Zero boilerplate** — no oauth library, no google-api-python-client, no token refresh logic
- **Structured JSON** — parse stdout directly
- **Auto-updating** — when Google adds new API methods, gws picks them up
- **Agent skills** — can also be used directly by OpenClaw agents

### Python Wrapper Pattern
```python
import subprocess
import json

async def gws_command(service: str, resource: str, method: str, 
                      params: dict = None, body: dict = None) -> dict:
    """Execute a gws CLI command and return parsed JSON."""
    cmd = ["gws", service, resource, method]
    if params:
        cmd.extend(["--params", json.dumps(params)])
    if body:
        cmd.extend(["--json", json.dumps(body)])
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise Exception(f"gws error: {result.stderr}")
    return json.loads(result.stdout)
```

### New FastAPI Endpoints

```python
/api/v1/gworkspace/

├── /auth/
│   ├── POST /setup           # Trigger gws auth setup
│   ├── GET  /status          # Check gws auth status
│   └── POST /export          # Export credentials for headless use

├── /drive/
│   ├── POST /folders         # gws drive files create (folder)
│   ├── GET  /folders/{id}    # gws drive files list in folder
│   └── PUT  /permissions     # gws drive permissions create

├── /documents/
│   ├── POST /contracts       # gws docs documents create + batchUpdate
│   ├── GET  /templates       # gws docs documents get (template)
│   ├── POST /proposals       # gws slides presentations create
│   └── GET  /{id}/status     # gws docs documents get (check state)

├── /signatures/
│   ├── POST /request         # Send doc for e-signature via gws
│   ├── GET  /{id}/status     # Check signing status
│   └── POST /remind          # Send reminder

└── /sheets/
    ├── POST /mrr-tracker     # gws sheets spreadsheets create
    ├── PUT  /invoice-data    # gws sheets spreadsheets.values update
    └── GET  /dashboard       # gws sheets spreadsheets.values get
```

### Database Schema Changes

```sql
-- Google Workspace document tracking
CREATE TABLE google_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id),
    deal_id UUID REFERENCES deals(id),
    document_type VARCHAR(50) NOT NULL,
    google_doc_id VARCHAR(255) NOT NULL,
    drive_folder_id VARCHAR(255),
    template_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'draft',
    signature_request_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    signed_at TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB
);

-- Google Workspace connection tracking
CREATE TABLE google_workspace_auth (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    google_user_email VARCHAR(255),
    scopes TEXT[],
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
);

-- Template management
CREATE TABLE document_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    google_doc_id VARCHAR(255) NOT NULL,
    variables JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 3. UI/UX Workflow Design

### Google Workspace Hub (New War Room Panel)

**Sidebar Navigation:**
```
━━━ GOOGLE WORKSPACE ━━━
🔗 Workspace Hub          [!]
📁 Client Folders
📋 Document Templates
✍️ Signature Requests     [3]
🧠 NotebookLM Projects
```

**Hub Dashboard:** Quick stats (active contracts, pending signatures, signed this month), recent activity feed, quick actions (Create Client Folder, Generate Contract, New Proposal, Setup NotebookLM).

### Contract Workflow: End-to-End
```
Deal Closes in CRM
    → Auto-trigger gws drive folder creation
    → Generate contract from template (gws docs)
    → Variable injection (name, pricing, dates)
    → Send for e-signature
    → Track signing status
    → Auto-file signed copy
    → Notify invoicing
```

### Client Onboarding — Auto Folder Structure
```
📁 Clients/
  └── 📁 ACME Corporation (2026)/
      ├── 📁 01-Contracts/
      ├── 📁 02-Invoices/
      ├── 📁 03-Project-Assets/
      │   ├── 📁 Design-Files/
      │   ├── 📁 Development/
      │   └── 📁 Client-Provided/
      ├── 📁 04-Communications/
      └── 📁 05-Deliverables/
```

### Multi-User Considerations
- **Eddy:** Full admin access (create, delete, manage all documents)
- **Wife:** Scoped editor access (view, edit, create — cannot delete)
- **Service account:** For automated operations
- **Per-client:** Share specific folders with team/clients as needed

---

## 4. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Install `gws` on server, configure OAuth/service account
- Python wrapper for gws commands
- Basic Drive integration (folder CRUD)
- Google Workspace Hub UI shell
- New database tables

### Phase 2: Contract Automation (Week 3-4)
- Docs API via gws for template processing + variable injection
- e-Signature workflow
- Contract status tracking
- CRM integration triggers (deal closed → auto-setup)

### Phase 3: Invoice & Tracking (Week 5-6)
- Sheets integration for MRR tracking
- Invoice generation from signed contracts
- Payment status dashboard
- Automated invoice delivery

### Phase 4: Advanced Features (Week 7-8)
- Slides API for proposal/pitch deck generation
- NotebookLM integration for client knowledge bases
- Advanced template management
- Full client onboarding automation

### Phase 5: Polish & Scale (Week 9-10)
- Rate limiting, error handling, monitoring
- Permission system refinements
- Performance optimizations
- Documentation and training

---

## 5. Success Metrics
- **Client Onboarding Time:** 30 minutes (from 2-3 days)
- **Contract Turnaround:** Same-day (from 1-2 days)
- **Manual Task Reduction:** 80% less document management time
- **API Response Time:** <500ms for document operations
- **Error Rate:** <2% in document generation

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Google API rate limiting | Medium | High | Exponential backoff, request queuing |
| OAuth token expiration | High | Medium | gws handles refresh automatically |
| Template corruption | Low | High | Version control, backup/restore |
| Service changes | Medium | Medium | gws auto-updates from Discovery Service |
| Client data exposure | Low | Critical | Scoped permissions, audit logging |

---

## Conclusion

Using `@googleworkspace/cli` instead of raw Python API clients **dramatically simplifies** the integration. No oauth library, no google-api-python-client, no token refresh logic — just shell out to `gws` and parse JSON. The tool auto-updates when Google adds new API methods, ships with 100+ agent skills, and handles auth/encryption natively.

**Next Step:** Install gws, configure OAuth, build the Python wrapper, and start Phase 1.

---

**Document Status:** Ready for Implementation  
**Estimated Development Time:** 8-10 weeks  
**Key Dependency:** `npm install -g @googleworkspace/cli`
