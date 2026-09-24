# Receipts, polling, process hygiene

## The durability contract

Billing happens when the venue ACCEPTS the job, not when the result is fetched. So:

1. Print the handle the instant it exists — `task created (BILLED): <id>` — and append it to an
   append-only ledger (`receipts/tasks-created.log`, `receipts/hf-jobs-<scene>.json`,
   `receipts/fal-requests.log`) BEFORE any polling starts. A hard kill then still leaves a recoverable id.
2. Write the raw venue reply to `receipts/raw/<scene>-s<n>.json` (stdout + stderr) — the reply shape
   changes (a bare list, a dict with `id`, a dict with `job_id`); parse shape-safely and keep the
   original.
3. Poll with a BROAD `except Exception` and a miss budget. `RemoteDisconnected` is a
   `ConnectionResetError`, not a `URLError`; a narrow except once killed the script and took a paid task
   id with it.
4. Guard the download separately from the receipt: a 403 on the download must not lose the paid URL.
   Prefer `result_url`; the poller once grabbed the INPUT url.
5. Record output dimensions and bytes in the receipt — a hosted model changed resolution mid-session
   with no signal; only a stored number catches it.
6. `COMPLETED` is "finished running", never "succeeded": gate on a file on disk (and a 2xx on the
   result). fal's queue accepts any body and validates on the runner, so a bad request reaches
   `COMPLETED` and the result fetch returns 422 or 504.
7. Cost is a receipt, not arithmetic: fal's `X-Fal-Billable-Units` arrives on a re-fetch seconds to
   hours later — re-fetch up to six times; never record a missing header as zero. Arithmetic ran ~10 %
   high across ten runs. A refusal returns `billable='0'`.
8. Never resubmit a billed job. Results persist; re-fetch by job id (`higgsfield generate get <id>`,
   `monid runs get -r <run id>`).
9. **monid has FIVE terminal statuses** — `COMPLETED` · `FAILED` · `BLOCKED` · `STOPPED` · `TIMED_OUT` — and the
   vendor's own CLI guidance is to *"run without `--wait` and poll separately"*. `status` and
   `providerResponse.httpStatus` are INDEPENDENT: `COMPLETED` + `404` is a normal, unbilled no-match.
10. On monid the handle is the `runId`, and an async fire writes it to **stdout only** — `-o` writes
   nothing. Persist it from the submit envelope before anything else can fail. A reply carrying **no
   `runId`** is a body the gateway rejected: no run was created, so nothing was billed.

## Refusals, refunds, outages

| signal | meaning | do |
|---|---|---|
| Higgsfield status `nsfw` / `ip_detected` within a minute or two | prompt-word or framing moderation; refunded | check `higgsfield account transactions`; fix the words/framing; resubmit inside the original GO |
| fal result 422 `content_policy_violation` | reference/frame moderation; billed 0 | not a retry case — change venue or remove the person from the reference |
| kie `flagged as sensitive` | classifier on the FRAMING, not the subject (disposal language — "dumped like a rubbish pile"; product pieces at large scale; anatomy-word density); billed 0 | never retry verbatim, never abandon the shot: re-anchor the same image to a culturally legitimate referent (an ossuary, a museum store room) and retry ONCE; on a plate carrying pieces, edit the clean plate and composite after |
| Higgsfield HTTP 503 on one seed of a batch | transient | resubmit THAT seed under a NEW scene key (the same key clobbers the batch receipts) |
| two 504s in a row (any venue) | outage | stop paying to find out; keep a recovery watcher only for already-billed results; switch venue on the next GO |
| fal result lookup 504 for hours | vendor down | switch vendor; never resubmit |
| `Timeout after 10m` (Higgsfield `--wait`) | wait too short | `--wait-timeout 20m`, or poll without `--wait` |
| monid `COMPLETED` + `providerResponse.httpStatus` 404/500 | the RUN finished, the generation did not — and a provider error is **NOT charged** | read `cost.value` (0) before recording any spend; fix the body and resubmit inside the original GO |
| monid reply with no `runId` | the gateway refused the body before a run existed | nothing billed and no handle to recover; correct the body and resubmit |
| monid `status: BLOCKED` | a control gate refused the run BEFORE execution (`200` + `reason` + `controls`) | free and never reached the model; read `reason`, fix the body, resubmit inside the original GO |
| monid `status: TIMED_OUT` / `STOPPED` | the run exceeded its time budget, or was stopped by request | terminal — a poller that waits only for `COMPLETED`/`FAILED` hangs here until its own timeout |
| monid `--wait` returning a timeout at 300 s | the default wait is shorter than the job (p50 245 s, p95 603 s) | never `--wait`; fire, persist the `runId`, poll detached — the run is still billing |
| Topaz/Starlight submission hangs (no job, no charge) | route hazard | one retry, then the local Rhea route |
| `Session expired` | OAuth token | the operator re-logs in |
| "Image fetch failed" (kie) | reference URL expired (~24 h) | re-upload (free), merge into `refs-urls.json` |

**Diagnosis discipline for a refusal:** list what PASSED first and diff it against what failed — the
load-bearing fact ("two earlier gens passed with the same words") is usually asked for two hypotheses too late.

## Polling and monitors

- The poller runs detached: `python3 ~/.claude/skills/video-production/scripts/detach.py --log <abs>/takes/hf-poll-<key>.log -- python3 <abs>/hf_poll.py --root <abs> <abs>/receipts/hf-jobs-<key>.json`
  (`hf_submit.py` does this itself). Every path absolute: the shell's cwd resets between tool calls, so a
  relative path resolves against a directory nobody picked.
- Log lines start with a timestamp (`17:40:27 DONE S06-B-v8-s3 …`) — match `" DONE | FAILED|HF-POLL-END"`
  anywhere in the line; a pattern anchored on `^DONE` never fires (three landed seeds sat unread for 33
  minutes). `hf_submit.py` APPENDS to an existing scene log.
- One background waiter at a time; a waiter is a polling loop with a bounded lifetime and a single
  notification on the sentinel — never `tail -f | grep` (it pins a 300 MB process as an endless filter).
- Every backgrounded call is killed, awaited, or named to the operator as still running at the end of
  the turn.
- `detach.py` prints the job's pid, which leads its own session and process group (`ps -o pid,pgid,sid`);
  `pgrep -f <pattern>` matches the calling shell — anchor it (`'^python3 .*hf_poll'`) and kill by explicit PID only.
- Batch ≤ 5 assets per shell call on the image leg (1–2 min each; a 5-minute tool timeout kills the loop
  mid-flight); ~30 % transient errors in tight loops — retry.
- A missing completion sentinel is a failure regardless of file size.
- kie video (`gen_video_kie.py`) writes `receipts/kie-tasks-<key>.json` at task creation, then detaches `kie_poll.py` on
  that batch's own file (`receipts/kie-batch-<key>-<stamp>.json`), logging to `takes/kie-poll-<key>.log`; its sentinel
  is `KIE-POLL-END`. A later batch for the same scene numbers its takes after the last one on record, so it never
  overwrites a paid take.

## Disk and memory

- Each finish writes a mezzanine pair of several GB; a project reached 210 GB and the drive fell to
  4.7 GB free, the swap file could not grow, and the whole environment crashed. Check free space before a
  batch and before every finish; prune only pairs the operator names (no VCS on the project tree — no
  undo).
- Uploads to a venue are free; keep them. Takes and receipts are never deleted.
