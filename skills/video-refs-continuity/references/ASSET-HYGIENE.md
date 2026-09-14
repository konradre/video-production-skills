# Asset hygiene — the prompts, the job document and the files agree, or the gen is wrong

Every rule here is a drift between three things that must agree — the prompts (what is cited), the job
document (what exists as an asset), and the files on disk (what will actually be uploaded) — and each one
billed a render, or nearly did, before it was caught. None is visible from inside a prompt.

## Cross-check citations against assets in BOTH directions

Every `@ref` a prompt cites must resolve to an asset that exists, and every asset in the job document must
be cited by something. Ten of twelve prompts cited a look plate and four an eyeshine plate; the plates'
prompts had been written but never entered into the job document, so no generation leg ever saw them and
nothing reported them missing. A set-difference both ways surfaces the whole class in one pass — it also
flagged a camp plate orphaned by an ending rewrite and three uppercase specs superseded by the operator's
own lowercase sheets. Run it before the first paid call of a batch, and again after any scene edit.

## A spec that lives in two documents is not changed until it is changed in both

A human prompt doc and a machine job doc both carried the thrown stone: the correction (a car-wheel
boulder → a baseball-sized river stone) reached the job doc and not the prompt doc, which the resume doc
named as the authority. The two would have disagreed silently until someone regenerated from the wrong
one. Either generate one from the other, or gate every spec change on both files agreeing.

## Never bulk-replace a domain noun — enumerate every hit and rule on each

The same rewrite left "real mass and gravity on the boulder" in one prompt's physics tail — the one clause
that is not storyboard, so it was never reread — and that word is the strongest size cue in the prompt. A
find-and-replace would have fixed it and broken another prompt where "a wet boulder" is a real rock in a
creek. A correct usage and an incorrect one routinely share the word.

## A generated frame can settle a question the prose later contradicts

A start still had the truck correctly approaching camera; the video prompt and both storyboards still had
it receding. When an image has settled a geometry question, diff every later prose and derived artifact
against the IMAGE, never against the other prose — consistency between documents is not evidence.

## Superseded assets: strip the cached citation, do not annotate it

A bone-filled interior plate sat beside its clean replacement under a near-identical name and got cited. A
"do-not-cite" note in the resume doc is a stopgap with no enforcement; the structural fix is to strip the
cached reference array in the job document itself, so the stale plate cannot be re-cited by construction.
Provider URLs are cache (they expire in ~24 h); the local files are the source of truth. A resume document
is generated FROM the files, never written from memory — it drifts within one session otherwise.

## Never select an asset by filename order

`sorted(glob)[-1]` over hash-suffixed files returns an arbitrary version — a review script picked the
superseded boulder plate because `be6b…` sorts after `5e93…`. Alphabetical order has nothing to do with
time. Select by `mtime` or an explicit version field; the same line in a generation path feeds a stale
reference into a paid render with no error.

## A defect note names the hash-suffixed FILE, and the fix that clears it clears the note

Assets are regenerated under a stable logical name (`SB_G2`) and land as distinct files
(`SB_G2-sheet-7cea….png` → `SB_G2-sheet-a035….png`). A note written about the first silently re-points at
the second. One such note — "both boards are WRONG, neither usable until re-rolled" — outlived the re-roll
that fixed it by six hours, reported an A/B as blocked, had the operator authorise a regeneration of an
asset that was already correct, and had the two variants' merits reversed. **The doc stored a verdict where
it should store a measurement**, and a false FAIL is self-confirming: nobody re-inspects an asset already
written off. Two rules: every "X is broken" line carries the file it was written about, and the re-roll
that fixes it deletes or rewrites the line in the same step; and **re-read the artifact before spending on
the strength of a note about it**, even your own and recent — one file read, against $0.09 and a day.

## Counts, tables and totals are derived from the artifacts, never retyped

Inserting one gen mid-timeline touched three documents (the prompt file, a gen map with its own beat grid,
the resume doc); it happened twice; ten of twelve char-count headers were stale and one shot carried a
phantom 7 s. Regenerate every count, duration, char total and slot list by measuring the text and the
files at doc-write time. The QA checklist grows rather than renumbers — budget for it.

## A derived artefact carries the fingerprint of the state it was derived from

A proxy clip, a start image cut from a plate, a sheet split from a three-view: each is derived from a source
that can change after it was made, and nothing about the file says so. Record the source's hash beside the
artefact at derivation time (`scene_proxy.py` writes `<clip>.mp4.json` with the scene's sha256; a crop's
record names the keeper file it came from) and let the gate diff that against the live source. A mismatch is
not a warning to weigh — the artefact is stale and is re-derived before it is cited. The same rule caught a
playblast recorded before its scene was edited in the tool this was lifted from: conditioning a model on
footage that no longer matches the prompt is a wrong result, not a cosmetic nit.

The same fingerprint guards a RECORD about a file: `qc_seed.py --record` writes `<take>.review.json` beside the take
with the take's sha256 and bytes, and `--read` refuses it when either no longer matches. A stale record is
re-measured, never hand-edited into freshness — a hash that then describes a file the body no longer matches is the
poisoned cache the sidecar format this was lifted from (`cdaf`) exists to prevent. Each measurement in the record
names its instrument and rule, so a reader knows what was measured and what was inferred.
