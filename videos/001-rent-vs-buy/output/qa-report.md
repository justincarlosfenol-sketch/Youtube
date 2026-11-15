# QA report

**0 errors, 4 warnings**

| | Check | Result |
|---|---|---|
| ✅ | resolution | 1920x1080 |
| ✅ | frame rate | 30.00 fps |
| ✅ | codec | h264 yuv420p |
| ✅ | audio codec | aac 48000 Hz |
| ✅ | duration | 484.2s file vs 484.2s timeline |
| ✅ | mid-roll eligible | 8.07 min (mid-roll ads need 8:00+) |
| ✅ | loudness | -14.5 LUFS integrated (target -14) |
| ✅ | true peak | -1.3 dBFS (max -1.0) |
| ✅ | black frames | 0 black segments >1s |
| ✅ | captions | 119 cues; 0 with a line >42 chars; 0 with >2 lines |
| ✅ | data binding | 0 unresolved template tokens |
| ✅ | sources exist | cited 11 source ids; missing: [] |
| ⚠️ | sources verified | unverified (human must open & confirm): ['S1', 'S10', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9'] |
| ⚠️ | numbers sourced | lines with numbers but no source id: ['s18_l02'] |
| ✅ | banned claims | matches: [] |
| ✅ | title length | 54 chars: Rent vs Buy at 7%: The Breakeven Year Nobody Shows You |
| ✅ | title length | 69 chars: Your Mortgage Costs the Same as Rent. Buying Still Loses for 9 Years. |
| ✅ | title length | 59 chars: Renting vs Buying at 7% Mortgage Rates (We Ran the Numbers) |
| ✅ | description length | 4512 chars |
| ✅ | chapters | 7 chapters, first at 0:00, min gap 43s |
| ✅ | tags | 12 tags, 272/500 chars |
| ⚠️ | links | calculator link placeholder still in description (set site_url in channel.yaml) |
| ✅ | thumbnail | A-number: 1280x720, 103 KB |
| ✅ | thumbnail | B-versus: 1280x720, 116 KB |
| ✅ | thumbnail | C-chart: 1280x720, 111 KB |
| ⚠️ | voice | Synthetic (TTS) narration present: the altered/synthetic disclosure will be set and the description says so. Recommended: record human narration (python -m breakeven teleprompter <slug>). |
