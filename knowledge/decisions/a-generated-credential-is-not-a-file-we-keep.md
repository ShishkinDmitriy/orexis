---
type: Decision
title: A generated credential is not a file we keep, and an ignore rule is not the thing that stops it
description: >-
  The sensing world's broker password file was tracked for three weeks and reached main in
  seven re-salted versions, while `.gitignore` had named its directory since the commit that
  added it. The rule could not bite: a trailing-slash pattern matches a directory, git prunes
  an ignored directory only while nothing in it is tracked, and two generated files committed
  alongside kept it alive. Decided that the invariant is a test over `git ls-files`, not a
  pattern — and that the leaked material is rotated rather than argued about.
status: accepted
timestamp: 2026-08-28T22:00:00Z
---

# What was true

`world/sensing/mosquitto/` held three files `orexis-mqtt` generates: the broker's `passwd`, its
derived `acl.conf`, and `orexis.conf`. All three were tracked from `0b40cea` (2026-08-05, *a
broker per world*) — **the same commit that added `world/*/mosquitto/` to `.gitignore`.** Staged
in one change, the rule never applied to them, and `passwd` accumulated seven versions in main as
re-onboarding re-salted it.

The other two worlds' equivalents were never tracked and are correctly ignored, which is what made
this invisible: `git status` was clean, and the rule demonstrably worked where nothing had gone
wrong.

# Why the rule could not bite

**A trailing-slash pattern matches a DIRECTORY.** Git prunes an ignored directory wholesale — but
only while nothing inside it is tracked. `world/loner/mosquitto/` is untracked, so git prunes it
and never looks inside. `world/sensing/mosquitto/` held two tracked files, so git had to descend,
and once descending it tests each **file** against the patterns. `world/*/mosquitto/` matches no
file. Every `git add -A` after that swept up whatever the generator had just written, silently.

So the failure was self-sustaining: the two files that should not have been there were the reason
nothing else in that directory could be ignored.

# What is decided

**The invariant is a test, not a pattern.** `tests/test_layout.py::test_no_generated_credential_is_tracked`
reads `git ls-files` and refuses any tracked path under a world's `secrets/` or `mosquitto/`, or
under `infra/secrets/`, `infra/grafana/certs/`, `infra/grafana/dashboards/` — plus any `.key`,
`.pem`, `passwd`, `keys.ttl`, `config.h` or `.env` that is not an `.example`. An ignore rule is
advice about files git has not yet been told to track; this holds whatever `.gitignore` says, and
it is the thing that would have failed on the branch that introduced the defect.

**Both pattern shapes are written**, `world/*/mosquitto/` and `world/*/mosquitto/**`, so the rule
covers the case where the directory cannot be pruned. The same for `firmware/**/include/config.h`
and `firmware/*/include/config.h` — and the line that used to sit between them was a sentence that
had lost its `#`, which git read as a pattern matching nothing.

**And the material is rotated, not reasoned about.** Mosquitto's `$7$` is PBKDF2-SHA512, salted
per entry, over passwords `orexis-mqtt` generates at random — so the practical risk is low and the
correct response is still to treat every credential in that file as public. `orexis-mqtt sensing`
mints new ones. Nothing about the low risk makes the old hashes worth keeping.

# What this is not

**Not an argument for committing generated files elsewhere.** `world/*/wiring.yaml` is committed
because it is the thing that DIFFS; its renderings are not. `world/*/keys.ttl` is a public roster
and is still ignored, because it is machine-generated and committing one machine's would attest
another's identities. The line is authorship, not secrecy, and this record does not move it.

# Seams left open

- **The history still holds the hashes.** Removing a file from the index removes it from the
  future, not the past; seven versions remain reachable in main. Scrubbing them is a rewrite of
  shared history and is the sovereign's call, not a consequence of this record.
- **Nothing scans content.** The guard tests paths. A credential pasted into a `.md` or a world's
  TTL would pass it, and the shapes that catch that are a different tool.
- **`world/sensing`'s board must be reflashed if its credential rotates.** `config.h` carries the
  board's password, which is why rotation is an operator's decision with a soldering-iron cost
  attached rather than a thing a test can insist on.
