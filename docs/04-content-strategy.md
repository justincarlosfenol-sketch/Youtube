# 04 — Content Strategy (first 90 days)

Calendar and full ranked backlog: [`content/calendar-90d.md`](../content/calendar-90d.md) (generated from [`content/ideas.csv`](../content/ideas.csv), 52 concepts).

## Format mix (decided, with reasons)
- **Long-form is the business.** 13 flagship videos in 90 days (1/week, Tuesday 10:00 ET; finance viewers search on weekday evenings and the first 48 hours of browse traffic land Tue–Thu).
- **Shorts are a funnel.** 3 per flagship (39 total), each a single surprising number with a "full model →" related-video link. Shorts are cut from the flagship's own scenes, so they cost about 10 minutes each.
- **Mix inside the 90 days:** about 80% evergreen/search-driven ("Roth vs Traditional"), about 20% timely with a news hook ("…at 7%", "…when yields are 5%"). Timely titles get refreshed annually.
- **Search vs recommendation:** every flagship needs *both*: a searchable decision ("rent vs buy") **and** a browse hook (a surprising computed number). An idea that is only one of these goes to the bottom of the backlog.

## Series (the shelves of the channel)
| Series | Promise | Example |
|---|---|---|
| **The Breakeven** (flagship, ~60%) | One decision, one model, one crossing point | Rent vs Buy at 7% |
| **Run It Back** (~20%) | History replayed: every start date, every decade | $500/month in every 30-year period since 1928 |
| **The Real Cost** (~10%) | Full lifetime cost of something people underestimate | A dog, a car, a wedding |
| **Paycheck** (~5%) | Career and income decisions, modelled | Grad school ROI |
| **The Money Behind** (~5%) | How the systems around your money work | Who pays for credit-card rewards |

## The repeatable video framework: "Hook → Iceberg → Fair Fight → Race → Levers → Your Numbers"

| Beat | Time | Purpose | Visual signature |
|---|---|---|---|
| **1. Cold open** | 0:00–0:40 | The single most surprising *computed* number, the tension, and the promise ("by the end, you'll know your own breakeven") | Kinetic big number, no logo intro |
| **2. The iceberg** | ~0:40–2:30 | What people usually compare vs what actually matters (hidden costs) | Stacked bar that "sinks" to reveal hidden layers |
| **3. The fair fight** | ~2:30–3:45 | Rules of the comparison and assumptions, each with a source | Assumption cards with source tags |
| **4. The race** | ~3:45–6:00 | The simulation over time; the **breakeven moment** | Two animated lines, crossing marker, freeze frame |
| **5. The levers** | ~6:00–8:30 | Which 3 inputs flip the answer; sensitivity map | Slider animations, heatmap |
| **6. Your numbers** | ~8:30–end | Rules of thumb, the honest caveat, the calculator, next video | Checklist plus end screen (last 20 s) |

**Retention rules:** a visual change at least every 4–6 seconds; a new "open loop" every ~90 seconds ("but there's a number that changes everything — we'll get there"); chapter cards every 1.5–2.5 minutes (they also become YouTube chapters); never more than 20 seconds of narration without a number on screen.

## Packaging system (titles and thumbnails)
- Three title variants per video: **(A) Number-led** ("Buying Loses for 9 Years. Here's the Math"), **(B) Question-led** ("Rent or Buy at 7%? We Found the Breakeven Year"), **(C) Search-led** ("Rent vs Buy Calculator, Explained (2026 Data)"). Publish with the one that best fits search + browse, and A/B the thumbnail with YouTube **Test & Compare**.
- Thumbnail grammar: **one number** (max 4 characters plus unit), **one object** (house, car, piggy, paycheck), **one tension device** (crossing lines, ✕, split screen). Brand colours; the ink-on-paper look stands apart in a feed dominated by red/yellow faces.
- Curiosity without deception: the number in the thumbnail must appear in the video, and the title's promise must be answered before 70% of runtime.

## Turning one video into many (the "model dividend")
1. **3 Shorts** (most surprising number; the twist; one lever).
2. **Calculator page** on the site (SEO + email capture + affiliate).
3. **Newsletter issue**: the model with extra charts.
4. **Spreadsheet product** (the exact model).
5. **Annual refresh** with new data.
6. **Spin-offs** from the comments ("what about with rental income?") become new flagships (e.g. #1 → #43, #44, #50).
7. **Localized variants** (by metro/state) for long-tail search (#50).

## Opportunity discovery system
`python -m breakeven ideas discover` (needs a YouTube Data API key) does the following:
1. Queries YouTube for seed decision phrases ("vs", "worth it", "should I", "breakeven", "calculator") across our topic map.
2. Computes an **outlier ratio** (views ÷ channel's median views) to find topics that over-perform for *small* channels, which signals demand that isn't served by big brands.
3. Scores freshness: high-view topics whose best video is older than 2 years, or built on outdated rates and data, are refresh opportunities.
4. Writes candidates to `content/discovered.csv` for monthly review. Approved ones get added to `ideas.csv` and scored.

Plus three manual signals tracked monthly: viewer comments asking "what about X?", Google Trends seasonality (tax season, open enrollment, new year), and rate/market events (a 50 bp mortgage-rate move triggers the refinance video).

## Prioritization formula
`score = 25% search demand + 20% browse appeal + 20% monetization value + 15% evergreen + 10% data availability + 10% production ease`, with each input rated 1–5 and the result scaled to 0–100. Pins override the score for sequencing (audience coherence first: the first three videos are all housing, so the algorithm learns who our viewer is).
