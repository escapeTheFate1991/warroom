# War Room — Dashboard Metrics Recommendations

> Built for the Command Center dashboard. Each section maps to a panel or widget group.
> Priority: **P0** = must-have at launch, **P1** = add within first sprint, **P2** = nice-to-have.

---

## 1. Essential Business Metrics

The core financial and operational heartbeat. Top of the dashboard, always visible.

### Revenue Tracking (P0)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **MRR** (Monthly Recurring Revenue) | Sum of all active subscriptions/retainers | Real-time on payment events |
| **ARR** (Annual Recurring Revenue) | MRR × 12 (projected) | Daily |
| **Net Revenue** | Total invoiced minus refunds/credits | Monthly |
| **Revenue Churn Rate** | Lost MRR from cancellations ÷ starting MRR | Monthly |
| **Expansion Revenue** | Upsell/cross-sell revenue from existing clients | Monthly |
| **Average Revenue Per Client (ARPC)** | Total revenue ÷ active clients | Monthly |
| **Days Sales Outstanding (DSO)** | Average days to collect payment | Weekly |

**Target:** MRR growth ≥ 10% MoM in early stage. Churn < 5% monthly.

### Client Health (P0)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Client Health Score** | Composite: engagement + deliverable satisfaction + payment history (0-100) | Weekly |
| **NPS (Net Promoter Score)** | Would they recommend us? (-100 to +100) | Quarterly survey |
| **Active Clients** | Clients with work in progress or active retainer | Real-time |
| **At-Risk Clients** | Health score < 40 or no engagement in 14+ days | Daily |
| **Client Lifetime Value (CLV)** | Average total revenue per client relationship | Monthly |

### Project Delivery (P1)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **On-Time Delivery Rate** | % of milestones delivered by deadline | Per milestone |
| **Scope Creep Index** | Added tasks ÷ original task count | Per project |
| **Average Project Duration** | Mean days from kickoff to completion | Monthly |
| **Active Projects** | Currently in-flight work | Real-time |
| **Backlog Depth** | Queued tasks not yet started | Daily |

### Agent Utilization (P1)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Billable Utilization Rate** | Billable hours ÷ available hours (target: 70-80%) | Weekly |
| **Agent Capacity** | Available hours across all team members/agents | Real-time |
| **Task Throughput** | Tasks completed per agent per week | Weekly |

---

## 2. Social Media Metrics

For the **Socials** panel. Cross-platform view with per-platform drill-down.

### Growth (P0)

| Metric | Definition | Platforms |
|--------|-----------|----------|
| **Follower Count** | Total followers (absolute) | All |
| **Follower Growth Rate** | (New followers - Unfollows) ÷ Starting count × 100 | All |
| **Follower Growth Velocity** | Net new followers per day/week (trend line) | All |
| **Audience Quality Score** | % of followers who engage vs. ghost accounts | IG, TikTok, X |

**Target:** Consistent positive growth rate. Flag if growth stalls for 7+ days.

### Engagement (P0)

| Metric | Definition | Platforms |
|--------|-----------|----------|
| **Engagement Rate** | (Likes + Comments + Shares + Saves) ÷ Reach × 100 | All |
| **Engagement Rate by Follower** | Total engagements ÷ Followers × 100 | All |
| **Comments-to-Likes Ratio** | Higher = deeper engagement | IG, TikTok, YouTube |
| **Share Rate** | Shares ÷ Impressions × 100 (virality signal) | All |
| **Save Rate** | Saves ÷ Reach × 100 (content value signal) | IG |

**Benchmarks:**
- Instagram: 1-3% engagement rate is healthy, >6% is exceptional
- TikTok: 4-8% is average, >15% is viral territory
- LinkedIn: 2-4% for company pages
- X/Twitter: 0.5-1% is typical

### Content Performance (P0)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Reach** | Unique accounts that saw the content | Per post |
| **Impressions** | Total views (including repeats) | Per post |
| **Video Views** | 3s+ views (IG/FB), full views (TikTok) | Per post |
| **Average Watch Time** | Mean seconds watched per view | Per video |
| **Completion Rate** | % who watched to end | Per video |
| **Click-Through Rate (CTR)** | Link clicks ÷ Impressions × 100 | Per post with link |
| **Top Performing Content** | Ranked by engagement rate, last 30 days | Daily |
| **Content Mix Performance** | Engagement by format: Reels vs. Stories vs. Carousels vs. Static | Weekly |

### Timing & Scheduling (P1)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Best Posting Times** | Hours with highest avg engagement (heatmap) | Weekly recalc |
| **Best Posting Days** | Days of week with highest reach | Weekly recalc |
| **Posting Frequency** | Posts per week per platform | Real-time |
| **Content Calendar Adherence** | Scheduled vs. actually posted | Weekly |

### Audience Demographics (P1)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Age Distribution** | % breakdown by age bracket | Monthly |
| **Gender Split** | % male/female/other | Monthly |
| **Top Locations** | Cities and countries | Monthly |
| **Active Hours** | When audience is online (overlay with posting times) | Monthly |
| **Language Distribution** | Primary languages of audience | Monthly |

---

## 3. Lead Generation Metrics

For the **Pipeline** panel. Sales funnel from first touch to close.

### Pipeline Overview (P0)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Total Pipeline Value** | Sum of all active opportunity values | Real-time |
| **Weighted Pipeline** | Each opp × probability of close | Real-time |
| **Pipeline Coverage Ratio** | Pipeline value ÷ Revenue target (want ≥ 3x) | Weekly |
| **New Opportunities** | Deals entered pipeline this period | Daily |
| **Pipeline Velocity** | (Opportunities × Win Rate × Avg Deal Size) ÷ Sales Cycle Length | Monthly |

### Conversion (P0)

| Metric | Definition | Target |
|--------|-----------|--------|
| **Lead-to-MQL Rate** | % of leads that qualify | 15-25% |
| **MQL-to-SQL Rate** | % of MQLs accepted by sales | 40-60% |
| **SQL-to-Close Rate** | % of SQLs that become clients | 20-30% |
| **Overall Lead-to-Close Ratio** | End-to-end conversion | 2-5% |
| **Average Deal Size** | Mean closed deal value | Track trend |
| **Sales Cycle Length** | Days from first touch to signed contract | Track trend |

### Cost & Efficiency (P1)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Cost Per Lead (CPL)** | Total marketing spend ÷ Leads generated | Monthly |
| **Cost Per Acquisition (CPA)** | Total spend ÷ New clients | Monthly |
| **CAC Payback Period** | Months to recoup acquisition cost | Monthly |
| **CAC:LTV Ratio** | Customer acquisition cost ÷ Lifetime value (want ≥ 1:3) | Monthly |
| **Channel ROI** | Revenue attributed ÷ Spend, by channel | Monthly |

### Lead Scoring & Outreach (P1)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Lead Score Distribution** | Histogram of scores across pipeline | Daily |
| **Hot Leads (Score > 80)** | Count + list of high-priority leads | Real-time |
| **Outreach Volume** | Emails/DMs/calls sent per day | Daily |
| **Outreach Response Rate** | Replies ÷ Outreach sent × 100 | Weekly |
| **Follow-Up Adherence** | % of leads contacted within SLA | Daily |
| **Meeting Booked Rate** | Meetings ÷ Outreach sent × 100 | Weekly |
| **No-Show Rate** | Missed meetings ÷ Booked meetings | Weekly |

---

## 4. AI/Agent Metrics

**Unique to us.** This is what makes the War Room different from any generic dashboard.

### Sub-Agent Operations (P0)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Active Sub-Agents** | Currently running agent sessions | Real-time |
| **Task Completion Rate** | Successfully completed ÷ Total spawned × 100 | Per session |
| **Average Task Duration** | Mean time from spawn to completion | Daily |
| **Failure Rate** | Failed/errored ÷ Total spawned | Daily |
| **Failure Reasons** | Categorized: timeout, context overflow, tool error, model error | Per failure |
| **Queue Depth** | Tasks waiting for agent availability | Real-time |
| **Concurrent Agent Ceiling** | Max parallel agents before degradation | Weekly benchmark |

### Token Usage & Costs (P0)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Daily Token Burn** | Total input + output tokens consumed | Daily |
| **Token Cost** | Dollar cost by model tier (Opus/Sonnet/Haiku/Local) | Daily |
| **Cost Per Task** | Average token cost per completed sub-agent task | Daily |
| **Model Mix** | % of tasks routed to each model tier | Daily |
| **Token Efficiency** | Useful output tokens ÷ Total tokens (signal vs. noise) | Weekly |
| **Monthly AI Spend** | Running total with projection | Real-time |
| **Budget Burn Rate** | % of monthly AI budget consumed | Real-time |

### Model Performance (P1)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Model Success Rate** | Task completion by model (Opus vs. Sonnet vs. Haiku) | Weekly |
| **Model Latency** | Average response time by model | Daily |
| **Model Routing Accuracy** | % of tasks routed to optimal tier (post-hoc analysis) | Weekly |
| **Fallback Rate** | % of tasks that escalated from Haiku → Sonnet → Opus | Daily |
| **Local Model Utilization** | % of tasks handled by Ollama (zero-cost) | Daily |

### Automation Savings (P1)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Hours Saved** | Estimated manual hours replaced by automation | Weekly |
| **Dollar Value of Time Saved** | Hours saved × billable rate | Weekly |
| **Automation ROI** | Value saved ÷ AI costs | Monthly |
| **Tasks Automated vs. Manual** | Ratio of agent-handled vs. human-handled tasks | Weekly |
| **Automation Coverage** | % of repeatable workflows that are automated | Monthly |

---

## 5. Competitive Intelligence Metrics

For the **Intel** panel. Know your market.

### Content & Social Velocity (P1)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Competitor Content Velocity** | Posts/week per competitor across platforms | Weekly |
| **Competitor Engagement Benchmarks** | Their engagement rates vs. ours | Weekly |
| **Share of Voice** | Our mentions ÷ (Our mentions + Competitor mentions) | Monthly |
| **Trending Topics in Niche** | What competitors are talking about that we're not | Weekly |
| **Content Gap Analysis** | Topics they cover that we don't | Monthly |

### Market Position (P2)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Market Share Indicators** | Relative follower count, search volume, review count | Monthly |
| **Pricing Position** | Our pricing vs. competitor range | Quarterly |
| **Feature Gap Tracking** | Services they offer that we don't (and vice versa) | Monthly |
| **Review Sentiment** | Competitor review ratings and sentiment trends | Monthly |
| **New Competitor Alerts** | New entrants in our space | Monthly scan |

### Industry Signals (P2)

| Metric | Definition | Update Frequency |
|--------|-----------|-----------------|
| **Industry Growth Rate** | TAM/SAM expansion metrics | Quarterly |
| **Technology Adoption Trends** | AI/agent adoption in our target market | Quarterly |
| **Regulatory Changes** | New laws/regulations affecting AI services | As they happen |

---

## 6. Visual Recommendations

How to display each metric category in the Command Center UI.

### Layout Philosophy

```
┌─────────────────────────────────────────────────────────────┐
│  COMMAND CENTER                                    [Friday] │
├──────────┬──────────┬──────────┬───────────────────────────┤
│  MRR     │  Active  │  Pipeline│   AI Spend    │  Agents   │
│  $XXk    │  Clients │  $XXXk   │   $XX.XX/day  │  3 active │
│  ↑12%    │  12      │  3.2x    │   ██████░░ 67%│  0 failed │
├──────────┴──────────┴──────────┴───────────────────────────┤
│                    [Main Content Area]                       │
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │  Revenue Chart   │  │  Social Media Performance       │  │
│  │  (Area + Line)   │  │  (Multi-platform cards)         │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │  Pipeline Funnel │  │  Agent Activity Feed            │  │
│  │  (Funnel chart)  │  │  (Live timeline)                │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Widget Types by Metric

| Widget Type | Best For | Examples |
|-------------|----------|---------|
| **KPI Card** | Single number with trend | MRR, Active Clients, Pipeline Value, Daily Token Burn |
| **Sparkline** | Compact trend in small space | Follower growth, Revenue trend, Token usage |
| **Gauge / Radial** | Progress toward a target | Budget burn, Utilization rate, Automation coverage |
| **Area Chart** | Volume over time | Revenue over months, Token usage over days |
| **Line Chart** | Comparing trends | MRR vs. Churn, Model cost comparison |
| **Bar Chart** | Comparing categories | Engagement by platform, Model success rates |
| **Stacked Bar** | Composition breakdown | Content mix, Model tier distribution |
| **Funnel** | Conversion pipelines | Lead → MQL → SQL → Close |
| **Heatmap** | Time-based patterns | Best posting times (day × hour grid) |
| **Donut Chart** | Proportions | Revenue by client, Audience demographics |
| **Table with Status** | Detailed lists | Client health (with color-coded scores), At-risk clients |
| **Live Feed / Timeline** | Real-time events | Sub-agent spawns, completions, failures |
| **Progress Bar** | Budget/target tracking | Monthly AI spend, Pipeline coverage |

### Color System

```
Green  (#10B981) → On track, healthy, positive trend
Yellow (#F59E0B) → Warning, approaching threshold
Red    (#EF4444) → Critical, needs attention
Blue   (#3B82F6) → Neutral/informational
Purple (#8B5CF6) → AI/Agent specific metrics
Gray   (#6B7280) → Inactive, historical
```

### Interaction Patterns

- **Click any KPI card** → Expand to full chart with historical data
- **Hover sparklines** → Show exact value + date tooltip
- **Click gauge** → Show breakdown of contributing factors
- **Filter bar** → Date range picker (Today / 7d / 30d / 90d / Custom)
- **Alert badges** → Red dot on cards when metric crosses threshold
- **Drag to reorder** → Let users customize their layout

### Responsive Behavior

- **Desktop (1440px+):** Full grid, 4-5 columns of KPI cards, side-by-side charts
- **Tablet (768-1439px):** 2-3 columns, stacked charts
- **Mobile (< 768px):** Single column, KPI cards as horizontal scroll strip

### Real-Time vs. Periodic Updates

| Update Strategy | Metrics | Method |
|----------------|---------|--------|
| **WebSocket (live)** | Active agents, queue depth, live feed | Push from backend |
| **30-second poll** | Token burn, agent status | Short interval fetch |
| **5-minute poll** | Social metrics cache, pipeline updates | API rate-limit friendly |
| **Daily batch** | Demographics, competitive intel, cost rollups | Cron job aggregation |

---

## 7. Implementation Priority

### Phase 1 — MVP (Week 1-2)
- [ ] KPI cards: MRR, Active Clients, Pipeline Value, AI Spend
- [ ] Agent activity live feed (sub-agent spawns/completions)
- [ ] Token usage daily chart
- [ ] Basic social metrics (follower count + engagement rate per platform)

### Phase 2 — Core (Week 3-4)
- [ ] Revenue area chart with trend
- [ ] Lead pipeline funnel
- [ ] Client health score table
- [ ] Social media posting heatmap
- [ ] Model performance comparison

### Phase 3 — Intelligence (Week 5-6)
- [ ] Automation savings calculator
- [ ] Competitive intel panel
- [ ] Lead scoring distribution
- [ ] Content performance rankings
- [ ] Audience demographics breakdown

### Phase 4 — Polish (Week 7-8)
- [ ] Customizable layout (drag-and-drop)
- [ ] Alert threshold configuration
- [ ] Export/reporting
- [ ] Mobile optimization
- [ ] Historical comparisons (this month vs. last month)

---

## Notes

- **Instagram reel sources:** `DVapMMJETxi` (Olivia Network influencer commercial) and `DVeV1K0jw8u` (dashboard metrics reel) — could not extract captions due to Instagram auth wall. Content was used as inspiration for social media and competitive intelligence sections.
- **Data sources to integrate:** Stripe/payment processor (revenue), CRM (pipeline), Instagram/TikTok/X APIs (social), OpenClaw gateway logs (agent metrics), Google Analytics (web traffic).
- **Framework suggestion:** Use the same tech stack as the War Room frontend — Next.js + Recharts or Tremor for charts. Tremor has excellent pre-built dashboard components.

---

*Generated 2026-03-06 for the War Room Command Center build.*
