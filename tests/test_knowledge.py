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

WHY THE ASSERTS ARE AT THE END and never inside the loops: see the root `conftest.py`. A loop
over an empty glob runs its body zero times and passes. Each test here asserts the corpus is
non-empty FIRST, then asserts on a collected list — so an emptied glob fails loudly instead of
going green.
"""

from __future__ import annotations

import itertools
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE = REPO_ROOT / "knowledge"

# What `type` may say. The bundle root and AGENTS.md both state this list in prose; this is the
# copy that fails when they disagree with the files.
#
# FIVE concept types where there were two, and the split was asked for by the pages themselves:
# `auction` opened "an auction is a PROCESS", `bid-matching` called itself "the STEP that turns a
# lot and a set of bids into an allocation", `onboarding` "the PHASE between genesis and a running
# society" — three pages naming their own type in prose because the field could not hold it.
# `Capability` is rule 2's unit and not a subtype of convenience: those pages carry a family term,
# its interchangeable members, and the premise that grants it, which no other kind of page has.
#
# Distribution when the split landed: Concept 10, Process 5, Component 5, Capability 4, Role 4 —
# no type with one member, which is the evidence it is a real division rather than a tidy one. A
# type that drops to one page is a type to fold back, not to defend.
TYPES = {"Decision", "Domain Concept", "Process", "Capability", "Role", "Component", "Runbook"}
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
    """The claim the bundle root makes about itself, held to a real parser rather than a grep."""
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
_TOP = ("agent/", "packages/", "onboarding/", "tests/", "infra/", "tools/", "firmware/", "world/")
_PATH = re.compile(r"`((?:" + "|".join(re.escape(t) for t in _TOP) + r")[A-Za-z0-9_./<>*-]*)`")


def _exists(spec: str) -> bool:
    """A placeholder segment matches anything; a glob is a glob; and prose names a module
    without its extension as often as with it, which is not a broken reference."""
    spec = spec.rstrip("/")
    if not spec:
        return True
    pattern = re.sub(r"<[^>]+>", "*", spec)
    if "*" in pattern:
        return any(REPO_ROOT.glob(pattern))
    return (REPO_ROOT / pattern).exists() or (REPO_ROOT / f"{pattern}.py").exists()


def test_no_document_names_a_path_that_is_not_there():
    """`one-tree-and-one-mechanic` moved the capability tree and 27 documents went on naming the
    old path in the present tense. Nothing failed, because nothing was looking.

    A record legitimately narrates a path that USED to exist. Those are the exceptions below, and
    each one is a sentence that says "was" or "at the time" or draws a before/after.
    """
    absent_on_purpose = {
        # one-tree-and-one-mechanic: the before/after diagram, and the argument that the old
        # name already spelled the new idea.
        "agent/capabilities/<name>/",
        "agent/capabilities/market",
        # repository-layout: a section titled "Why there is no `agent/kernel/`" — the whole
        # point is that this path does not exist, and a day it does is a day to reread that
        # section rather than to edit this list.
        "agent/kernel/",
        # repository-layout: the two-distribution layout, past tense — "used a `src` layout and
        # were pip-installed separately".
        "onboarding/src/onboarding/",
        "onboarding/src/onboarding",
        # where-the-belief-base-lives, describing what it removed: "`infra/fuseki/` no longer
        # exists".
        "infra/fuseki/",
        # capability-packages: a throwaway package dropped in to prove the loader finds one
        # without being told, then deleted. It is evidence, not a path.
        "packages/capability/forecast/",
        # domain/world: a runbook step. `world/orchard/` is what the reader is being told to
        # CREATE, so its absence is the precondition.
        "world/orchard/world.ttl",
    }
    docs = concepts()
    missing = []
    for path in docs:
        for spec in set(_PATH.findall(path.read_text())):
            if spec in absent_on_purpose or _exists(spec):
                continue
            missing.append(f"{path.relative_to(BUNDLE)}: `{spec}`")
    assert docs, "no concept documents found — the glob stopped matching"
    assert not missing, (
        "documents naming a path that is not on disk — a rename that did not reach the "
        "bundle:\n  " + "\n  ".join(sorted(missing))
    )


# --- the one table that claims to be checkable -------------------------------------------------


def test_the_deliberation_table_matches_what_is_built():
    """`domain/deliberation.md` says which members exist so nobody has to read the records to
    find out. The table is only worth having if it cannot drift."""
    from agent import loader

    package = next(p for p in loader.of_kind("capability") if p.name == "deliberation")
    built = {str(cls.CAPABILITY).rsplit("#", 1)[-1] for cls in package.provides()}
    declared = set(
        re.findall(r"^:(\w+) a :\w*Capability", (package.path / "ontology.ttl").read_text(), re.M)
    )
    table = (BUNDLE / "domain" / "deliberation.md").read_text()
    rows = dict(re.findall(r"^\| `deliberation:(\w+)` \|[^|]*\| \*\*(yes|no)\*\*", table, re.M))

    assert declared, "no members declared — the ontology pattern stopped matching"
    assert rows, "no member table found in domain/deliberation.md"
    assert set(rows) == declared, (
        f"the table lists {sorted(rows)}; the ontology declares {sorted(declared)}"
    )
    assert {m for m, v in rows.items() if v == "yes"} == built, (
        f"the table says {sorted(m for m, v in rows.items() if v == 'yes')} are built; "
        f"PROVIDES says {sorted(built)}"
    )


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
    """Every local name any project TTL declares — packages and the ratified worlds both.

    Worlds are included because a domain page legitimately names an individual as an example,
    and an individual is declared by the world that holds it rather than by an ontology.
    """
    names: set[str] = set()
    for ttl in list((REPO_ROOT / "packages").rglob("*.ttl")) + \
               list((REPO_ROOT / "world").rglob("*.ttl")):
        text = ttl.read_text()
        names |= set(re.findall(r"^:(\w+)\b", text, re.M))
        names |= {local for _, local in _TERM.findall(text)}
    return names


def test_a_domain_page_names_only_terms_that_exist():
    # Terms the pages state do NOT exist. Each is a sentence saying so, which is a legitimate and
    # useful thing for a page to say — and is exactly why this cannot be a bare existence check.
    said_not_to_exist = {
        # domain/auction.md: "no `ag:Auction` anywhere", "There is no `ag:Auction` to point at."
        "ag:Auction",
        # domain/genesis-process.md: "There is no `ag:worldKind`".
        "ag:worldKind",
        # domain/world.md, under "What this replaced": the simulation design that was removed.
        "ag:models", "ag:ModelledSubject", "ag:SimulatedSensing",
        # domain/desire.md names this to say it is NOT a name that exists — it is what an earlier
        # version of the page invented for a constraint that has no shape of its own (#275).
        # When #275 lands and gives that constraint a real name, this entry comes out.
        "desire:UnwatchedDesireShape",
    }

    from agent import loader
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
}


def _bound_terms(meta: dict) -> list[str]:
    value = meta.get("term")
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def test_a_dictionary_term_is_a_declared_one():
    import rdflib

    from agent.store import NAMESPACES

    ontologies = list((REPO_ROOT / "packages").rglob("ontology.ttl")) + \
                 list((REPO_ROOT / "firmware").glob("*/ontology.ttl"))
    project = rdflib.Graph()
    for ttl in ontologies:
        project.parse(ttl)
    declared = {str(s) for s in project.subjects() if isinstance(s, rdflib.URIRef)}

    vendored: dict[str, set[str]] = {}
    for prefix, filename in _VENDORED_VOCABULARIES.items():
        vocabulary = rdflib.Graph()
        vocabulary.parse(REPO_ROOT / "tests" / "fixtures" / "vocabularies" / filename)
        vendored[prefix] = {str(s) for s in vocabulary.subjects() if isinstance(s, rdflib.URIRef)}

    #  Longest binding first, so nested namespaces (ag: inside every package's) resolve to the
    #  package that actually owns the term rather than to the kernel.
    bindings = sorted(((str(iri), prefix) for prefix, iri in NAMESPACES.items()),
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
            if str(NAMESPACES[prefix]).startswith("http://example.org/agora"):
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
    # `a ag:Capability` directly are deliberately out of scope — a member is the family's page's
    # to describe, not a second owner.
    RDFS = rdflib.RDFS
    ag_capability = rdflib.URIRef(str(NAMESPACES["ag"]) + "Capability")
    families = {str(s) for s in project.subjects(RDFS.subClassOf, ag_capability)}
    for family in sorted(families - set(owners)):
        wrong.append(f"{family} is a capability family no dictionary page binds")

    assert pages, "no concept documents found — the glob stopped matching"
    assert ontologies, "no ontologies found — the globs stopped matching"
    assert declared, "no declared terms found — the ontology parse yielded nothing"
    assert families, "no capability families found — the subclass pattern stopped matching"
    assert owners, "no page binds any term — the term: field stopped being read"
    assert not wrong, "the dictionary and the T-Box disagree:\n  " + "\n  ".join(wrong)
