# The story method for a short — what transfers from feature screenwriting, and what does not

The feature corpus (Truby, Weiland, Snyder, Vogler, Pratt) assumes ~120 pages; nothing in it handles
a short. Four of its assets transfer once the unit changes from pages to seconds.

## 1. Write the self-revelation FIRST, derive everything backward (Truby END-FIRST)

"Start by determining the self-revelation, at the end of the story; then go back to the beginning and
figure out your hero's need and desire." One paragraph — what she understands, and what she does
with it — written before any beat; every beat is then setup or consequence of it. The paired
anti-pattern is *Verdict*: a self-revelation at 25 % removes the hero's moral jeopardy for the rest of
the film → **hold it to 90 %**.

## 2. The character machinery — Weiland's four-slot schema

```yaml
lie:   one sentence — the misconception about self or the world
want:  external, physical; salves the Lie's symptoms
need:  internal; the Truth that is the antidote to the Lie
ghost: the past wound that caused belief in the Lie (may be null — but stated)
```

Arc taxonomy with canonical state chains — pick one and keep the chain in the beats:

| arc | chain |
|---|---|
| Positive Change | BELIEVES LIE → ENCOUNTERS TRUTH → RESISTS → ACCEPTS → ACTS ON TRUTH → REJECTS LIE |
| Flat | BELIEVES TRUTH → TESTED → HOLDS → TRANSFORMS WORLD |
| **Disillusionment** | BELIEVES LIE → OVERCOMES LIE → NEW TRUTH IS TRAGIC — *structurally identical to Positive, the Truth's polarity negative*: an un-sanitised ending costs nothing structurally |
| Fall | BELIEVES LIE → CLINGS → REJECTS TRUTH → BELIEVES WORSE LIE |
| Corruption | SEES TRUTH → REJECTS TRUTH → EMBRACES LIE |

The **3-question classifier** (genre wants positive or negative change? · starts in a good place with
the Truth or a bad place with the Lie? · ends in a better Truth, a darker Truth wiser, or a worse Lie?)
names the arc; `arc_check.py` refuses a beat sheet whose answers and arc disagree.

**The arc-delta double-check**: the same action at 0:00 and at the climax with the motive inverted
(she lights the lamp because she loves it; she lights it knowing what it does). If the two actions are
not the same action, the arc is asserted, not shown.

## 3. Cast — a two-hander

The opponent doubles as the Impact Character. Four-corner opposition (hero + main opponent + two
secondary, all in value conflict) is right for a feature and fragments attention under six minutes.
Two to four lines of dialogue for the whole film is normal; the revelation is never spoken.

## 4. The beat sheet — Truby's 7-step DNA on Pratt's percentage axis, in seconds

`beat_second = ceil(total_seconds × pct/100)` (`beat_calc.py`). The seven steps are the organic
nucleus; the 22-step spine is a checklist to confirm nothing structural is missing, never a
structure (22 steps across 5 minutes is a shot list with delusions).

| % | step | role |
|---|---|---|
| 0 | Weakness & Need | the Characteristic Moment — sympathy FIRST (points 6–7 of Weiland's first-scene checklist), then the flaw (point 10 hints at the Lie); the order is load-bearing |
| 12 | Desire | the wish is made |
| 25 | Opponent | the world stops enabling the Lie |
| 50 | Plan | reaction flips to action |
| 75 | Battle | the ultimate Want-vs-Need choice, in the smallest space |
| 90 | SELF-REVELATION | the anagnorisis — one face, no dialogue, the held close-up |
| 95 | New Equilibrium | what the choice costs; the final image |

**Every beat carries a subworld** (Truby's Visual Seven Steps): a physical expression of the
character's state — the enslaving world, the boundary crossed, the opponent's world of power, the
road out, the smallest space, the same street now unbearable. Build environments before shots
(Anderson's own method, and the generative pipeline's hardest problem is continuity between them).

## 5. What does NOT transfer

The 22-step spine as structure · four-corner opposition · the agent-pipeline software of the corpus
(use the methodology, not the tooling) · the industry critique layer (useful later as a critique pass,
irrelevant to locking a premise).
