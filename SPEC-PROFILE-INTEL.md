# Profile Intel — Feature Specification

## What Profile Intel Is

Profile Intel is the platform's **self-improvement engine**. It exists for one purpose: to make the user better at creating content that performs. It is not a dashboard. It is not a competitor visualization tool. It is a personalized coaching system that tells you exactly what to fix, what to keep doing, and what to create next — backed by data from your own account and measured against your competitor database.

The distinction matters: Competitor Intelligence tells you what the market is doing. Profile Intel tells you what **you** should do about it.

---

## Two Data Sources, One Picture

Profile Intel merges two perspectives of the same account to get the complete picture.

### Source 1: OAuth (Back-End Data)

This is the data only the account owner can see. It comes from authenticating through the platform's API (starting with Instagram Graph API).

**What we collect:**

- Account-level metrics: follower count, following count, post count, reach, impressions
- Audience demographics: age ranges, gender split, top cities, top countries, active hours
- Per-post performance: reach, impressions, saves, shares, profile visits, follows from post
- Story/Reel insights: completion rate, drop-off points, replay rate, swipe-away rate
- Engagement rate over time (trending up or down)
- Reply rate: what percentage of comments the user responds to
- Reply timing: average time to respond
- DM insights: messages from non-followers (what strangers are reaching out about — this reveals what content is pulling in new audience and what they're asking for)
- Follower growth rate: net new followers per day/week/month
- Unfollower patterns: spikes in unfollows correlated with specific posts

### Source 2: Scraper (Front-End Data)

This is what anyone sees when they visit the profile. It uses the same scraping infrastructure built for Competitor Intelligence, but pointed at the user's own account.

**What we collect:**

- Bio text (what it says, what it doesn't say)
- Profile picture
- Link in bio (where it points, is it optimized)
- Highlight covers and titles (branding consistency)
- Grid aesthetic (visual consistency, thumbnail quality, color patterns)
- Pinned posts (what's pinned and whether it's the right content)
- Recent post captions (hashtag strategy, caption structure, CTA patterns)
- Posting frequency and consistency
- Content mix (reels vs. carousels vs. static posts — ratio analysis)
- Public engagement signals (visible like/comment counts from the outside)

### Why Both Sources Are Required

OAuth alone tells you the numbers but not what someone sees when they land on your page. The scraper alone tells you the surface but not whether it's actually converting. Together:

- OAuth says your profile visits-to-follow rate is 8%. The scraper shows your bio doesn't mention what you do. **That's the connection.**
- OAuth says a specific reel got 10x your normal shares. The frame-by-frame analyzer shows why (hook structure, pacing, visual format). **That's actionable.**
- OAuth shows DMs from non-followers asking the same question. The scraper shows none of your content addresses that topic. **That's your next video.**

---

## The Five Pillars of Profile Intel

Everything Profile Intel does falls into one of these five areas.

### Pillar 1: Profile Optimization

**What it analyzes:** Bio, link in bio, profile picture, highlights, grid aesthetic, pinned posts, content mix ratio.

**What it tells you:**

- Is your bio communicating what you do and who it's for?
- Is your link in bio optimized (direct to offer vs. linktree vs. dead)?
- Do your highlights serve a purpose (social proof, portfolio, FAQ, funnel)?
- Is your grid visually consistent (does it look professional from 6 feet away)?
- Are your pinned posts your best performers or just your most recent?
- Is your content mix right for your niche (reel-heavy niches need 80%+ reels)?

**How it scores:** Profile Optimization Grade (0-100) based on weighted criteria. Each criterion has a specific recommendation if it falls below threshold.

### Pillar 2: Video Analysis

**What it analyzes:** The user's last N videos, run through the same frame-by-frame analysis pipeline and competitor feature set used on competitor videos.

**What it tells you:**

- Per-video grade with breakdown (hook strength, pacing, value delivery, CTA effectiveness, visual quality, text overlay usage)
- Where retention drops (if we have the data from OAuth insights) correlated with what was happening visually at that timestamp
- Which video formats work best for your account (talking head vs. screen demo vs. B-roll montage)
- Hook analysis: are your hooks catching? What's your average hook-through rate vs. competitor average?
- CTA analysis: are your CTAs converting? What percentage actually follow through?
- Storyboard quality: are your videos structured (hook → value → CTA) or rambling?
- Text overlay usage compared to top performers in your niche
- Pacing comparison: are you too fast, too slow, or matching what works?

**How it scores:** Video Messaging Grade (0-100) and Storyboarding Grade (0-100).

### Pillar 3: Audience Intelligence (Your Own)

**What it analyzes:** Comments on your posts, DMs from non-followers, saves/shares patterns, audience demographics from OAuth.

**What it tells you:**

- What your audience is asking for (extracted from comments + DMs)
- What objections your audience raises (from comments)
- What content gets saved (high-value, reference-worthy) vs. shared (identity-signaling, tag-worthy) vs. commented (conversation-starting, controversial)
- Who your audience actually is (demographics) vs. who you think they are
- DM patterns from non-followers: what's pulling strangers in and what they want when they arrive
- Sentiment trends: is audience sentiment improving or declining over time?

**How it scores:** Audience Engagement Grade (0-100) based on engagement rate, reply rate, reply quality, and audience-content alignment.

### Pillar 4: Competitive Positioning

**What it analyzes:** Your performance metrics and content approach compared against your competitor database. This is NOT a competitor dashboard — it's a mirror that shows where you stand.

**What it tells you:**

- How your engagement rate compares to competitor average and top performers
- Which content formats your competitors use that you don't (gaps in your strategy)
- What topics your competitors' audiences care about that your content doesn't address
- Where you outperform competitors (your unfair advantages to double down on)
- Audience overlap signals: what your audience says they want (from your comments/DMs) vs. what competitor audiences respond to (from competitor audience intelligence)
- Content velocity comparison: are you posting enough, too much, or at the wrong times?

**How it scores:** Feeds into overall recommendations. Not a separate grade — this is the comparison lens that sharpens every other pillar's recommendations.

### Pillar 5: Actionable Recommendations

This is the output of everything above, organized by priority and specificity. This is where Profile Intel becomes a coach instead of a dashboard.

**What it delivers:**

**Keep Doing (with evidence):**
- "Your talking-head hook format converts at 2.3x your average. 4 of your top 5 videos use this format. Keep using it."
- "Your reply rate in the first hour is 45% — that's above competitor average (28%). This is driving comment velocity."

**Stop Doing (with evidence):**
- "Static image posts get 12% of your reel engagement. You posted 6 this month. Reallocate to reels or carousels."
- "Your last 3 CTAs were 'follow for more' — this is the weakest CTA type. Your one video with a content-specific CTA got 3x the follows."

**Change (specific, prioritized):**
- HIGH: "Update bio — current bio doesn't mention AI automation. 73% of profile visitors who don't follow leave within 3 seconds. Suggested bio: [specific recommendation]."
- HIGH: "Your average hook is 4.2 seconds before the value statement. Top performers in your niche hit the value in 1.8 seconds. Tighten your hooks."
- MEDIUM: "Pin your top-performing reel (currently your 3rd most recent post is pinned — it's your worst performer this month)."
- LOW: "Highlight covers are inconsistent. 3 use icons, 2 use photos. Pick one style."

**Create Next (content recommendations):**
- "Your audience asked about [topic] 23 times in comments and 8 times in DMs. No competitor has covered this well. This is your next video."
- "Your screen demo format has the highest save rate (4.2%). Create more tutorial-style content."
- "Competitor @handle's video on [topic] got 72K engagement. Your audience has expressed interest in this topic 15 times. Create your version."

**Videos to Remove:**
- "Video [title] — C grade, off-brand for current positioning, lowest engagement in last 30 posts, pulling down your average metrics. Consider archiving."

---

## What Needs to Change from Current Implementation

### Remove

| Item | Why |
|------|-----|
| All loader/spinner components | Pages render structure immediately. No loaders anywhere. |
| Any dashboard-style visualization of competitor data | Profile Intel is about YOU, not a competitor dashboard. Competitor data is used as a comparison lens, not displayed as its own section. |
| Generic psychology labels ("Behavioral Signals", "Positive Psychology") | These are meaningless vanity metrics from the old Audience Psychology Intelligence module. Completely gone. |

### Rebuild

| Item | What Changes |
|------|-------------|
| Data pipeline | Must merge OAuth + scraper data into single ProfileIntelData model. Currently these are not connected. |
| Video analysis | User's own videos must run through the SAME frame-by-frame pipeline used for competitor videos. Not a separate, simpler analysis. Same depth. |
| Audience intelligence | Must extract from user's own comments + DMs, not just competitor comments. Same extraction categories (objections, desires, questions, triggers, gaps) but from YOUR audience. |
| Recommendations engine | Must produce specific, evidence-backed, prioritized recommendations — not generic tips. Every recommendation links to the data that generated it. |
| Competitive comparison | Used as context for recommendations, not as a standalone section. "Your hook rate is 2.1s. Top competitor average is 1.6s." — that lives inside the hook analysis, not in a comparison dashboard. |

### Add (New Capabilities)

| Capability | Description |
|-----------|-------------|
| DM analysis | Read messages from non-followers to understand what strangers are asking/wanting when they find the profile. Requires OAuth permissions for messaging. |
| Multi-platform support | Architecture must support connecting Instagram first, then TikTok, YouTube, etc. Each platform has its own OAuth + scraper pair, but recommendations are unified. |
| Historical tracking | Profile Intel should track your grades over time so you can see if you're improving. "Your Video Messaging grade went from 62 to 78 this month." |
| Content calendar integration | "Create Next" recommendations should be pushable to a content calendar or directly into the UGC Video Studio as a new project. |
| Auto-reanalysis | When new videos are posted or new comments come in, Profile Intel should automatically re-process and update recommendations. Not manual sync. |

---

## 12 Improvements

### 1. Reply Quality Analysis (Not Just Reply Rate)

Reply rate measures IF you reply. Reply quality measures HOW you reply:

- Are you giving one-word responses ("thanks!") or building conversation?
- Are you asking follow-up questions that drive more comments?
- Are you using replies to seed future content? ("Great question — I'll make a video about this")
- Are competitor replies more engaging than yours? What patterns do they use?

A user who replies to 30% of comments with "thanks" is worse off than a user who replies to 15% with genuine engagement. The grade should weight quality over quantity.

### 2. Follower Journey Mapping

The real insight is the journey: did they discover you from a reel → visit profile → follow → DM → become a customer? OAuth can give you "follows from post." DMs give you the conversation. If you can connect these, you can tell the user: "Your screen demo reels are your #1 follower acquisition source. Your talking-head reels get more engagement but fewer new followers." That changes the content strategy.

### 3. Posting Time Optimization

OAuth gives you when your audience is active. Your posting history shows when you actually post. Profile Intel should flag misalignment: "Your audience is most active Tue/Thu 7-9pm EST. You post Mon/Wed/Fri at 2pm EST. You're missing your peak window by 5 hours."

### 4. Caption and Hashtag Analysis

- Which hashtags actually drive discovery (correlate hashtag usage with reach from non-followers via OAuth)
- Caption length vs. engagement (are your long captions performing better or worse?)
- CTA placement in captions (beginning vs. end vs. none)
- Emoji usage patterns compared to top performers

### 5. Save-to-Share Ratio as a Content Strategy Signal

High saves = educational/reference content (people bookmark for later). High shares = identity/social content (people share to signal who they are). Profile Intel should track this ratio and recommend: "Your content is 80% save-heavy. This builds authority but limits viral reach. Mix in more share-worthy content (hot takes, relatable moments, tag-a-friend hooks) to balance growth."

### 6. Audience-to-Content Alignment Score

Compare WHO your audience is (demographics from OAuth) with WHAT your content talks about. If your audience is 65% 25-34 year old males interested in tech, but your last 5 videos were about generic entrepreneurship motivation — there's a misalignment. Profile Intel should flag this.

### 7. Competitor Content Gap Detection

Identify topics your competitor database covers that you don't, AND that your audience has expressed interest in. This is the triple-match: competitor proves the topic works + your audience wants it + you haven't made it yet. That's the highest-confidence content recommendation possible.

### 8. Story and Ephemeral Content Analysis

Track story completion rates, which story types retain attention (polls, questions, behind-the-scenes, product teasers), and story-to-profile-visit conversion.

### 9. Comment Sentiment Velocity

Not just "what's the sentiment" but "how is it changing." If sentiment on your last 5 videos is trending negative while engagement is trending positive, that's a warning sign — you're growing but attracting the wrong audience or creating polarizing content unintentionally.

### 10. Funnel Leakage Detection

View content → Visit profile → Follow → Click link → DM/Convert. Profile Intel should identify where the biggest drop-off is:

- Lots of profile visits but low follow rate: bio/grid problem (Pillar 1)
- Lots of follows but low link clicks: link-in-bio or content isn't driving action (Pillar 1 + 2)
- Lots of engagement but low profile visits: content isn't compelling enough to investigate (Pillar 2)
- Lots of DMs but low conversion: messaging/offer alignment problem

Each leakage point gets a specific fix recommendation.

### 11. Content Cannibalization Detection

If you've posted 3 videos on the same topic and each performed worse than the last, that's topic fatigue. "Topic fatigue detected — your last 3 videos on [topic] show declining engagement (8.2K → 5.1K → 2.3K). Rotate to a different topic or find a fresh angle."

### 12. Collaboration Opportunity Detection

From DM analysis: if other creators (accounts with significant followings) are reaching out, flag these as potential collaboration opportunities and rank them by audience overlap / growth potential.

---

## Page Structure (scrollable single page, NOT tabbed)

1. **Overall Grade + Trend** — Letter grade (A-F) with trend arrow and one-sentence summary
2. **Profile Optimization** — Bio, link, highlights, grid, pins, content mix
3. **Video Grades** — Last 5-10 videos graded individually, expandable
4. **Audience Intelligence** — What YOUR audience wants, asks, objects to, shares, saves
5. **Engagement Analysis** — Reply quality, reply timing, save/share ratios, sentiment trajectory
6. **Competitive Positioning** — Contextual comparison, NOT a dashboard
7. **What's Working** — Evidence-backed
8. **What to Improve** — Prioritized HIGH/MED/LOW
9. **Content Recommendations** — Audience demand + competitor gaps + proven formats
10. **Videos to Consider Removing** — With reasoning
11. **Next Steps** — Top 5 prioritized actions for this week

---

## Data Flow

```
Instagram OAuth API ──┐
                      ├──→ ProfileIntelData ──→ Analysis Engine ──→ Recommendations
Instagram Scraper ────┘                              ↑
                                                     │
                                            Competitor Database
                                            (comparison lens, not display)
                                                     │
                                            Frame-by-Frame Analyzer
                                            (user's own videos, same pipeline)
                                                     │
                                            Audience Intelligence
                                            (user's own comments + DMs)
```

---

## Multi-Platform Architecture

```
ProfileIntelData {
  platforms: [{
    platform: "instagram" | "tiktok" | "youtube" | "twitter"
    oauthConnected: boolean
    scraperConnected: boolean
    lastSynced: timestamp
    platformSpecificData: { ... }
  }]

  unifiedGrades: {
    // Grades computed across all connected platforms
    // Weighted by platform importance to the user
  }

  unifiedRecommendations: {
    // Recommendations that consider all platforms
    // "Your Instagram hook style works — apply it to TikTok too"
  }
}
```

---

## Success Criteria

Profile Intel is successful when a user can:

1. Open the page and immediately know their biggest weakness and how to fix it
2. See exactly which videos to create next and why (with evidence, not vibes)
3. Track their improvement over time (grades trending up)
4. Never wonder "what should I post today" — the answer is always waiting in recommendations
5. Outperform their competitive set because they're making data-driven decisions while competitors are guessing

If Profile Intel requires the user to interpret data themselves, it has failed. The interpretation IS the product.
