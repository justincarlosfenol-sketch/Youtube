# 06 — Launch Guide: what you do, step by step

Total hands-on time to launch: **about 3–4 hours**, spread over a few days. After launch: **about 1.5 h per video**.
Nothing here costs money except an optional microphone (~$70–200). I've marked every step that needs an account, a key, or a purchase.

---

## Step 1: Review video #1 (30 min) ⭐ do this first
**Files** (in this repo):
- Video: `videos/001-rent-vs-buy/output/001-rent-vs-buy.mp4` (8:04, 1080p)
- Script with timestamps and sources: `videos/001-rent-vs-buy/SCRIPT.md`
- Thumbnails: `videos/001-rent-vs-buy/output/thumbnails/` (A-number, B-versus, C-chart, plus `_preview-mobile-and-desktop.png`)
- Shorts: `videos/001-rent-vs-buy/output/shorts/short-1..3.mp4`
- Description: `videos/001-rent-vs-buy/output/description.txt`
- QA report: `videos/001-rent-vs-buy/output/qa-report.md`

**What to judge:** Is the cold open gripping? Does every number feel trustworthy? Are any visuals confusing? Tell me in plain words ("chapter 3 drags", "the lever charts are hard to read") and I'll revise. Re-renders take minutes because unchanged shots are cached.

## Step 2: Verify the sources (20 min) — required before publishing
Open `videos/001-rent-vs-buy/sources.yaml`. For each S1–S10, click the URL, confirm the figure matches, and change `verified: false` → `verified: true`. **Why:** this build environment couldn't reach FRED/NAR/Freddie Mac directly, so figures came from indexed releases. A finance channel lives or dies on trust, and the approval tool refuses to proceed until you've done this.

## Step 3: Decide the narration (recommended: your voice)
| Option | Cost | Quality / risk |
|---|---|---|
| **A. You record it (recommended)** | Mic ~$70–200 one-off (e.g. Samson Q2U, Rode PodMic USB) | Strongest protection against the "inauthentic content" policy; builds a recognisable voice; no AI-disclosure label |
| B. Hire a voice actor | ~$100–250 / video | Human and consistent, but recurring cost |
| C. Publish the draft AI voice | $0 | Allowed **with** the synthetic-media disclosure (already set automatically). Higher risk of viewer distrust and policy friction |

**To record (option A):**
```bash
python -m breakeven teleprompter 001-rent-vs-buy   # writes videos/001-rent-vs-buy/voice/TELEPROMPTER.md
# record each line as voice/<line_id>.wav (e.g. voice/s01_l00.wav). Free tools: Audacity (https://www.audacityteam.org/)
python -m breakeven produce 001-rent-vs-buy        # timing, captions, cues and the AI-disclosure flag update automatically
```
Tips: a closet full of clothes is a great booth; keep 15–20 cm from the mic; leave 1 second of silence around each take.

## Step 4: Create the channel (30 min) 🔑 account
1. Sign in at https://www.youtube.com with the Google account that will own the business (a dedicated account is best).
2. Create a channel: https://www.youtube.com/account → **Create a channel** → name **Breakeven**. Pick the handle `@breakeven`, or the first available of: `@breakevenmoney`, `@breakeven.money`, `@runbreakeven`, `@breakevenlab`. Then update `handle:` in `channel.yaml`.
3. **Verify your phone** (required for custom thumbnails and uploads over 15 min): https://www.youtube.com/verify
4. YouTube Studio → **Customization**:
   - Branding → Picture: `brand/assets/avatar-800.png` · Banner: `brand/assets/banner-2560x1440.png` · Watermark: `brand/assets/watermark-150.png` (display: entire video)
   - Basic info → Description: copy from `docs/03-brand-guide.md` ("Channel description") · Links: add the calculator site once live (Step 7)
5. Studio → Settings → Upload defaults: Category **Education**; language English; caption certification "None of the above" (our captions are our own script).

## Step 5: Set up your computer (30 min, one-time)
You need Python 3.11+, FFmpeg and Git.
- **macOS:** `brew install python ffmpeg git` (Homebrew: https://brew.sh)
- **Windows:** install Python from https://www.python.org/downloads/ (tick "Add to PATH"), then `winget install Gyan.FFmpeg Git.Git`
- **Ubuntu/Debian:** `sudo apt install python3 python3-pip ffmpeg git libegl1`

```bash
git clone https://github.com/justincarlosfenol-sketch/Youtube.git breakeven && cd breakeven
python -m pip install -r requirements.txt
python -m breakeven setup          # downloads the open-source voice model (~350 MB)
python -m pytest -q tests          # should print "6 passed"
python -m breakeven produce 001-rent-vs-buy
```

## Step 6: Publish video #1 (20 min)
> ⚠️ **Why manual first:** YouTube locks videos uploaded through *unverified* API projects to private. Until the API audit in Step 9 passes, upload in Studio. Everything is pre-packaged for copy-paste.

1. Studio → **Create → Upload video** → `001-rent-vs-buy.mp4`
2. Title: pick from `output/metadata.json → titles` (recommended: *Rent vs Buy at 7%: The Breakeven Year Nobody Shows You*)
3. Description: paste `output/description.txt`. Thumbnail: `output/thumbnails/A-number.jpg`. Then **Test & Compare** → add `C-chart.jpg` and `B-versus.jpg`.
4. Tags: from `metadata.json → tags`. Audience: **No, not made for kids**.
5. **Altered content:** "Yes" *only if* you published the AI voice (option C); "No" if it's your recorded voice.
6. Subtitles → Upload file → **With timing** → `001-rent-vs-buy.en.srt`
7. End screen (last 20 s): Subscribe element over the left circle, "Best for viewer" video over the right panel.
8. Visibility: **Schedule → Tuesday 10:00 ET**. After it's live, pin the comment from `metadata.yaml → pinned_comment`.
9. Shorts: upload `output/shorts/short-1..3.mp4` on Wed/Fri/Mon (titles in `shorts/*.txt`), and set **Related video** → the flagship.
10. Log the upload so the dashboard links it: create `output/upload.json` → `{"video_id": "<id from the URL>", "thumbnail_id": "A-number"}`

## Step 7: Launch the free calculator site (15 min)
The site is `site/` (static HTML; the calculator is tested against the video's model). Pick one:
- **Netlify Drop (fastest, free):** https://app.netlify.com/drop → drag the `site` folder in → you get a URL.
- **GitHub Pages:** works free on *public* repos (private repos need GitHub Pro). Repo → Settings → Pages → Source: **GitHub Actions**. The workflow `.github/workflows/pages.yml` deploys `site/` on every push to `main`.
- **Custom domain (optional, ~$12/yr):** e.g. `breakeven.money` via Cloudflare Registrar / Namecheap, pointed at Netlify or Pages.

Then put the URL in `channel.yaml → site_url`, run `python -m breakeven qa 001-rent-vs-buy` (the description now has the real link), and add it to the channel's Links.

## Step 8: Owned audience and products (30 min) 🔑 accounts, free tiers
- **Newsletter:** https://www.beehiiv.com (free to 2,500 subs) or https://buttondown.com → put the signup URL in `channel.yaml → newsletter_url`.
- **Digital products:** https://gumroad.com or https://www.lemonsqueezy.com (no monthly fee, % of sales) → list "The Rent vs Buy Model" spreadsheet when ready (I'll build it next) → `models_store_url`.
- **Affiliates:** apply **after** the site has 3–5 calculator pages: https://impact.com and https://www.flexoffers.com (search: high-yield savings, brokerage, budgeting app, mortgage marketplace, term life). Add approved links to `channel.yaml → affiliates`. Disclosures are inserted automatically.

## Step 9: API access for automated uploads and analytics (45 min) 🔑 Google Cloud
1. https://console.cloud.google.com → create project **breakeven-pipeline**.
2. APIs & Services → Library → enable **YouTube Data API v3** and **YouTube Analytics API**.
3. OAuth consent screen → External → app name "Breakeven Pipeline" → add your email as a **test user**.
4. Credentials → Create credentials → **OAuth client ID** → *Desktop app* → download JSON →
   ```bash
   mkdir -p ~/.config/breakeven && mv ~/Downloads/client_secret_*.json ~/.config/breakeven/client_secret.json
   chmod 600 ~/.config/breakeven/client_secret.json
   ```
5. First run of `python -m breakeven analytics pull` opens a browser to grant access; the token is stored in `~/.config/breakeven/token.json` (never in the repo).
6. **Request the API audit** so API uploads can be public: https://support.google.com/youtube/contactus/form (YouTube API Services, Audit and Quota Extension form). Until approved, keep uploading via Studio.
7. Optional keys, both free, stored in `~/.config/breakeven/env` (one per line):
   ```
   FRED_API_KEY=...        # https://fredaccount.stlouisfed.org/apikeys  -> python -m breakeven data refresh
   YOUTUBE_API_KEY=...     # Cloud console -> Credentials -> API key (restrict to YouTube Data API v3) -> python -m breakeven ideas discover
   ```

## Step 10: Weekly operating rhythm (after launch)
| When | Who | What |
|---|---|---|
| Mon | Claude | Next video: research, model, script draft, render → you get a review package |
| Tue 10:00 ET | You (5 min) | Flagship goes live (scheduled). Pin comment |
| Tue–Wed | You (≈1 h) | Review next draft, record narration, approve |
| Wed / Fri / Mon | You (2 min each) | Publish the 3 Shorts |
| Thu | You (2 min) | Community post / poll (text drafted by Claude) |
| Sun | Claude | `analytics pull` → dashboard → weekly report and recommendations |

Commands you'll use: `produce`, `qa`, `approve`, `upload` (after the audit), `analytics pull`, `dashboard`.

---

## What Claude can't do (and why)
- **Log into or operate your YouTube or Google accounts.** You create them and grant API access via OAuth on your machine.
- **Spend money or sign up for services.** All the paid options above are optional and need your go-ahead.
- **Make videos public via the API before the audit passes.** That's YouTube's rule.
- **Reach some data sites from this build environment** (FRED, NAR, Freddie Mac). Inputs were gathered from indexed releases and are flagged for your verification; on your machine, `data refresh` pulls FRED directly.
