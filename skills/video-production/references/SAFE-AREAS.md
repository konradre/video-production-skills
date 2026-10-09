# Safe areas — where the platform UI sits over a vertical deliverable

A project's safe area is a PARAMETER, whether or not it has a client: the project declares its target platforms and
their placement (ad or organic) in `delivery-targets.json` at its root (§ The declaration), or declares none. Its band is
the UNION of those targets' keep-outs below — rectangles, not four margins, since TikTok's right rail is a keep-out of
its own. With nothing declared, recommend the strict union of the common vertical ad bands, say what it costs, and the
operator rules (`video-gen-cost-gate` § 0: a constraint guides, it never blocks).

## The keep-outs at 1080×1920 (read 2026-10-09)

| target | top | bottom | left | right | also | source |
|---|---|---|---|---|---|---|
| Meta — Reels, Stories, Feed 9:16 (ads) | 269 | 672 (768 with a disclaimer: 40 %) | 65 | 65 | — | Meta's ads guide: 14 % top, 35 % bottom, 6 % each side (official spec) |
| YouTube — Shorts and every vertical ad | 288 | 672 | 48 | 192 | in-feed the player can compress to 1:1, cropping 420 px off the top and the bottom | Google's vertical safe-zone PNG, measured first-hand (official template) |
| TikTok — In-Feed (ads) | 240 | 660 | 120 | 120 | the right rail, x ≥ 780 for y 840–1260; the band grows with the caption's length and with add-ons (anchors, cards) | TikTok's In-Feed Standard LTR template as measured by a third party (ToolsWebPro, 2026-09); a first-hand read is pending |
| X — vertical video | — | — | — | — | none published (a logo recommendation only) | X's ads specs |

Every number is an AD placement's. Organic overlays are smaller and no platform publishes them: for an organic-only
project, read the platform's current overlay off a live post at 1:1, or keep the ad band.

**The strict union** — top 288, bottom 672, left 120, right 192, plus TikTok's rail — leaves a 768 × 960 box less the
rail's 108 × 408 px notch: about 33 % of the frame (about 29 % where YouTube's 1:1 crop applies). Say that cost when
recommending it; a project that runs on one platform takes that platform's row, not the union.

Other rasters scale by the short side ÷ 1080 (×2 on the 2160×3840 mezzanine). The numbers move when an app redesigns:
re-read the templates when this table is older than about six months, or when a platform announces a new layout.

## The declaration

```json
{"targets": ["meta:ad", "tiktok:ad", "youtube:organic"], "conditions": ["meta-disclaimer"], "keep_out": []}
```

- `targets` — `<platform>:<placement>`, platform `meta` · `youtube` · `tiktok` · `x`, placement `ad` · `organic`.
  `[]` declares no platform UI (a festival cut, a site loop): no zone is read. An organic target with no published
  overlay takes its ad row, and the tool says so.
- `conditions` — `meta-disclaimer` (Meta's bottom band grows to 768 px) · `youtube-1to1` (YouTube's in-feed compression
  to 1:1: a 420 px top band).
- `keep_out` — the project's own measured keep-outs as zones (an organic overlay read off a live post at 1:1, a client's
  spec, another aspect's numbers); when present they replace the table.

It is written at intake (`video-production` § 1), at the project root — the directory holding `.claude/skill-gate.json`,
`RESUME.md` or `.git` — or in the compositions' root. `scripts/safe_zones.py --from <dir>` resolves it: it searches from
`<dir>` up to that root, never from `$HOME` or above, and with no root found only `<dir>` and two parents, so a file in a
shared parent never sets every project's band. It prints the zones and one SAFE BAND line naming the file it used.

## Checking it

- **A designed composition** — `designed-elements` `render_hyper.sh` reads the band before every render with
  `safe_zones.py` and runs `hyperframes check --caption-zone` once per zone, report-only: the bottom and top bands, each
  rail, and the side margins as strips between the bands — the strict union is five zones: bottom `x0=0;y0=0.65;x1=1;y1=1`,
  top `x0=0;y0=0;x1=1;y1=0.15`, TikTok's rail `x0=0.7222;y0=0.4375;x1=1;y1=0.6563`, right `x0=0.8222;y0=0.15;x1=1;y1=0.65`,
  left `x0=0;y0=0.15;x1=0.1112;y1=0.65`. With no declaration it reads the strict union and says so; `--keep-out "<zone>"`
  adds a zone. The first run carries the full report and runs alone, the other zones run at once (about 40 s for a short
  card on the render host), sampled once a second and never at fewer than 11 points. A zone flags an element CENTRED in
  it at a sampled time, as a WARNING — the report's `ok` stays true, so read the summary's ZONE lines, never the verdict.
  It reads TEXT elements only, by the centre of each box (hyperframes 0.8.18), so three things pass it: an image in a
  band (a logo, a pack shot), text that straddles the zone's edge with its centre outside, and text marked
  `data-layout-allow-caption-zone` (exempt with its children — put it only on copy the declared band allows). A
  composition with a lint error is never laid out, so the zone read is blind until the lint is fixed.
- **Burned-in captions** are text and sit inside the band too. `spot-audio-assembly` `build_captions.py` centres the
  block at `y: 0.70` (1344 px) by default — inside every ad band above; set the campaign's `caption_style.y` so the whole
  block clears the declared band, and check its WIDTH where a rail sits: under the strict union a block centred on the
  frame fits 696 px between y 288 and 840, but only 480 px between 840 and 1248, beside TikTok's rail — keep a block in
  those rows that narrow, or set it above y 840.
- **Everything else** (an end card over footage, a delivered spot) — read the delivered frames at every text beat and
  on the end card with the band painted on them, at 1:1: `ffmpeg … -vf "$(safe_zones.py --from <project> --drawbox
  1080x1920)"`. This read also catches what the zone check passes — images in a band and straddling text.

## Evidence

- The house figures this table replaces disagreed with each other: a 0.78 content wrap (~230 px clear at the bottom),
  250/350 in the ad pre-production spec, and 150/350/right 10 % in the finish pipeline's delivery spec.
