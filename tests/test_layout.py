"""The agent image carries no operator code, and an agent is handed no more than it reads —
asserted rather than implied.

Nothing here installs from an index: the image copies directories and runs `pip install -e .`,
so what keeps `onboarding/` out of an agent is the Containerfile not naming it. If someone adds
`COPY onboarding/` for convenience, this fails; nothing else would.

Deliberately reads the Containerfile and the compose files rather than building: a test that
needed a container runtime would be skipped on every machine that lacks one, which is exactly
the machine where someone is most likely to be editing quickly.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTAINERFILE = REPO_ROOT / "Containerfile"

#  What an agent legitimately runs: the runtime and its packages, the domains its worlds import,
#  and the simulator a world runs as a process of its own.
ALLOWED_TREES = {"agent", "domains", "simulation"}

#  Never in an agent image. `orexis-influx` reads the admin token, which opens every bucket in the
#  store and which no agent may ever hold; the surest guarantee is that the code using it is
#  absent. See knowledge/domain/onboarding/onboarding.md.
FORBIDDEN_TREES = {"onboarding"}


def copied_paths() -> list[str]:
    """Every source path the image copies, as written."""
    out: list[str] = []
    for line in CONTAINERFILE.read_text().splitlines():
        line = line.strip()
        if line.upper().startswith("COPY "):
            parts = re.split(r"\s+", line)[1:]
            out.extend(p for p in parts[:-1] if not p.startswith("--"))
    return out


def test_the_image_copies_something():
    """A guard on the guard: were COPY renamed or the file moved, every assertion below would
    pass vacuously and the boundary would be unwatched."""
    assert copied_paths(), f"no COPY lines found in {CONTAINERFILE} — this test is not looking"


@pytest.mark.parametrize("forbidden", sorted(FORBIDDEN_TREES))
def test_the_agent_image_carries_no_operator_code(forbidden):
    offenders = [p for p in copied_paths() if p.split("/")[0].strip("./") == forbidden]
    assert not offenders, (
        f"the Containerfile copies {offenders} into the agent image. {forbidden}/ mints "
        "credentials and reads the admin token; an agent must not hold that code at all. "
        "If this is deliberate, knowledge/decisions/series-and-bus-isolation.md is what needs "
        "changing first.")


def test_the_image_copies_only_what_an_agent_runs():
    """The positive half. Forbidding one name only catches the tree we thought of; this
    catches the next one, which is the one that will actually be added."""
    trees = {p.split("/")[0].strip("./") for p in copied_paths() if "/" in p}
    unexpected = trees - ALLOWED_TREES
    assert not unexpected, (
        f"the agent image copies {sorted(unexpected)}, which is not part of what an agent runs. "
        f"Expected only {sorted(ALLOWED_TREES)} — add it here deliberately, or do not copy it.")


def test_onboarding_is_not_hidden_from_the_build_context():
    """Ignoring `onboarding/` in .containerignore would also keep it out of the image, move the
    reasoning into a file nobody reads, and make the test above pass for the wrong reason."""
    ignored = [line.strip() for line in (REPO_ROOT / ".containerignore").read_text().splitlines()
               if line.strip() and not line.strip().startswith("#")]
    assert "onboarding" not in ignored, (
        ".containerignore excludes onboarding/. That works, but it hides the boundary: the "
        "Containerfile should be the one place that says what an agent image contains.")


def test_the_mounted_trees_are_the_copied_trees():
    """What compose bind-mounts is what the image copies. Twice a tree moved and a husk went on
    being mounted silently; the third time it failed, but only at the next restart, because a
    bind resolves when a container is CREATED and a stale one runs until the day it cannot."""
    compose = (REPO_ROOT / "onboarding" / "compose.py").read_text()
    mounts = set(re.findall(r"\.\./\.\./([a-z_]+):/app/", compose))
    copied = {p.split("/")[0].strip("./") for p in copied_paths() if "/" in p}
    assert mounts, "no source trees mounted — the pattern stopped matching"
    assert mounts == copied, (
        f"compose mounts {sorted(mounts)} and the image copies {sorted(copied)}. A tree in one "
        "and not the other is a container that starts today and refuses at its next restart.")


# --- what an AGENT is given, which is less than the world -------------------------------------

HARDWARE_NAMESPACES = (
    "http://example.org/orexis/microcontroller#",
    "http://example.org/orexis/esp32#",
    "http://example.org/orexis/dht11#",
    "http://example.org/orexis/rgb-led#",
    "http://example.org/orexis/moisture-probe#",
    "http://example.org/orexis/onewire#",
    "http://example.org/orexis/i2c#",
    "http://example.org/orexis/bme280#",
)


def _worlds() -> list[str]:
    return sorted(p.parent.name for p in (REPO_ROOT / "world").glob("*/world.ttl"))


def test_an_agent_is_given_the_society_and_not_the_hardware():
    """It never asks which pin a probe is on. Pins, wires, part models and firmware are the
    sovereign's: they decide what CAN be built and what a board is flashed with, and once it is
    built the agent talks to topics. Asserted on the CONTENT of every document of a kind an agent
    reads — the world's own and every agent's beliefs — so a pin put into world.ttl is caught
    where nothing about the kind would warn anyone; and the other way, every document speaking
    hardware is of a kind no agent reads."""
    import rdflib

    from onboarding.compose import read_by_an_agent

    worlds, withheld = _worlds(), []
    assert worlds, "no world found — the guard would check nothing"
    for world in worlds:
        read = read_by_an_agent(world)
        assert read, f"{world}: an agent reads none of its documents — the guard would check nothing"
        here = REPO_ROOT / "world" / world
        for path in sorted([*here.glob("*.ttl"), *here.glob("*.trig"), *here.glob("beliefs/*.ttl")]):
            g = rdflib.Dataset()
            g.parse(path, format="trig")          # a Turtle file is TriG, and a want file holds a GRAPH
            spoken = {str(t) for quad in g.quads() for t in quad[:3] if str(t).startswith(HARDWARE_NAMESPACES)}
            if path.resolve() in read:
                assert not spoken, (f"{world}/{path.name}: an agent would be handed hardware vocabulary "
                                    f"it never queries: {sorted(spoken)[:5]}")
            elif spoken:
                withheld.append(path)
    assert withheld, "no world holds hardware an agent is not given — the guard checks one direction only"


def test_a_compose_file_mounts_a_document_because_an_agent_reads_its_kind():
    """The other half, and the one that enforces it: a rule the agent is trusted to follow is not
    a boundary. A container is handed the documents of a kind an agent reads and no other, so the
    hardware is not in its filesystem — decided by the kind the document states, never its name."""
    from onboarding.compose import read_by_an_agent

    composed = sorted(p.parent.name for p in (REPO_ROOT / "world").glob("*/compose.yaml"))
    assert composed, "no world has a compose file — the guard would compare nothing"
    unmounted = []
    for world in composed:
        here = (REPO_ROOT / "world" / world).resolve()
        compose = (here / "compose.yaml").read_text()
        mounted = {(here / m).resolve() for m in re.findall(rf"- \./([^:]+):/app/world/{world}/", compose)}
        assert mounted, f"{world}/compose.yaml mounts no document — the pattern stopped matching"
        read = read_by_an_agent(world)
        assert mounted <= read, (f"{world}/compose.yaml mounts {sorted(p.name for p in mounted - read)}, of a "
                                 f"kind no agent reads — regenerate with `orexis-compose {world}`")
        unmounted += sorted(p for p in here.glob("*.ttl") if p.resolve() not in read)
    assert unmounted, "every document of every composed world is read by an agent — the guard withholds nothing"


# --- a document's kind says who reads it, and a kind nobody reads is refused ------------------

def test_every_graph_a_world_holds_is_of_a_kind_somebody_reads():
    """Every reader passes over a kind it does not declare, so a misspelled kind would be lost in
    silence; `orexis-onboard` refuses one, and no shipped world may hold one."""
    from onboarding.reading import unread

    worlds = _worlds()
    assert worlds, "no world found — the guard would check nothing"
    for world in worlds:
        assert unread(REPO_ROOT / "world" / world) == [], f"{world} holds graphs of a kind no reader declares"


def test_onboarding_refuses_a_world_holding_a_kind_no_reader_declares(tmp_path, monkeypatch):
    """Broken on purpose: the hanoi world with its state's kind misspelled. The agent's boot would
    pass over the state and start from nothing; onboarding names the graph and grants nothing."""
    from onboarding import onboard, reading

    world = tmp_path / "hanoi"
    world.mkdir()
    domain = (REPO_ROOT / "domains" / "hanoi" / "ontology.ttl").as_uri()
    hanoi = REPO_ROOT / "world" / "hanoi"
    (world / "world.ttl").write_text((hanoi / "world.ttl").read_text().replace("<../../domains/hanoi/ontology.ttl>", f"<{domain}>"))
    (world / "wants.ttl").write_text((hanoi / "wants.ttl").read_text())
    (world / "state.ttl").write_text((hanoi / "state.ttl").read_text().replace("orexis:StateGraph", "orexis:StateGrpah"))
    assert [line.split(":", 1)[0] for line in reading.unread(world)] == ["state.ttl"]
    monkeypatch.setattr(onboard, "world_dir", lambda name: world)
    with pytest.raises(SystemExit, match="StateGrpah"):
        onboard.onboard("hanoi")


def test_the_firmware_generator_reads_the_hardware_beside_the_society():
    """What the agent is not handed, onboarding still reads: a board's pins join the topics its
    sensors publish on, so the generator finds every board a hardware graph states."""
    from onboarding import firmware

    for world, board in (("terrace", "esp32_terrace"), ("sensing", "esp32_fern")):
        found = {r["boardId"] for r in firmware._rows(firmware._world(world), firmware._BOARDS_Q)}
        assert board in found, f"{world}: the firmware generator finds {sorted(found)}"


# --- the entry documents name only what exists --------------------------------------------------

#  Instances AGENTS.md names on purpose, as the thing rule 1 forbids. They are not terms and must
#  never be declared — naming them here keeps the check from being weakened to "any word with a
#  colon in it".
_COUNTER_EXAMPLES = {"orexis:fern_agent", "orexis:world"}


@pytest.mark.parametrize("doc", ["README.md", "AGENTS.md"])
def test_the_docs_only_name_terms_that_exist(doc):
    """Every `prefix:Term` in the two entry documents is declared by some vocabulary. Written after
    finding eight in README.md that nothing had declared since a namespace split, each with a live
    successor elsewhere: the prose was not vague, it was wrong, and nothing failed. A renamed term
    leaves no dangling reference for a reader to trip over."""
    import rdflib

    sources = sorted(p for p in [*REPO_ROOT.glob("agent/**/*.ttl"), *REPO_ROOT.glob("onboarding/*.ttl"),
                                 *REPO_ROOT.glob("domains/*/*.ttl"), *REPO_ROOT.glob("tests/fixtures/vocabularies/*.ttl")]
                     if not (p.is_relative_to(REPO_ROOT / "agent") and "tests" in p.parts))
    #  THE PROJECT'S NAMESPACES AND THE VENDORED ONES: a standard no file here declares — schema,
    #  SSN-System — is not this census's to check, and a term of it is not held.
    vendored = {iri for path in REPO_ROOT.glob("tests/fixtures/vocabularies/*.ttl")
                for iri in re.findall(r"^@prefix :\s*<([^>]*)>", path.read_text(), re.M)}
    inverse: dict[str, str] = {}
    for path in sources:
        for label, iri in re.findall(r"^@prefix ([A-Za-z][\w.-]*)?:\s*<([^>]*)>", path.read_text(), re.M):
            if iri.startswith("http://example.org/orexis") or iri in vendored:
                inverse.setdefault(iri, label or iri.rstrip("#/").rsplit("/", 1)[-1])
    declared = set()
    for path in sources:
        g = rdflib.Graph()
        g.parse(path, format="turtle")
        for triple in g:
            for node in triple:
                if isinstance(node, rdflib.URIRef):
                    for ns, label in inverse.items():
                        if str(node).startswith(ns):
                            declared.add(f"{label}:{str(node)[len(ns):]}")
    known = set(inverse.values())
    named = {t for t in re.findall(r"`([a-z][a-z0-9-]*:[A-Za-z][A-Za-z0-9_]*)`", (REPO_ROOT / doc).read_text())
             if t.split(":")[0] in known}
    assert named, f"{doc} names no project terms at all — this guard checks nothing"
    missing = sorted(named - declared - _COUNTER_EXAMPLES)
    assert not missing, (f"{doc} names {missing}, which no vocabulary declares. A renamed term leaves "
                         f"the prose wrong rather than broken, so nothing else will tell you.")


# --- the domain is a plug-in -----------------------------------------------------------------------

@pytest.mark.parametrize("tree", ["onboarding", "agent"])
def test_no_shipped_code_names_a_domain(tree):
    """The domain is a plug-in, and the runtime and the operator's tools are what must survive the
    swap. A generator that named `water:` anything worked for exactly one domain and failed the
    next silently — interpolated `water:hasTarget` outlived the term's deletion and matched nothing
    until a live run exposed it. Prose may narrate a domain; no IRI in code may."""
    domains = [f"example.org/orexis/{p.name}#" for p in (REPO_ROOT / "domains").iterdir() if p.is_dir()]
    assert domains, "no domain found — the guard would check nothing"
    for path in sorted((REPO_ROOT / tree).rglob("*.py")):
        if "tests" in path.parts:
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#")[0]
            named = [d for d in domains if d in code]
            assert not named, f"{path.relative_to(REPO_ROOT)}:{n} names {named} — code must survive the domain swap"


# --- nothing generated is tracked --------------------------------------------------------------------

def test_no_generated_credential_is_tracked():
    """Nothing git tracks may be a credential, or a file a generator writes beside one. A broker's
    `passwd`, its ACL and its config were tracked for three weeks once: a trailing-slash ignore
    pattern matches a DIRECTORY, and once anything inside was tracked git descended and the pattern
    matched none of the files. An ignore rule is advice about untracked files; this is the
    invariant."""
    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                             check=True, cwd=REPO_ROOT).stdout.split()
    assert tracked, "git tracks nothing — `git ls-files` stopped answering"
    generated = ("world/", "infra/secrets/", "infra/grafana/certs/", "infra/grafana/dashboards/")
    offenders = sorted(
        path for path in tracked
        if (any(part in path for part in ("/mosquitto/", "/secrets/")) and path.startswith(generated))
        or path.endswith((".key", ".pem", "/passwd", "/keys.ttl", "/config.h"))
        or path.endswith(".env") and not path.endswith(".env.example"))
    assert not offenders, ("a credential or a generated file is tracked — regenerate it with "
                           "`orexis-onboard` instead of committing it, and rotate whatever leaked:\n  "
                           + "\n  ".join(offenders))
