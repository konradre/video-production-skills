# The beat list — the script as code, and the gate's rules

`prompts/<SPOT>-beats.json` is the client script (the SSOT) rewritten as a list of beats in script
order, each claiming the EDL events that realise it. It is written BEFORE the EDL, from the script
alone; the EDL is then checked against it by `beat_sheet.py` before every finish. It exists because a script
line read literally, a beat dropped by an in-point, and a character's return the operator had objected
to each shipped once before the gate did.

```json
{
 "spot": "S01B",
 "source": "prompts/S01B-SCRIPT-client.txt (verbatim) via the shot list",
 "markers": { "HIT": {"event": "S01B-D", "take": 4.325, "_note": "MEASURED: RMS peak, 25 ms windows"} },
 "beats": [
  { "beat": "S01B-01", "events": ["S01B-A1"], "vo": ["OS"], "sfx": ["knock"],
    "order": ["sfx:knock", "vo:OS", "marker:ME"], "script": "the dead party … KNOCK … VISITOR (O.S.)" },
  { "beat": "S01B-09", "events": ["S01B-D"], "vo": ["L0"], "vo_ends_before": "HIT",
    "music_end_at": ["cue1", "HIT"], "layer_before_next": ["ELEM-WALL", 0.5], "script": "…she fires" },
  { "beat": "S01B-11b", "events": ["S01B-F2"], "optional": true, "script": "…fires another at him" },
  { "beat": "S01B-14", "events": ["S01B-14"], "sfx": ["sting"], "min_dur": 2.5, "script": "end card" }
 ],
 "extra_vo": { "L3": ["S01B-13"] },
 "forbidden_events": { "S07-ALT": "an alternate the operator ruled out of every delivered spot" }
}
```

## Fields

| field | meaning |
|---|---|
| `markers` | `{event, take}` — a take time inside an event; the gate converts it to the timeline through that event's `tl` and `in`. MEASURED on the keeper (RMS peak of the hit, a word onset by whisper, the frame a wall clears). The builder rewrites them when a pick moves. |
| `beat` · `events` · `script` | the beat id, the EDL events that realise it (in order), the script line verbatim |
| `vo` · `sfx` | lines and sounds that must sit inside the beat's span (`[t0 − 0.05, t1)`) |
| `order` | `sfx:` / `vo:` / `marker:` names that must occur in this order (sfx → O.S. line → the reaction word) |
| `vo_ends_before` | a MARKER name; every listed line must end at or before it (the narrator clears the hit) |
| `music_end_at` / `music_start_at` | `[cue, marker]` — a cue edge within 2 ms of the marker; `"event"` = the beat's first event |
| `layer_before_next` | `[layer id, lead]` — the layer starts `lead` s before the NEXT beat's first event |
| `min_dur` | the beat's span floor (the card's full 2.5 s) |
| `optional` | the beat may be absent from this cut — but if any of its events is present, all must be |
| `extra_vo` | lines that ride over an event without being a beat of their own (the closer over the turntable) |
| `forbidden_events` | ids that must appear in neither events NOR layers, with the reason |

## What the gate fails

1. A non-optional beat with a missing event; an optional beat with SOME of its events.
2. Beats out of script order (a line that sat too late; a reaction before its cause).
3. A VO or sfx placed outside its beat's span; an `order` rule violated.
4. A VO not ending before its marker; a cue edge off its marker; a layer off its lead; a short beat.
5. A placed VO line no beat claims; an EDL event no beat claims (**an invented beat**).
6. A forbidden id present as an event OR a layer (a forbidden layer once passed because only events
   were tested — the check is on both).

The printed sheet (events with their beats, then every audio/layer/marker time in order) is pasted into
the deliverable ask so the reviewer reads the cut against the script without opening the file.

## Writing the beats

- One beat per script line or stage direction that lands on screen; a sound-only beat still needs its
  visual cause in the events.
- A reveal is a beat of its own with a marker; the thing revealed appears in no earlier beat.
- Client-cited beats are located in the DELIVERED file and the EDL history before a change is made.
- A beat the client added in a round gets its `script` from their words verbatim, dated.
