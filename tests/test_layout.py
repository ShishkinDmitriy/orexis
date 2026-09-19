"""The agent image carries no operator code, asserted rather than implied.

This used to be a property of the packaging: two distributions, and an agent installed only
one of them. It never was, quite. Nothing here installs from an index — the image copies
directories and runs `pip install -e .` — so what actually kept `onboarding/` out of an agent
was the Containerfile not naming it, and a reader had to infer that from two pyproject files
that said nothing about images.

The boundary is here, and it stayed here when the packages became twenty-one distributions of
their own: a dependency graph is not a boundary. If someone adds `COPY onboarding/` for
convenience, this fails; before, nothing did.

Deliberately reads the Containerfile rather than building: a test that needed a container
runtime would be skipped on every machine that lacks one, which is exactly the machine where
someone is most likely to be editing quickly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTAINERFILE = REPO_ROOT / "Containerfile"

# What an agent legitimately runs: the KERNEL that loads packages, and the packages. `packages/`
# holds a capability's Python and a part's ontology in one tree, and onboarding reads the same
# terms without importing any of it, so neither side owns it.
#
# This list carries more weight than it used to. Capability Python lived under `agent/` before,
# so the tree itself showed which of it a runtime loads; it does not show that now, and this
# file plus the import contracts are the whole of the boundary.
#  firmware/ is admitted for its ontologies alone — the third T-Box source (#175) — and the
#  .containerignore exception narrows the COPY to them; the test below holds both halves.
#  `assembly` is what FINDS packages, so an agent that loads any needs it — the kernel is
#  one of the things it assembles (the-assembly-is-not-the-mind).
ALLOWED_TREES = {"assembly", "agent", "packages", "firmware"}

# Never in an agent image. `orexis-influx` reads the admin token, which opens every bucket in the
# store and which no agent may ever hold; the surest guarantee is that the code using it is
# absent. See knowledge/domain/onboarding.md.
FORBIDDEN_TREES = {"onboarding"}


def copied_paths() -> list[str]:
    """Every source path the image copies, as written."""
    out: list[str] = []
    for line in CONTAINERFILE.read_text().splitlines():
        line = line.strip()
        if not line.upper().startswith("COPY "):
            continue
        parts = re.split(r"\s+", line)[1:]
        out.extend(p for p in parts[:-1] if not p.startswith("--"))
    return out


def test_the_image_copies_something():
    """A guard on the guard: if COPY were renamed or the file moved, every assertion below
    would pass vacuously and the boundary would be unwatched."""
    assert copied_paths(), f"no COPY lines found in {CONTAINERFILE} — this test is not looking"


@pytest.mark.parametrize("forbidden", sorted(FORBIDDEN_TREES))
def test_the_agent_image_carries_no_operator_code(forbidden):
    offenders = [p for p in copied_paths() if p.split("/")[0].strip("./") == forbidden]
    assert not offenders, (
        f"the Containerfile copies {offenders} into the agent image. {forbidden}/ mints "
        "credentials and reads the admin token; an agent must not hold that code at all. "
        "If this is deliberate, the isolation design in "
        "knowledge/decisions/series-and-bus-isolation.md is what needs changing first."
    )


#  A vocabulary of files the loader already knows how to find, and the accessor that answers
#  for each. Globbing a tree for one of these is re-deriving what the loader assembles — which
#  is the mistake this guard exists to refuse.
_LOADER_ANSWERS = {
    "*.ttl": "loader.sources('*.ttl'), or ontology_files() / shapes_files() / action_files()",
    "*.ru":  "loader.sources('*.ru'), or rule_files() for the derivations",
    "*.rq":  "loader.sources('*.rq'), or review_rules()",
    "*.py":  "loader.sources('*.py')",
}


@pytest.mark.parametrize("tree", ["tests", "onboarding"])
def test_no_scan_rederives_what_the_loader_already_assembles(tree):
    """Ask the loader what to scan. Never glob a package tree for it.

    THE PATTERN BEHIND FIVE DEFECTS, made a rule. Every guard in this repo that reads source
    text has to decide which files to read, and five of them decided by globbing
    `packages/**` — correct while every module lived there, and silently wrong the day the mind
    came into the kernel. They did not fail. They NARROWED, and narrowing is invisible: a glob
    can be asserted non-empty, and four of these had exactly that assertion beside them, passing
    the whole time.

    What it cost: one parametrised case lost from the subclass-path scan; the kernel's whole
    vocabulary dropped from two term censuses; every IRI in `agent/*.py` unread by the linker.
    Two real defects hid in the gap — `orexis:amountL`, undeclared and in use for months, and five
    terms of a change sitting inside an `rdfs:comment` as prose, which the suite passed over.

    So the rule is not "remember to include the kernel". It is that a scan does not get to
    decide which trees exist — `loader.sources()` does, and it is one place to fix when the
    layout moves again. See knowledge/decisions/the-mind-is-not-a-package.md.

    Scoped to the file kinds the loader has an answer for. A glob for something else — a
    `wokwi/` directory, a world's TriG — is nobody's business but the test's.
    """
    offenders = []
    for path in sorted((REPO_ROOT / tree).rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#")[0]
            #  A GLOB of the package tree, not a mention of it. `loader.sources()` partitioned by
            #  `"packages" in p.parts` is the fix and names both — the defect is reaching for the
            #  directory yourself, which is what `.glob(` / `.rglob(` on that path means.
            if ".glob(" not in code and ".rglob(" not in code:
                continue
            if "PACKAGES_ROOT" not in code and '"packages"' not in code and "'packages'" not in code:
                continue
            for pattern, answer in _LOADER_ANSWERS.items():
                if f'"{pattern}"' in code or f"'{pattern}'" in code:
                    offenders.append(
                        f"{path.relative_to(REPO_ROOT)}:{n} globs the package tree for "
                        f"{pattern} — ask {answer}")
    assert not offenders, (
        "a scan re-deriving what the loader assembles:\n  " + "\n  ".join(offenders))


def test_the_kernel_stands_alone_with_no_packages_at_all(tmp_path, monkeypatch):
    """An empty `packages/` is a complete build — the claim every other rule here rests on.

    "A package is optional" was said long before it was true. Two things made it false at once:
    the base vocabulary WAS a package (`packages/core/orexis/`, a family of exactly one that
    nothing could remove), and the kernel imported three of them — for the mind, which is not
    plug-in-able and had no business being a grant. Both are fixed, so the sentence can be a
    test rather than an aspiration.

    What is asserted is the KERNEL's self-sufficiency, not that a useful society needs nothing:
    every shipped world names `water:`, `mqtt:` and `part:` terms and would not validate here.
    The claim is narrower and load-bearing — the thing that LOADS packages does not need one.
    """
    from assembly import loader

    #  EVERY cache the loader has, found by looking. This was a hand-list of four, and the
    #  test populates far more than four while the tree is empty — `shapes_files`, `hooks`,
    #  `_namespace_owners` — so they survived the restore holding kernel-only answers and
    #  poisoned every later test that built an agent. `pytest tests/test_layout.py
    #  tests/test_hooks.py` failed deterministically and the full suite hid it, because
    #  `-n auto` puts the two files on different workers.
    caches = tuple(v for v in vars(loader).values() if hasattr(v, "cache_clear"))
    monkeypatch.setattr(loader, "PACKAGES_ROOT", tmp_path / "nothing-here")
    for cache in caches:
        if cache is not None and hasattr(cache, "cache_clear"):
            cache.cache_clear()
    try:
        found = loader.packages()
        assert found == (loader.ASSEMBLY, loader.KERNEL), (
            "with no packages the build should be the two roots — what assembles, and what it "
            f"assembles onto — got {[p.name for p in found]}")
        assert loader.registry() == {}, "no packages, no capabilities to implement"
        assert loader.prefixes().get("orexis"), "the kernel still declares its own namespace"

        #  And it is a WORKING build, not just a non-empty list: the kernel ships all four of
        #  the things a package may ship, and the vocabulary it declares is really there.
        assert loader.shapes_files() == (loader.KERNEL.file(loader.SHAPES),), \
            "with no packages, the only shapes are the kernel's own"
        #  AND NO DERIVATION: the kernel's one rule minted every agent's pick record graph by
        #  name, in the world graph, for nobody to read — a graph is classified by its owner
        #  when it writes it, and a name is for eyes.
        assert loader.rule_files() == (), "with no packages there is nothing to derive"

        import rdflib
        g = rdflib.Graph()
        g.parse(loader.KERNEL.file(loader.ONTOLOGY), format="turtle")
        assert (rdflib.URIRef("http://example.org/orexis#Agent"), None, None) in g, \
            "the kernel declares what an agent IS without help from anything"

        #  `ontology_files()` may still yield more than the kernel's, and that is right rather
        #  than a leak: a FIRMWARE directory is a third T-Box source (#175), discovered beside
        #  the packages and not one of them. So the assertion is about packages, not about
        #  everything the loader reads.
        from_packages = [f for f in loader.ontology_files()
                         if not str(f).startswith(str(loader.REPO_ROOT / "firmware"))]
        assert from_packages == [loader.ASSEMBLY.file(loader.ONTOLOGY),
                                 loader.KERNEL.file(loader.ONTOLOGY)], \
            f"a package ontology survived an empty packages tree: {from_packages}"
    finally:
        for cache in caches:
            if cache is not None and hasattr(cache, "cache_clear"):
                cache.cache_clear()


def test_the_image_copies_only_what_an_agent_runs():
    """The positive half. Forbidding one name only catches the tree we thought of; this
    catches the next one, which is the one that will actually be added."""
    trees = {p.split("/")[0].strip("./") for p in copied_paths() if "/" in p or "." not in p}
    unexpected = trees - ALLOWED_TREES - {"pyproject.toml"}
    assert not unexpected, (
        f"the agent image copies {sorted(unexpected)}, which is not part of what an agent runs. "
        f"Expected only {sorted(ALLOWED_TREES)} — add it here deliberately, or do not copy it."
    )


def test_onboarding_is_not_hidden_from_the_build_context():
    """The boundary must be visible where the decision is made.

    Ignoring `onboarding/` in .containerignore would also keep it out of the image, and would
    move the reasoning into a file nobody reads while making this test pass for the wrong
    reason. The Containerfile is where it is decided.
    """
    ignored = [
        line.strip() for line in (REPO_ROOT / ".containerignore").read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert "onboarding" not in ignored, (
        ".containerignore excludes onboarding/. That works, but it hides the boundary: the "
        "Containerfile should be the one place that says what an agent image contains."
    )


def test_the_firmware_ontologies_reach_the_image_and_nothing_else_of_firmware_does():
    """The third T-Box source (#175) must actually arrive, and only it.

    Found on the bench, not by a test: the sensing world's agent booted without firmware/ in
    its image, derived no sensing capability from a board typed by its firmware class, and
    subscribed to NOTHING — silently, because the loader tolerates the missing tree. The COPY
    is half the fix; the ignore-file exception is the other half, and it is load-bearing for
    secrets: a generated include/config.h carries the wifi and a device credential, so the
    exception must admit the ontologies alone. Asserted textually on both files, the same way
    the onboarding boundary is.
    """
    assert "firmware/" in copied_paths(), (
        "the Containerfile no longer copies firmware/ — a world that types a board by its "
        "firmware class will boot an agent that derives no sensing capability at all"
    )
    ignored = [
        line.strip() for line in (REPO_ROOT / ".containerignore").read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert "firmware/*/*" in ignored and "!firmware/*/ontology.ttl" in ignored, (
        ".containerignore must exclude everything under firmware/ EXCEPT the ontologies: "
        "wider admission ships credentials (include/config.h), narrower ships a T-Box "
        "source missing. The exclusion is one level deep (firmware/*/*) deliberately — "
        "excluding the directories themselves prunes the walk and the ! exception never fires"
    )


# --- what an AGENT is given, which is less than the world -------------------------------------

def test_an_agent_is_given_the_society_and_not_the_hardware():
    """It never asks which pin a probe is on.

    The runtime queries what it acts for, what it may poll, which topics reach that sensor and
    how it is driven. Pins, wires, rails, silkscreen markings and part models are the
    sovereign's: they decide what CAN be built and what a board must be flashed with, and once
    it is built the agent talks to topics.

    Asserted on the CONTENT of what an agent would load rather than on the filename, so it also
    catches a pin assignment put into world.ttl — where nothing about the file name would warn
    anyone. Enforcement is that the container does not have the file at all, which is the same
    shape as the Containerfile keeping onboarding out of the image.
    """
    import rdflib

    from agent import genesis

    HARDWARE_NAMESPACES = (
        "http://example.org/orexis/microcontroller#",
        "http://example.org/orexis/esp32#",
        "http://example.org/orexis/wokwi#",
        "http://example.org/orexis/dht11#",
        "http://example.org/orexis/rgb-led#",
        "http://example.org/orexis/moisture-probe#",
        "http://example.org/orexis/onewire#",
        "http://example.org/orexis/i2c#",
    )

    for world in genesis.worlds():
        #  A world file is TriG (genesis parses it so), and hanoi's desire.ttl carries a
        #  GRAPH block — a plain Graph parsed as turtle raises, and parsed as trig silently
        #  DROPS the named-graph triples, which is the vacuous direction. ConjunctiveGraph
        #  keeps every quad and iterates across contexts.
        g = rdflib.ConjunctiveGraph()
        for path in genesis.society_files(genesis.world_dir(world)):
            g.parse(path, format="trig")
        leaked = {str(t) for triple in g for t in triple
                  if str(t).startswith(HARDWARE_NAMESPACES)}
        assert not leaked, (
            f"{world}: an agent would be handed hardware vocabulary it never queries: "
            f"{sorted(leaked)[:5]}")


def test_the_society_hosting_agrees_with_the_wiring():
    """One fact said twice, in two FILES, to two audiences — held to agreeing.

    It used to be said in two vocabularies as well: `mc:carries` in the wiring, `sosa:hosts` in
    the society, held together by a subproperty axiom. `mc:carries` is gone and both files say
    `sosa:hosts`, which removes the vocabulary half of the problem and leaves the half that was
    always the real one — the society restates the hosting because an agent is never handed the
    wiring, and only the SOVEREIGN loads both, so nothing in the running system would notice
    them diverging.

    Checked in the direction drift actually goes. Rewiring a probe onto a different board edits
    `hardware.ttl`; the society keeps the old answer and every gate stays green, because each
    file is internally consistent and no query spans them. So: wherever the wiring hosts
    something the society also names, the society must say the same — and nothing in the society
    may claim a host the wiring contradicts.

    NOT symmetric, and sharing a word does not change that — the reason is stronger than
    `silence is not contradiction`. **The society legitimately hosts things the wiring does
    not.** `orexis:air_sensor_fern sosa:hosts` its two channels and the wiring names neither of
    them; a simulated device has no wiring at all. So a society-side pair with no counterpart
    cannot be an error, and unwiring — deleting a part from `hardware.ttl` while the society
    still hosts it — is still not caught. Closing that needs a rule that can tell a board's
    hosting from a part's, which nothing here can: the society does not type the board as a
    `mc:Microcontroller`, because `mc:` is exactly what the test above forbids it.

    The other direction is likewise deliberate. `orexis:status_led_fern` is hosted by the board and
    absent from the society, which is correct: an agent polls sensors and has no business
    knowing about an indicator it can never observe.
    """
    import rdflib

    from agent import genesis

    SOSA = rdflib.Namespace("http://www.w3.org/ns/sosa/")

    for world in genesis.worlds():
        world_path = genesis.world_dir(world)
        #  TriG for the society files, for the reason the hardware-leak test states above.
        society, wiring = rdflib.ConjunctiveGraph(), rdflib.Graph()
        for path in genesis.society_files(world_path):
            society.parse(path, format="trig")
        for name in genesis.HARDWARE_FILES:
            if (world_path / name).exists():
                wiring.parse(world_path / name, format="turtle")
        if not wiring:
            continue  # a world with no stated hardware has nothing to disagree with

        SSN = rdflib.Namespace("http://www.w3.org/ns/ssn/")
        carried = set(wiring.subject_objects(SOSA.hosts))
        # Since #99 the wiring's hosting is what its DEPLOYMENT produces, so this check
        # performs the same two-link entailment the closure does: a platform in a deployment
        # that deploys a system hosts that system. Asserted hosts stay covered — a wiring may
        # still say it directly, and a part hosting its channels does.
        for platform, deployment in wiring.subject_objects(SSN.inDeployment):
            for system in wiring.objects(deployment, SSN.deployedSystem):
                carried.add((platform, system))
        hosted = set(society.subject_objects(SOSA.hosts))
        named = {s for s, _, _ in society} | {o for _, _, o in society}

        missing = {(h, t) for h, t in carried if t in named} - hosted
        assert not missing, (
            f"{world}: the wiring carries {sorted(str(t) for _, t in missing)} and the society "
            f"does not host it — an agent would not know which board its sensor is on")

        # And nothing may claim a host the wiring puts elsewhere. Only pairs the wiring
        # actually states are checked — it names no channel of the KY-015, so the society states
        # that chain alone rather than in contradiction to anything. That used to be guaranteed
        # by `mc:carries` having mc:Microcontroller for its domain; it is now a fact about what
        # the wiring says rather than about what it could say, which is weaker as a guarantee
        # and identical in effect, because a domain axiom nothing materialises guaranteed
        # nothing either.
        carriers = {t: h for h, t in carried}
        contradicted = {(h, t) for h, t in hosted if t in carriers and carriers[t] != h}
        assert not contradicted, (
            f"{world}: the society hosts {sorted((str(h), str(t)) for h, t in contradicted)} "
            f"but the wiring mounts it elsewhere")


# Everything a subject can honour, in seconds. One pattern, and the SAME one for both sides of
# the guard below — which is the whole of what the `owl:hasValue` restriction bought. The wiring
# side used to need a hand-walk the society side did not: part, its `rdf:type`, that CLASS's
# capability, that capability's frequency, across two graphs. `agent/inference.py` rule 5 does the
# class hop now, so both sides are read by asking what the subject HAS.
_WHAT_IT_CAN_HONOUR = """SELECT ?subject ?seconds WHERE {
    ?subject ssn-system:hasSystemCapability ?capability .
    ?capability ssn-system:hasSystemProperty ?frequency .
    ?frequency a ssn-system:Frequency ; schema:value ?seconds ; schema:unitCode unit:SEC }"""


def test_the_society_repeats_every_limit_the_wiring_states():
    """A device's floor is stated on the PART and needed by the AGENT, which is never given the
    part. So it is said twice — once on `dht11:Dht11` in the vocabulary, and again on each sensor
    that part hosts in the society — and only the sovereign loads both.

    The vocabulary states it ONCE and reaches instances by entailment: `dht11:Dht11` is put under
    an `owl:hasValue` restriction, so a sovereign that loads the wiring observes the capability on
    `orexis:air_sensor_fern` with nobody having written it there. What that does NOT cross is the
    boundary — an agent is given no `a dht11:Dht11`, so nothing entails anything for it, and the
    society must still repeat the number. An agent may know a part's properties and not its
    identity. See knowledge/decisions/what-is-true-of-a-part-is-true-of-every-one-of-them.md.

    So this guard survives the entailment; what it stops doing is walking the class hop by hand.
    Each side is built as its own world, put through the same closure the sovereign runs, and
    asked the same question.

    Checked in the direction drift goes. A part gaining a limit, or having it changed, is an edit
    to the vocabulary; the society keeps the old answer and every gate stays green, because each
    file is internally consistent and no query spans them. The agent then commits to a cadence
    its board will never keep, which is the whole of #59.

    NOT symmetric, and for a different reason than the hosting guard above. There it was that a
    hardware-only part must not be forced into the society. Here it is that a society MAY state a
    floor the wiring does not — a simulated device has no part and no datasheet, and a deployment
    that knows its board wakes slowly on battery is stating something true that no class
    declares. Extra is allowed; missing and contradicting are not.
    """
    from agent import genesis, inference
    from assembly import loader
    from orexis_agent_progression.ontology import ONTOLOGY_GRAPH, WORLD_GRAPH
    from orexis_agent_progression.store import Store, bindings

    t_box = "\n".join(path.read_text() for path in loader.ontology_files())

    def built(paths):
        """The world those files describe, entailments and all — as the sovereign would build it,
        except that it is handed one SIDE rather than the whole. That is deliberate: merge the two
        and the question "does the society repeat this?" stops having an answer."""
        st = Store()
        st.put_graph(ONTOLOGY_GRAPH, t_box)
        st.put_graph(WORLD_GRAPH, "\n".join(p.read_text() for p in paths), dataset=True)
        inference.materialise(st)
        return st

    def floors(st):
        out = {}
        for row in bindings(st.query(_WHAT_IT_CAN_HONOUR)):
            out.setdefault(row["subject"], set()).add(int(row["seconds"]))
        return out

    compared = 0  # see the assertion at the end, which is the point of counting

    for world in genesis.worlds():
        world_path = genesis.world_dir(world)
        hardware = [world_path / name for name in genesis.HARDWARE_FILES
                    if (world_path / name).exists()]
        if not hardware:
            continue  # no parts, so nothing the society could be failing to repeat

        society = built(genesis.society_files(world_path))
        said = floors(society)
        # Whatever a part is composed of, or the part itself where it is composed of nothing — a
        # single-property probe IS its sensor and carries the limit directly, while a KY-015 is a
        # system whose two channels carry it and which states none of its own.
        #
        # BOTH relations, because the society uses both and means the same thing by them here: a
        # board `sosa:hosts` the parts bolted to it, and a part `ssn:hasSubSystem` the channels it
        # is read through. A floor is a property of the physical device, so it reaches either way
        # — the KY-015's two channels come out of one 40-bit frame and neither can be had faster
        # than the frame. Following only `sosa:hosts` was the second thing wrong with this guard:
        # the same PR that killed the query above also made the KY-015's channels its
        # `ssn:hasSubSystem`, so even a live version would have compared the wrong subject — and
        # the first break hid the second.
        composed = {}
        for row in bindings(society.query(
                "SELECT ?part ?sensor WHERE { ?part sosa:hosts|ssn:hasSubSystem ?sensor }")):
            composed.setdefault(row["part"], set()).add(row["sensor"])

        for part, stated in floors(built(hardware)).items():
            for sensor in composed.get(part) or {part}:
                if not bindings(society.query(f"SELECT ?p WHERE {{ <{sensor}> ?p ?o }} LIMIT 1")):
                    continue  # the society does not mention it, so it repeats nothing
                compared += 1
                assert said.get(sensor, set()) >= stated, (
                    f"{world}: the wiring says {sorted(stated)}s for <{sensor}> and the society "
                    f"says {sorted(said.get(sensor, set()))}s — an agent would commit to a "
                    f"cadence its board will not keep")

    # The guard on the guard, and it is here because this test WAS dead. PR #95 renamed
    # `sensing:seconds` to schema.org's `value`/`unitCode` pair; the walk above still asked for
    # the old term, found nothing anywhere, and passed every run since by having nothing to
    # compare. Measured on the commit before this one: zero parts reached an assertion.
    #
    # Every "if not, continue" in a guard is a way for it to pass by doing nothing, and each one
    # here is legitimate — a world with no wiring, a part with no datasheet floor, a part the
    # society never names. The cost of legitimate skips is that total silence looks identical to
    # total success. So count, and refuse the count of zero. Same move as test_store.py asserting
    # its globs are non-empty, for the same failure arriving by a different route.
    assert compared, ("this guard compared nothing at all. Either no world states a hardware "
                      "floor any more, or the query above has drifted off the vocabulary again")


def test_the_compose_file_does_not_mount_hardware_at_an_agent():
    """The other half, and the one that actually enforces it: a rule the agent is trusted to
    follow is not a boundary. What keeps the wiring out of an agent is that the file is not in
    its filesystem."""
    from agent.config import REPO_ROOT
    from agent import genesis

    for world in genesis.worlds():
        compose = REPO_ROOT / "world" / world / "compose.yaml"
        if not compose.exists():
            continue
        for name in genesis.HARDWARE_FILES:
            assert f"/{name}:" not in compose.read_text(), (
                f"{world}/compose.yaml mounts {name} into an agent — regenerate with "
                f"`orexis-compose {world}`")


def test_a_packages_python_namespace_is_the_one_its_ontology_declares():
    """`terms.py` writes `NS` so Python can name a term without parsing Turtle, and
    `ontology.ttl` declares the same namespace so a query can reach it through the prefix the
    loader assembles. Two copies of one fact, and nothing but this holds them together.

    Drifting them apart fails in the worst available way: Python would build terms in one
    namespace while SHACL validated them in another, and a world would conform while the agent
    reading it found nothing — an empty result, which is not an error.
    """
    import importlib

    from assembly import loader

    checked = []
    for package in loader.packages():
        if not (package.path / "terms.py").exists():
            continue
        ns = getattr(importlib.import_module(f"{package.import_name}.terms"), "NS", None)
        if ns is None:
            continue  # a package still living in the kernel's `orexis:` names no namespace of its own
        declared = {iri for iri in loader.prefixes().values()}
        assert ns in declared, (
            f"{package.name}/terms.py declares NS={ns!r}, which no ontology.ttl declares as a "
            "prefix — the loader cannot give a query the prefix to reach it"
        )
        assert ns in (package.file("ontology.ttl") or package.path).read_text(), (
            f"{package.name}/terms.py declares NS={ns!r} but its own ontology.ttl does not — "
            "Python would build terms in a namespace the vocabulary never defines"
        )
        checked.append(package.name)
    assert checked, "no package declares a namespace of its own — this guard is checking nothing"


# --- the prose is checkable too ---------------------------------------------------------------

# Instances that AGENTS.md names on purpose, as the thing rule 1 forbids. They are not terms and
# must never be declared — naming them here is what keeps the check below from being weakened to
# "any word with a colon in it".
_COUNTER_EXAMPLES = {"orexis:fern_agent", "orexis:world"}


@pytest.mark.parametrize("doc", ["README.md", "AGENTS.md"])
def test_the_docs_only_name_terms_that_exist(doc):
    """Every `prefix:Term` in the two entry documents is declared by some package.

    Written after finding EIGHT in README.md that no vocabulary had declared since the namespace
    split — `orexis:senseMode`, `orexis:Subscribing`, `orexis:readingTopic` and five more. Every one had a
    live successor in another namespace, so the prose was not vague, it was wrong, and nothing
    failed: a renamed term leaves no dangling reference for a reader to trip over.

    Prose is where this project keeps its reasoning, so prose going stale is not cosmetic. The
    same rename swept the code, the shapes and the worlds, and stopped at the door of the file
    people read first.
    """
    import re

    import rdflib

    from assembly import loader

    # The census is built from the PARSED graphs, not from the files' spellings. It used to
    # be a regex over the text, which went quiet the day ontologies took the default prefix
    # for their own terms (#179): `:Actuation` matched nothing, so every doc mention of
    # `actuation:Actuation` read as undeclared. Resolving IRIs through the discovered
    # prefixes keeps the guard's point — a renamed term vanishes from the graph exactly as
    # it vanished from the text — without caring how a file chooses to write itself.
    inverse = {iri: label for label, iri in loader.prefixes().items()}
    declared = set()
    #  Shapes as well as ontologies. A SHAPE is a declared thing and prose may legitimately
    #  name one — AGENTS.md cites `orexis:KeeperShape` to say what a stake still decides. While the
    #  shapes lived in packages this cost nothing to miss, because the docs happened not to name
    #  one; the kernel's shapes are named in the entry documents now.
    for path in loader.ontology_files() + loader.shapes_files():
        g = rdflib.Graph()
        g.parse(path, format="turtle")
        for triple in g:
            for node in triple:
                if not isinstance(node, rdflib.URIRef):
                    continue
                for ns, label in inverse.items():
                    if str(node).startswith(ns):
                        declared.add(f"{label}:{str(node)[len(ns):]}")
    known = set(loader.prefixes()) | {"orexis"}

    named = {t for t in re.findall(r"`([a-z][a-z0-9-]*:[A-Za-z][A-Za-z0-9_]*)`",
                                   (REPO_ROOT / doc).read_text())
             if t.split(":")[0] in known}
    assert named, f"{doc} names no project terms at all — this guard checks nothing"

    missing = sorted(named - declared - _COUNTER_EXAMPLES)
    assert not missing, (
        f"{doc} names {missing}, which no package declares. A renamed term leaves the prose "
        f"wrong rather than broken, so nothing else will tell you."
    )


def test_a_packages_own_tests_are_actually_collected():
    """A package may carry its own tests. Nothing would notice if they stopped running.

    Measured before this was allowed: with `testpaths = ["tests"]`, a `test_*.py` inside a
    package is collected by NEITHER `pytest tests` NOR a bare `pytest`. It runs only when named
    by path — so the suite goes green having skipped it, and the count moves by an amount nobody
    is watching. That is exactly how the layout move lost 143 cases (see
    knowledge/decisions/one-tree-and-one-mechanic.md) and it is issue #106's shape.

    So this asserts the link between the two facts rather than either alone: if any package
    carries a test, `testpaths` must name the tree it lives in.
    """
    import tomllib

    packages = REPO_ROOT / "packages"
    carried = sorted(p.relative_to(REPO_ROOT) for p in packages.rglob("test_*.py"))
    if not carried:
        pytest.skip("no package carries its own tests yet")

    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    testpaths = config["tool"]["pytest"]["ini_options"]["testpaths"]
    assert "packages" in testpaths, (
        f"{[str(p) for p in carried]} live inside packages/, and testpaths is {testpaths}. "
        f"They are collected by neither `pytest tests` nor a bare `pytest` — the suite would "
        f"pass without ever running them."
    )


def test_onboarding_names_no_domain():
    """The domain is a plug-in, and onboarding is what must survive the swap.

    A generator that names `water:` anything works for exactly one domain and fails the next
    one silently — the sim-compose dose join did precisely that, twice: interpolated
    `water:hasTarget` outlived the term's deletion (#120) and matched nothing until the first
    live run's UNMET flag exposed it. The cure is not the right domain term but NO domain
    term: the market vocabulary's `aboutProperty` contract carries everything a generator
    needs. Held here as text, because SPARQL interpolation is invisible to lint-imports.
    """
    from pathlib import Path

    for path in sorted(Path("onboarding").glob("*.py")):
        assert "example.org/orexis/water" not in path.read_text(), \
            f"{path} names the water domain — a generator must survive the domain swap"


def test_the_kernel_names_no_domain():
    """The sibling of the onboarding guard, one level down (#148). `agent/` is the kernel:
    it loads worlds, stores, capabilities — and for a long time it also loaded every plant's
    physics through the water domain's own terms, into a dict nothing read. Dead code and a
    domain leak are the usual pairing: a fact nobody consumes is a fact nobody notices the
    kernel had no business naming. Prose may say water (docstrings narrate history); no IRI
    may."""
    from pathlib import Path

    for path in sorted(Path("agent").glob("*.py")):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#")[0]
            assert "example.org/orexis/water" not in code, \
                f"{path}:{n} names the water domain — the kernel must survive the domain swap"


def test_no_reader_names_a_per_agent_graph():
    """A graph's name is for eyes; code relies on its classification alone.

    An owner classifies what it writes (`Store.classify`) and a reader asks by class
    (`Store.graphs_of`, `recorded_graphs`). The helpers that spell a readable name —
    `roots_graph`, `pursued_graph`, the ledger's, review's — are the WRITERS' conventions, and
    a module that reads the mind's graphs may import none of them: the planner named five,
    the desires projection five and filtered the rest by string prefix, and boot typed every
    per-agent graph by matching its name against a prefix its class declared — the sovereign
    asked which graphs could be renamed freely, and this is what makes it all of them.
    """
    helpers = {"picks_graph", "roots_graph", "promises_graph", "obligations_graph", "intentions_graph",
               "pursued_graph", "remembered_graph", "revisions_graph", "evidence_graph", "summaries_graph",
               "judgments_graph"}
    readers = ["packages/orexis-agent-deliberation/planner.py", "packages/orexis-agent-deliberation/desires.py",
               "packages/orexis-agent-deliberation/imaginarium.py", "packages/orexis-agent-deliberation/pursuit.py",
               "packages/orexis-agent-deliberation/judge_desires.py", "packages/orexis-agent-deliberation/derive_wants.py",
               "packages/orexis-agent-deliberation/afforder.py", "packages/orexis-agent-deliberation/affordances.py",
               "packages/orexis-agent-deliberation/reviser.py", "agent/judgments.py", "agent/validate.py"]
    offenders = []
    for path in readers:
        text = (REPO_ROOT / path).read_text()
        for name in sorted(helpers):
            if re.search(rf"\b{name}\(", text):
                offenders.append(f"{path} names a graph through {name}()")
    assert not offenders, "\n".join(offenders)


def test_the_kernel_namespace_holds_no_individuals():
    """A world owns its individuals; orexis: is the vocabulary's (#179's other half).

    Every orexis: name a world file uses must be a term the core ontology declares — classes,
    properties, the shared individuals the kernel itself defines. A world's OWN things (its
    agents, sensors, pins, its orexis:world node as was) live in that world's namespace, declared
    with the empty prefix, so the A-Box/T-Box split rule 1 polices in code is structural in
    the files. Parse-based, so a spelling choice can never fool it.

    This function was in the file TWICE, byte for byte, and Python bound the second — so one
    copy had never run since whenever the paste happened. Nothing could see it: two defs of one
    name is legal, and the surviving copy passed."""
    import rdflib

    from assembly import loader

    OREXIS = "http://example.org/orexis#"
    core = rdflib.Graph()
    core.parse(loader.KERNEL.file(loader.ONTOLOGY), format="turtle")
    declared = {str(n) for t in core for n in t
                if isinstance(n, rdflib.URIRef) and str(n).startswith(OREXIS)}

    checked = 0
    for path in sorted((REPO_ROOT / "world").glob("*/**/*.ttl")):
        #  TriG, ConjunctiveGraph — a GRAPH block's names must be scanned, not dropped.
        g = rdflib.ConjunctiveGraph()
        g.parse(path, format="trig")
        strays = {str(n) for t in g for n in t
                  if isinstance(n, rdflib.URIRef) and str(n).startswith(OREXIS)} - declared
        assert not strays, (
            f"{path.relative_to(REPO_ROOT)} puts {sorted(strays)} in the kernel namespace, "
            "and the vocabulary declares none of them — a world's individuals belong in the "
            "world's own namespace")
        checked += 1
    assert checked >= 8, f"only {checked} world files checked — the glob has gone quiet"


def test_no_generated_credential_is_tracked():
    """Nothing git tracks may be a credential, or a file a generator writes beside one.

    Three files under `world/sensing/mosquitto/` were tracked for three weeks — the broker's
    `passwd`, its ACL and its config — and `passwd` reached main in seven successively
    re-salted versions. `.gitignore` had named that directory since the very commit that added
    them, and the rule could not bite: **a trailing-slash pattern matches a DIRECTORY**, git
    prunes an ignored directory only while nothing in it is tracked, and once the ACL and the
    config were in the index git had to descend — at which point `world/*/mosquitto/` matched
    none of the files inside. Every `git add -A` after that swept up whatever `orexis-mqtt`
    had just written.

    An ignore rule is advice about untracked files. This is the invariant, and it holds
    whatever `.gitignore` says.
    """
    import subprocess

    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                             check=True).stdout.split()
    assert tracked, "git tracks nothing — `git ls-files` stopped answering"

    #  Directories a generator owns, and the file shapes that carry a secret wherever they sit.
    #  `infra/mosquitto/` is the image's own source — a Containerfile and an entrypoint, written
    #  by hand and true of the installation — which is why the pattern is a world's copy.
    generated = ("world/", "infra/secrets/", "infra/grafana/certs/", "infra/grafana/dashboards/")
    offenders = sorted(
        path for path in tracked
        if (any(part in path for part in ("/mosquitto/", "/secrets/")) and path.startswith(generated))
        or path.endswith((".key", ".pem", "/passwd", "/keys.ttl", "/config.h"))
        or path.endswith(".env") and not path.endswith(".env.example"))
    assert not offenders, (
        "a credential or a generated file is tracked — regenerate it with `orexis-onboard` "
        "instead of committing it, and rotate whatever leaked:\n  " + "\n  ".join(offenders))


def test_the_mounted_trees_are_the_copied_trees():
    """What compose bind-mounts is what the image copies — the block's own recurring lesson.

    `onboarding/compose.py` carries the warning in its own comment: the mounts are *"the SAME
    two the Containerfile copies, and keeping the pair in step is the lesson this block keeps
    relearning"*. Twice before, a tree moved and a husk went on being mounted silently; the
    third time it failed loudly, but only at the next restart, because a bind resolves when a
    container is CREATED and a stale one keeps running until the day it cannot.

    It relearned it once more when `assembly/` arrived. So the two lists are compared rather
    than described, and `firmware/` is excepted: the image copies its ontologies as a third
    T-Box source, and no agent needs the tree mounted to read what is already inside.
    """
    import pathlib
    import re

    compose = pathlib.Path(__file__).resolve().parent.parent / "onboarding" / "compose.py"
    mounts = set(re.findall(r"\.\./\.\./([a-z_]+):/app/", compose.read_text()))
    copied = {p.split("/")[0].strip("./") for p in copied_paths() if "/" in p} - {"firmware"}
    assert mounts, "no source trees mounted — the pattern stopped matching"
    assert mounts == copied, (
        f"compose mounts {sorted(mounts)} and the image copies {sorted(copied)}. A tree in one "
        "and not the other is a container that starts today and refuses at its next restart.")



def test_a_package_manifest_imports_nothing_expensive():
    """`__init__.py` may import stdlib and `assembly` — nothing else.

    Every one of them is imported at ASSEMBLY, for every agent, because that is how the loader
    asks what a package brings. So a heavy import there is paid by every agent for every
    package — including the packages that agent was never granted, which is exactly what #216
    removed: *"an agent granted no Consulting never touches whatever Consulting will need
    installed."*

    The classes go behind `provides()`, which is a function for this reason and not a constant.
    A package's own `.terms` is allowed: it is constants and a string concatenation.
    """
    import ast
    import pathlib
    import sys

    stdlib = sys.stdlib_module_names
    root = pathlib.Path(__file__).resolve().parent.parent
    offenders = []
    for path in sorted((root / "packages").glob("*/__init__.py")):
        tree = ast.parse(path.read_text(), str(path))
        for node in tree.body:                      # TOP LEVEL only — inside a function is the point
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:                      # `from .terms import …` — its own, and cheap
                    continue
                names = [node.module or ""]
            for name in names:
                root = name.split(".")[0]
                if root not in stdlib and root != "assembly":
                    offenders.append(f"{path}: {name}")
    assert not offenders, (
        "a package manifest imports something expensive at the top level — every agent pays "
        "for it, for every package, granted or not. Move it inside `provides()`:\n  "
        + "\n  ".join(offenders))



def test_a_service_nobody_offers_is_refused_by_name(monkeypatch):
    """Asking for a service nothing provides names it, rather than returning None.

    `agent.provider(family)` answers None on purpose — an agent that composed neither member of
    a family simply cannot do that thing, and callers are written for it. A SERVICE is the other
    shape: a module that declared `@requires(HISTORY)` has said it cannot work without one, so
    silence would be the wrong answer twice over — at the point of use, far from the
    declaration, and indistinguishable from a service that legitimately returned nothing.
    """
    import pytest

    from conftest import build_agent

    agent = build_agent("fern", monkeypatch=monkeypatch)
    with pytest.raises(KeyError, match="nothing offers"):
        agent.service("urn:orexis:nothing-of-the-sort")


def test_what_the_kernel_offers_is_reachable_by_its_class(monkeypatch):
    """Every service the kernel puts on the table answers to the class a package would import.

    The key is the CLASS, not a term, and the two ends of that must not drift: a service
    registered under something a package cannot name is the twelve undeclared attributes this
    design was written against, wearing a registry.
    """
    from orexis_agent_deliberation.beliefs import Beliefs
    from orexis_agent_deliberation.desires import Desires
    from agent.metrics import Metrics
    from conftest import build_agent

    agent = build_agent("fern", monkeypatch=monkeypatch)
    for contract in (Beliefs, Desires, Metrics):
        got = agent.service(contract)
        assert isinstance(got, contract), (
            f"{contract.__name__} is offered as {type(got).__name__} — a package asking for the "
            "class it imported would be handed something else")


def test_every_hard_requirement_is_offered_by_something():
    """`@requires` is a promise the build can keep, and it is checked without booting an agent.

    Build-wide, not per agent — which is a correction to what the record first said. A service
    is offered by a PACKAGE, and every package is in every build; what differs between agents is
    which MODULES get constructed, and a module class's requirements are static. So the question
    is *does anything offer this*, and it needs no world to ask.

    An OPTIONAL annotation — `X | None` — is deliberately not checked: the module has said it
    can work without, so a missing one is a fact about which packages were installed rather than
    a broken build. It resolves to `None` and the module checks.
    """
    from assembly import loader
    from assembly.inject import injections_of
    from agent.runtime import KERNEL_SERVICES

    offered = set(loader.offers()) | set(KERNEL_SERVICES)
    assert offered, "nothing is offered at all — the scan stopped matching"

    classes = [cls for p in loader.packages() for cls in p.provides()]
    assert classes, "no provided classes found — the loader found nothing"

    unmet = sorted(
        f"{cls.__module__}.{cls.__name__} requires {name}, which nothing offers"
        for cls in classes
        for name, (key, optional) in injections_of(cls).items()
        if not optional and key not in offered)
    assert not unmet, (
        "a module declares a hard requirement no package provides. It would raise at first "
        "touch, deep inside a running agent, far from the declaration:\n  " + "\n  ".join(unmet))


def test_a_service_that_yields_is_closed_when_the_agent_stops(monkeypatch):
    """A provider may yield, and what follows the yield runs at shutdown, newest first.

    A module has `stop()`; a service is not a module and had nothing, so #311's history ring
    would have had nowhere to flush. Reverse order because a service that leans on another must
    be closed before the thing it leans on, and the same reason `contextlib.ExitStack` unwinds
    that way.
    """
    from assembly.inject import opened

    order = []

    def first(agent):
        order.append("open-first")
        yield "first"
        order.append("close-first")

    def second(agent):
        order.append("open-second")
        yield "second"
        order.append("close-second")

    closing = []
    for build in (first, second):
        _, close = opened(build, None)
        closing.append(close)
    for close in reversed(closing):
        close()

    assert order == ["open-first", "open-second", "close-second", "close-first"], (
        f"services must close newest first, got {order}")


def test_an_ordinary_provider_leaves_nothing_to_close():
    """The common case costs nothing: a provider that returns is not a generator, and the agent
    has no teardown to remember for it."""
    from assembly.inject import opened

    service, close = opened(lambda agent: object(), None)
    assert service is not None
    assert close is None, "a plain provider should leave no teardown behind"


# --- the pull: a required key loads its provider, a soft one takes what is there (#455) ------
#
#  The load set is the grants' owner packages plus every package a REQUIRED injection pulls,
#  needs after needs (a-layer-is-a-package-and-need-loads-it). The tree ships no `@provides`
#  offer today, so the pull is proved against a synthetic tree of real `loader.Package`
#  records — real directories, real manifests, imported through the loader's own doors — and
#  the marker files say WHEN a package's Python actually arrived, which is the fact under test.

_PULL_ALPHA = '''\
from pathlib import Path

from assembly import inject


class Alpha:
    pass


@inject.provides
def alpha(agent) -> Alpha:
    return Alpha()


def provides():
    Path(__file__).with_name("loaded.marker").write_text("pulled")
    from orexis_pulled_beta import Beta

    class AlphaModule:
        beta: Beta          # required: the pull follows this

    return (AlphaModule,)
'''

_PULL_BETA = '''\
from pathlib import Path

from assembly import inject


class Beta:
    pass


@inject.provides
def beta(agent) -> Beta:
    return Beta()


def provides():
    Path(__file__).with_name("loaded.marker").write_text("pulled")
    from orexis_pulled_gamma import Gamma

    class BetaModule:
        gamma: Gamma        # a pulled package's needs follow it

    return (BetaModule,)
'''

_PULL_GAMMA = '''\
from pathlib import Path

from assembly import inject


class Gamma:
    pass


@inject.provides
def gamma(agent) -> Gamma:
    return Gamma()


def provides():
    Path(__file__).with_name("loaded.marker").write_text("pulled")
    from orexis_pulled_alpha import Alpha

    class GammaModule:
        alpha: Alpha        # the cycle back to the start — terminates, loads nothing twice

    return (GammaModule,)
'''

_PULL_DELTA = '''\
from pathlib import Path

from assembly import inject


class Delta:
    pass


@inject.provides
def delta(agent) -> Delta:
    Path(__file__).with_name("built.marker").write_text("x")
    return Delta()


def provides():
    Path(__file__).with_name("loaded.marker").write_text("x")
    return ()
'''


@pytest.fixture
def synthetic_tree(tmp_path, monkeypatch):
    """Real packages on disk, appended to the discovered tree.

    `loader.Package` records over real directories, so equality, `manifest()` and `provides()`
    behave exactly as production's do — the fakes differ from a shipped package only in being
    somewhere temporary. `offers()` is cached over `packages()`, so the cache is cleared going
    in and coming out, and the imported fakes leave `sys.modules` with the test.
    """
    import sys

    from assembly import loader

    def build(packages_py: dict[str, str]) -> list:
        made = []
        for module, body in packages_py.items():
            d = tmp_path / module
            d.mkdir()
            (d / "__init__.py").write_text(body)
            made.append(loader.Package(kind="service", name=module.rsplit("_", 1)[-1],
                                       path=d, module=module))
        monkeypatch.syspath_prepend(str(tmp_path))
        real = loader.packages
        monkeypatch.setattr(loader, "packages", lambda: real() + tuple(made))
        loader.offers.cache_clear()
        return made

    yield build
    loader.offers.cache_clear()
    for name in [n for n in sys.modules if n.startswith("orexis_pulled_")]:
        del sys.modules[name]


def test_a_required_key_pulls_its_provider_transitively(synthetic_tree):
    """Loading a package whose module requires a key offered by an unloaded package loads that
    package too, and its needs after it — and a cycle of needs terminates.

    Alpha's module requires Beta (another package's), Beta's requires Gamma, and Gamma's
    requires Alpha back — so one walk proves the pull, the transitivity and the cycle at once:
    exactly three packages, each loaded exactly once, in need order.
    """
    from assembly import loader

    alpha, beta, gamma = synthetic_tree({
        "orexis_pulled_alpha": _PULL_ALPHA,
        "orexis_pulled_beta": _PULL_BETA,
        "orexis_pulled_gamma": _PULL_GAMMA,
    })
    loaded = loader.pulled([alpha])
    assert loaded == (alpha, beta, gamma), (
        f"the pull should reach exactly alpha, beta, gamma in need order — got "
        f"{[p.import_name for p in loaded]}")
    assert (beta.path / "loaded.marker").exists(), (
        "beta's Python never arrived — a required key must load its provider")
    assert (gamma.path / "loaded.marker").exists(), (
        "gamma's Python never arrived — a pulled package's needs must follow it")


def test_a_soft_annotation_never_causes_a_load(synthetic_tree, monkeypatch):
    """A provider IS in the tree, and stays unloaded when only an optional annotation names it.

    The module gets None, the provider's `provides()` is never called and its offer never
    runs — a soft need takes what is already there, and nothing about fern's grants puts
    delta there.
    """
    from agent.module import Module
    from conftest import build_agent

    (delta,) = synthetic_tree({"orexis_pulled_delta": _PULL_DELTA})
    from orexis_pulled_delta import Delta
    #  Planted in this module's globals so the class body's string annotation (this file has
    #  `from __future__ import annotations`) resolves; monkeypatch takes it back out.
    monkeypatch.setitem(globals(), "Delta", Delta)

    class Soft(Module):
        name = "soft"
        delta: Delta | None

    agent = build_agent("fern", monkeypatch=monkeypatch)
    module = Soft(agent)
    assert module.delta is None, "a soft annotation must inject only what is already there"
    assert delta not in agent._packages, (
        "an optional annotation must never add to the packages an agent loads")
    assert not (delta.path / "loaded.marker").exists(), (
        "delta's Python was loaded with nothing but a soft annotation naming it")
    assert not (delta.path / "built.marker").exists(), (
        "delta's offer ran with nothing but a soft annotation naming it")


def test_a_service_outside_the_load_set_is_refused_by_name(synthetic_tree, monkeypatch):
    """A key offered only by a package no need pulled is refused, naming the package.

    Before #455 `agent.service` resolved tree-wide, so being in the checkout was being in the
    build. Now presence is the load set's, and the refusal says which package holds the offer
    and what would pull it in — without running the offer, which is the other half of the claim.
    """
    from conftest import build_agent

    (delta,) = synthetic_tree({"orexis_pulled_delta": _PULL_DELTA})
    from orexis_pulled_delta import Delta

    agent = build_agent("fern", monkeypatch=monkeypatch)
    with pytest.raises(KeyError, match="packages this agent loads"):
        agent.service(Delta)
    assert not (delta.path / "built.marker").exists(), (
        "the refusal built the service it was refusing")


SUBSCRIBING = "http://example.org/orexis/sensing#Subscribing"


def test_the_pull_adds_nothing_a_sensing_grant_does_not_need():
    """The load set of a sensing-only grant is sensing's package and no other — measured on
    the built load set. Sensing's module classes declare no required key any package offers,
    so the pull adds nothing — and since #455 closed, sensing's row types and picks load on
    first touch, so no layer arrives at assembly either; the test below measures it."""
    from assembly import loader

    assert [p.import_name for p in loader.packages_for({SUBSCRIBING})] == \
        ["orexis_capability_sensing"], (
        "a sensing-only grant should load exactly sensing's package")


def test_a_world_granting_only_sensing_loads_no_deliberation_python():
    """MEASURED on what a sensing-only build imports, in a process of its own — not asserted.

    The manifest (`orexis_agent_deliberation/__init__.py`) is excluded deliberately: every
    package's manifest is imported at assembly by design and is held cheap by the gate above.
    What must not arrive is the layer's actual Python — any submodule.
    """
    import json
    import subprocess
    import sys

    code = (
        "import json, sys\n"
        "from assembly import loader\n"
        f"loader.registry_for({{{SUBSCRIBING!r}}})\n"
        f"loader.packages_for({{{SUBSCRIBING!r}}})\n"
        "print(json.dumps(sorted(m for m in sys.modules\n"
        "                        if m.startswith('orexis_agent_deliberation.'))))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=REPO_ROOT)
    assert out.returncode == 0, out.stderr
    offenders = json.loads(out.stdout.strip().splitlines()[-1])
    assert not offenders, (
        "a sensing-only grant imported deliberation Python: " + ", ".join(offenders))
