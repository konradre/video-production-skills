# The style brief — the template, the check, and where a look may come from

CRAFT § Style comes from the subject says to write the style down before any composition exists and to get it approved
with the scene plan. This file is the form that writing takes: eleven fixed sections, a machine-readable block that
`scripts/style_brief_check.py` reads, and the rule for where a style may be derived from. A worked brief for an invented
subject: [`STYLE-BRIEF-EXAMPLE.md`](STYLE-BRIEF-EXAMPLE.md). The section shape follows a published film-style library's
schema (provenance in [`STYLE-CATALOGUE.md`](STYLE-CATALOGUE.md)), cut to what a designed element over footage needs.

Save it in the project as `style-brief.md`, beside the scene plan. One brief per subject: a campaign's spots share their
brief, and a new subject gets a new one.

## Where a look may come from — the subject, never a base

**The brief is written from the subject.** Its palette comes from the subject's own artefacts, its display face is chosen
for the subject's character, and its background language and motion signature come from a menu, chosen for this subject
and different from the last build. Three sources are never a base:

- **the last build, or any other subject's brief** — the self-repetition CRAFT measured (a second product shipped wearing
  the first product's skin);
- **a style in the catalogue** — [`STYLE-CATALOGUE.md`](STYLE-CATALOGUE.md) is for recognition and grammar: its entries
  name the neighbours a brief must stay clear of (§ 1), and its camera rows and native moves are moves a brief may
  borrow (§ 6, § 8). An entry's palette, its typefaces and its demo's choices are never taken;
- **a reference the operator sent** — it gives rhythm, never skin (CRAFT).

**A medium is not a base.** When the operator or the client names a medium (a risograph print, an ink wash, a paper
cut-out), § 2 takes that medium's physical rules and says who asked for it, and the catalogue entry tells you what its
frames must show. The palette, the typefaces, the motion signature and every choice its demo made still come from the
subject. A medium nobody named is chosen from the subject, like everything else.

**The one derivation allowed is from this subject's own accepted brief:** a later round, a new season or a second product
in the same campaign changes that brief through the creative checkpoint's change steps (`ad-spot-preprod` § 6), a
CHANGES table at most five rows long. A change to § 1 or § 10 is not a change: it is a new brief, written from the
subject.

## The eleven sections

Fixed numbers and names, in this order; the checker reads them as `## 1. Essence, and what it is not` … `## 11.
Variation space`. Every section carries content. A section that does not apply says why in one line, which still counts
as content.

| § | Section | What it holds | The rule it carries |
|---|---|---|---|
| 1 | Essence, and what it is not | The subject and three adjectives for the feeling to leave behind; the three to five traits that make a frame read as this piece in one glance; then **the neighbours it must not drift into**, each with the line between them. | ≥ 2 named neighbours; the last build is always one. Name catalogue styles by their catalogue name. |
| 2 | Materials and rendering | The surfaces and how they are drawn; the background language from the menu below; what is anchored to the world and what lives in screen space; where every asset comes from. | One background language (two only when the background changes with a chapter). Assets cut from the subject's own art (CRAFT § Assets). |
| 3 | Colour logic | Rules before swatches: how many hues, the neutral, what the accent is reserved for, what is never coloured; then the palette in hex and where each colour was read. | Palette sourced from the subject's own artefacts. A starter's colour surviving is a style never derived. |
| 4 | Type and captions | The display face and why it fits, the text face, each role with a size range against the legibility floor, how captions sit in this world. | The display face is chosen for character, never the first grotesk that renders. Readable time and the floors: CRAFT. |
| 5 | Motion quality | The motion signature — the move that repeats as identity — with its easing in numbers; the stepping (on ones, twos); what never moves. | Easing as a curve or a number, never an adjective ("`cubic-bezier(0.34,1.56,0.64,1)`, stagger 2–4 frames", not "bouncy"). |
| 6 | Camera grammar | A table: move → what it expresses → what it can serve. Three to six rows. No row names "the opening move". | The camera's order inside a scene and its half of a cut: `explainer-video` STORYBOARD. |
| 7 | Sound palette | The instruments and foley materials, the one wet timbre against a dry palette if there is one, what a silence may contain. | `spot-audio-assembly` § Sound direction owns placement, suck-outs and the silence counts; this section names the palette only. |
| 8 | Native moves | The special moment — the one place the most expensive effect is spent, once — and two to four moves this piece does well, each with **"fits content like:"** and examples unlike this job. | One special moment. A move borrowed from the catalogue is written in this subject's terms, never pasted. |
| 9 | Pitfalls of the medium | What breaks this look in our renderer, each with its fix. | The determinism traps: HYPERFRAMES-CONTRACT § Silent traps. |
| 10 | Renderer | The render class (below) and anything it needs installed. One line is normal. | Our lane is HyperFrames: Canvas 2D or DOM / SVG, or a WebGL pass under `det_check.py`'s software-rasteriser tolerance. A three.js scene has no determinism proof in this lane yet: prove it and get it ruled before the build. An offline renderer is outside the lane. |
| 11 | Variation space | What each spot or version decides (structure, opening, ending, copy, pacing) against what this brief fixes. | Everything not fixed here is free per spot and needs no change to the brief. |

## The machine block

One fenced block tagged `style-brief`, anywhere in the file (after the title is usual). One `key: value` per line;
lists are comma-separated.

```style-brief
subject: <what the piece fronts>
adjectives: <three words>
not: <neighbour>, <neighbour>[, …]
palette: #RRGGBB, #RRGGBB[, …]
palette_source: <the artefacts each colour was read from>
display_face: <family name>
background: <menu id>[, <menu id>]
transitions: <menu id>, <menu id>[, …]
motion_signature: <the repeating move, in one line, with its numbers>
special_moment: <where the most expensive effect is spent, once>
render: canvas-2d | dom-svg | webgl-pass | webgl-3d
```

**Background language — one id** (two only when the background changes with a chapter). The menu is CRAFT § Background
motion and transitions, in its order:

| id | the background |
|---|---|
| `still-ground` | a still textured ground with only the camera breathing |
| `gradient-drift` | a large gradient drifting or rotating slowly |
| `blob-drift` | two to four blurred colour blobs adrift |
| `living-texture` | a living grain or paper texture offset from the timeline |
| `light-sweep` | one light sweep per chapter, not a continuous one |
| `form-turn` | a large geometric shape from the subject's own form turning over 20–40 s in two parallax layers |
| `particles-rising` | particles rising |
| `pattern-breathing` | a grid or pattern breathing 1.0 ↔ 1.04 |
| `ghost-type` | giant ghost type sliding behind at low contrast |
| `image-push` | a themed image under a Ken Burns push with two parallax layers |
| `flow` | horizontal flow — streaks, lanes, rain — only when the subject genuinely is speed or flow |

**Transitions — at least two kinds, at least one with real depth** (`object-wipe` or `push`), from CRAFT's hierarchy;
the camera's breath runs under all of them and is not listed:

| id | the transition |
|---|---|
| `overlap` | overlapping choreography — the old scene's elements leave as the new one's arrive |
| `object-wipe` | an object wipe with thickness passing close to the lens |
| `push` | a motivated push — into a screen, through an aperture |

**Render class:** `canvas-2d`, `dom-svg`, `webgl-pass` (a shader pass over a 2D page), or `webgl-3d` (a three.js scene —
unvalidated here, so it WARNs).

## The check

```bash
python3 ~/.claude/skills/designed-elements/scripts/style_brief_check.py style-brief.md
python3 ~/.claude/skills/designed-elements/scripts/style_brief_check.py style-brief.md --prev ../<last project>/style-brief.md
```

It FAILs (exit 1) on: a missing, misnumbered or empty section; no `style-brief` block, or a key missing or empty; fewer
than two neighbours (punctuation is not a neighbour); three adjectives not given; a palette token that is not
`#RRGGBB`, or no colour at all (one is legal: a single-ink title); a display face that is the scaffold's placeholder
(`Display`) or a CSS generic family (a `generic(…)` form included); a background or transition id not on the menu; transitions with fewer than two
kinds or none with depth; a render class outside the lane. It WARNs on a palette colour equal to a colour `hyper_new.py`
writes into its scaffold (pure white and black aside) — confirm it was read on the subject — and on `webgl-3d`. Fences
follow CommonMark: a heading or a `style-brief` block quoted inside another fence is text, an empty fence is not
content, and an HTML comment block (a line that begins with `<!--`, through the first `-->`) is neither content nor a
place for the block; a `<!--` anywhere else is text.

`--prev` compares against the **last build's** brief, for another subject; a version of the same campaign keeps its brief
and changes it through `ad-spot-preprod` § 6 instead. It FAILs when the background repeats the last build's, when the
transitions are the same set, or when the two briefs share two or more of the four differentiators (CRAFT: two subjects
differ in at least three of four, so sharing two is already one too many):

| differentiator | shared when | how exact |
|---|---|---|
| palette | at least half this brief's colours lie within ΔE\*ab 10 (CIE76, in Lab) of a last-build colour | exact on the numbers; a near-identical palette counts as shared |
| display face | the same family, case and spacing ignored | exact |
| background language | an id in common | exact |
| motion signature | the two lines share at least half their content words (Jaccard on words of four letters or more) | **a word-overlap heuristic**: a reworded signature can pass. The check prints both lines on every run; read them. |

Exit 0 passes (WARNs are answered beside the brief); 2 is a usage error, an unreadable or undecodable file, or a
`--prev` brief whose block fails the same field validation — unusable data never counts as differing. `--selftest` runs its
fixtures, checks the worked example passes, and checks the two menus above match the script's.
