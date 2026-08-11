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

# What an agent legitimately runs. `agent/` carries capabilities and transports as subpackages;
# `vocabulary/` is the shared T-Box, which onboarding reads too and neither side owns.
ALLOWED_TREES = {"agent", "vocabulary"}

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
    """One fact said twice, in two vocabularies, to two audiences — held to agreeing.

    A board hosting its sensors is stated in `hardware.ttl` as `mc:carries` and in the society
    as `sosa:hosts`, because an agent is never handed the wiring and `mc:` is exactly what the
    test above forbids it. `mc:carries rdfs:subPropertyOf sosa:hosts` makes them one fact for
    anyone who loads both — but only the SOVEREIGN loads both, so nothing in the running system
    would ever notice them diverging. That is what this is for.

    Checked in the direction drift actually goes. Rewiring a probe onto a different board edits
    `hardware.ttl`; the society keeps the old answer and every gate stays green, because the
    society is internally consistent and the wiring is internally consistent and no query spans
    them. So: wherever the wiring hosts something the society also names, the society must say
    the same — and nothing in the society may claim a host the wiring contradicts.

    NOT symmetric, deliberately. `ag:status_led_fern` is carried by the board and absent from
    the society, which is correct: an agent polls sensors and has no business knowing about an
    indicator it can never observe. Demanding the society mirror the wiring would force
    hardware-only parts into it, which is the leak the test above exists to prevent.
    """
    import rdflib

    from agent import genesis

    MC = rdflib.Namespace("http://example.org/agora/microcontroller#")
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

        carried = set(wiring.subject_objects(MC.carries))
        hosted = set(society.subject_objects(SOSA.hosts))
        named = {s for s, _, _ in society} | {o for _, _, o in society}

        missing = {(h, t) for h, t in carried if t in named} - hosted
        assert not missing, (
            f"{world}: the wiring carries {sorted(str(t) for _, t in missing)} and the society "
            f"does not host it — an agent would not know which board its sensor is on")

        # And nothing may claim a host the wiring puts elsewhere. Only pairs the wiring can
        # speak about are checked: `mc:carries` has mc:Microcontroller for its domain, so it
        # cannot express a KY-015 hosting its own two channels, and the society states that
        # chain alone rather than in contradiction to anything.
        carriers = {t: h for h, t in carried}
        contradicted = {(h, t) for h, t in hosted if t in carriers and carriers[t] != h}
        assert not contradicted, (
            f"{world}: the society hosts {sorted((str(h), str(t)) for h, t in contradicted)} "
            f"but the wiring mounts it elsewhere")


def test_the_society_repeats_every_limit_the_wiring_states():
    """A device's floor is stated on the PART and needed by the AGENT, which is never given the
    part. So it is said twice — `ssn-system:Frequency` on `dht11:Dht11` in the vocabulary, and
    again on each sensor that part hosts in the society — and only the sovereign loads both.

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
    import rdflib

    from agent import genesis

    SSNS = rdflib.Namespace("http://www.w3.org/ns/ssn/systems/")
    SOSA = rdflib.Namespace("http://www.w3.org/ns/sosa/")
    PERC = rdflib.Namespace("http://example.org/agora/perception#")

    def floors(g, subject):
        """Every Frequency, in seconds, that this node states — through the two hops SSN puts
        between a system and a number."""
        out = set()
        for cap in g.objects(subject, SSNS.hasSystemCapability):
            for prop in g.objects(cap, SSNS.hasSystemProperty):
                if (prop, rdflib.RDF.type, SSNS.Frequency) in g:
                    out |= {int(s) for s in g.objects(prop, PERC.seconds)}
        return out

    vocabulary = rdflib.Graph()
    for path in sorted(genesis.REPO_ROOT.glob("vocabulary/*/ontology.ttl")):
        vocabulary.parse(path, format="turtle")

    for world in genesis.worlds():
        world_path = genesis.world_dir(world)
        society, wiring = rdflib.Graph(), rdflib.Graph()
        for path in genesis.society_files(world_path):
            society.parse(path, format="turtle")
        for name in genesis.HARDWARE_FILES:
            if (world_path / name).exists():
                wiring.parse(world_path / name, format="turtle")
        if not wiring:
            continue  # no parts, so nothing the society could be failing to repeat

        for part in set(wiring.subjects()):
            stated = {f for cls in wiring.objects(part, rdflib.RDF.type) for f in floors(vocabulary, cls)}
            stated |= floors(wiring, part)
            if not stated:
                continue
            # Whatever that part hosts, or the part itself where it hosts nothing — a
            # single-property probe IS its sensor and carries the limit directly, while a KY-015
            # is a platform whose two channels carry it and which states none of its own.
            hosted = set(society.objects(part, SOSA.hosts))
            for sensor in hosted or {part}:
                if (sensor, None, None) not in society:
                    continue
                assert floors(society, sensor) >= stated, (
                    f"{world}: the wiring says {sorted(stated)}s for <{sensor}> and the society "
                    f"says {sorted(floors(society, sensor))}s — an agent would commit to a "
                    f"cadence its board will not keep")


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
