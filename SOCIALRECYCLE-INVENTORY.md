# socialRecycle - Complete War Room Feature Inventory

This document provides a comprehensive inventory of every feature in the warroom codebase, categorized as **KEEP** (features that stay for socialRecycle) or **CUT** (features to be removed).

## Frontend Inventory

### Components Directory Analysis

**KEEP Components:**
- `ai-studio/` - Content generation, posts, carousels, video → KEEP (AI Studio)
- `auto-reply/` - Auto-reply engine → KEEP
- `chat/` - Chat system → KEEP  
- `content/` - Content pipeline and management → KEEP (for social content)
- `intelligence/` - Competitor intelligence → KEEP
- `scheduler/` - Content scheduler + multi-platform publishing → KEEP
- `settings/` - Settings management (general, social accounts, billing) → KEEP
- `social/` - Social platform integrations and analytics → KEEP
- `ui/` - Shared UI components → KEEP

**CUT Components:**
- `agents/` - Agent management → CUT
- `communications/` - Communications console → CUT  
- `contacts/` - Contact management → CUT (part of CRM)
- `contracts/` - Contract system → CUT
- `crm/` - All CRM functionality → CUT
- `dashboard/` - Command center dashboard → CUT (replace with social-focused dashboard)
- `email/` - Email inbox → CUT
- `invoicing/` - Invoicing system → CUT
- `kanban/` - Kanban board → CUT
- `leadgen/` - Lead generation → CUT
- `library/` - Library/Education system → CUT
- `marketing/` - Marketing campaigns → CUT (part of CRM)
- `navigation/` - Navigation components → CUT (rebuild for social focus)
- `notifications/` - General notifications → CUT (keep only social-specific)
- `org-chart/` - Org chart → CUT
- `pricing/` - Pricing components → CUT (rebuild for social SaaS)
- `profile/` - Profile management → CUT (simplify for social users)
- `prospects/` - Prospects management → CUT
- `reports/` - Business reports → CUT
- `team/` - Team management → CUT (simplify to team-focused, not org-focused)
- `workflows/` - Workflow automation → CUT

### App Pages Analysis

**KEEP:**
- Main app layout structure → KEEP (but simplify)
- Authentication system → KEEP (but team-focused)

**CUT:**
- Complex sidebar navigation → CUT (replace with social-focused nav)
- Multi-role user system → CUT (simplify to team members)

## Backend API Inventory

### API Routers - KEEP

**Social & Content (Core Features):**
- `social.py` - Social platform management → KEEP
- `social_oauth.py` - OAuth for Instagram, TikTok, YouTube, Facebook → KEEP  
- `social_content.py` - Social content management → KEEP
- `social_sync.py` - Platform synchronization → KEEP
- `social_accounts.py` - Social account management → KEEP
- `auto_reply.py` - Auto-reply engine → KEEP
- `carousel.py` - Text-to-carousel + Instagram posting → KEEP
- `content_scheduler.py` - Content scheduling + multi-platform publishing → KEEP
- `content_social.py` - URL → social posts pipeline → KEEP
- `competitors.py` - Competitor intelligence (monitoring, scraping, analysis) → KEEP
- `content_intel.py` - Content intelligence and analysis → KEEP
- `mirofish.py` - Mirofish engine (content scoring/prediction) → KEEP

**AI & Generation:**
- `google_ai_studio.py` - AI Studio (content generation) → KEEP
- `ugc_studio.py` - UGC Studio → KEEP
- `video_editor.py` - Video editor → KEEP
- `video_copycat.py` - Video copycat → KEEP
- `video_assets.py` - Video assets → KEEP
- `video_formats.py` - Video formats → KEEP

**Core System:**
- `auth.py` - Multi-tenant auth system (but team-focused) → KEEP
- `settings.py` - Settings management → KEEP
- `health.py` - Health checks → KEEP
- `stripe_settings.py` - Stripe billing → KEEP
- `files.py` - File management → KEEP
- `calendar.py` - Calendar sync → KEEP
- `google_calendar.py` - Google Calendar integration → KEEP
- `notifications.py` - Notifications (social-focused only) → KEEP

### API Routers - CUT

**CRM System:**
- `crm/deals.py` - Deals management → CUT
- `crm/contacts.py` - Contact management → CUT
- `crm/activities.py` - Activities → CUT
- `crm/pipelines.py` - Sales pipelines → CUT
- `crm/products.py` - Products → CUT
- `crm/emails.py` - CRM emails → CUT
- `crm/marketing.py` - Marketing campaigns → CUT
- `crm/attributes.py` - Custom attributes → CUT
- `crm/acl.py` - Access control → CUT
- `crm/data.py` - CRM data management → CUT
- `crm/audit.py` - CRM audit → CUT
- `crm/pipeline_board.py` - Pipeline board → CUT
- `crm/workflows.py` - CRM workflows → CUT
- `crm/workflow_executions.py` - Workflow executions → CUT

**Lead Generation & Sales:**
- `leadgen.py` - Lead generation → CUT
- `lead_enrichment.py` - Lead enrichment → CUT
- `prospects.py` - Prospects management → CUT
- `cold_email.py` - Cold email system → CUT

**Business Operations:**
- `invoicing.py` - Invoicing system → CUT
- `contracts.py` - Contracts system → CUT
- `email_inbox.py` - Email inbox → CUT

**Agent & AI Planning:**
- `agents.py` - Agent management → CUT
- `agent_chat.py` - Agent chat → CUT
- `agent_comms.py` - Agent communications → CUT
- `agent_onboarding.py` - Agent provisioning → CUT
- `anchor_agent.py` - Anchor agent → CUT
- `ai_planning.py` - AI Planning → CUT
- `task_deps.py` - Task dependencies → CUT
- `task_execution.py` - Task execution → CUT
- `blackboard.py` - Blackboard → CUT
- `knowledge_pool.py` - Knowledge pool → CUT

**Complex Systems:**
- `kanban.py` - Kanban board → CUT
- `team.py` - Team management → CUT (simplify)
- `library.py` - Library system → CUT
- `library_ingest.py` - Library ingestion → CUT
- `mental_library.py` - Mental library → CUT
- `skills_manager.py` - Skills manager → CUT
- `simulate.py` - Simulation → CUT

**Paperclip Architecture:**
- `entities.py` - Entities → CUT
- `goals.py` - Goals → CUT
- `approvals.py` - Approvals → CUT
- `budget.py` - Budget → CUT
- `task_checkout.py` - Task checkout → CUT
- `org_chart.py` - Org chart → CUT

**Communications:**
- `telnyx.py` - Telnyx voice → CUT
- `twilio.py` - Twilio → CUT
- `twilio_voice.py` - Twilio voice → CUT
- `comms.py` - Communications hub → CUT
- `voice.py` - Voice features → CUT

**Utilities & Background:**
- `admin.py` - Admin functions → CUT (simplify)
- `scraper.py` - Web scraper → CUT (keep only competitor scraping)
- `search.py` - Global search → CUT
- `contact_webhook.py` - Contact submissions → CUT
- `audit_trail.py` - Audit trail → CUT
- `token_metering.py` - Token metering → CUT
- `vector_memory.py` - Vector memory API → CUT
- `cdn_migration.py` - CDN migration → CUT
- `digital_copies.py` - Digital copies/Soul ID → CUT
- `soul.py` - Soul management → CUT
- `usage.py` - Usage tracking → CUT (replace with social analytics)
- `content_tracker.py` - Content tracking → CUT

## Backend Services Inventory

### Services - KEEP

**Social & Content:**
- `auto_reply_engine.py` - Auto-reply engine → KEEP
- `instagram_publisher.py` - Instagram publishing → KEEP
- `instagram_scraper.py` - Instagram scraping → KEEP
- `instagram_account_manager.py` - Instagram account management → KEEP
- `multi_account_poster.py` - Multi-platform publishing → KEEP
- `social_post_generator.py` - Social post generation → KEEP
- `social_inbox_processor.py` - Social inbox processing → KEEP
- `smart_distribution.py` - Smart distribution system → KEEP
- `content_scheduler.py` - Content scheduling → KEEP
- `content_analyzer.py` - Content analysis → KEEP
- `content_extractor.py` - Content extraction → KEEP
- `content_recycler.py` - Content recycling → KEEP
- `carousel_generator.py` - Carousel generation → KEEP
- `comment_scraper.py` - Comment scraping → KEEP
- `competitor_script_engine.py` - Competitor intelligence → KEEP
- `mirofish_engine.py` - Mirofish prediction engine → KEEP
- `audience_profile_service.py` - Audience profiling → KEEP
- `performance_tracker.py` - Performance tracking → KEEP
- `optimal_timing.py` - Optimal posting timing → KEEP

**Core System:**
- `stripe_service.py` - Stripe billing → KEEP
- `email.py` - Email service → KEEP (for notifications)
- `encryption.py` - Encryption utilities → KEEP
- `garage_s3.py` - S3 storage → KEEP
- `oauth_scoping.py` - OAuth management → KEEP
- `scheduler.py` - Background scheduler → KEEP
- `tenant.py` - Multi-tenant system (team-focused) → KEEP

**Video & Assets:**
- `video_pipeline.py` - Video processing → KEEP
- `video_composer.py` - Video composition → KEEP
- `video_analyzer.py` - Video analysis → KEEP
- `video_script_generator.py` - Video script generation → KEEP
- `video_transcriber.py` - Video transcription → KEEP
- `veo_service.py` - VEO video service → KEEP
- `asset_generator.py` - Asset generation → KEEP
- `avatar_service.py` - Avatar service → KEEP
- `tts_service.py` - Text-to-speech → KEEP
- `render_worker.py` - Rendering worker → KEEP

### Services - CUT

**Agent & AI Systems:**
- `agent_chat.py` - Agent chat → CUT
- `agent_comms.py` - Agent communications → CUT
- `agent_onboarding.py` - Agent provisioning → CUT
- `anchor_agent.py` - Anchor agent → CUT
- `knowledge_pool.py` - Knowledge pool → CUT
- `vector_memory.py` - Vector memory → CUT

**CRM & Sales:**
- `lead_deal_sync.py` - Lead-deal synchronization → CUT
- `recommendation_engine.py` - Recommendation engine → CUT

**Complex Systems:**
- `workflow_executor.py` - Workflow execution → CUT
- `workflow_queue.py` - Workflow queue → CUT
- `workflow_triggers.py` - Workflow triggers → CUT
- `audit_helper.py` - Audit helper → CUT
- `audit_trail.py` - Audit trail → CUT
- `token_metering.py` - Token metering → CUT

**Communications:**
- `telnyx_client.py` - Telnyx client → CUT
- `twilio_client.py` - Twilio client → CUT

**Utilities:**
- `scraping.py` - General scraping → CUT (keep only competitor-focused)
- `token_store.py` - Token storage → CUT
- `redis_pool.py` - Redis pool → CUT (if not used by KEEP features)
- `notify.py` - General notifications → CUT
- `content_embedder.py` - Content embeddings → CUT
- `editing_dna.py` - Editing DNA → CUT
- `nano_banana.py` - Nano banana → CUT

### Platform Publishers - KEEP/CUT Analysis
- Instagram publisher → KEEP
- TikTok publisher → KEEP  
- YouTube publisher → KEEP
- Facebook publisher → KEEP
- Twitter/X publisher → KEEP
- LinkedIn publisher → CUT (not in core platforms)

## Database Tables Inventory

### Tables - KEEP

**Core System:**
- Users, roles, organizations (simplified) → KEEP
- Settings, configurations → KEEP
- Social accounts, oauth tokens → KEEP
- Stripe products, billing → KEEP

**Social & Content:**
- Social posts, content → KEEP
- Instagram data, posts, stories → KEEP
- TikTok data and posts → KEEP
- YouTube data and videos → KEEP
- Facebook data and posts → KEEP
- Content scheduler, compositions → KEEP
- Carousel data and templates → KEEP
- Auto-reply rules and responses → KEEP
- Competitor data and analysis → KEEP
- Performance metrics and analytics → KEEP
- Content distribution settings → KEEP
- Mirofish predictions and scores → KEEP

### Tables - CUT

**CRM Schema (entire crm schema):**
- deals, contacts, activities → CUT
- pipelines, products, emails → CUT
- marketing campaigns → CUT
- attributes, acl, audit → CUT
- pipeline_board, workflows → CUT

**Lead Generation:**
- leads, lead_enrichments → CUT
- prospects, prospect_data → CUT
- cold_email campaigns → CUT

**Business Operations:**
- invoices, contracts → CUT
- contact_submissions → CUT
- email_inbox → CUT

**Agent & AI Systems:**
- agents, agent_assignments → CUT
- agent_chat, conversations → CUT
- knowledge_pool, vector_memory → CUT
- blackboard, task_execution → CUT
- ai_planning, task_deps → CUT

**Complex Systems:**
- kanban boards and tasks → CUT
- workflows, workflow_executions → CUT
- entities, goals, approvals → CUT
- budget, task_checkout → CUT
- org_chart, team_hierarchy → CUT
- mental_library, ml_videos → CUT
- digital_copies, soul_ids → CUT
- audit_trail, token_metering → CUT

## Main.py Router Map

### Include Routers - KEEP
```python
# Core System - KEEP  
app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"]) 
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(stripe_settings.router, prefix="/api", tags=["stripe"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(cal_api.router, prefix="/api", tags=["calendar"])
app.include_router(google_calendar.router, prefix="/api", tags=["google-calendar"])

# Social & Content - KEEP
app.include_router(social.router, prefix="/api/social", tags=["social"])
app.include_router(social_oauth.router, prefix="/api/social", tags=["social-oauth"])
app.include_router(social_content.router, prefix="/api/social", tags=["social-content"])
app.include_router(social_sync.router, prefix="/api/social", tags=["social-sync"])
app.include_router(social_accounts.router, prefix="/api/settings/social-accounts", tags=["social-accounts"])
app.include_router(content_social.router, prefix="/api/content-social", tags=["content-social"])
app.include_router(competitors.router, prefix="/api", tags=["competitors"])
app.include_router(content_intel.router, prefix="/api/content-intel", tags=["content-intelligence"])
app.include_router(content_scheduler.router, prefix="/api/scheduler", tags=["content-scheduler"])
app.include_router(carousel.router, prefix="/api/carousel", tags=["carousel"])
app.include_router(auto_reply.router, prefix="/api/auto-reply", tags=["auto-reply"])
app.include_router(mirofish.router, tags=["mirofish"])

# AI Studio - KEEP
app.include_router(google_ai_studio.router, prefix="/api/ai-studio", tags=["google-ai-studio"])
app.include_router(ugc_studio.router, prefix="/api/ai-studio/ugc", tags=["ugc-studio"])
app.include_router(video_editor.router, prefix="/api/video", tags=["video-editor"])
app.include_router(video_copycat.router, prefix="/api/video-copycat", tags=["video-copycat"])
app.include_router(video_assets.router, prefix="/api/video-copycat", tags=["video-assets"])
app.include_router(video_formats.router, prefix="/api", tags=["video-formats"])

# Webhooks - KEEP
app.include_router(instagram_webhook_router, tags=["webhooks"])
```

### Include Routers - CUT
```python
# Admin & Complex Systems - CUT
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(kanban.router, prefix="/api/kanban", tags=["kanban"])
app.include_router(team.router, prefix="/api/team", tags=["team"])

# Agents & AI Planning - CUT  
app.include_router(agent_onboarding.router, tags=["agent-onboarding"])
app.include_router(agents.router, prefix="/api", tags=["agents"])
app.include_router(agent_chat.router, prefix="/api", tags=["agent-chat"])
app.include_router(agent_comms.router, prefix="/api", tags=["agent-comms"])
app.include_router(anchor_agent.router, tags=["anchor-agent"])
app.include_router(knowledge_pool.router, prefix="/api/knowledge", tags=["knowledge-pool"])
app.include_router(ai_planning.router, prefix="/api", tags=["ai-planning"])
app.include_router(task_deps.router, prefix="/api", tags=["task-dependencies"])
app.include_router(task_execution.router, prefix="/api", tags=["task-execution"])
app.include_router(blackboard.router, prefix="/api", tags=["blackboard"])
app.include_router(simulate.router, prefix="/api/simulate", tags=["simulate"])

# Library & Education - CUT
app.include_router(library.router, prefix="/api/library", tags=["library"])
app.include_router(mental_library.router, prefix="/api/ml", tags=["mental-library"])
app.include_router(library_ingest.router, prefix="/api/library", tags=["library-ingest"])

# CRM System - CUT
app.include_router(deals.router, prefix="/api/crm", tags=["crm-deals"])
app.include_router(contacts.router, prefix="/api/crm", tags=["crm-contacts"])
app.include_router(activities.router, prefix="/api/crm", tags=["crm-activities"])
app.include_router(pipelines.router, prefix="/api/crm", tags=["crm-pipelines"])
app.include_router(products.router, prefix="/api/crm", tags=["crm-products"])
app.include_router(emails.router, prefix="/api/crm", tags=["crm-emails"])
app.include_router(marketing.router, prefix="/api/crm", tags=["crm-marketing"])
app.include_router(attributes.router, prefix="/api/crm", tags=["crm-attributes"])
app.include_router(acl.router, prefix="/api/crm", tags=["crm-acl"])
app.include_router(data.router, prefix="/api/crm", tags=["crm-data"])
app.include_router(audit.router, prefix="/api/crm", tags=["crm-audit"])
app.include_router(pipeline_board.router, prefix="/api/crm", tags=["crm-pipeline-board"])
app.include_router(workflows.router, prefix="/api/crm", tags=["crm-workflows"])
app.include_router(workflow_executions.router, prefix="/api/crm", tags=["crm-workflow-executions"])

# Lead Generation - CUT
app.include_router(leadgen.router, prefix="/api/leadgen", tags=["leadgen"])
app.include_router(lead_enrichment.router, prefix="/api", tags=["lead-enrichment"])
app.include_router(prospects.router, prefix="/api", tags=["prospects"])
app.include_router(cold_email.router, prefix="/api", tags=["cold-email"])

# Business Operations - CUT
app.include_router(invoicing.router, prefix="/api", tags=["invoicing"])
app.include_router(contracts.router, prefix="/api", tags=["contracts"])
app.include_router(email_inbox.router, prefix="/api", tags=["email-inbox"])

# Communications - CUT
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(telnyx.router, prefix="/api", tags=["telnyx"])
app.include_router(twilio.router, prefix="/api", tags=["twilio"])
app.include_router(twilio_voice.router, prefix="/api/twilio", tags=["twilio-voice"])
app.include_router(comms.router, prefix="/api/comms", tags=["communications"])

# Paperclip Architecture - CUT
app.include_router(entities.router, prefix="/api/entities", tags=["entities"])
app.include_router(goals.router, prefix="/api/goals", tags=["goals"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"])
app.include_router(org_chart.router, tags=["org-chart"])
app.include_router(task_checkout.router, prefix="/api/tasks", tags=["task-checkout"])
app.include_router(budget.router, prefix="/api/agents", tags=["agent-budget"])

# Utilities & Background - CUT
app.include_router(scraper.router, prefix="/api", tags=["scraper"])
app.include_router(skills_manager.router, prefix="/api", tags=["skills"])
app.include_router(soul.router, prefix="/api", tags=["soul"])
app.include_router(contact_webhook.router, prefix="/api", tags=["contact-webhook"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(content_tracker.router, prefix="/api", tags=["content-tracker"])
app.include_router(content_ai.router, prefix="/api/content", tags=["content-ai"])
app.include_router(audit_trail.router, prefix="/api/audit", tags=["audit-trail"])
app.include_router(token_metering.router, prefix="/api/tokens", tags=["token-metering"])
app.include_router(vector_memory.router, prefix="/api/memory", tags=["vector-memory"])
app.include_router(digital_copies.router, prefix="/api", tags=["digital-copies"])
app.include_router(usage.router, prefix="/api/usage", tags=["usage"])
app.include_router(cdn_migration.router, tags=["background-jobs"])
```

## Dependencies Between KEEP Features

### Critical Dependencies to Refactor

1. **Social Features depend on CRM models:**
   - Social content references `crm.organizations` → needs refactoring
   - Social accounts tied to `crm.users` → needs simplification
   - Performance tracking uses CRM contact data → remove/simplify

2. **Content Scheduler depends on:**
   - Agent system for task assignment → remove agent integration
   - CRM organization context → simplify to team context

3. **Auto-Reply depends on:**
   - Chat system → keep minimal chat for social DMs
   - Agent routing → remove agent integration

4. **Analytics depend on:**
   - Complex user management → simplify to team members
   - CRM integration → remove business metrics

5. **Billing system:**
   - Currently integrated with CRM → simplify to social SaaS plans

### Refactoring Required

**Database Schema Changes:**
- Simplify user management (remove complex ACL)
- Replace `crm.organizations` references with simple team concept
- Remove foreign keys to CUT tables
- Consolidate social platform data models

**API Changes:**
- Remove agent integration from KEEP endpoints
- Simplify auth middleware for team-based access
- Remove CRM context from social features
- Update billing endpoints for social SaaS pricing

**Frontend Changes:**
- Rebuild navigation for social-focused workflow
- Remove CRM dashboards, replace with social analytics
- Simplify user management UI
- Focus content pipeline on social platforms only

## Summary

**KEEP Features (Core socialRecycle):**
- Auto-reply engine
- AI Studio (content generation - posts, carousels, video)
- Content scheduler + multi-platform publishing  
- Instagram integration (OAuth, posting, scraping, webhooks)
- TikTok integration
- YouTube Shorts integration
- Facebook integration
- Competitor intelligence (monitoring, scraping, analysis)
- Analytics / performance tracking (social-focused)
- Chat system (minimal, for social DMs)
- Settings: general, social accounts, products & billing
- Email sync + calendar sync (social → meetings pipeline)
- Multi-tenant auth system (team-focused, not org-focused)  
- Stripe billing (social SaaS plans)
- Mirofish engine (content scoring + AI focus group)

**Major Refactoring Areas:**
1. Remove entire CRM schema and all business operations
2. Simplify user/auth system from org-focused to team-focused
3. Remove agent orchestration and AI planning systems
4. Remove lead generation and sales pipeline features
5. Focus analytics on social performance only
6. Rebuild navigation and dashboard for social workflow
7. Consolidate social platform integrations
8. Implement social-specific billing ($99/mo + $49/mo Mirofish upsell)

The result will be a focused social media management SaaS for service businesses, with powerful AI content generation and competitor intelligence features.