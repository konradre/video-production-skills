# The round protocol — from the client's notes to the next version

```
notes (verbatim, dated, numbered by DELIVERY order)
  → locate every cited beat in the DELIVERED file, the EDL history and the script
  → curate the numbered list — NO action — classified in the client's own words; each note ERROR or TASTE, anchored;
    every ERROR's check row (the check that missed it, or a proposed one)
  → the operator answers per item (a number, a yes/no, "best judgement", "the original", "regen")
  → execute by the ladder: cut → recycle → re-voice + build the alternative → regen last
  → a NEW version from a NEW EDL (shipped EDLs untouched); approved spots frozen; alternates as extra assets;
    every note answered by its number in the round record
  → QC on the delivered file → the compare page (N against N−1, lined up by event) → the ask (numbered, costed, pathed;
    the notes answered by number; the checks read from the run log) → the operator sends → wait
```

## Receive

- The notes are saved verbatim, dated, with the client's numbering mapped to spot ids (**client
  numbering = delivery order**: "#5" is the fifth file delivered). A note relayed by voice or chat is
  written down the same way.
- Approvals are quoted into the ledger in the client's words ("looks solid", "keep this version exactly
  as is") — an approved spot **freezes**; a later idea for it becomes an ALTERNATE asset (an alternate
  ending clip beside the untouched approved version).
- The operator sends and receives; the agent never contacts the client.

## Locate before anything

The client's script is read end to end FIRST — before any measurement of the delivered file; it contained, on one
rebuild, the exact direction the client later said was missing and a held beat an audit had logged as a defect.
Every cited beat is found in the delivered file (frame time), in the EDL history (which version
introduced it) AND in the script — the client may be pointing back at the script's original idea, and
a note's noun can refer to a different object than the one you assume. A note that names a version is
checked against that file, not the current one. A note about a break or a join names a seam between two
generations: it is never carried into the review of ONE generation, where a cut the model composed is a
capability and consistency across it is the read (`video-take-review` § 3).

A note about a SOUND at a timecode is located the same way a frame is: transcribe the DELIVERED file around the timecode
and quote back what is heard before anything changes. Spoken filler with no picture reads as a voice-over line; a fix
inferred from word times trimmed the wrong thing once (2026-09-15).

## Classify in the client's own words

| class | the client says | what it means for the build |
|---|---|---|
| **CUT** | "no regeneration needed, just cut it" · "a few cuts" · "holds too long" | an edit-only change on the existing keeper (`video-edit-edl`): a trim, a re-order, a drop |
| **RECYCLE** | "keep the scene from the original clip" · "the version we had at first" | a shot from an older version, into a new EDL |
| **REBUILD** | "rebuild the flow" · "tweak the appearance" | a regeneration — last on the ladder, ONE generation per continuity partition, through the cost line; its structure comes from the SCRIPT (`ad-spot-preprod` § 4), never from the rejected cut's scene boundaries |
| **CAUSALITY** | "both shots work individually, but one doesn't cause the other… one continuous joke" | a rejection of the METHOD, not a shot: chain the beats (action → consequence → payoff) with the take's own footage first, one connecting gen last |
| **APPROVE** | "exactly as they are" · "I'm good with this version" | quoted; frozen |
| **GATE** | "the product looks huge compared to the real one" · "does that person look like…" | a pre-production gate from now on (`ad-spot-preprod`: true-size framing, the likeness check) |

The client's **domain expertise defines what lands** for their audience — the original script gag is
restored, not argued. The client's **wording is exact** and the operator sets the diction. Where the
client separates what must be perfect from what may be loose, the shape rule is enforced where the
object is STILL and VISIBLE.

## Error or taste — and the check that missed it

Sort each note on one more axis beside its class. An **ERROR** is objectively wrong whatever anyone likes: elements
misaligned or overlapping, text cut off or touching the frame edge, a misspelled name, a wrong number or price, a click,
a pop, clipping, a black or frozen frame, sound out of sync, the wrong size or aspect. **TASTE** is colour, pace, music,
wording, feel. Fix both.

An ERROR that reached the client got past every check we ran, so the round records the check that would have caught it —
now, while the note is fresh, never weeks later in a retrospective:

| the check row | when |
|---|---|
| `{"existing": "<the check>", "missed": "<why it passed this>"}` | a check ran and passed the defect — a threshold, a blind spot, a sample that missed the frame |
| `{"propose": "<what it is>", "how": "<what it measures, on what>", "owner": "<skill>"}` | no check looks at this; the note is its example |

A proposal becomes a `pending` row of the fold table (SKILL.md § 3) and lands in the owning skill only through that skill's
next reviewed change.
Never write it into an installed copy of a skill: an installed copy is replaced whole at the next update, and the proposal
goes with it.

## Anchor every note

Every note points at what it is about, in the version the client saw:

| anchor | points at |
|---|---|
| `{"at": 41.0}` | a moment — seconds in the delivered file |
| `{"from": 12.0, "to": 20.0}` | a stretch ("it drags from 0:12 to 0:20") |
| `{"at": 41.0, "x": 0.85, "y": 0.15, "estimate": true}` | a spot on the frame, as fractions of the width and height from the top left; read off a frame, it is an estimate and is said as one when the notes are read back |
| `{"paragraph": 3}` | a paragraph of the script |
| `{"whole": true}` | the whole version (an approval, "too busy overall") |

The anchor is the spot § Locate before anything found — the delivered file, the EDL history, the script — never a guess
from the words. `notes_triage.py` reads a timecode in the words as a first anchor (`from_text`), never an aspect ratio
such as 9:16; confirm it against the file.

## The round record — every note answered by its number

`notes_triage.py --out prompts/CLIENT-ROUND-<date>.md` writes `prompts/CLIENT-ROUND-<date>.json` beside the list and never
overwrites it: it collects the round's answers. Per note: `n` (its number in the list), `spot` (`*` for a note on every
spot — answered once, shown in every spot's ask), `class`, `kind` (`ERROR` ·
`TASTE`; `?` until sorted; none on an approval), `words` (verbatim), `anchor`, `check` (an ERROR's row), `decision` (the
operator's answer to the item), and `answer`, written once the new version settles:

| `answer.status` | needs |
|---|---|
| `done` | `change` — exactly what changed and where ("the price corrected to $1,250, 0:39–0:44"), never "addressed" |
| `partly` · `not_done` | `why`, and `change` for whatever did move |
| `frozen` | `why` — the spot is approved and stays; a new idea for it becomes an alternate asset |

An approval starts anchored to the whole version and answered `frozen`. A paragraph that is no note — a greeting, a
thank-you, a sign-off — is `class: "CHAT"`: no spot, no kind, no answer; the ask and the compare page skip it. The ask prints every note with its answer
(`delivery_ask.py --round`) and refuses while a note has no anchor, a kind still `?`, an ERROR with no check row, or no
answer. "Not done, because …" is an answer: the refusal only ever asks for the truth to be written down.

## The ladder

1. **Cut** — frame-exact in/out, a re-time, a drop, a swap from an older version: zero credits, minutes.
2. **Re-voice the same words** when a line "lands flat" (delivery is the note) AND build the
   client's alternative line in the same slots; both go back.
3. **Recycle** the older version's shot (a new EDL; the shipped EDL untouched).
4. **Regen** — last; the approved cut frozen; alternate assets from the same prompt skeleton (only the
   event script changes), one continuous shot, the fewest seeds the cost line allows.

Quip assignment is a **fit pass** scored against each spot's gag before VO is generated (a table goes
stale); the sign-off copy loop caps at five candidates, then tighter variants of the operator's own line.

**Every note set names what to KEEP.** A fix note constrains one defect; a set of them with nothing protecting what
the previous version got right flattens the piece — the brand system, each spot's hook and the concept's device all
went in one round that landed its five fixes (2026-09-15). Beside each fix, the guard: what stays.

## A UGC / creator-style spot in the round

Two more locates before anything moves. The **disclosure state** of the delivered version — the on-creative line and
overlay, the platform's paid-partnership or commercial-content setting, the AI label (`ad-spot-preprod` RISKS.md § UGC
compliance) — is read and written down beside the note, because a "small fix" can change it: a dub, a lipsync pass or a
face repair on a REAL creator's take moves the asset from the creator path to the AI path, and the round's ask says so.
And the **persona line**: a note that the spot "feels like an ad" or "feels fake" is read against UGC-GRAMMAR.md § Where
lo-fi wins and § The hook before any regen — the fix is usually the open, the light or the delivery, not the model. A new
version re-sets what the platforms reset: TikTok's AI-content toggle clears on every campaign duplicate; a re-encode
strips Content Credentials; the finish checklist carries both.
