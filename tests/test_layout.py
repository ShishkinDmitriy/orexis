"""The agent image carries no operator code, asserted rather than implied.

This used to be a property of the packaging: two distributions, and an agent installed only
one of them. It never was, quite. Nothing here installs from an index — the image copies
directories and runs `pip install -e .` — so what actually kept `onboarding/` out of an agent
was the Containerfile not naming it, and a reader had to infer that from two pyproject files
that said nothing about images.

One distribution now, and the boundary is here. If someone adds `COPY onboarding/` for
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
ALLOWED_TREES = {"agent", "packages"}

# Never in an agent image. `agora-influx` reads the admin token, which opens every bucket in the
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
        "http://example.org/agora/microcontroller#",
        "http://example.org/agora/esp32#",
        "http://example.org/agora/wokwi#",
        "http://example.org/agora/dht11#",
        "http://example.org/agora/rgb-led#",
        "http://example.org/agora/moisture-probe#",
        "http://example.org/agora/onewire#",
        "http://example.org/agora/i2c#",
    )

    for world in genesis.worlds():
        g = rdflib.Graph()
        for path in genesis.society_files(genesis.world_dir(world)):
            g.parse(path, format="turtle")
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
    not.** `ag:air_sensor_fern sosa:hosts` its two channels and the wiring names neither of
    them; a simulated device has no wiring at all. So a society-side pair with no counterpart
    cannot be an error, and unwiring — deleting a part from `hardware.ttl` while the society
    still hosts it — is still not caught. Closing that needs a rule that can tell a board's
    hosting from a part's, which nothing here can: the society does not type the board as a
    `mc:Microcontroller`, because `mc:` is exactly what the test above forbids it.

    The other direction is likewise deliberate. `ag:status_led_fern` is hosted by the board and
    absent from the society, which is correct: an agent polls sensors and has no business
    knowing about an indicator it can never observe.
    """
    import rdflib

    from agent import genesis

    SOSA = rdflib.Namespace("http://www.w3.org/ns/sosa/")

    for world in genesis.worlds():
        world_path = genesis.world_dir(world)
        society, wiring = rdflib.Graph(), rdflib.Graph()
        for path in genesis.society_files(world_path):
            society.parse(path, format="turtle")
        for name in genesis.HARDWARE_FILES:
            if (world_path / name).exists():
                wiring.parse(world_path / name, format="turtle")
        if not wiring:
            continue  # a world with no stated hardware has nothing to disagree with

        carried = set(wiring.subject_objects(SOSA.hosts))
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
    `ag:air_sensor_fern` with nobody having written it there. What that does NOT cross is the
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
    from agent import genesis, inference, loader
    from agent.ontology import ONTOLOGY_GRAPH, WORLD_GRAPH
    from agent.store import Store, bindings

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
                f"`agora-compose {world}`")


def test_a_packages_python_namespace_is_the_one_its_ontology_declares():
    """`terms.py` writes `NS` so Python can name a term without parsing Turtle, and
    `ontology.ttl` declares the same namespace so a query can reach it through the prefix the
    loader assembles. Two copies of one fact, and nothing but this holds them together.

    Drifting them apart fails in the worst available way: Python would build terms in one
    namespace while SHACL validated them in another, and a world would conform while the agent
    reading it found nothing — an empty result, which is not an error.
    """
    import importlib

    from agent import loader

    checked = []
    for package in loader.packages():
        if not (package.path / "terms.py").exists():
            continue
        ns = getattr(importlib.import_module(f"{package.import_name}.terms"), "NS", None)
        if ns is None:
            continue  # a package still living in the kernel's `ag:` names no namespace of its own
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
_COUNTER_EXAMPLES = {"ag:fern_agent", "ag:world"}


@pytest.mark.parametrize("doc", ["README.md", "AGENTS.md"])
def test_the_docs_only_name_terms_that_exist(doc):
    """Every `prefix:Term` in the two entry documents is declared by some package.

    Written after finding EIGHT in README.md that no vocabulary had declared since the namespace
    split — `ag:senseMode`, `ag:Subscribing`, `ag:readingTopic` and five more. Every one had a
    live successor in another namespace, so the prose was not vague, it was wrong, and nothing
    failed: a renamed term leaves no dangling reference for a reader to trip over.

    Prose is where this project keeps its reasoning, so prose going stale is not cosmetic. The
    same rename swept the code, the shapes and the worlds, and stopped at the door of the file
    people read first.
    """
    import re
    from agent import loader

    declared = set()
    for path in loader.ontology_files():
        declared |= set(re.findall(r"\b[a-z][a-z0-9-]*:[A-Za-z][A-Za-z0-9_]*\b",
                                   Path(path).read_text()))
    known = set(loader.prefixes()) | {"ag"}

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
        assert "example.org/agora/water" not in path.read_text(), \
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
            assert "example.org/agora/water" not in code, \
                f"{path}:{n} names the water domain — the kernel must survive the domain swap"
