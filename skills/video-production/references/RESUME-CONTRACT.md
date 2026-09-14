# The resume contract — pausing so the next window can continue, and continuing from a pause

## The persist ritual (the operator invokes it by name before a compaction)

In order:

1. `date` — every timestamp comes from the clock, never from memory.
2. **The RESUME document** gets a `STATE AT PAUSE — READ THIS FIRST ON RESUME` block
   (`pause_block.py`): the deliverable and whether it was sent; the exact builder line (the slot SSOT
   — re-run it to regenerate the EDL); the keepers with their windows and the voids; the reference set
   as gate-accepted names; the balances and free disk; the background jobs (named, or "none — every
   monitor stopped"); the open items; the resume commands in order; NEXT in capitals.
3. **The continuity ledger** — every state change a shot introduced, restated (`video-refs-continuity`).
4. **The SOP items**, where the project keeps them — numbered, appended, never renumbered; the retrospective for the arc's lessons.
5. **Memory** — where the agent keeps a persistent memory, it carries the STATE and the NEXT pointer.
6. The operator compacts by name; automatic compaction stays off.

## Resuming

- Read the LATEST pause block first, then **the full files it names** — grep locates, it does not read.
- Resume from the **latest deliverable**, not from the last one you remember.
- After a crash (the host, the shell, an API error): re-check every background job by its OUTPUT FILE and
  its sentinel, never by memory; an interrupt resumes the step in flight, it does not restart the phase.
- Ownership: a project can move between agents or sessions; another session's documents are
  read-only until ownership transfers; its message is information, not consent.

## The status template (`status_line.py`) — every status carries it

```
deliverable: <path> (<size>)                 ← every "it is with you" names the path
drive: <free GB>                             ← under the floor = stop heavy work
balances: <vendor> <credits> · <vendor> <chars> · vendors without a balance endpoint: unreadable
background jobs: <named> | none
open: <items>
```

A balance the API cannot read is SAID to be unreadable, never shown as 0; a balance is given on demand.
