# The ask — what the operator reads, and what the client receives

## To the operator (decisions)

- **Numbered plain questions**, each answerable with a number or a yes/no, **the cost inline**
  ("1. Redo scene C by extending scene B (3 seeds, 37.5 cr) — yes or no? 2. Which clip, 2–7? 3. Add
  the door-slam cutaway (3 seeds, 37.5 cr) — yes or no?"); a default when there is one ("say
  defaults"); rationale before or after, never inside the questions.
- **Every item to look at carries its full path IN THE ASKING MESSAGE** (as the operator opens it); a pick-a-number
  question lists one line per option = label + path (+ the tile or reel path); re-asking after a pause
  repeats the paths.
- Seeds go to the operator as **clips**, never contact sheets; "not bad" is not a pick — wait for the
  path.
- A file ≤ 30 MiB may ride in chat; above that, the path is the delivery (uploads over ~20 MiB time
  out). 1080p masters only.

## With the deliverable (`delivery_ask.py`)

1. The spot and version, the full path, runtime and size.
2. What changed since the previous version (one line per item, mapped to the client's numbered notes).
3. The VO script as placed — every line verbatim with its time.
4. The QC line (`QC-DELIVERABLE PASS`) and the beat sheet (`beat_sheet.py`) pasted so the cut is
   read against the script without opening the file.
5. **Residual doubts with frame times, in the note** — never "approve or re-roll over a fleck?" after a
   final top-up; the operator decides whether the client sees them.
6. What is frozen (approved spots, in the client's words).
7. The decisions, numbered.

## Saving is not sending

Every round's deliverables land in the standing deliver directory (a named output directory is a
standing instruction for the whole arc, never re-asked) with their provenance beside them (the EDL,
the notes file, the receipts); a chat attachment is not a save. Sub-folders per round keep it legible
(`deliver/`, `deliver/final/`, `deliver/alts/`).
