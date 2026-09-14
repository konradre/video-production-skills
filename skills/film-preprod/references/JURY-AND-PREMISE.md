# Whoever judges the film decides the veto map — then the premise is chosen twice

## 1. Derive the veto map from the judges (or the audience, or the client)

Research each judge's own work and stated taste; find the archetype their careers converge on, and
the one beat that resolves it (for one panel: the ego that discovers its world was authored and must
choose meaning anyway — the anagnorisis, resolved to a single shot: a face under a push-in whose
speed the performance dictates). Then write **two tables before anything is generated**:

- **the veto map** — vetoes are asymmetric: one strong aversion outweighs three mild positives; treat
  the column as constraints, not preferences (a tech demo with a thin story · over-lighting, hard
  backlight, showy camera, nothing to cut to · exposition that explains the mystery, irony, smugness ·
  a sanitised resolution · any screening failure);
- **the compliance table** against the rule set (runtime floor, aspect, subtitles, watermark, no real
  likeness, no political/religious statement, all-AI audio, on-platform generation) — each row ✅ / ⚠ /
  ⬜ with where it is enforced.

The convergence claim is a synthesis — no judge says "here is what I would reward" — so it is
recorded as the method's own inference, and the vetoes (which ARE sourced) carry the weight.

## 2. Blind competitor premises

Generate N alternatives with a **different model family**, each run receiving the identical brief
(the judge dossiers, the archetype, the veto map, the prohibitions, the production limits) and **one
assigned divergence axis** (domestic with no fantastical element · landscape and season · work and
machinery · an invented tradition · the one speculative run) — a single prompt asking for five ideas
returns five variations of one idea. Ban the default metaphors as literal elements; cap the laziest
route (amnesia / simulation / false reality) at one run — it reads as derivative to exactly the judges
who made those films. Do not feed the runs your own premise.

Read the set for what it settles: when three of five resolve to the same shape, they corroborate the
archetype AND they are not alternatives to each other — compare only the materially different bets.

## 3. Rank twice — story and execution — and let them disagree

**Premise selection is a pipeline decision, not only a creative one.** Rank the candidates on how
likely each is to survive the pipeline, separately from which is the best film:

- a world already understood to be made of paint absorbs texture crawl, reconstituting edges and
  over-smooth surfaces as diegetic behaviour; a domestic-realism premise has the tightest error bars
  that exist (everyone is an expert on kitchens and old hands) and may need legible handwriting;
- night with one motivated source is the most forgiving lighting; landscape is where the models are
  strongest; repetitive mechanical motion, water, animals, scale relationships and layered voices
  resolving into a younger self are live risks;
- the hero shot needs a real fallback (two clips cut on a caught breath) or the premise is exposed.

`premise_rank.py` prints both rankings; when they disagree, **the disagreement IS the decision** and
goes to the operator as such ("most likely to be executed well is not the same as most likely to
win"). Record each premise's objection (a premise about an AI authoring a world, submitted to an AI
company's festival, trips a judge's "don't editorialise about AI" veto) beside its rank.

## 4. Lock, then publish

When a contest rewards early publication AND binds continuity, lock the premise first (a day of
work), then publish; never publish a placeholder to reserve a date. Everything published becomes
public with its prompts — assume every prompt will be read.
