# Competitor Intelligence Platform — Execution Plan

Full spec provided by Eddy on 2026-03-25. This is the canonical reference for all sub-agents.

## Navigation (Before → After)

Before: Competitors | Top Content | Hooks | Scripts | Creator Directives | Profile Intel | Video Analytics
After: Competitors | Top Content | Hooks | Scripts | Profile Intel

- Creator Directives → moved to per-video detail page (tab)
- Video Analytics → moved to per-video detail page (tab)  
- Audience Psychology Intelligence → killed, rebuilt as actionable data layer

## New Routes

| Route | Description |
|-------|-------------|
| /competitor-intelligence/top-content | Redesigned horizontal card list |
| /competitor-intelligence/top-content/:videoId | New video detail page with tabs |
| /competitor-intelligence/top-content/:videoId/transcript | Tab: Timestamped transcript + storyboard |
| /competitor-intelligence/top-content/:videoId/creator-directives | Tab: CDR for this video |
| /competitor-intelligence/top-content/:videoId/video-analytics | Tab: Analytics for this video |
| /competitor-intelligence/profile-intel | Rebuilt recommendation engine page |

## CRITICAL RULES FOR ALL SUB-AGENTS

1. Before writing any code, query the context system. Understand what exists.
2. No isolated state. Use shared data models.
3. No loaders. Pages render structure immediately.
4. No fake metrics. Document formula or remove.
5. Every component declares: what it consumes, what it produces, what it renders.
6. Runtime format is M:SS. Stored as integer seconds. No decimals.
7. Test with real data. No mock data demos.
8. Use context system and perfect recall.
