# Placing the sound from the picture

Every audio time is derived from a picture time — a marker measured on a keeper, an event edge, or
another line's edge. The operator gives placement as **word × time × event**; the builder turns it into
a reference and the gate holds it.

## The timing vocabulary

| said | means |
|---|---|
| "the word '…' should be at 0:13" | a WORD lands on a timeline second → shift the line so that word's onset (word times) sits there |
| "the '…' line should be during the product reveal that starts at 0:17" | the line inside an event's span |
| "move the line a tad further; it should end just before the sign-off sound" | `vo_ends_before` a marker, small gap |
| "the first half of the quip where he aims, the second half on the knock — time it for comedic effect" | a quip's two halves on SETUP and PAYOFF — two entries, two anchors |
| "the product quip makes no sense until the product can be seen" | a product quip lands only AFTER the product is visible |
| "make the product shot slightly longer and put a little more gap before the outro line" | pacing: lengthen the event, then the gap |
| "only the first 0.9 s" · "without the first third" · "shave a quarter second off the end" · "cut a little off the start" | trims as time or fraction on the keeper's window |
| "cut before the heads swivel" | the last STILL frame by motion energy, not the eye (one to two frames late) |
| "cut in to just before she trips over it" | a measured motion onset |
| "lock these in for now" | status: the placement is frozen; the next version keeps it |

## The narrator chain — derived backwards from the hit

The last line clears the hit: `L0` ends ≥ 0.5 s before `HIT` (`vo_ends_before`, floored to the frame
so the rule survives rounding). Earlier lines chain backwards with 0.1 s gaps (`before_vo`). If three
lines do not fit the picture between the silence and the hit, the picture is lengthened or a line is
pulled forward over the bend-in — never overlapped, never sped up. The closer rides 0.7 s into the
turntable (a campaign constant); the disclaimer starts 0.2 s into the montage and must end before the
after-state (`vo_ends_before: PARTY`), or a montage window is lengthened.

## Lines inside a shot

- An O.S. line sits at its TAKE time (`{event, take}`) — the door take's words land on the listener.
- A **dub** replaces a line the venue refused (a tamer line generated in-take, the scripted line voiced
  in the character's clone): the clone take is placed at the take onset of the mouth shape, and the
  event's `native_audio_to` mutes the take from that onset. The mouth check (video-take-review) decides
  whether the shape carries the word.
- A placed character line over a muffled native shout: same shape, `native_audio_to` at the shout.
- A **lip-synced line** — the take was generated to this voice — sits where the take's own generated audio says:
  `{event, take}` measured by 10 ms envelope NCC of the VO file against the take's audio over their overlap.
  Replacing the file (a clean render for an excerpt, a re-voice) moves the line — re-measure, never carry the old
  `at`: a clean render with less leading silence sat 0.54 s later than the file it replaced, and the carried number
  would have dubbed the shot. Mark the entry `lip_synced: true` and stamp its `at` with the file and the take
  (`EDL-CONTRACT.md` § Derived constants).

## Carried sound — the L-cut as a placed sfx

When the picture cuts before the sound finishes, the sound is cut FROM the take at the cut frame and
placed as an sfx at the next event's `tl[0]`: a shouted word cuts on its first consonant and its tail
rides over the surprise shot; a tear carries into the next cut; a take's own knock re-timed a beat
earlier becomes an sfx at the new time with the native muted from the raps. A word remainder across a
cut ("persist what remains of the last word") is the same device.

## Music

- A cue is CUT to the marker it must end on (the before cue to the HIT) from the head of the candidate —
  the file's name carries the length (`cue1-before-to-hit-33.867s.wav`); the gate checks the edge.
- A cue that must slam in ON a reveal starts at the REVEAL marker (the frame the wall clears), not on the
  cut before it; `fade_in: 0`.
- A bed under the turntable and the card starts at the turntable's `tl[0]` and runs to the end.
- Ducks: `[[from, to, gain]]` in timeline seconds under a line (−12 dB under the disclaimer, −6 dB under
  a dub or a shout, −10 dB under the closer) with 0.25 s ramps — the music must never fight the VO.
- When the client's reference stems exist, the bed's level under the voice and the duck are MEASURED from them
  (`spot-audio-assembly` MIX-AND-QC.md § The bed against the voice) and stamped with their inputs — never carried
  from an earlier round.
- The hit's own shot and the line after it carry only native sound — no bed under the HIT.
- Chimes on a designed display are OPT-IN; the audio signature on the card sits at card + 0.02 s so its
  hit lands on the card's burst.

## The native bed

`native_audio_vol` > 0 only when the keeper's own sound is the sound (its raps, its thud, its tear, its
line). `native_audio_from` mutes a generated drone before the hit; `native_audio_to` mutes a rap the
cut would truncate into a click, or the take's own thud when a floor insert owns it. A generated tone
in a take's first second doubles a quiet bed — scan every take's audio head (video-take-review row 7).

## Captions

The narrator's lines only, as word ranges (`{line, words:[i,j]}`), three-word cards for a fast
disclaimer; the spoken word highlighted; NO punctuation; a card ends a frame before the next card's
lead; never over the end card. A swapped VO take means re-running the word times for that line only
(`--only`) so hand patches on the other lines survive.
