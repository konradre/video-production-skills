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
