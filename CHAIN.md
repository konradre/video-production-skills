# Skill chain contract

Governs what happens when one skill hands off to another. Applies to **every** skill-to-skill handoff
— declared in a boundary clause, named in a body, or reached by the agent's own judgement.

A **chain** is the run of skills following one originating invocation. Uncontrolled, a chain
re-enters skills it already ran, burns budget on speculative hops, and slides past the point where a
human should have decided something. The rules below are the guardrails.

---

## Budget: 3 automatic handoffs after the originating skill

**This is a safety and cost policy, not a measurement.** A budget answers *"how far should an agent
go without a human"*, which is a risk appetite, not a property of the skill set. Three keeps an
unattended run short enough to reason about. Raise it only with evidence that a real automatic path
needed more — never to accommodate a run that overran.

**Count only automatic edges.** An operator-gated step (a spend, a send, a delete), a recurring
maintenance step, or a skill invoked as a subroutine of another is not a hop the agent takes
unattended, and counting it inflates the budget.

**An operator-authorised phase scope is a budget override.** A go that names the phases it covers —
"this go covers pre-production through the finish for spot X" — sets the budget to that chain's length
for that phase, and the handoff record quotes it. A finished spot from existing footage is at least four
automatic hops (the entry → designed elements → the EDL → the sound → the finish), which the default
would cut mid-chain. The visited set and the stop conditions still apply; without the named scope the
default holds.

**In practice a stop condition fires first.** The budget is a backstop for chains nobody designed,
not the expected terminator.

## Visited set

Carry the set of skills already run in this chain. **Never run one twice.**

On a loop — the next skill is already in the set — **name the skipped skill and offer the operator a
rerun decision**. That decision requires *new scope or new evidence*. Supplying inputs that were merely
missing the first time is not new evidence; it is the same run again.

## Stop conditions — these outrank the budget

Halt the chain and hand back when any fires:

| Condition | Why it stops |
|---|---|
| **Missing authority** | The next skill needs a permission this request never granted |
| **Material fork** | Proceeding on an assumption could change truth, safety, cost, or reversibility |
| **Unresolved safety gate** | An unanswered safety gate resolves against proceeding. **License is not a gate** — it is exposure, recorded and handed up; only an explicit operator-imposed policy makes it a stop |
| **External side effect** | Publish, send, spend, deploy, delete, or any outward-facing action |
| **Ambiguous route** | Two successors are similarly plausible |
| **Inputs absent** | The successor's required inputs do not exist yet |

**Ambiguity is a stop, not a coin-flip.** Two plausible routes get **presented**; silently picking one
launders a decision the operator never made.

## Stopping well

A chain that stops mid-pipeline is a normal outcome, not a failure — but it reports:

- **`status`** — `DONE` · `DONE_WITH_CONCERNS` · `BLOCKED` · `NEEDS_INPUT`
- **`recommended_next_skill`** — the successor by name. When the budget is the *only* thing stopping an
  otherwise-unambiguous, input-ready successor, **name it and wait.** Do not run it, and do not
  downgrade it to `none` — an exhausted budget is not the absence of a next step.
- **`open_loops`** — what remains, plus the visited chain and the reason for stopping
- **`evidence`** — each finding labelled **Measured · User-provided · Calculated · Estimated · Proxy ·
  Unknown**. A proxy presented as a measurement is the failure this label exists to prevent.

## ❌/✅

```
❌ Chain runs 6 skills because each named a plausible next one
✅ Budget 3 automatic hops; a stop condition usually fires first

❌ Two routes look equally good → pick the first
✅ Two routes look equally good → present both, stop

❌ Budget exhausted → recommended_next_skill: none
✅ Budget exhausted → name the successor, record the exhausted budget, wait

❌ Loop detected → rerun the skill with the inputs it was missing
✅ Loop detected → name it in open_loops, ask; missing inputs are not new evidence

❌ "Publishing the result" as the last automatic hop
✅ External side effect → stop and confirm, every time

❌ Report an estimate in the same voice as a measurement
✅ Label every finding Measured / Estimated / Proxy / Unknown
```

## For skill authors

A skill that hands off names its successor in the fixed boundary form —
`Not for <X> — use <sibling>.` — so the handoff target can be verified to exist. A chaining skill
points at this contract rather than restating it.
