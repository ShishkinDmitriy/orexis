"""The bundle's own gates — what `tools/validate-okf.sh` cannot check, and one thing it should.

`validate-okf.sh` is VENDORED from the okf skill and checks the OKF v0.1 spec: frontmatter
exists, `type` is non-empty, reserved files are shaped right. It is deliberately not edited here,
because the header says to re-copy it when the skill's copy gains checks, and a local edit would
be silently reverted by that.

So the PROJECT's rules about its own bundle live here instead, where they run under `pytest` —
one of the two gates — and where they can ask questions a grep cannot. Every one of them exists
because the thing it checks had already gone wrong:

- frontmatter that no YAML parser can read. 27 files, because a `description` said "on one axis:
  the agent asks" and an unquoted colon-space ends a plain scalar. `validate-okf.sh` greps for
  `^description:` and cannot see it, so a bundle that calls itself "readable by any OKF consumer"
  was not readable by any of them.
- a document nothing links. Two, and in OKF the index IS navigation, so an unlisted file is
  invisible rather than merely untidy.
- a link to a record that never existed. Three, two of them to the same imagined slug.
- a path in prose that is not a path on disk. 27 documents went on naming
  `agent/capabilities/` for nine days after the tree moved, including four in `domain/`, which
  is the layer whose job is to say where things are.
- an index entry that is an abstract. They averaged 82 words, which is why nothing could be
  found by scanning.

WHY THE ASSERTS ARE AT THE END and never inside the loops: see the desire `conftest.py`. A loop
over an empty glob runs its body zero times and passes. Each test here asserts the corpus is
non-empty FIRST, then asserts on a collected list — so an emptied glob fails loudly instead of
going green.
"""

from __future__ import annotations

import itertools
import pathlib
import re
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE = REPO_ROOT / "knowledge"

# What `type` may say. The bundle desire and AGENTS.md both state this list in prose; this is the
# copy that fails when they disagree with the files.
#
# FIVE concept types where there were two, and the split was asked for by the pages themselves:
# `auction` opened "an auction is a PROCESS", `bid-matching` called itself "the STEP that turns a
# lot and a set of bids into an allocation", `onboarding` "the PHASE between genesis and a running
# society" — three pages naming their own type in prose because the field could not hold it.
# `Capability` is rule 2's unit and not a subtype of convenience: those pages carry a family term,
# its interchangeable members, and the premise that grants it, which no other kind of page has.
#
# Distribution when Component folded: Concept 10, Service 7, Process 5, Capability 4, Role 4,
# Repository 2 — Component's own two examples, the belief base and the imaginarium, WERE the
# repositories, so the word had nothing left to mean once they were named.
# no type with one member, which is the evidence it is a real division rather than a tidy one. A
# type that drops to one page is a type to fold back, not to defend.
TYPES = {"Decision", "Domain Concept", "Process", "Capability", "Role", "Service", "Repository",
         "Runbook"}
STATUSES = {"accepted", "superseded", "superseded-in-part"}

# An index entry is the CLAIM. The abstract is the record's own `description`, and the record is
# the argument. 26 is the longest entry that survived the rewrite, not a round number.
MAX_INDEX_ENTRY_WORDS = 26


def concepts() -> list[Path]:
    """Every non-reserved document. `index.md` is navigation and carries no frontmatter."""
    return sorted(p for p in BUNDLE.rglob("*.md") if p.name not in ("index.md", "log.md"))


def indexes() -> list[Path]:
    return sorted(BUNDLE.rglob("index.md"))


def frontmatter(path: Path) -> dict:
    text = path.read_text()
    assert text.startswith("---\n"), f"{path} has no frontmatter"
    return yaml.safe_load(text[4 : text.index("\n---\n", 3) + 1])


# --- the schema -------------------------------------------------------------------------------


def test_every_frontmatter_parses_as_yaml():
    """The claim the bundle desire makes about itself, held to a real parser rather than a grep."""
    docs = concepts()
    broken = []
    for path in docs:
        try:
            frontmatter(path)
        except Exception as exc:  # noqa: BLE001 — the failure text is the report
            broken.append(f"{path.relative_to(REPO_ROOT)}: {str(exc).splitlines()[0]}")
    assert docs, "no concept documents found — the glob stopped matching"
    assert not broken, "frontmatter that no YAML consumer can read:\n  " + "\n  ".join(broken)


def test_frontmatter_carries_what_its_kind_requires():
    """A decision has a status and a date; a living concept has neither, because it has no state
    to be in — it is either current or it is wrong, and the fix is to edit it."""
    docs = concepts()
    wrong = []
    for path in docs:
        rel = path.relative_to(REPO_ROOT)
        meta = frontmatter(path)
        for key in ("type", "title", "description"):
            if not meta.get(key):
                wrong.append(f"{rel}: missing {key}")
        if meta.get("type") not in TYPES:
            wrong.append(f"{rel}: type {meta.get('type')!r} is not one of {sorted(TYPES)}")
        if meta.get("type") == "Decision":
            if meta.get("status") not in STATUSES:
                wrong.append(f"{rel}: status {meta.get('status')!r} is not one of {sorted(STATUSES)}")
            if not meta.get("timestamp"):
                wrong.append(f"{rel}: a decision states when it was taken")
        else:
            #  Every other type is either current or wrong; only a decision has a state to be in.
            for key in ("status", "timestamp", "stage", "tags"):
                if key in meta:
                    wrong.append(f"{rel}: {key} is a decision's field")
    assert docs, "no concept documents found — the glob stopped matching"
    assert not wrong, "frontmatter schema:\n  " + "\n  ".join(wrong)


def test_a_superseded_record_says_what_superseded_it():
    """Supersession used to be expressed four ways — a status, a blockquote, a prose aside, an
    index annotation — and a reader had to find whichever one a record chose."""
    decisions = [p for p in concepts() if frontmatter(p).get("type") == "Decision"]
    wrong = []
    for path in decisions:
        meta = frontmatter(path)
        if not str(meta.get("status", "")).startswith("superseded"):
            continue
        successor = meta.get("superseded-by")
        if not successor:
            wrong.append(f"{path.name}: status is {meta['status']} with no superseded-by")
        elif not (BUNDLE / "decisions" / f"{successor}.md").exists():
            wrong.append(f"{path.name}: superseded-by {successor} — no such record")
    assert decisions, "no decision records found — the glob stopped matching"
    assert not wrong, "supersession:\n  " + "\n  ".join(wrong)


# --- navigation -------------------------------------------------------------------------------


def test_no_document_is_unreachable_from_an_index():
    """In OKF the index IS navigation. A file nothing links is invisible to a consumer."""
    docs = concepts()
    listed = "\n".join(p.read_text() for p in indexes())
    orphans = [
        str(p.relative_to(BUNDLE))
        for p in docs
        if f"{p.parent.name}/{p.name}" not in listed
    ]
    assert docs, "no concept documents found — the glob stopped matching"
    assert not orphans, f"documents no index links: {orphans}"


def test_every_internal_link_resolves():
    links = []
    for path in list(concepts()) + indexes():
        for target in re.findall(r"\]\(([^)]+\.md)\)", path.read_text()):
            if target.startswith("http"):
                continue
            resolved = (BUNDLE / target.lstrip("/")) if target.startswith("/") \
                else (path.parent / target)
            links.append((path.relative_to(REPO_ROOT), target, resolved.exists()))
    dead = [f"{src} -> {tgt}" for src, tgt, ok in links if not ok]
    assert links, "no internal links found — the pattern stopped matching"
    assert not dead, "dead links:\n  " + "\n  ".join(sorted(set(dead)))


def test_an_index_entry_is_a_claim_not_an_abstract():
    """They averaged 82 words and the longest was 173, which is not an index."""
    entries = []
    for path in indexes():
        for line in path.read_text().splitlines():
            if line.startswith("* ["):
                # the entry is what follows the link
                _, _, gloss = line.partition(") - ")
                entries.append((path.relative_to(BUNDLE), line[:60], len(gloss.split())))
    too_long = [f"{f} {name}… {n} words" for f, name, n in entries if n > MAX_INDEX_ENTRY_WORDS]
    assert entries, "no index entries found — the pattern stopped matching"
    assert not too_long, (
        f"index entries over {MAX_INDEX_ENTRY_WORDS} words — put the abstract in the record's "
        "own `description`:\n  " + "\n  ".join(too_long)
    )


# --- the bundle against the tree ---------------------------------------------------------------

# Prose names paths constantly, and a rename sees none of them. Only backticked things that look
# like a repo path are checked: a leading known top-level directory, or a `packages/...` segment.
# A trailing `/` is a directory, `<name>` is a placeholder and matches any single segment.
_TOP = ("agent/", "agent_old/", "packages/", "onboarding/", "tests/", "infra/", "tools/", "firmware/", "world/")
_PATH = re.compile(r"`((?:" + "|".join(re.escape(t) for t in _TOP) + r")[A-Za-z0-9_./<>*-]*)`")


#  ASK GIT, NOT THE FILESYSTEM. This guard used to call `Path.exists()`, and that made its
#  verdict depend on gitignored local state in both directions at once:
#
#  - a GENERATED path — `infra/.env`, `world/<w>/secrets/`, a board's `config.h` — is absent
#    until somebody runs onboarding, so a fresh clone or a new worktree reported five real
#    documents as broken. Three readers in a row called the whole failure environmental and
#    moved on, which is what a guard that cries wolf buys;
#  - and a DELETED path can be kept alive by a leftover. `world/society` was removed, five
#    documents went on naming it, and the checkout it was written in still held an empty
#    `world/society/secrets/` from before the deletion. Untracked, gitignored, invisible — and
#    enough to make `exists()` say yes. The guard was green here and red everywhere else.
#
#  Tracked, ignored and absent are three different answers and git knows all three. A path is
#  fine if git TRACKS it, or if git IGNORES it (a generator's output, legitimately named in
#  prose, whose presence is nobody's business here). Anything else is a rename that did not
#  reach the bundle — the same verdict in a fresh clone, a worktree and a working checkout.


def _tracked() -> set[str]:
    """Every tracked path, plus every directory on the way to one."""
    files = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT,
                           capture_output=True, text=True, check=True).stdout.split("\0")
    known = {f for f in files if f}
    for f in list(known):
        known |= {str(d) for d in pathlib.PurePosixPath(f).parents if str(d) != "."}
    return known


def _ignored(specs: list[str]) -> set[str]:
    """Which of these git would ignore — asked in one call, because there can be dozens."""
    if not specs:
        return set()
    done = subprocess.run(["git", "check-ignore", "--stdin"], cwd=REPO_ROOT,
                          input="\n".join(specs), capture_output=True, text=True)
    return {line for line in done.stdout.splitlines() if line}


def _as_regex(pattern: str) -> re.Pattern:
    """A shell-ish glob over slash-separated paths: `**` crosses separators, `*` does not."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")     # `**/` spans zero directories or many, as a shell does
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + "$")


def _is_tracked(spec: str, known: set[str]) -> bool:
    """A placeholder segment matches anything; a glob is a glob; and prose names a module
    without its extension as often as with it, which is not a broken reference."""
    spec = spec.rstrip("/")
    if not spec:
        return True
    pattern = re.sub(r"<[^>]+>", "*", spec)
    if "*" in pattern:
        rx = _as_regex(pattern)
        return any(rx.match(k) for k in known)
    return spec in known or f"{spec}.py" in known


def _concrete(spec: str) -> str:
    """A path git can be asked about: every placeholder filled with a name nothing else uses.

    The trailing slash is KEPT. `.gitignore` says `world/*/secrets/`, and a directory-only
    pattern will not match a path git cannot stat — which every generated path is, on a machine
    where nobody has run onboarding. With the slash it matches by spelling alone."""
    return re.sub(r"<[^>]+>", "placeholder", spec).replace("**", "placeholder")


def test_no_document_names_a_path_that_is_not_there():
    """`one-tree-and-one-mechanic` moved the capability tree and 27 documents went on naming the
    old path in the present tense. Nothing failed, because nothing was looking.

    A record legitimately narrates a path that USED to exist. Those are the exceptions below, and
    each one is a sentence that says "was" or "at the time" or draws a before/after.
    """
    absent_on_purpose = {
        # THE 0.1.0 ONBOARDING COMMANDS, retired with it (2026-09-25): validation, its link step,
        # the key generator and the sovereign's question channel, narrated by the records.
        "onboarding/ask.py",
        "onboarding/linker",
        "onboarding/linker.py",
        "onboarding/validate.py",
        # RETIRED WITH 0.1.0 (2026-09-25): the switched-off suite's files, the loner and
        # simulation worlds and the stand-ins the simulator replaced. The records narrate them as
        # what 0.1.0 had and did; git history keeps every one.
        "firmware/simulated-sensor/simulator.py",
        "firmware/simulated-valve",
        "tests/test_capabilities.py",
        "tests/test_clearing.py",
        "tests/test_clock.py",
        "tests/test_clockless.py",
        "tests/test_deliberation.py",
        "tests/test_desires.py",
        "tests/test_execution.py",
        "tests/test_firmware.py",
        "tests/test_hooks.py",
        "tests/test_inference.py",
        "tests/test_intention.py",
        "tests/test_isolation.py",
        "tests/test_kernel_namespaces.py",
        "tests/test_layering.py",
        "tests/test_legality.py",
        "tests/test_linker.py",
        "tests/test_provenance.py",
        "tests/test_runtime.py",
        "tests/test_shapes.py",
        "tests/test_simulated_valve.py",
        "tests/test_tower.py",
        "tests/test_violation.py",
        "tests/test_vocabulary.py",
        "tests/test_w3c_descriptions.py",
        "world/loner",
        "world/simulation",
        "world/simulation/compose.yaml",
        "world/simulation/world.ttl",
        # one-tree-and-one-mechanic: the before/after diagram, and the argument that the old
        # name already spelled the new idea.
        "agent/capabilities/<name>/",
        "agent/capabilities/market",
        # repository-layout: a section titled "Why there is no `agent/kernel/`" — the whole
        # point is that this path does not exist, and a day it does is a day to reread that
        # section rather than to edit this list.
        "agent/kernel/",
        # domain/package: the same argument one tree over. The kernel is not a FAMILY, and the
        # evidence offered is that `packages/kernel/` is not a directory anyone can add a
        # sibling to. Its absence is the sentence.
        "packages/kernel/",
        # the-region-want-is-sensings-want and the records it amends narrate where the region want
        # and its arithmetic USED to be derived and held. Both files are sensing's now
        # (`desires.ru`, `regions.py` under packages/orexis-capability-sensing/), and a record that
        # says so in the past tense is not a rename that missed the bundle.
        "agent/desires.ru",
        "agent/regions.py",
        # the-kernel-has-no-mailbox and a-dead-session-is-resigned-not-endured narrate where
        # the watchdog WAS; it is `packages/orexis-transport-mqtt/watchdog.py` now.
        "agent/watchdog.py",
        # metrics-are-an-aspect narrates where the sink, the driver contract and the sovereign
        # channel WERE; they are reporting's and sensing's now.
        "agent/influx_writer.py",
        "agent/sovereign.py",
        "agent/driver.py",
        # repository-layout: the two-distribution layout, past tense — "used a `src` layout and
        # were pip-installed separately".
        "onboarding/src/onboarding/",
        "onboarding/src/onboarding",
        # where-the-belief-base-lives, describing what it removed: "`infra/fuseki/` no longer
        # exists".
        "infra/fuseki/",
        # capability-packages: a throwaway package dropped in to prove the loader finds one
        # without being told, then deleted. It is evidence, not a path.
        "packages/orexis-capability-forecast/",
        # domain/world: a runbook step. `world/orchard/` is what the reader is being told to
        # CREATE, so its absence is the precondition.
        "world/orchard/world.ttl",
        # The base vocabulary lived here until it came into `agent/` — a family of exactly one
        # is not a family. Five records narrate that arrangement in the past tense: the table
        # row capability-packages struck through, the term count every-term-in-its-own-house
        # took at the time, pins-and-wires' 205-line file, the naming section of
        # repository-layout, and the rename sweep in the-society-is-named-for-its-appetite.
        "packages/core/<name>/",
        "packages/core/orexis",
        "packages/core/orexis/",
        "packages/core/orexis/ontology.ttl",
        # auction-and-clearing-are-the-markets: three records narrate where the auction, the
        # clearing validator and the market's types lived before they went to the package —
        # "stayed in", "said of itself", "is a function" — all past tense about the kernel.
        "agent/auction.py",
        "agent/clearing.py",
        "agent/market.py",
        # sensing-owns-the-reading-pipeline: four records narrate where the reading pipeline
        # lived in the kernel — the sensed writer, the observations recorder, the pointer and
        # the readings query — before it went to the sensing package. Past tense, every one.
        "agent/observation.py",
        "agent/sensed_writer.py",
        "agent/readings.rq",
        "agent/pointer.py",
        # and the two empty directories it deleted, named as what went.
        "agent/codecs",
        "agent/scalings",
        # a-layer-is-a-package-and-need-loads-it (#451): the mind's stores left the kernel's
        # directory for `packages/orexis-modality-graph/`. The two layering records name the
        # files where they were when the decision was taken, and half a dozen older records
        # narrate the kernel vocabulary, the store, the belief reader and the two mental-state
        # modules at their old addresses — "was", "until #451", "at the time", every one.
        "agent/store.py",
        "agent/beliefs.py",
        "agent/graphs.py",
        "agent/desire.py",
        "agent/intentions.py",
        "agent/ontology.py",
        # a-layer-is-a-package-and-need-loads-it (#452): the kernel's own modules left `agent/`
        # for the three layer packages. The layering records, the mind's record and the act,
        # plan and intention records name the files where they were when each was written.
        "agent/act.py",
        "agent/planner.py",
        "agent/deliberator.py",
        "agent/keeper.py",
        "agent/execution.py",
        "agent/reviser.py",
        # two-worlds-were-one removed `world/society`, a near-duplicate of `world/simulation`.
        # Three records narrate it and each is explicit: a struck-through seam marked "Moot",
        # the pair of worlds that WAS device-for-device identical, and the two that once shared
        # a broker. This entry is why the guard had to stop asking the filesystem — the checkout
        # where those records were written still holds an empty `world/society/secrets/`, so
        # `exists()` said the world was there.
        "world/society",
    }
    #  THE ROOT DOCUMENTS TOO. `README.md` and `AGENTS.md` name paths exactly as a record does,
    #  and nothing was looking: the README described `packages/core/`, a tree that came into
    #  `agent/`, and a Fuseki endpoint removed with the shared store, while AGENTS.md cited
    #  `tests/test_goals.py` — renamed to `test_desires.py` by the goal-is-a-desire ruling, in
    #  the very file that tells everyone which guard pins what.
    docs = concepts() + [REPO_ROOT / "README.md", REPO_ROOT / "AGENTS.md"]
    known = _tracked()
    assert docs, "no concept documents found — the glob stopped matching"
    assert all(d.exists() for d in docs), "a desire document moved — README.md or AGENTS.md"
    assert known, "git tracks nothing — `git ls-files` stopped answering, and every path below "
    "would read as missing"

    unresolved = {}
    for path in docs:
        for spec in set(_PATH.findall(path.read_text())):
            if spec in absent_on_purpose or _is_tracked(spec, known):
                continue
            where = (path.relative_to(BUNDLE) if BUNDLE in path.parents
                     else path.relative_to(REPO_ROOT))
            unresolved.setdefault(_concrete(spec), []).append(f"{where}: `{spec}`")

    #  The second question, asked only of what the first could not answer: is it a generator's
    #  output? Those are named in prose on purpose and are absent until somebody runs onboarding.
    #  Asked about both spellings: a bare path, and the same with a trailing slash, since a
    #  directory-only `.gitignore` pattern matches only the second when the path is not on disk.
    asked = sorted({s for c in unresolved for s in (c.rstrip("/"), c.rstrip("/") + "/")})
    generated = {g.rstrip("/") for g in _ignored(asked)}
    missing = sorted(m for concrete, mentions in unresolved.items()
                     if concrete.rstrip("/") not in generated for m in mentions)
    assert not missing, (
        "documents naming a path git neither tracks nor ignores — a rename that did not reach "
        "the bundle. (A path that is merely UNGENERATED does not appear here: git ignores those, "
        "so this list is the same in a fresh clone as in a working checkout.)\n  "
        + "\n  ".join(missing)
    )


# --- the one table that claims to be checkable -------------------------------------------------


#  `test_the_deliberation_table_matches_what_is_built` stood here. It held
#  `domain/deliberation.md`'s member table to the deliberation package's `PROVIDES`, and both
#  ends of it are gone: there is no package, and the two built members turned out to be one
#  class with a conditional clause rather than two ways of having an ability. A guard whose
#  subject no longer exists is deleted rather than loosened — the page now argues why the
#  family folded, which is a claim about the past that nothing can drift from.

# --- the terms a document cites ----------------------------------------------------------------

# `domain/` is the CURRENT statement, so a term it names in the present tense should be a term
# that exists. `decisions/` is deliberately not checked: a record narrates the vocabulary of its
# own moment, and half the value of one is the rejected name it argues against.
#
# This found #275. `domain/desire.md` cited `desire:UnwatchedDesireShape` for a constraint that
# is real and fires — but the term does not exist, because the constraint has no shape of its
# own and sits inside one named for something else. The page had reached for the name the
# constraint deserves. Nothing could see that: SHACL does not care what a shape is called, and
# no gate read the prose.

_TERM = re.compile(r"\b([a-z][a-z0-9]*):([A-Za-z]\w*)\b")


def _declared() -> set[str]:
    """Every local name any project TTL declares — the kernel, the packages, and the ratified
    worlds.

    Worlds are included because a domain page legitimately names an individual as an example,
    and an individual is declared by the world that holds it rather than by an ontology.

    The kernel is reached through the loader rather than through a path. It used to be
    `packages/core/orexis/` and is `agent/` now, so a `packages/**` glob alone would stop
    covering it — silently as far as this function is concerned, and loudly one line later,
    since every `orexis:` term a page names would read as undeclared.
    """
    from assembly import loader

    #  ALL of the kernel's TTL, not just its ontology. A SHAPE is declared in `shapes.ttl` and a
    #  page may legitimately name one — `orexis:KeeperShape` does — and while the shapes lived in
    #  packages the `packages/**` glob swept them up for free. It does not any more.
    #  AND THE 0.2.0 TREE'S OWN ONTOLOGIES, which the 0.1.0 loader never walks: a layer's
    #  `agent/<layer>/ontology.ttl` (and a rule set beside it) declares words a page names.
    names: set[str] = set()
    for ttl in (list(loader.sources("*.ttl")) + list((REPO_ROOT / "world").rglob("*.ttl"))
                + sorted(p for p in (REPO_ROOT / "agent").rglob("*.ttl") if "tests" not in p.parts)
                + sorted((REPO_ROOT / "domains").rglob("*.ttl"))):
        text = ttl.read_text()
        names |= set(re.findall(r"^:(\w+)\b", text, re.M))
        names |= {local for _, local in _TERM.findall(text)}
    return names


def test_a_domain_page_names_only_terms_that_exist():
    # Terms the pages state do NOT exist. Each is a sentence saying so, which is a legitimate and
    # useful thing for a page to say — and is exactly why this cannot be a bare existence check.
    said_not_to_exist = {
        # domain/auction.md: "no `orexis:Auction` anywhere", "There is no `orexis:Auction` to point at."
        "orexis:Auction",
        # domain/genesis-process.md: "There is no `orexis:worldKind`".
        "orexis:worldKind",
        # domain/desire.md names this to say it is NOT a name that exists — it is what an earlier
        # version of the page invented for a constraint that has no shape of its own (#275).
        # When #275 lands and gives that constraint a real name, this entry comes out.
        "desire:UnwatchedDesireShape",
    }

    from assembly import loader
    project = set(loader.prefixes())          # found by looking, never listed — as the code does
    declared = _declared()

    pages = sorted((BUNDLE / "domain").glob("*.md"))
    undeclared = []
    for page in pages:
        for prefix, local in set(_TERM.findall(page.read_text())):
            term = f"{prefix}:{local}"
            if prefix not in project or term in said_not_to_exist or local in declared:
                continue
            undeclared.append(f"{page.name}: {term}")

    assert pages, "no domain pages found — the glob stopped matching"
    assert project, "no project prefixes discovered — loader.prefixes() stopped finding them"
    assert declared, "no terms discovered — the TTL globs stopped matching"
    assert not undeclared, (
        "a domain page names a term no TTL declares — either the term was renamed and the page "
        "was not, or the page invented the name the thing deserves (which is #275):\n  "
        + "\n  ".join(sorted(undeclared))
    )


# --- one claim, one owner -----------------------------------------------------------------------

# A `domain/` page is the current statement of ONE concept. When two of them state the same claim
# in the same words, the claim has two owners, and the next change updates whichever the author
# happened to open. That is how `market` came to carry the short-side principle WITHOUT the word
# "structurally" while citing the very record that was amended to add it — the page and the
# amendment never met.
#
# Measured rather than judged: overlapping runs of words between every pair of domain pages. It
# does not care about topic, only about restatement, which is the thing that rots.
#
# The cluster measured 32 shared runs before this check existed and 4 after, and the 4 are a
# deliberate mirror — see the exception. The cap sits just above them: high enough that a shared
# term of art or a quoted `sh:message` is fine, low enough that a restated paragraph is not.

_RUN = 8          # words; shorter matches idiom, longer misses a restated sentence
_CAP = 4          # shared runs allowed between any two pages


def _runs(path: Path) -> set[tuple[str, ...]]:
    body = path.read_text().split("\n---\n", 1)[-1]
    # links, code spans and punctuation are not prose and must not count as agreement
    words = re.sub(r"`[^`]*`|\[[^\]]*\]\([^)]*\)|[^\w\s]", " ", body).lower().split()
    return {tuple(words[i:i + _RUN]) for i in range(max(0, len(words) - _RUN))}


def test_no_two_domain_pages_state_the_same_claim():
    # Pairs that legitimately share wording, with the reason. A mirror is not a duplicate.
    mirrors = {
        # `market` uses "a time slot, a right of way" to show the REJECTED model made such a
        # market undeclarable; `good` uses it to show the current one keeps it expressible.
        # Same example, opposite halves of one argument — changing one should change both.
        frozenset({"market.md", "good.md"}),
    }
    pages = sorted((BUNDLE / "domain").glob("*.md"))
    runs = {p.name: _runs(p) for p in pages}

    offenders = []
    for a, b in itertools.combinations(sorted(runs), 2):
        shared = runs[a] & runs[b]
        if len(shared) > _CAP and frozenset({a, b}) not in mirrors:
            sample = "; ".join(" ".join(s) for s in sorted(shared)[:2])
            offenders.append(f"{a} <-> {b}: {len(shared)} shared runs — e.g. “{sample}”")

    assert pages, "no domain pages found — the glob stopped matching"
    assert any(runs.values()), "no word runs extracted — the pattern stopped matching"
    assert not offenders, (
        "two domain pages state the same claim in the same words. Give the claim ONE owner and "
        "have the other link to it — or, if it is a deliberate mirror, add the pair to `mirrors` "
        "with the reason:\n  " + "\n  ".join(offenders)
    )


# --- the dictionary names its terms ---------------------------------------------------------------

# A `term:` in a domain page's frontmatter binds the page's WORD to the T-Box term that carries
# it, which is the join the other gates could not see: prose↔prose is the overlap check above,
# code↔ontology is tests/test_vocabulary.py, and nothing held the dictionary to the ontology —
# which is how the class everyone called the mandate stayed `review:Commitment` for months after
# the collision was recorded, and how "stream" and "channel" named one node for longer. See
# knowledge/decisions/the-dictionary-names-its-terms.md.
#
# A page WITHOUT a `term:` is a statement, not an omission: a gap is computed and never stored,
# an auction is an event, a venue is an instance-side word for a class another page owns — none
# of them has a term to bind, and forcing one would be reification for the gate's sake.
#
# External vocabularies are vendored under tests/fixtures/vocabularies/ so that sosa:Observation
# is checked against what SOSA actually declares rather than against our spelling of it. Words
# borrowed WITHOUT their IRIs (REA/ValueFlows, per settlement-speaks-rea) never appear in
# `term:` — vf: is deliberately unbound, and `term:` names only what code could query.

_VENDORED_VOCABULARIES = {
    "sosa": "sosa.ttl",
    "ssn": "ssn.ttl",
    "prov": "prov.ttl",
    "dcterms": "dcterms.ttl",
    "sh": "shacl.ttl",
    "mqtt4ssn": "mqtt4ssn.ttl",
}


def _bound_terms(meta: dict) -> list[str]:
    value = meta.get("term")
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def test_a_dictionary_term_is_a_declared_one():
    import re

    import rdflib

    from assembly import loader
    from orexis_agent_progression.store import NAMESPACES

    #  Asked of the loader, not globbed. This was `packages/**/ontology.ttl` plus a firmware
    #  glob — the same list the loader already assembles, maintained twice — and when the kernel
    #  left `packages/core/orexis/` for `agent/` the glob went on matching twenty files while
    #  covering none of `orexis:`. Non-empty is not complete, and the two asserts at the foot of this
    #  function would both have passed.
    #  AND THE 0.2.0 TREE'S, which the 0.1.0 loader never walks: `agent/<layer>/ontology.ttl`
    #  is where a layer or the belief package declares its words, and a dictionary page that
    #  binds one of them binds a term this guard would otherwise call undeclared. Their
    #  prefixes are read off their own `@prefix` lines, as `agent.store` reads them.
    ontologies = list(loader.ontology_files()) + sorted(
        p for p in (REPO_ROOT / "agent").rglob("ontology.ttl") if "tests" not in p.parts) + sorted(
        (REPO_ROOT / "domains").glob("*/ontology.ttl"))     # and the domains 0.2.0's worlds import
    project = rdflib.Graph()
    for ttl in ontologies:
        project.parse(ttl)
    declared = {str(s) for s in project.subjects() if isinstance(s, rdflib.URIRef)}
    #  An ontology that spells its own words with the empty prefix (`@prefix : <…/belief#>`)
    #  binds them under the last segment of its namespace, since a binding needs a label and
    #  the file gives none.
    namespaces = dict(NAMESPACES)
    for ttl in ontologies:
        for label, iri in re.findall(r"@prefix\s+([A-Za-z][\w.-]*)?:\s*<([^>]*)>", ttl.read_text()):
            namespaces.setdefault(label or iri.rstrip("#/").rsplit("/", 1)[-1], iri)

    vendored: dict[str, set[str]] = {}
    for prefix, filename in _VENDORED_VOCABULARIES.items():
        vocabulary = rdflib.Graph()
        vocabulary.parse(REPO_ROOT / "tests" / "fixtures" / "vocabularies" / filename)
        vendored[prefix] = {str(s) for s in vocabulary.subjects() if isinstance(s, rdflib.URIRef)}

    #  Longest binding first, so nested namespaces (orexis: inside every package's) resolve to the
    #  package that actually owns the term rather than to the kernel.
    bindings = sorted(((str(iri), prefix) for prefix, iri in namespaces.items()),
                      key=lambda pair: -len(pair[0]))

    owners: dict[str, list[str]] = {}
    wrong = []
    pages = concepts()
    for page in pages:
        rel = str(page.relative_to(REPO_ROOT))
        meta = frontmatter(page)
        terms = _bound_terms(meta)
        if terms and page.parent.name != "domain":
            wrong.append(f"{rel}: only the dictionary binds terms — a {meta.get('type')} is not a word's owner")
            continue
        for iri in terms:
            #  A FULL IRI, never prefix:Name — the bundle is the unit of distribution, and a
            #  prefixed name is unresolvable the moment knowledge/ leaves this repo.
            if not isinstance(iri, str) or not iri.startswith(("http://", "https://")):
                wrong.append(f"{rel}: term {iri!r} is not a full IRI")
                continue
            prefix = next((p for base, p in bindings if iri.startswith(base)), None)
            if prefix is None:
                wrong.append(f"{rel}: {iri} is in no namespace the store binds")
                continue
            owners.setdefault(iri, []).append(page.name)
            if str(namespaces[prefix]).startswith("http://example.org/orexis"):
                if iri not in declared:
                    wrong.append(f"{rel}: {iri} is not declared by any project ontology")
            elif prefix in vendored:
                if iri not in vendored[prefix]:
                    wrong.append(f"{rel}: {iri} is not in the vendored {prefix} vocabulary")
            # a bound namespace with no vendored copy (schema, unit …) is binding-checked only

    for iri, holders in sorted(owners.items()):
        if len(holders) > 1:
            wrong.append(f"{iri} is bound by {len(holders)} pages ({', '.join(sorted(holders))}) — one term, one owner")

    # The reverse direction, scoped to what rule 2 calls its unit: every capability FAMILY the
    # ontologies declare is a word someone answers for. Members and single abilities typed
    # `a orexis:Capability` directly are deliberately out of scope — a member is the family's page's
    # to describe, not a second owner.
    RDFS = rdflib.RDFS
    ag_capability = rdflib.URIRef(str(namespaces["orexis"]) + "Capability")
    families = {str(s) for s in project.subjects(RDFS.subClassOf, ag_capability)}
    for family in sorted(families - set(owners)):
        wrong.append(f"{family} is a capability family no dictionary page binds")

    assert pages, "no concept documents found — the glob stopped matching"
    assert ontologies, "no ontologies found — the globs stopped matching"
    assert declared, "no declared terms found — the ontology parse yielded nothing"
    assert families, "no capability families found — the subclass pattern stopped matching"
    assert owners, "no page binds any term — the term: field stopped being read"
    assert not wrong, "the dictionary and the T-Box disagree:\n  " + "\n  ".join(wrong)


# --- the graphs a document names ---------------------------------------------------------------

#  A bundle writes a graph as `:sensed` and an individual as `:fern_agent` — the same shorthand,
#  and neither has a namespace to check. So this asks one question of both: does the project
#  DECLARE the thing? A graph is declared in an ontology as `…/graph/<name>`, per-agent ones
#  through an `orexis:graphPrefix`; an individual is declared by the world that holds it, which
#  `_declared()` already sweeps up for the term guard above.
#
#  This found #269 — `:attested`, `:opinion`, `:claims`, `:ledger` and `:exp/<agent>` across nine
#  documents, written as if they were graphs. None of them was ever built: the first two were the
#  witness's, dropped by `trusted-agent-mode` before anything wrote them, and the record cited as
#  the authority on who authors what had all three of its graph names wrong.
#
#  Exact rather than a word list, which is the point: the day a graph is renamed, every document
#  naming the old one fails here, and nobody has to remember to update a list of forbidden words.

_GRAPH_BASE = "http://example.org/orexis/graph/"
_SHORTHAND = re.compile(r"`(:[A-Za-z][\w/<>-]*)`")


def _graphs() -> tuple[set[str], set[str]]:
    """Every graph the project declares: fixed names, and the prefixes per-agent ones grow from."""
    from assembly import loader

    fixed, prefixes = set(), set()
    for ttl in loader.sources("*.ttl"):
        text = ttl.read_text()
        fixed |= {iri[len(_GRAPH_BASE):]
                  for iri in re.findall(rf"<({re.escape(_GRAPH_BASE)}[^>]*)>", text)}
    #  THE PER-AGENT PREFIXES ARE THE WRITERS' CONVENTIONS — a graph's name is for eyes and
    #  code asks the class, so no ontology declares one; the helpers that spell them are the
    #  source, asked with a marker id.
    from orexis_agent_deliberation.ontology import pursued_graph, remembered_graph
    from orexis_agent_progression.graphs import intentions_graph
    from orexis_agent_progression.ontology import picks_graph, obligations_graph, promises_graph, desires_graph
    from orexis_capability_review.graphs import evidence_graph, revisions_graph, summaries_graph
    for helper in (picks_graph, desires_graph, promises_graph, obligations_graph, intentions_graph,
                   pursued_graph, remembered_graph, evidence_graph, revisions_graph, summaries_graph):
        name = helper("x")
        assert name.startswith(_GRAPH_BASE) and name.endswith("x")
        prefixes.add(name[len(_GRAPH_BASE):-1])
    #  THE CATALOGUE IS THE ONE FIXED NAME NO ONTOLOGY DECLARES: it describes itself, and the
    #  only spelling is genesis's, which creates it (one-catalogue-describes-every-graph-and-itself).
    from orexis_agent_progression.ontology import CATALOGUE_GRAPH
    assert CATALOGUE_GRAPH.startswith(_GRAPH_BASE)
    fixed.add(CATALOGUE_GRAPH[len(_GRAPH_BASE):])
    return {f for f in fixed if f}, prefixes


def test_no_document_names_a_graph_the_store_has_never_had():
    """Every `:shorthand` a document writes is a graph the store has, or something declared.

    One thing it cannot check: a per-agent graph's AGENT. `:picks/nobody` passes, because the
    prefix is what the ontology declares and the suffix is whatever agents a world happens to
    hold — and a document naming `:picks/fern` as an example is not claiming that world exists.
    The graph before the slash is the part that can rot, and that part is checked.
    """
    absent_on_purpose = {
        # THE WITNESS'S GRAPHS, dropped by trusted-agent-mode before anything wrote them. Four
        # records and one component page narrate them, each explicitly: "does not exist", "was
        # never built", "this said", "becomes asserted".
        ":attested",
        ":attested/<plant>",
        # The judgment graph trusted-agent-mode asked for, which shipped as `:classification`.
        # That record keeps the name it chose, with the amendment beside it.
        ":opinion",
        # And what it shipped as: the graph an agent's own interpretations went to, later the
        # graph each owner typed its graphs into (#708), and since one-catalogue-describes-
        # every-graph-and-itself a row of the catalogue. Five documents narrate the first
        # sense, each in the past tense or beside the record that amended it.
        ":classification",
        # Three writers with three graphs, in agent-centric-epistemics' two-store block. The
        # writers collapsed into one and none of these names was built; the block quotes itself.
        ":ledger",
        ":exp/<agent>",
        # Untrusted peer assertions. Never built and never needed — a bid is a message on the
        # bus, weighed and discarded — which `domain/belief-base.md` says in those words, and
        # which is why the name survives only inside sentences denying it.
        ":claims",
        # PROPOSALS, not drift: three documents name a per-subject or per-witness split of
        # `:sensed` as the next step, each saying in the same breath that `:sensed` is still one
        # shared graph. Naming what does not exist yet is what a seam is for.
        ":sensed/<plant>",
        ":sensed/<subject>",
        ":sensed/<witness>",
        # The decommissioned component, named as the provenance a witnessed fact would carry.
        ":gateway",
        # The authored venue `world/simulation` held until arc 3, when a source offered by
        # someone who states how they match BECAME a market and the venue derived. Two records
        # narrate it: the one that argued for the change, and the one recording that this guard
        # caught it still being named in the present tense.
        ":barrel1_market",
    }
    fixed, prefixes = _graphs()
    declared = _declared()
    docs = concepts()
    assert docs, "no concept documents found — the glob stopped matching"
    assert fixed, "no graphs found — the ontology scan stopped matching"
    assert prefixes, "no per-agent graph prefixes found — the helpers stopped answering"

    def resolves(name: str) -> bool:
        bare = name.lstrip(":")
        if "/" in bare:
            #  A slash is unambiguous: no term has one, so this is a per-agent graph or nothing.
            return bare in fixed or any(bare.startswith(p) and len(bare) > len(p)
                                        for p in prefixes)
        return bare in fixed or bare in declared

    wrong = sorted(
        f"{path.relative_to(BUNDLE)}: `{name}`"
        for path in docs
        for name in set(_SHORTHAND.findall(path.read_text()))
        if name not in absent_on_purpose and not resolves(name)
    )
    assert not wrong, (
        "documents naming a graph the store has never had, or a term nothing declares — the "
        "graphs are enumerable, so this is exact rather than a list of forbidden words:\n  "
        + "\n  ".join(wrong)
    )


#  A section nobody can read is a section nobody reads. `decisions/index.md` had ten headings and
#  one of them held 38 of its 127 entries — a third of the bundle in a flat list called "The mind",
#  which is where anything not obviously about hardware or the market ended up. Thirteen of those
#  38 were not about the mind at all: four guard records, three about vocabulary ownership, two
#  about the market, two about sensing. Nothing was wrong with any single entry; the section had
#  simply stopped meaning anything, and it stopped one entry at a time.
#
#  The cap is not a truth about how many decisions may exist. It is the point at which a heading
#  has to earn itself again — 24 leaves room above today's largest (19) and trips long before a
#  section becomes a dumping ground.
MAX_INDEX_SECTION_ENTRIES = 24


def test_no_index_section_is_a_dumping_ground():
    """Every heading holds a readable number of entries, so a section still names something."""
    oversized, seen = [], 0
    for path in indexes():
        section = "(no heading)"
        counts: dict[str, int] = {}
        for line in path.read_text().splitlines():
            if line.startswith("#"):
                section = line.lstrip("# ").strip()
            elif line.startswith("* ["):
                counts[section] = counts.get(section, 0) + 1
                seen += 1
        oversized += [f"{path.relative_to(BUNDLE)}: {name} — {n} entries"
                      for name, n in counts.items() if n > MAX_INDEX_SECTION_ENTRIES]
    assert seen, "no index entries found — the pattern stopped matching"
    assert not oversized, (
        f"an index section over {MAX_INDEX_SECTION_ENTRIES} entries — split it into headings "
        "that each name something, or the section becomes where records go to be lost:\n  "
        + "\n  ".join(oversized))


def test_a_committed_diagram_is_not_stale():
    """A rendered image is safe to commit only if something notices when it stops matching.

    `tools/render-diagrams.sh` stamps each SVG with the sha256 of the `.puml` it came from, so
    this compares two strings and needs NO renderer — which is the point: a gate that only runs
    where plantuml is installed could not run on a fresh clone (a-guard-that-asks-the-filesystem
    -asks-about-somebodys-machine). Rendering needs the tool; checking never does.
    """
    import hashlib

    sources = sorted((REPO_ROOT / "knowledge" / "diagrams").glob("*.puml"))
    assert sources, "no diagram sources found — the glob stopped matching"
    wrong = []
    for src in sources:
        svg = src.with_suffix(".svg")
        if not svg.exists():
            wrong.append(f"{src.name}: no rendered .svg beside it")
            continue
        want = hashlib.sha256(src.read_bytes()).hexdigest()
        text = svg.read_text()
        marker = "<!-- source-sha256: "
        if marker not in text:
            wrong.append(f"{svg.name}: no source stamp — re-run tools/render-diagrams.sh")
            continue
        got = text.rsplit(marker, 1)[1].split(" ")[0].strip()
        if got != want:
            wrong.append(f"{svg.name}: stale — {src.name} changed since it was rendered")
    assert not wrong, ("committed diagrams are out of step with their sources. Run "
                       "`./tools/render-diagrams.sh`:\n  " + "\n  ".join(wrong))


def test_every_declared_hook_has_an_asker():
    """A hook nobody asks is a contract every module must honour and nothing consumes.

    `orexis:notices` was exactly that for two releases — declared, given a base method and a real
    override in sensing, and asked by NOBODY once the deliberator stopped: freshness had become
    a want, and the hook was left computing the same judgment on request that nobody made
    (#413). Deleting it is only half the fix; this is the half that keeps it deleted.

    An asker is `agent.ask(CONST, …)` or `agent.tell(CONST, …)` for the kernel's own points, or
    a direct call on whoever provides it — `size` and `take` are reached through
    `agent.provider(family)` rather than the choir, which is a different door to the same
    contract and counts.
    """
    import re

    sources = [REPO_ROOT / "agent_old" / "ontology.ttl"]
    sources += sorted((REPO_ROOT / "packages").glob("*/ontology.ttl"))
    declared = []
    for f in sources:
        declared += [(f, n) for n in
                     re.findall(r"^\w*:(\w+) a assembly:Extension", f.read_text(), re.M)]
    #  BOTH prefix forms, and the count is pinned: the kernel writes `orexis:handle` and a package
    #  writes `:record` against its own base. A pattern that caught only one silently checked a
    #  third of the hooks and passed — which is the empty-glob failure wearing a regex.
    assert len(declared) >= 16, (
        f"only {len(declared)} hook declarations found across {len(sources)} ontologies — "
        "the pattern stopped matching one of the two prefix forms")

    code = "\n".join(p.read_text() for tree in ("agent", "packages")
                     for p in (REPO_ROOT / tree).rglob("*.py"))
    orphans = []
    for f, local in declared:
        const = re.sub(r"(?<!^)(?=[A-Z])", "_", local).upper()
        if re.search(rf"\.(ask|tell)\(\s*{const}\b", code) or re.search(rf"\.{local}\(", code):
            continue
        orphans.append(f"{f.relative_to(REPO_ROOT)}: {local} is declared and asked by nobody")
    assert not orphans, ("a hook every module must honour and nothing consumes — wire it or "
                         "retire it (#413):\n  " + "\n  ".join(orphans))
