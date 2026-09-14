## What this changes

<!-- One or two sentences. Link the issue if there is one. -->

## ⚠ Before you edit anything under `skills/`

**`skills/` is generated.** It is exported from a separate source tree through an overlay, so a hand
edit to a `SKILL.md`, a `references/` file, or a `scripts/` file in this repository is overwritten by
the next export and will not be merged.

If your change belongs in a skill, open an issue describing it instead: what the step should do, which
skill owns it, and the measurement behind it. That is not a brush-off, it is the only route that sticks.

Edit here freely: `README.md`, `METHOD.md`, `CHAIN.md`, `AGENTS.md`, `CLAUDE.md`, `SECURITY.md`,
`install.sh`, `.env.example`, `.github/`, and `look-library/` recipes and documentation.

## Checks

- [ ] No credential, `.env` content, or client material is in the diff.
- [ ] Nothing under `skills/` is edited by hand.
- [ ] Any script I touched still prints its usage on `--help` and changes nothing when asked.
- [ ] A number I added names the model, venue, version and date it was measured on.
- [ ] No count that goes stale as the repository grows (file counts, line counts).

## How you tested it

<!-- The command you ran and what it printed. "Docs only" is a fine answer. -->
