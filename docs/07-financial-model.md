# 07 — Financial Model

> **Everything on this page is a projection built from stated assumptions. None of it is an actual result.** The model is in `finance/model.py`; month-by-month output is in `finance/scenarios.csv`. Edit the assumption table in the code and re-run `python finance/model.py` to regenerate this page. Replace assumptions with real numbers from the dashboard as they arrive (from about month 3).

## Setup costs (one-time)
| Item | Cost |
|---|---:|
| USB dynamic microphone (e.g. Samson Q2U / Rode PodMic USB) | $150 |
| Reflection filter / acoustic foam | $50 |
| Domain name (year 1) | $15 |
| **Total** | **$215** |

Everything else in the stack is free or already in place: Python, FFmpeg, skia, Kokoro TTS (open weights), our own fonts/music/graphics, GitHub Pages hosting for the calculator site, and the free tiers of a newsletter tool (e.g. Beehiiv/Buttondown) and digital-product storefront (Gumroad / Lemon Squeezy take a % of sales instead of a fee). **No paid subscriptions are required to launch.**

### Optional paid upgrades (not in the base case; each needs your approval)
| Upgrade | Approx. cost | When it's worth it |
|---|---|---|
| Professional voice actor per video (if you won't narrate) | ~$100–250 / video | Only if you can't record. Human narration is the strongest "authentic content" signal |
| Licensed music library (Epidemic Sound / Artlist) | ~$10–20 / mo | After ~10 videos, if comments mention the music. Our procedural score is owned and safe |
| vidIQ / TubeBuddy | ~$10–50 / mo | When doing keyword research for 10+ ideas a month |
| Custom domain email + newsletter paid tier | ~$0–40 / mo | Past ~2,500 newsletter subscribers |

## Cost per video
- **Cash:** ≈ $0 marginal. Rendering runs locally; data sources are public; all assets are generated.
- **Human time:** about 1.2–2.0 h (script edit, recording narration, final review, approval).
- **Machine time:** about 10–15 min render on a 4-core machine (cached shots re-render in seconds).

## Scenario summary
| Scenario | YPP (8,000 h + 1,000 subs) | Cumulative break-even | First $1k month | First $5k month | Month-12 revenue | Month-24 revenue | Year-1 revenue | Year-2 revenue | Month-24 profit margin |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| conservative | not within 24 mo | not within 24 mo | not within 24 mo | not within 24 mo | $6 | $22 | $39 | $156 | 73% |
| moderate | month 12 | month 13 | month 21 | not within 24 mo | $74 | $2,710 | $418 | $12,794 | 98% |
| optimistic | month 7 | month 6 | month 9 | month 14 | $3,965 | $21,685 | $9,457 | $153,961 | 99% |

## Revenue mix at month 24
| Scenario (month 24) | Ads | Affiliate | Products | Sponsors | Revenue per human hour |
|---|---:|---:|---:|---:|---:|
| conservative | $0 | $13 | $8 | $0 | $2 |
| moderate | $1,109 | $222 | $166 | $1,212 | $417 |
| optimistic | $7,611 | $2,030 | $1,522 | $10,522 | $4,173 |

## How to read this
- **AdSense starts late in every scenario** because of the 8,000-hour YPP bar from Feb 2027. Affiliate and digital products carry year one. This is why the business is designed around them.
- The **conservative** case is a channel that works but stays small. It still covers its (tiny) costs because there are almost no fixed costs. Our real exposure is your time, not cash.
- **Break-even** here means cumulative cash profit ≥ 0 including setup. It doesn't price your time. Revenue per human hour (table above) is the number to watch for that.
- The biggest uncertainties, in order: (1) first-month views per new video (packaging and topic), (2) growth of that number over time, (3) affiliate conversion. The dashboard tracks all three.

## Monetization milestones checklist
- [ ] Month 1: calculator site live, newsletter signup live, first spreadsheet product listed
- [ ] Month 1–2: apply to 2–3 affiliate programs that fit the videos (HYSA, brokerage, budgeting), via Impact/FlexOffers once the site has 5+ calculator pages
- [ ] 500 subs + 3,000 h: expanded YPP (memberships, Super Thanks)
- [ ] ~10k average views per new video: build the media kit (`python -m breakeven` can draft it) and pitch fintech sponsors
- [ ] 1,000 subs + 8,000 h: full YPP (ads)
- [ ] Year 2: licensing outreach (credit unions, benefits platforms), course only if the audience asks

## Assumption table
| Assumption | Conservative | Moderate | Optimistic |
|---|---:|---:|---:|
| `videos_per_month` | 4.33 | 4.33 | 4.33 |
| `v1_views_28d` | 250 | 700 | 1,800 |
| `new_video_growth_mo` | 0.1 | 0.14 | 0.18 |
| `growth_cap_multiple` | 12 | 20 | 30 |
| `tail_share_mo` | 0.08 | 0.12 | 0.15 |
| `shorts_views_per_mo` | 3,000 | 12,000 | 40,000 |
| `avg_view_minutes` | 3.6 | 4.2 | 4.8 |
| `subs_per_view` | 0.01 | 0.014 | 0.02 |
| `ad_rpm` | 6.0 | 10.0 | 15.0 |
| `affiliate_per_1k` | 0.8 | 2.0 | 4.0 |
| `product_per_1k` | 0.5 | 1.5 | 3.0 |
| `sponsor_cpm` | 25 | 40 | 60 |
| `sponsor_min_views` | 10,000 | 10,000 | 10,000 |
| `sponsor_fill` | 0.25 | 0.5 | 0.75 |
| `monthly_tools` | 5 | 25 | 60 |
| `human_hours_per_video` | 2.0 | 1.5 | 1.2 |
