# Security policy for video-production-skills

This kit is a set of agent skills and local scripts. It runs on your machine, reads your credentials
from your environment, and calls third-party generation and finishing services on your behalf. There is
no server here and nothing phones home.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting on this repository: **Security → Report a vulnerability**.
That channel is private until a fix is published.

Please do not open a public issue for a security problem. For anything that is not a vulnerability, a
normal issue is the right place.

Useful things to include: what an attacker can do, the file and line, and the smallest reproduction you
have. There is no bounty.

## What is in scope

- Any path where a credential could be written to disk, printed, logged, or placed on a command line.
- Any script that would execute an untrusted string, path, or downloaded file.
- A skill instruction that would cause an agent to disclose a key, or to send project material to a
  service the operator did not choose.
- The installer, and anything it links or overwrites outside the folders it documents.

## What is out of scope

- Vulnerabilities in the third-party services the kit calls, or in DaVinci Resolve, Dehancer, Topaz,
  ComfyUI, Node or ffmpeg. Report those to that vendor.
- The cost of a generation call. Spend is governed by the kit's own cost gate, not by this policy.
- Anything requiring an attacker who already has a shell on your machine as your user.

## How the kit handles secrets

- Every credential is read from the process environment. No script reads `.env` directly.
- `.env` is ignored by git; `.env.example` ships placeholders only and names what each variable is for.
- A key never goes into a skill, a prompt, a receipt, or a command line. Receipts record vendor
  responses with the credential removed.
- Some vendors are not keyed here at all: their own CLI holds the credential in its own store.

If you find a case where any of that is not true, it is in scope above.

## Supported versions

The latest commit on `main` is the supported version. Fixes land there; there are no maintenance
branches.
