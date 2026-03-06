# Lead Generation Research — Feature Extraction from Open Source Repos

> Generated: 2026-03-06 | Purpose: Extract features & patterns from OSS lead gen repos to enhance War Room

---

## Table of Contents

1. [Features We Should Build](#1-features-we-should-build)
2. [Code Patterns to Steal](#2-code-patterns-to-steal)
3. [Free vs Paid Analysis](#3-free-vs-paid-analysis)
4. [Architecture Recommendation](#4-architecture-recommendation)
5. [Repos Researched](#5-repos-researched)

---

## 1. Features We Should Build

Prioritized by impact × feasibility. Effort estimates assume one developer.

### 🔴 P0 — High Impact, Build First

#### 1.1 Email Discovery Engine (Effort: 1–2 weeks)
**What:** Find business email addresses from websites without paid APIs.
**Why:** We already crawl websites (`website_crawler.py`) and extract emails via regex. But we're missing *pattern-based email guessing* and *validation*.

**Sub-features:**
- **Website scraping (DONE)** — Already implemented in `website_crawler.py`. Crawls `/contact`, `/about`, `/team` pages for `mailto:` and regex matches.
- **Email pattern generation (NEW)** — Given a name + domain, generate candidates: `john@acme.com`, `john.doe@acme.com`, `jdoe@acme.com`, `j.doe@acme.com`, etc. The `sales-lead-scraper-tool` repo has a full `EmailExtractor.generate_patterns()` with confidence scoring.
- **Email validation (NEW)** — Three-level validation: (1) syntax check, (2) DNS MX record verification, (3) SMTP RCPT TO probe. All free, no API needed. The `sales-lead-scraper-tool` repo has `EmailValidator` with `ValidationLevel.SYNTAX`, `DNS`, `SMTP`.
- **Contact page endpoint scanning (ENHANCE)** — `yogsec/email-finder` scans 30+ endpoint patterns (`/contact-us`, `/reach-us`, `/enquiries`, `/customer-service`, `/meet-the-team`, `/en/contact`, `/company/contact`). We currently check ~10. Expand the list.

**Source repos:**
- `codiebyheaart/sales-lead-scraper-tool` — Best architecture. Has `src/extractors/email_extractor.py` with pattern generation + confidence scoring, `src/validators/` with multi-level validation.
- `yogsec/email-finder` — Multi-threaded, scans 30+ contact endpoints per domain.
- `WildSiphon/Mailfoguess` — OSINT email guessing from first/last name + domain. Generates all permutations, verifies via `holehe`.
- `eneiromatos/TS-email-scraper` — Uses Crawlee (Node.js) to crawl from Google search keywords → domain → email extraction.

#### 1.2 Natural Language Lead Search (Effort: 1 week)
**What:** Type "find marketing agencies in Miami that need a website" → AI extracts structured filters → runs search.
**Why:** The `brightdata/ai-lead-generator` does exactly this with OpenAI. We can do it with our own AI (Claude via OpenClaw gateway or Ollama).

**How it works in Bright Data's repo:**
1. User types natural language query
2. LLM extracts: `{role: "marketing agency", location: "Miami", industry: "marketing"}`
3. Structured filters drive the scraper
4. Results are AI-scored and enriched

**Our implementation:**
- Add an endpoint `POST /leadgen/smart-search` that takes a natural language string
- Use Claude/Ollama to extract: `{query, location, radius_km, business_types[], min_rating, must_have_website: bool}`
- Feed into our existing `search_places()` + `enrich_job()` pipeline
- Return results with AI-generated relevance explanations

#### 1.3 AI-Powered Lead Scoring v2 (Effort: 3–5 days)
**What:** Upgrade our rule-based scorer with semantic AI analysis.
**Why:** Our current `lead_scorer.py` is pure rules (no_website=25pts, bad_audit=20pts, etc.). Good start, but we should add AI reasoning.

**Enhancement layers:**
- **Keep existing rule-based scoring** as the base (fast, predictable)
- **Add AI qualification layer** — For leads scoring >50, send a prompt to Claude/Ollama with the lead's data (website tech, reviews, social presence) and get:
  - Qualification reasoning ("This business has a Wix site from 2019 with broken mobile layout — strong candidate for redesign")
  - Personalized pitch angle
  - Best contact channel recommendation
  - Estimated conversion probability
- **Intent signals** — If we add social listening (see P1), boost score for businesses actively discussing problems we solve

**Source:** `brightdata/ai-lead-generator` does this — each lead gets an AI summary, relevance score, and outreach tip.

#### 1.4 AI Cold Email/Outreach Generation (Effort: 3–5 days)
**What:** Auto-generate personalized cold emails for each lead.
**Why:** `LeadGenPy` and `sales-lead-scraper-tool` both do this. We have all the data — business name, website audit results, missing features. Let AI write the pitch.

**Implementation:**
- Template engine with variable substitution (`{{business_name}}`, `{{audit_score}}`, `{{top_fix}}`)
- AI personalization layer that reads the lead's website/reviews and writes a unique opener
- Multiple templates: cold outreach, follow-up sequence (3-touch), "we noticed your website" approach
- `sales-lead-scraper-tool` has a full `TemplateEngine` class with `render_template()` and variable substitution

### 🟡 P1 — Medium Impact, Build Second

#### 1.5 Social Listening for Intent Signals (Effort: 2–3 weeks)
**What:** Monitor Reddit, X/Twitter, forums for people/businesses expressing pain points we solve.
**Why:** The `awesome-ai-lead-generation` list highlights this as the #1 category. Tools like Leado, GummySearch, F5Bot monitor Reddit for buying intent.

**Sub-features:**
- **Reddit monitoring** — Use Reddit's free JSON API (`reddit.com/r/{sub}.json`) or PRAW to monitor subreddits like r/smallbusiness, r/webdesign, r/Entrepreneur for keywords: "need a website", "looking for web developer", "redesign my site"
- **X/Twitter monitoring** — Use the free search endpoint or scrape with Playwright for tweets mentioning business pain points
- **Forum scraping** — Use Playwright to monitor industry-specific forums
- **Intent scoring** — AI classifies posts as: high intent ("I need a website ASAP"), medium ("thinking about redesigning"), low ("just browsing")
- **Alert system** — Push notifications when high-intent leads are found

**Source repos:**
- `GURPREETKAURJETHRA/AI-Lead-Generation-Agent` — Scrapes Quora for intent signals, uses Firecrawl + Phidata for orchestration. The *pattern* is what matters: search platform → extract profiles → qualify with AI → store.
- F5Bot concept — Free keyword alerts for Reddit (we can self-host this with a cron + PRAW)

#### 1.6 Google Maps Scraper Enhancement (Effort: 1 week)
**What:** Upgrade our Google Places integration with patterns from top scrapers.
**Why:** `omkarcloud/google-maps-scraper` (2400+ stars) has features we're missing.

**Features to add:**
- **"Tech Savvy, High Earners" sort** — Prioritize businesses that: have more reviews, have websites, are spending on Google Ads. We can detect ad spend from the Places API `business_status` field.
- **Country-wide search** — Search for a business type across all cities in a state/country. Iterate through a city list.
- **Review scraping** — Extract review text for sentiment analysis. Businesses with complaints about their "online presence" are warm leads.
- **Enrichment: social links, AI-recommended emails** — omkarcloud's new Business Enrichment API extracts social links + generates likely email addresses. We do some of this already but can improve.

#### 1.7 LinkedIn Data Extraction — Free Methods (Effort: 1–2 weeks)
**What:** Extract business/person data from LinkedIn without paid APIs.
**Why:** LinkedIn is the #1 B2B data source. Multiple repos do this with Selenium.

**Approaches (all free):**
- **`ahmedmujtaba1/Linkedin-Leads-Generation`** — Selenium-based. Logs into LinkedIn, searches by keyword/location, extracts profiles + emails. Uses the AllForLeads Chrome extension for email discovery.
- **Public profile scraping** — LinkedIn public profiles (`linkedin.com/in/username`) are accessible without login. Parse with BeautifulSoup.
- **Google dork approach** — Search `site:linkedin.com/in "marketing manager" "Miami"` via SearXNG (free, self-hosted search).
- **`Aboodseada1/CEO-Finder`** — Uses SearXNG + LLM to find company executives. Searches "Who is the CEO of {company}", collects results, feeds to LLM for analysis. Supports Ollama for fully free operation.

**⚠️ Risk:** LinkedIn aggressively blocks scrapers. Use rate limiting, residential proxies, or the Google dork method.

#### 1.8 Google Maps Full-Stack Scraper (Effort: 1 week)
**What:** Puppeteer/Playwright-based Google Maps scraper that doesn't need the Places API.
**Why:** Google Places API has costs at scale. `ismailsoud/easyLead` does it with Puppeteer (free).

**Architecture from easyLead:**
- React + Vite frontend
- Node.js + Express + Puppeteer backend
- User enters "restaurants in New York" → Puppeteer opens Google Maps → scrapes all results
- Exports to CSV
- We could adapt this pattern using Playwright (which we already have in Docker)

### 🟢 P2 — Nice to Have, Build Later

#### 1.9 Voice AI for Outbound Calls (Effort: 3–4 weeks)
**What:** AI voice agent that calls leads, qualifies them, and schedules meetings.
**Why:** The `awesome-ai-lead-generation` list includes Bland AI, Synthflow, Vapi — but all are paid SaaS.

**Free approach:**
- Use our existing voice infrastructure (edge-tts, whisper)
- Build a call script engine with decision trees
- Integrate with Twilio (pay-per-call, ~$0.01/min) or self-hosted Asterisk/FreeSWITCH
- AI decides next question based on response transcription

**⚠️ Complex.** Voice AI for cold calls is hard to get right. Start with warm leads only.

#### 1.10 Company Intelligence Lookup (Effort: 3–5 days)
**What:** Given a company name/domain, find: CEO/founder name, company size, tech stack, funding status.
**Why:** `CEO-Finder` does the name lookup. We can extend it to full company profiles.

**How:**
- SearXNG search for "{company} CEO founder owner" → LLM extracts name
- Wappalyzer-style tech detection from website headers/HTML (already partially in `website_crawler.py`)
- Crunchbase/LinkedIn public pages for company size
- All queryable via SearXNG + Ollama (zero cost)

#### 1.11 Multi-Platform Lead Aggregation (Effort: 2 weeks)
**What:** Scrape leads from YellowPages, Yelp, BBB, Facebook Pages — not just Google Maps.
**Why:** Multiple repos in the `leadgeneration` topic do this: `sushil-rgb/YellowPage-scraper`, `wael-sudo2/facebook-page-info-scraper`.

**Sources to add:**
- YellowPages (BeautifulSoup, no JS needed)
- Yelp (Playwright, JS-rendered)
- BBB (BeautifulSoup)
- Facebook Pages (Playwright)
- Deduplicate across sources using business name + address matching

---

## 2. Code Patterns to Steal

### 2.1 Email Pattern Generation (from `sales-lead-scraper-tool`)

```python
# Pattern: Generate candidate emails from name + domain with confidence scores
class EmailPattern:
    email: str
    confidence: float  # 0.0 - 1.0

def generate_patterns(first_name: str, last_name: str, domain: str) -> list[EmailPattern]:
    """Generate all common email patterns with confidence ranking."""
    patterns = [
        (f"{first_name}.{last_name}@{domain}", 0.95),      # john.doe@acme.com (most common)
        (f"{first_name[0]}{last_name}@{domain}", 0.85),     # jdoe@acme.com
        (f"{first_name}@{domain}", 0.80),                    # john@acme.com
        (f"{first_name}{last_name}@{domain}", 0.75),         # johndoe@acme.com
        (f"{first_name[0]}.{last_name}@{domain}", 0.70),    # j.doe@acme.com
        (f"{last_name}.{first_name}@{domain}", 0.60),        # doe.john@acme.com
        (f"{first_name}_{last_name}@{domain}", 0.55),        # john_doe@acme.com
        (f"{first_name[0]}{last_name[0]}@{domain}", 0.30),  # jd@acme.com
        (f"info@{domain}", 0.90),                             # Generic catch-all
        (f"contact@{domain}", 0.85),                          # Generic
        (f"hello@{domain}", 0.70),                            # Generic
    ]
    return [EmailPattern(email=e.lower(), confidence=c) for e, c in patterns]
```

### 2.2 Three-Level Email Validation (from `sales-lead-scraper-tool`)

```python
import dns.resolver
import smtplib
import socket

def validate_email_syntax(email: str) -> bool:
    """Level 1: Regex syntax check."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_email_dns(email: str) -> bool:
    """Level 2: Check domain has MX records."""
    domain = email.split('@')[1]
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        return len(mx_records) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return False

def validate_email_smtp(email: str) -> bool:
    """Level 3: SMTP RCPT TO probe (use sparingly — can trigger rate limits)."""
    domain = email.split('@')[1]
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_host = str(mx_records[0].exchange)
        server = smtplib.SMTP(timeout=10)
        server.connect(mx_host)
        server.helo('verify.local')
        server.mail('verify@verify.local')
        code, _ = server.rcpt(email)
        server.quit()
        return code == 250
    except Exception:
        return False
```

### 2.3 NL Query → Structured Filters (from `brightdata/ai-lead-generator`)

```python
FILTER_EXTRACTION_PROMPT = """
Extract structured search filters from this natural language query.
Return JSON with these fields:
- query: search terms for Google Maps/Places
- location: city, state, or region
- business_types: list of business categories
- min_rating: minimum Google rating (null if not specified)
- must_have_website: boolean
- keywords: additional keywords to filter by

Query: "{user_input}"
"""

async def parse_search_query(user_input: str) -> dict:
    """Use LLM to extract structured filters from natural language."""
    response = await llm_complete(FILTER_EXTRACTION_PROMPT.format(user_input=user_input))
    return json.loads(response)
```

### 2.4 SearXNG + LLM for Company Intelligence (from `CEO-Finder`)

```python
# Pattern: Web search → LLM analysis for structured extraction
async def find_company_executive(company: str) -> dict:
    """Use SearXNG (free, self-hosted) + LLM to find company leadership."""
    queries = [
        f"Who is the CEO of {company}",
        f"{company} founder owner",
        f"{company} leadership team",
    ]
    
    all_results = []
    for query in queries:
        results = await searxng_search(query)  # Free, self-hosted
        all_results.extend(results)
    
    # Feed to LLM for analysis
    prompt = f"""Analyze these search results and identify the CEO/founder/owner of {company}.
    Return JSON: {{"ceo_name": "Name or null", "confidence": 0.0-1.0, "source": "url"}}
    
    Results: {json.dumps(all_results[:20])}"""
    
    return await llm_complete(prompt)  # Works with Ollama (free)
```

### 2.5 Google Maps Selenium Scraper (from `LeadGenPy`)

```python
# Pattern: Selenium → Google Maps search → data extraction → AI email generation
class GoogleMapsScraper:
    def search(self, business_type: str, location: str):
        self.driver.get("https://maps.google.com")
        search_box = self.driver.find_element(By.ID, "searchboxinput")
        search_box.send_keys(f"{business_type} in {location}")
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)
        
        # Scroll results panel to load all
        results_panel = self.driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
        for _ in range(10):
            self.driver.execute_script(
                'arguments[0].scrollTop = arguments[0].scrollHeight', results_panel
            )
            time.sleep(1)
        
        # Extract each listing
        listings = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
        for listing in listings:
            listing.click()
            time.sleep(1)
            yield self._extract_details()
    
    def _extract_details(self) -> dict:
        return {
            "name": self._safe_text('h1'),
            "address": self._safe_text('[data-item-id="address"]'),
            "phone": self._safe_text('[data-item-id^="phone"]'),
            "website": self._safe_attr('[data-item-id="authority"] a', 'href'),
            "rating": self._safe_text('span[role="img"]'),
            "reviews": self._safe_text('span[aria-label*="reviews"]'),
        }
```

### 2.6 Reddit Intent Monitoring (inspired by GummySearch/F5Bot)

```python
import praw  # Reddit API wrapper — free

class RedditIntentMonitor:
    """Monitor subreddits for buying intent keywords."""
    
    INTENT_KEYWORDS = [
        "need a website", "looking for web developer", "redesign my site",
        "worst website", "help with SEO", "need an app", "hire developer",
        "recommend a web designer", "small business website",
    ]
    
    SUBREDDITS = [
        "smallbusiness", "Entrepreneur", "webdesign", "webdev",
        "startups", "marketing", "SEO", "freelance",
    ]
    
    def __init__(self):
        self.reddit = praw.Reddit(
            client_id="...",  # Free Reddit API credentials
            client_secret="...",
            user_agent="warroom-intent-monitor/1.0"
        )
    
    async def scan_for_intent(self) -> list[dict]:
        """Scan subreddits for posts matching intent keywords."""
        leads = []
        for sub_name in self.SUBREDDITS:
            subreddit = self.reddit.subreddit(sub_name)
            for post in subreddit.new(limit=100):
                text = f"{post.title} {post.selftext}".lower()
                matches = [kw for kw in self.INTENT_KEYWORDS if kw in text]
                if matches:
                    leads.append({
                        "source": "reddit",
                        "subreddit": sub_name,
                        "title": post.title,
                        "url": f"https://reddit.com{post.permalink}",
                        "author": str(post.author),
                        "keywords_matched": matches,
                        "created_utc": post.created_utc,
                        "score": post.score,
                    })
        return leads
```

### 2.7 Expanded Contact Page Scanning (from `yogsec/email-finder`)

```python
# Comprehensive contact endpoint list — scan ALL of these per domain
CONTACT_ENDPOINTS = [
    "/contact-us", "/contact", "/about", "/support", "/help",
    "/team", "/careers", "/jobs", "/faq", "/press", "/media",
    "/partners", "/company", "/privacy-policy", "/terms", "/legal",
    "/get-in-touch", "/reach-us", "/enquiries", "/feedback",
    "/customer-support", "/customer-service", "/connect",
    "/who-we-are", "/meet-the-team",
    "/en/contact", "/en/about", "/en/support",    # i18n variants
    "/info/contact", "/company/contact",           # Nested paths
    "/staff", "/people", "/our-team", "/leadership",
    "/about-us", "/contactus",                     # No-hyphen variants
]
```

### 2.8 Production-Mode Pipeline (from `LeadGenPy`)

```python
# Pattern: Full pipeline in one command — search → extract → enrich → email
# Mode 5: "Production Mode"
async def production_pipeline(business_type: str, location: str):
    """End-to-end: search → scrape → enrich → generate emails → send."""
    # Step 1: Search Google Maps
    leads = await google_maps_search(business_type, location)
    
    # Step 2: Extract contact data from websites
    for lead in leads:
        if lead.website:
            lead.contacts = await crawl_website(lead.website)
    
    # Step 3: Store in database
    await bulk_insert_leads(leads)
    
    # Step 4: AI-generate personalized emails
    for lead in leads:
        if lead.contacts.emails:
            lead.email_draft = await ai_generate_email(lead)
    
    # Step 5: Send emails (with rate limiting)
    await send_emails_with_throttle(leads, delay_seconds=30)
```

---

## 3. Free vs Paid Analysis

### What We Can Build 100% Free

| Feature | Free Implementation | Dependencies |
|---------|-------------------|--------------|
| **Google Maps scraping** | Playwright scraper (bypass Places API) | Playwright (in Docker ✅) |
| **Website crawling** | httpx + BeautifulSoup (DONE ✅) | httpx, bs4 |
| **Email extraction** | Regex on crawled pages (DONE ✅) | None |
| **Email pattern generation** | Name + domain → permutations | None |
| **Email validation (syntax)** | Regex | None |
| **Email validation (DNS)** | MX record lookup | `dnspython` |
| **Email validation (SMTP)** | RCPT TO probe | `smtplib` (stdlib) |
| **AI lead scoring** | Claude via OpenClaw / Ollama | OpenClaw gateway ✅ |
| **AI email generation** | Claude via OpenClaw / Ollama | OpenClaw gateway ✅ |
| **NL search parsing** | Claude via OpenClaw / Ollama | OpenClaw gateway ✅ |
| **Reddit monitoring** | PRAW (free Reddit API) | `praw` |
| **Company exec finder** | SearXNG + Ollama | Self-hosted SearXNG |
| **LinkedIn public profiles** | Google dork + BeautifulSoup | None |
| **Website tech detection** | HTML/header analysis (DONE ✅) | None |
| **Website auditing** | Lighthouse CLI or custom (DONE ✅) | None |
| **Social link extraction** | Regex on crawled pages (DONE ✅) | None |
| **YellowPages scraping** | BeautifulSoup | bs4 |
| **Data export (CSV/JSON)** | stdlib (DONE ✅) | None |

### What Needs Paid Services (and Free Alternatives)

| Feature | Paid Service | Free Alternative | Trade-off |
|---------|-------------|------------------|-----------|
| **Google Places API** | $17/1K requests | Playwright Google Maps scraper | Slower, rate-limited |
| **Email sending at scale** | SendGrid, Mailgun | Self-hosted Postfix + DKIM | Deliverability harder to manage |
| **LinkedIn scraping** | PhantomBuster ($69/mo) | Selenium + rate limiting | Account ban risk |
| **Voice AI calls** | Bland AI, Vapi ($0.10/min) | Asterisk + Whisper + edge-tts | Much harder, lower quality |
| **Proxy rotation** | Bright Data ($500/mo) | Free proxy lists + tor | Unreliable, slow |
| **Search API** | SerpAPI ($50/mo) | SearXNG (self-hosted) | Slightly less reliable |
| **AI models** | OpenAI API ($20/mo) | Ollama (llama3.1:8b, free) | Lower quality, slower |

### Our Stack (Zero Cost)

```
Scraping:      Playwright (Docker) + httpx + BeautifulSoup
AI:            OpenClaw gateway → Claude (already paid) or Ollama (free)
Search:        Google Places API (free tier: 200 req/day) + Playwright fallback
Email verify:  dnspython + smtplib (self-hosted)
Social listen: PRAW (free Reddit API) + Playwright (X/Twitter)
Database:      PostgreSQL on Brain 2 (10.0.0.11:5433)
Email send:    Postfix or existing email service
Company intel: SearXNG (self-host) + Ollama
```

---

## 4. Architecture Recommendation

### 4.1 Current State

```
backend/app/services/leadgen/
├── __init__.py
├── google_places.py      # Google Places API search
├── enrichment.py          # Website crawl → email/social extraction → scoring
├── lead_scorer.py         # Rule-based scoring (no_website=25, bad_audit=20, etc.)
├── website_auditor.py     # Lighthouse-style website quality audit
└── website_crawler.py     # httpx crawler for emails, phones, socials, platform detection

backend/app/api/
├── leadgen.py             # API routes: search, leads CRUD, audit, contact logging, export
└── leadgen_schemas.py     # Pydantic schemas

backend/app/db/
└── leadgen_db.py          # Async SQLAlchemy session for leadgen DB

backend/app/models/
└── lead.py                # Lead + SearchJob SQLAlchemy models
```

### 4.2 Proposed New Structure

```
backend/app/services/leadgen/
├── __init__.py
├── google_places.py          # (existing) Google Places API
├── google_maps_scraper.py    # (NEW) Playwright-based Google Maps scraper (free fallback)
├── enrichment.py             # (existing, enhanced) Add email pattern gen + validation
├── lead_scorer.py            # (existing, enhanced) Add AI scoring layer
├── website_auditor.py        # (existing)
├── website_crawler.py        # (existing, enhanced) Expand contact endpoints
├── email_discovery.py        # (NEW) Email pattern generation + multi-level validation
├── email_generator.py        # (NEW) AI-powered cold email drafting
├── smart_search.py           # (NEW) NL query → structured filters via LLM
├── social_listener.py        # (NEW) Reddit/X intent monitoring
├── company_intel.py          # (NEW) SearXNG + LLM company/exec lookup
├── linkedin_scraper.py       # (NEW) LinkedIn public profile extraction
└── multi_source_scraper.py   # (NEW) YellowPages, Yelp, BBB scrapers

backend/app/api/
├── leadgen.py                # (existing, add new routes)
├── leadgen_schemas.py        # (existing, add new schemas)
└── leadgen_outreach.py       # (NEW) Email generation + sending endpoints
```

### 4.3 New API Endpoints

```python
# Smart Search
POST /leadgen/smart-search          # NL query → AI extracts filters → runs search

# Email Discovery
POST /leadgen/leads/{id}/discover-emails    # Run email pattern gen + validation for a lead
POST /leadgen/leads/{id}/validate-emails    # Validate existing emails (DNS + SMTP)

# AI Features  
POST /leadgen/leads/{id}/ai-score          # Get AI qualification analysis
POST /leadgen/leads/{id}/generate-email    # Generate personalized cold email
POST /leadgen/leads/{id}/company-intel     # Lookup CEO, company size, tech stack

# Social Listening
POST /leadgen/social-listen/start          # Start monitoring subreddits/keywords
GET  /leadgen/social-listen/results        # Get intent signals found
POST /leadgen/social-listen/stop           # Stop monitoring

# Multi-Source Search
POST /leadgen/search/google-maps-free      # Playwright-based (no API key needed)
POST /leadgen/search/yellowpages           # YellowPages scraper
POST /leadgen/search/linkedin              # LinkedIn public profile search

# Outreach
POST /leadgen/outreach/draft               # Generate email drafts for a batch of leads
POST /leadgen/outreach/send                # Send emails (with rate limiting)
GET  /leadgen/outreach/templates           # List email templates
```

### 4.4 Database Additions

```sql
-- New columns on leads table
ALTER TABLE leads ADD COLUMN email_patterns JSONB;        -- Generated email candidates with confidence
ALTER TABLE leads ADD COLUMN email_validation JSONB;       -- Validation results per email
ALTER TABLE leads ADD COLUMN ai_qualification TEXT;         -- AI reasoning about lead quality
ALTER TABLE leads ADD COLUMN ai_pitch_angle TEXT;           -- Suggested pitch
ALTER TABLE leads ADD COLUMN ai_contact_channel TEXT;       -- Best way to reach them
ALTER TABLE leads ADD COLUMN ceo_name VARCHAR(255);         -- Company executive name
ALTER TABLE leads ADD COLUMN company_size VARCHAR(50);      -- small/medium/large
ALTER TABLE leads ADD COLUMN tech_stack JSONB;              -- Detected technologies
ALTER TABLE leads ADD COLUMN outreach_email_draft TEXT;     -- Generated email draft
ALTER TABLE leads ADD COLUMN intent_signals JSONB;          -- Social listening matches
ALTER TABLE leads ADD COLUMN source_platform VARCHAR(50);   -- google_maps, yellowpages, reddit, linkedin

-- New table for social listening
CREATE TABLE intent_signals (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,         -- reddit, twitter, forum
    platform_id VARCHAR(255),            -- post ID on source platform
    title TEXT,
    content TEXT,
    url TEXT,
    author VARCHAR(255),
    keywords_matched TEXT[],
    intent_score FLOAT,                  -- AI-rated 0.0-1.0
    subreddit VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    lead_id INTEGER REFERENCES leads(id) -- linked lead if converted
);

-- New table for outreach campaigns
CREATE TABLE outreach_campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    template_id VARCHAR(100),
    status VARCHAR(50) DEFAULT 'draft',  -- draft, active, paused, complete
    leads_count INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    opened_count INTEGER DEFAULT 0,
    replied_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.5 Implementation Roadmap

```
Week 1-2: Email Discovery Engine
  - email_discovery.py (pattern gen + validation)
  - Expand website_crawler.py contact endpoints
  - API endpoints + schema updates
  - DB migrations

Week 3: Smart Search + AI Scoring v2
  - smart_search.py (NL → filters)
  - Enhance lead_scorer.py with AI layer
  - POST /leadgen/smart-search endpoint

Week 3-4: AI Outreach Generation
  - email_generator.py (template engine + AI personalization)
  - Outreach API endpoints
  - Email draft UI in frontend

Week 5-6: Social Listening
  - social_listener.py (Reddit first, X later)
  - Intent signals DB table
  - Background worker for continuous monitoring
  - Alert system integration

Week 7-8: Multi-Source + LinkedIn
  - google_maps_scraper.py (Playwright, free)
  - linkedin_scraper.py (public profiles)
  - company_intel.py (SearXNG + Ollama)
  - multi_source_scraper.py (YellowPages, Yelp)
```

---

## 5. Repos Researched

### Primary Sources

| Repo | Stars | Key Features | Relevance |
|------|-------|-------------|-----------|
| [omkarcloud/google-maps-scraper](https://github.com/omkarcloud/google-maps-scraper) | 2400+ | Google Maps scraping, email enrichment, social links, ad spend detection | ⭐⭐⭐⭐⭐ |
| [brightdata/ai-lead-generator](https://github.com/brightdata/ai-lead-generator) | ~200 | NL search → AI scoring → personalized outreach | ⭐⭐⭐⭐⭐ |
| [codiebyheaart/sales-lead-scraper-tool](https://github.com/codiebyheaart/sales-lead-scraper-tool) | ~50 | Best architecture: email patterns, validation, CRM integration, templates | ⭐⭐⭐⭐⭐ |
| [toofast1/awesome-ai-lead-generation](https://github.com/toofast1/awesome-ai-lead-generation) | ~100 | Curated list of 20+ lead gen tools across 5 categories | ⭐⭐⭐⭐ |
| [Wikkiee/LeadGenPy](https://github.com/Wikkiee/LeadGenPy) | ~50 | Full pipeline: Maps → extract → AI email → send | ⭐⭐⭐⭐ |
| [Aboodseada1/CEO-Finder](https://github.com/Aboodseada1/CEO-Finder) | ~30 | SearXNG + LLM for executive lookup, supports Ollama | ⭐⭐⭐⭐ |
| [yogsec/email-finder](https://github.com/yogsec/email-finder) | ~40 | Multi-threaded email extraction, 30+ contact endpoints | ⭐⭐⭐⭐ |

### Secondary Sources

| Repo | Key Features |
|------|-------------|
| [GURPREETKAURJETHRA/AI-Lead-Generation-Agent](https://github.com/GURPREETKAURJETHRA/AI-Lead-Generation-Agent) | Quora intent scraping + Phidata orchestration |
| [WildSiphon/Mailfoguess](https://github.com/WildSiphon/Mailfoguess) | OSINT email guessing from name + domain permutations |
| [ahmedmujtaba1/Linkedin-Leads-Generation](https://github.com/ahmedmujtaba1/Linkedin-Leads-Generation) | Selenium LinkedIn scraper + email extraction |
| [eneiromatos/TS-email-scraper](https://github.com/eneiromatos/TS-email-scraper) | Crawlee-based email scraper from Google keywords |
| [ismailsoud/easyLead](https://github.com/ismailsoud/easyLead) | Full-stack Google Maps scraper (React + Puppeteer) |
| [PatrykIA/High_Lead_Generation_Automation_Tool](https://github.com/PatrykIA/High_Lead_Generation_Automation_Tool) | Apify + Google Sheets + AI email pipeline (1000 leads/min) |
| [mishakorzik/MailFinder](https://github.com/mishakorzik/MailFinder) | OSINT: find email from first + last name |

---

## Key Takeaways

1. **Our biggest gap is email discovery.** We scrape emails from websites but don't generate patterns or validate them. The `sales-lead-scraper-tool` repo has the exact code we need.

2. **AI scoring is table stakes.** Every modern lead gen tool uses LLMs for qualification. Our rule-based scorer is a good foundation, but we need an AI layer on top.

3. **Natural language search is a huge UX win.** "Find plumbers in Brooklyn without a website" should just work. One LLM call to parse → our existing pipeline.

4. **Social listening is the moat.** Intent-based leads (someone actively saying "I need a website") convert 10x better than cold outreach. Reddit API is free.

5. **Everything can be free.** Playwright replaces paid scraping APIs. Ollama replaces OpenAI. SearXNG replaces SerpAPI. dnspython replaces Hunter.io. The only cost is compute time.

6. **We already have 60% of the infrastructure.** Our `website_crawler.py`, `enrichment.py`, `lead_scorer.py`, and the full API layer are solid. We're adding capabilities on top, not rebuilding.
