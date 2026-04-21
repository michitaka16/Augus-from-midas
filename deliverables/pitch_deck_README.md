# GreenLoop Pitch Deck — Week 8

## Overview

`GreenLoop_Pitch_Deck_v2.pptx` is the investor-facing presentation for the Week 8 pitch,
covering the GreenLoop product vision, market opportunity, go-to-market strategy, and Q&A
preparation. It uses the **Forest & Moss** color palette and is delivered in **16:9 widescreen**.

## Deck Specs

| Property | Value |
|----------|-------|
| Slides | 16 |
| Format | 16x9 widescreen |
| Color palette | Forest & Moss |
| Narrative alignment | `01_pitch_storyline.md`, `03_qa_preparation.md` |

## Slide Structure

| # | Title | Content |
|---|-------|---------|
| 1 | Cover | GreenLoop logo, tagline, date |
| 2 | The Problem | Grid outage stats, economic cost of instability |
| 3 | Our Solution | GreenLoop product overview, core value proposition |
| 4 | How It Works | System architecture, real-time dispatch flow |
| 5 | Market Opportunity | TAM/SAM/SOM, regulated market context |
| 6 | Business Model | Revenue streams, pricing tiers |
| 7 | Traction | Current pilots, LOIs, adoption metrics |
| 8 | Competition | Landscape map, GreenLoop differentiators |
| 9 | **Typhoon v2** | **Power outage scenario — the core demo scenario** |
| 10 | Go-to-Market | Channel strategy, pilot-to-contract motion |
| 11 | Team | Founders, advisors, hiring plan |
| 12 | Financials | 3-year projection, key assumptions |
| 13 | The Ask | Funding amount, use of proceeds, milestones |
| 14 | Vision | Long-term roadmap, 5-year picture |
| 15 | Risks & Mitigations | Key risks with mitigation strategies |
| 16 | Closing | Contact, next steps, call to action |

## Slide 9 — Typhoon v2 Scenario

Slide 9 is the **Typhoon v2 power outage scenario** — the primary demo narrative
demonstrating GreenLoop's real-time dispatch during a grid stress event. This slide
shows a simulated typhoon-induced outage with GreenLoop's autonomous response
activating flexible loads and virtual power plants to stabilize the grid without
requiring peaker plant activation.

The Typhoon v2 narrative aligns with:
- `docs/01_pitch_storyline.md` — outage scenario driving home the problem
- `docs/03_qa_preparation.md` — Q&A prep for "how does it handle a real outage?"

## Source Files

The presentation was built from `scripts/generate_pitch_deck.js`. To regenerate:

```bash
node scripts/generate_pitch_deck.js
```

See `scripts/generate_pitch_deck.js` for the generation script and source data.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v1 | — | Initial deck |
| v2 | Week 8 | Added Typhoon v2 scenario (slide 9), updated traction metrics, Forest & Moss palette refresh |
