# A motion move as a CARD

A move the studio uses twice is written once, as a card, so the next spot looks it up instead of re-deriving it. The
format is video-shotcraft's (152 cards in ten categories, indexed in `gallery/api/library.json` — mine a single card when
a spot needs a move: https://github.com/kingselyjoe/video-shotcraft-dsh, `references/shots/`); the cards here are ours.

```markdown
---
name: <kebab-case>
one-line: <what the viewer sees, in one sentence>
fits: <where it goes — an opening, a data reveal, a transition, an outro>
duration: <N frames at <fps>>
energy: <low | medium | high>
source: <where the move was first seen — a URL, a donor card's path — and the date it was read>
demo: <the composition or render that shipped it>
demo_sha256: <sha256 of that file at the shipped revision>
prompt: <a captured prompt the move was built from, when there is one — verbatim, beside the card>
prompt_sha256: <its sha256>
---
## Intent
<the read it serves — what the viewer must get from it>

## Motion core
<the move as ONE line: `camera = stepTransform.inverse()`, `scale 0.92 → 1.0 over 8 f, ease-out-back 1.4`>

## Parameters
| parameter | typical | how turning it feels |
|---|---|---|
| <name> | <value> | <what more or less of it does to the read> |

## Pitfalls
- <the failure that only shows in one situation — a multi-axis move, a dark background, a 9:16 crop>

## Demo
<the path of a working render or composition that shows it>
```

A card is written after the move has shipped once and survived review, never speculatively; its numbers are the
shipped ones. Pattern: video-shotcraft (`references/shots/camera/basic-3d-scene.md` is typical).

**A card carries its provenance, and the hashes make it checkable.** `source` says where the move came from; `demo`
and `demo_sha256` pin the exact file that shipped it; a move lifted from a captured prompt keeps that prompt verbatim
beside the card with its hash. Before a card is reused, `sha256sum <demo>` must still print `demo_sha256` — a demo
that changed since means the card describes a composition that no longer exists: re-verify the move on the current
file, then re-stamp the hash, or re-point the card. Pattern: cth9191/motion-design `skills/motion-design/assets/presets.json`
(each preset's `source`: the URL, the section, the date observed, the captured prompt's path and SHA-256).
