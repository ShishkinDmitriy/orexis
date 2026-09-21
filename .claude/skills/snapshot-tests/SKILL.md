---
name: snapshot-tests
description: Write, read and regenerate the deliberation package's snapshot cases — a store before, a patch, and the store after. Use when adding or changing a case under packages/orexis-agent-deliberation/tests/, when a case goes red after a behaviour change, or when a diff is noisy and should not be.
---

# Snapshot cases

A case holds a function to one claim: **given this store, leave that one.** Two files, in a
directory named for the function under test:

```
packages/orexis-agent-deliberation/tests/<function>/<case>.trig     the store BEFORE
packages/orexis-agent-deliberation/tests/<function>/<case>.patch    what the function changes
```

What the function must leave is `<case>.trig` with `<case>.patch` applied. **The patch is the
claim.** A reader diffs nothing by hand — the file IS the diff, and a review reads it as one.

Some directories keep `<case>.snapshot.trig` instead: the whole store afterwards, which is
worth having where a case is large and someone wants to open it and read what is there. Both
shapes are live; follow whichever the directory already uses.

## The rule you keep being told: USE NAMESPACES

**Every IRI a case or a patch spells is a prefixed name**, never `<http://…>`, wherever a prefix
exists for it. The renderer abbreviates against the prefix map it is handed, longest namespace
first, so a case written with full IRIs will not match what the renderer produces and the diff
fills with noise that says nothing.

```turtle
#  yes
possible:Move-disk_1-PegC deliberation:from graph:sensed .
:keeper orexis:holds :keeper.in_range.pursued.tank1 .

#  no — the renderer will never write these, so every one is a spurious diff line
<http://example.org/orexis/graph/possible/Move-disk_1-PegC> <http://example.org/orexis/deliberation#from> …
```

A full IRI is correct in exactly one place: a term **no loaded prefix covers**. If you are
writing one for a term a package declares, the prefix is missing from the case's header, not
from the vocabulary.

Declare a case's prefixes at the top of its `.trig` as Turtle does, and use the same spelling
the rest of the repo uses (`orexis:`, `deliberation:`, `progression:`, `market:`, `sensing:`,
`hanoi:`, `courier:`).

### And check the REGENERATED file too

A snapshot the renderer wrote is not canonical by construction. Where a local part will not
abbreviate — anything outside word characters, dots and hyphens — the renderer **falls back to
a full IRI, silently**.

So **a full IRI in a regenerated snapshot is a finding, not a formatting detail.** It means an
IRI was minted in a shape no prefix can cover, and the fix is the code that mints it, never the
snapshot. Grep the regenerated files before committing:

```bash
grep -n "<http" packages/orexis-agent-deliberation/tests/<function>/*.trig | grep -v "@prefix"
```

Nothing should come back. This is not hypothetical: a candidate named `<parent>/<segment>`
spelled 132 full IRIs across three cases, because a slash cannot appear in a prefixed name's
local part. The separator changed; the snapshots did not need to.

## Canonical form, and why a case must already be in it

The renderer writes **one statement per line, flat at the top**, subjects in rendered order,
predicates and objects sorted, `a` for `rdf:type`, bare numbers where Turtle has them, a blank
node used once inlined where it is used, and an RDF list as `( … )`.

Flat because Turtle's `;` and `,` make every line depend on the next: adding one statement flips
its neighbour's `;` to `.`, so a one-statement change is a three-line diff and **no diff over
grouped Turtle can ever be minimal**.

**So a hand-written case must already be in that order.** A statement put in the wrong place
still parses, still passes — and the patch then carries a hunk that only moves lines. That is
the commonest noise in a review, and it is avoidable:

- sort a subject's statements as the renderer would: `a` first, then predicates in order
- put a new statement where sorting puts it, not where it reads best
- when a patch gains a hunk that only moves lines, fix the CASE, not the patch

## Regenerating

```bash
pytest packages/orexis-agent-deliberation/tests --update-snapshots
```

Rewrites every case's patch (or snapshot) from what the function actually left. Then:

1. **`git diff` and read it.** A regenerated patch is a claim that behaviour changed on
   purpose. If a line surprises you, the change is wrong or the case is.
2. **Reordering hunks mean the case is not canonical.** Fix the `.trig` and regenerate.
3. Commit the regenerated files WITH the change that caused them, never separately.

`--update-snapshots` must be given the package path. Naming a single test file will not
register the option.

## When a case is red

The failure names the case and tells you what to do. `<case>.actual.trig` is written **on a
break and never otherwise** — the store as it actually came out, to diff against:

```bash
diff packages/orexis-agent-deliberation/tests/<function>/<case>.trig \
     packages/orexis-agent-deliberation/tests/<function>/<case>.actual.trig
```

A green run leaves nothing behind, and `.gitignore` refuses the file either way.

## The applier is strict on purpose

`patched()` applies by line number, with no fuzz and no context search. It only ever applies a
patch this machinery wrote against the case it was written from, so **a hunk that does not land
where it says it lands is a stale patch**, not something to guess at. It asserts rather than
guessing:

```
stale patch at line 47: '  :keeper orexis:holds …'
```

That means the `.trig` changed after the `.patch` was generated. Regenerate.

## Adding a case

1. Write `<case>.trig`: the whole store the function is handed, in canonical form, with
   prefixes. Comments are allowed — both sides strip them before diffing, so a case can explain
   itself without touching the claim.
2. Run the case's test. It fails, and writes `<case>.actual.trig`.
3. Read the actual, satisfy yourself it is what the function SHOULD leave.
4. `--update-snapshots` to write the patch, then read the patch as the reviewer will.

Never write a `.patch` by hand.

## What a case may not do

- **no wall clock.** The machinery pins one instant; a case that reads `NOW()` is not a case.
- **no hidden setup.** Everything the function reads is in the `.trig`, including the vocabulary
  it needs — if an action's parameters matter, the case declares `orexis:takes` itself. A case
  that passes because a fixture quietly injected an axiom is testing the fixture.
- **no assertion inside a loop over something that may be empty.** The repo-root `conftest.py`
  fails a test that executed no assertion, which is the guard against exactly that.
