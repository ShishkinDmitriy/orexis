---
name: author-a-world
description: Genesis as a procedure — the sovereign narrates a world, the documents are drafted under world/<name>/, held by onboarding and a test beside them, and ratified by the sovereign's merge. Use when asked to create a world, add an agent or a bed to one, or turn a described society into documents.
---

# Author a world

Genesis is the one place a model belongs in this project: the sovereign narrates, a draft is made,
the sovereign ratifies, the ratified draft is Turtle under `world/<name>/`
(`knowledge/decisions/genesis.md`). This skill is the procedure; the knowledge is in the runbook
`knowledge/runbooks/author-a-world.md` and the pages it links, and this file points at them
rather than repeating them. Where the two disagree, the runbook wins and this file is wrong.

## 1. Narrate

Take the sovereign's words down as they stand: the subjects, what observes them, what acts on
them, who acts for whom, what each agent is for. Keep them; the world's header comment and the
commit message carry them, so a reader of the documents can see the narration they came from.
Ask only what the documents need and the words leave out — a range a subject states, a cadence a
sensor reports at, a cap a device has. **Never a step, a dose, a price or an aim**: those are the
agents' to find (control-the-derivative-not-the-value).

## 2. Draft

Write what `knowledge/runbooks/author-a-world.md` lists, each document saying which graph it is on
its first line, importing its domains with `owl:imports` and speaking no word a domain does not
declare: `world.ttl`; `society.ttl` only where there is a bus; `state.ttl` for a world nothing
senses; the desires or wants per agent; `deployment.ttl` only to pin a port; `hardware.ttl` only
where a board is flashed. Model the nearest shipped world — `world/greenhouse/` with a bus and
sensors, `world/dispatcher/` or `world/courier/` without, `world/tower/` for two levels — and
copy its layout, not its words. A word the bundle does not have is written as a domain page in the
same change, first (AGENTS.md).

## 3. Hold

```bash
pytest -q world/<name>          # the test beside it: boots the world, runs it, asserts what it was written for
orexis-compose <name>           # writes world/<name>/compose.yaml from the roster; commit it
pytest -q tests                 # layout and knowledge read every world: a document of a kind no reader declares is refused
pytest -q && lint-imports && ./tools/validate-okf.sh knowledge
```

Write `world/<name>/tests/test_<name>.py` as the runbook says — `Runtime(boot(WORLD, "<id>"), "<id>")`
with a clock that ticks, run, and the claim asserted — and break it on purpose once so it is a
guard. `orexis-onboard <name>` is the full onboarding and needs the series store and the broker up;
on a bench without them, the compose generator and the tests above are what hold the draft.
Measure what the runbooks measure where the world is about the search
(`knowledge/runbooks/measure-the-search.md`, `measure-a-pass.md`): a new world's figures go there.

## 4. Ratify

Open the PR with the narration in its body and what you did not verify named. **The sovereign's
merge is the ratification**: nothing else writes `world/`, and a draft the sovereign edits before
merging is the sovereign's, not yours. An amendment later — a bed added, a desire changed — is the
same four steps over again, which is also what reflection comes back to
(`knowledge/decisions/reflection-is-genesis-run-again-over-the-series.md`).
