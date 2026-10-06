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
        #  A document under `secrets/` is not committed, so a clone cannot say what it is: its mount is
        #  held to its kind only where the checkout has it.
        mounted = {(here / m).resolve() for m in re.findall(rf"- \./([^:]+):/app/world/{world}/", compose)
                   if not m.startswith("secrets/") or (here / m).exists()}
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


# --- one broker, one address: onboarding refuses what it would otherwise merge ---------------

_BUS_WORLDS = ("allotment", "greenhouse", "sensing", "terrace")
_DOMAINS = (REPO_ROOT / "domains").as_uri()


def _installed(tmp_path, monkeypatch, edit=None, installation=lambda text: text, derivation=True) -> Path:
    """The worlds with a bus, copied, each document `edit[(world, file)]` changes rewritten (a file
    it names that is not there is written from nothing, and one it answers None for is dropped),
    beside a copy of the installation and — `derivation` — of what was derived from it: every
    onboarding tool redirected to the copy. Answers the copy's `world/`."""
    from onboarding import compose, firmware, installation as installed, mqtt

    edit = edit or {}
    root = tmp_path / "world"
    names = sorted({*_BUS_WORLDS, *(w for w, _ in edit)})
    for name in names:
        here, there = REPO_ROOT / "world" / name, root / name
        there.mkdir(parents=True)
        files = {p.name: p.read_text() for p in (here.glob("*.ttl") if here.is_dir() else [])}
        for (w, file), change in edit.items():
            if w == name:
                files[file] = change(files.get(file, ""))
        for file, text in files.items():
            if text is not None:
                (there / file).write_text(text.replace("<../../domains/", f"<{_DOMAINS}/"))
    infra = tmp_path / "infra"
    infra.mkdir()
    (infra / "installation.ttl").write_text(installation((REPO_ROOT / "infra" / "installation.ttl").read_text()))
    if derivation:
        (infra / "installation.derived.ttl").write_text((REPO_ROOT / "infra" / "installation.derived.ttl").read_text())
    monkeypatch.setattr(installed, "INSTALLATION", infra / "installation.ttl")
    monkeypatch.setattr(installed, "DERIVATION", infra / "installation.derived.ttl")
    monkeypatch.setattr(installed, "worlds", lambda: names)
    for module in (installed, mqtt, compose, firmware):
        monkeypatch.setattr(module, "world_dir", lambda name: root / name)
    return root


def _asserting(*urls: str, world: str = "sensing") -> str:
    """A deployment graph a world asserts of its own broker."""
    said = " , ".join(f'"{u}"' for u in urls)
    return (f"@prefix : <http://example.org/orexis/world/{world}#> .\n@prefix onboarding: <http://example.org/orexis/onboarding#> .\n"
            f"@prefix schema: <https://schema.org/> .\n<> a onboarding:DeploymentGraph .\n:broker schema:url {said} .\n")


_SENSING_BROKER = "http://example.org/orexis/world/sensing#broker"

#  A SECOND BROKER, stated as a first one is: named in the society as what a client could connect
#  to, and its address asserted in a deployment graph of the world's own.
_TWO_BROKERS = {("sensing", "society.ttl"): lambda text: text + "\n:elsewhere a mqtt4ssn:Broker .\n",
                ("sensing", "deployment.ttl"): lambda _: _asserting("mqtt://elsewhere:1999", "mqtts://elsewhere:8999")
                .replace(":broker schema:url", ":elsewhere schema:url")}


def test_a_world_stating_two_brokers_is_refused_naming_both(tmp_path, monkeypatch):
    """Broken on purpose: the sensing world with a second broker. `broker` kept the first host it
    met and a port per scheme from whichever url sorted last, so this world was handed
    `elsewhere` with the sensing broker's ports and nothing said so. How several brokers reach an
    agent is an open seam (a-documents-kind-says-who-reads-it), so onboarding refuses instead."""
    from onboarding import mqtt

    _installed(tmp_path, monkeypatch, _TWO_BROKERS)
    with pytest.raises(SystemExit, match=r"2 mqtt4ssn:Brokers") as refused:
        mqtt.broker("sensing")
    assert "sensing#broker" in str(refused.value) and "sensing#elsewhere" in str(refused.value)


@pytest.mark.parametrize("edit, contradiction", [
    (lambda text: text.replace('"mqtts://localhost:8888"', '"mqtts://elsewhere:8888"'), "two hosts"),
    (lambda text: text.replace('"mqtts://localhost:8888"', '"mqtt://localhost:1999"'), "two mqtt:// ports"),
    (lambda text: text.replace('"mqtt://localhost:1888"', '"mqtt://localhost:1888" , "mqtts://localhost:8999"'),
     "two mqtts:// ports"),
], ids=["hosts", "plain", "tls"])
def test_one_broker_given_two_addresses_is_refused(tmp_path, monkeypatch, edit, contradiction):
    """One broker whose urls disagree — two hosts, or two ports for one scheme — was answered with
    whichever sorted first or last. A board is flashed with one host and one port, so one of them
    is simply wrong, and onboarding cannot tell which. The terrace asserts its urls."""
    from onboarding import mqtt

    _installed(tmp_path, monkeypatch, {("terrace", "deployment.ttl"): edit})
    with pytest.raises(SystemExit, match=contradiction):
        mqtt.broker("terrace")


@pytest.mark.parametrize("tool", ["compose", "firmware"])
def test_the_tools_told_the_address_inherit_the_refusal(tmp_path, monkeypatch, tool):
    """`orexis-compose` writes the address into every agent's environment and `orexis-firmware`
    into every board's config.h; both ask `broker`, so neither writes a merged address."""
    from onboarding import compose, firmware

    _installed(tmp_path, monkeypatch, _TWO_BROKERS)
    with pytest.raises(SystemExit, match=r"2 mqtt4ssn:Brokers"):
        compose.render("sensing") if tool == "compose" else firmware.generate("sensing")


def test_what_onboarding_tells_an_agent_of_its_series_stores_is_what_the_sinks_load(tmp_path):
    """A series store is told by purpose (#825, #826): for history, and for metrics where the world is
    monitored, `orexis-compose` writes where the store serving the purpose is under
    `INFLUX_<PURPOSE>_*` and mounts the file `orexis-influx` mints, which says the bucket and the token
    under the same purpose, and for metrics the window. Put together as the terrace's container has
    them, they load both sinks, each on a bucket of its own, and the installation's window. In every
    compose file history is told, metrics exactly where the world is monitored, and the environment
    naming one bucket with no purpose is gone."""
    import yaml
    from dotenv import dotenv_values

    from agent.metrics import window as metrics
    from agent.series import HISTORY, METRICS, PURPOSES, install, load, sink
    from onboarding import compose, influx, installation

    service = yaml.safe_load(compose.render("terrace"))["services"]["agent-terrace"]
    environment = dict(service["environment"])
    for purpose in PURPOSES:
        minted = influx.credential_file("terrace", "terrace", purpose)
        assert minted.name == f"influx-{purpose.lower()}-terrace.env"
        assert f"./secrets/{minted.name}" in service["env_file"], "compose mounts what influx mints"
        credential = tmp_path / minted.name
        influx._write_credential(credential, "terrace", purpose, influx.bucket_name("terrace", "terrace", purpose), "a-token")
        environment.update(dotenv_values(credential))
    try:
        assert load(environment) == (HISTORY, METRICS)
        assert (sink(HISTORY).bucket, sink(METRICS).bucket) == ("terrace-terrace", "terrace-terrace-metrics")
        assert metrics.load(environment) == installation.interval(METRICS) == 60
    finally:
        for purpose in PURPOSES:
            install(purpose, None)
        metrics.reset()
    composed = sorted((REPO_ROOT / "world").glob("*/compose.yaml"))
    assert composed, "the glob stopped matching"
    told = {path.parent.name: installation.purposes(path.parent.name) for path in composed}
    assert {w for w, p in told.items() if METRICS in p} == {"greenhouse", "terrace"}, told
    assert {w for w, p in told.items() if METRICS not in p}, "every world is monitored — the guard checks one side"
    for path in composed:
        text = path.read_text()
        assert "INFLUX_HISTORY_URL" in text, path
        monitored = METRICS in told[path.parent.name]
        assert ("INFLUX_METRICS_URL" in text) == ("influx-metrics-" in text) == (metrics.INTERVAL_KEY in text) == monitored, path
        assert not re.search(r"\bINFLUX_(URL|ORG|BUCKET|TOKEN)\b", text), path


def test_history_is_served_by_one_store_and_metrics_by_one_or_by_none(tmp_path, monkeypatch):
    """The installation ties a store to a purpose by `onboarding:serves` (#826). History is served
    by exactly one and kept for ever, and served by none it is refused, since every agent writes it.
    Metrics are optional (amended): served by none, a world that does not ask is told of history
    alone, and one that says it is `onboarding:monitored` is refused — by `purposes`, which every
    tool asks, so the compose file refuses it too."""
    from agent.series import HISTORY, METRICS, PURPOSES
    from onboarding import compose, installation

    assert {p: installation.series(p) for p in PURPOSES} == {p: ("http://localhost:8086", "orexis") for p in PURPOSES}
    assert installation.retention(HISTORY) is None and installation.retention(METRICS) == 30
    assert installation.interval(HISTORY) is None and installation.interval(METRICS) == 60
    _installed(tmp_path, monkeypatch, installation=lambda text: text.replace(" , onboarding:Metrics .", " ."))
    assert installation.served(METRICS) is None
    assert installation.purposes("allotment") == (HISTORY,)
    for ask in (lambda: installation.purposes("terrace"), lambda: compose.render("greenhouse")):
        with pytest.raises(SystemExit, match=r"monitored.*Metrics from no store"):
            ask()
    _installed(tmp_path / "again", monkeypatch, installation=lambda text: text.replace("onboarding:History , ", ""))
    with pytest.raises(SystemExit, match=r"0 onboarding:SeriesStores serving History"):
        installation.series(HISTORY)


def test_a_world_is_monitored_only_where_its_own_deployment_says_so(tmp_path, monkeypatch):
    """Opt-in, one statement: the terrace says it and is monitored; take the statement out and it is
    not, whatever the installation serves."""
    from agent.series import HISTORY, METRICS
    from onboarding import installation

    assert installation.purposes("terrace") == (HISTORY, METRICS)
    _installed(tmp_path, monkeypatch, {("terrace", "deployment.ttl"): lambda text: text.replace("<> onboarding:monitored true .", "")})
    assert not installation.monitored("terrace") and installation.purposes("terrace") == (HISTORY,)


# --- asserted wins, derived completes: a port no world asserts is the installation's (#827) ------

def test_an_asserted_url_wins_and_a_broker_asserting_none_is_allocated_one():
    """The terrace asserts where its broker listens and is told exactly that; the sensing world
    asserts nothing, and is told what the installation allocated it — and the allocation names no
    broker that asserts."""
    from onboarding import installation, mqtt

    assert mqtt.broker("terrace") == ("localhost", 1888, 8888)
    assert mqtt.broker("sensing") == ("localhost", 1884, 8884)
    assert installation.allocated(_SENSING_BROKER) == ["mqtt://localhost:1884", "mqtts://localhost:8884"]
    assert installation.allocated("http://example.org/orexis/world/terrace#broker") == []


def test_an_assertion_wins_over_an_allocation_already_made(tmp_path, monkeypatch):
    """A world that comes to assert a url is told its assertion at once, whatever the derived
    document still says, and the next derivation lets the allocation go."""
    from onboarding import installation, mqtt

    _installed(tmp_path, monkeypatch, {("sensing", "deployment.ttl"): lambda _: _asserting("mqtt://localhost:1885", "mqtts://localhost:8885")})
    assert mqtt.broker("sensing") == ("localhost", 1885, 8885)
    assert _SENSING_BROKER not in installation.derive()


def test_the_allocation_gives_the_sensing_world_the_port_it_used_to_assert():
    """Nothing to reflash: the sensing world asserted 1884 and 8884 until #827, its board is flashed
    with 1884, and the lowest free slot of the installation's pool — derived from nothing
    remembered — is exactly that."""
    from onboarding import installation

    assert installation.derive(remember=False) == {_SENSING_BROKER: ["mqtt://localhost:1884", "mqtts://localhost:8884"]}


def test_the_committed_derived_document_is_a_fresh_derivation():
    """`infra/installation.derived.ttl` says GENERATED — do not edit, and it is what every renderer
    reads a port from, so one left behind by a change to the documents tells a world a port nobody
    allocated. Held to what a derivation writes now, as a committed compose file is."""
    from onboarding import installation

    assert installation.DERIVATION.read_text() == installation.derivation_text(), \
        "infra/installation.derived.ttl is not what a derivation writes now — run `orexis-onboard`"


def test_a_derived_document_edited_by_hand_is_refused(tmp_path, monkeypatch):
    """The derivation keeps what it allocated before, so its own output is one of its inputs, and a
    hand edit would be kept as if allocated — the fresh-derivation test above passing on it. A kept
    allocation must be one slot of the pool, both urls raised alike, or it is refused."""
    from onboarding import installation

    _installed(tmp_path, monkeypatch)
    installation.DERIVATION.write_text(installation.DERIVATION.read_text().replace('localhost:1884"', 'localhost:1885"'))
    with pytest.raises(SystemExit, match="no slot of the installation's pool"):
        installation.derive()


def test_the_derived_document_arrives_derived_and_the_installation_asserted():
    """How a graph arrived is the loader's to say, as the boot says it of its closure: onboarding
    reads the installation as asserted and what it derived as derived, and asks by both."""
    from onboarding import derived, installation
    from onboarding.reading import DEPLOYMENT

    s = installation._store()
    assert derived.graphs(s, DEPLOYMENT, derived.ASSERTED) == [installation.INSTALLATION.resolve().as_uri()]
    assert derived.graphs(s, DEPLOYMENT, derived.DERIVED) == [installation.DERIVATION.resolve().as_uri()]


def test_no_renderer_computes_a_port(tmp_path, monkeypatch):
    """With nothing derived, a world asserting no url has no address, and every renderer says so
    rather than working one out — the allocation is the derivation's alone."""
    from onboarding import compose, mqtt

    _installed(tmp_path, monkeypatch, derivation=False)
    for render in (lambda: mqtt.broker("sensing"), lambda: compose.render("sensing")):
        with pytest.raises(SystemExit, match="has allocated it none"):
            render()
    assert mqtt.broker("terrace") == ("localhost", 1888, 8888)


def _a_world_before_sensing(text: str) -> str:
    return text.replace("/world/sensing#", "/world/aaa#")


def test_a_world_added_later_moves_no_other_port(tmp_path, monkeypatch):
    """A world whose name sorts before every other, asserting nothing, is allocated the lowest slot
    left, and the sensing world keeps the port its board is flashed with. Forgetting what was
    allocated would have handed the newcomer 1884 and moved the sensing world — which is why the
    derivation remembers."""
    from onboarding import installation

    aaa = {("aaa", "world.ttl"): lambda _: _a_world_before_sensing((REPO_ROOT / "world/sensing/world.ttl").read_text()),
           ("aaa", "society.ttl"): lambda _: _a_world_before_sensing((REPO_ROOT / "world/sensing/society.ttl").read_text())}
    _installed(tmp_path, monkeypatch, aaa)
    newcomer = "http://example.org/orexis/world/aaa#broker"
    assert installation.derive() == {newcomer: ["mqtt://localhost:1885", "mqtts://localhost:8885"],
                                     _SENSING_BROKER: ["mqtt://localhost:1884", "mqtts://localhost:8884"]}
    assert installation.derive(remember=False)[_SENSING_BROKER] == ["mqtt://localhost:1885", "mqtts://localhost:8885"]


@pytest.mark.parametrize("edit, slot", [
    ({("terrace", "deployment.ttl"): lambda _: _asserting("mqtt://localhost:1884", "mqtts://localhost:8884", world="terrace")}, 1885),
    ({("terrace", "deployment.ttl"): lambda _: _asserting("mqtt://localhost:1884", "mqtts://localhost:8885", world="terrace")}, 1886),
], ids=["both-taken", "one-of-the-pair-taken"])
def test_an_allocation_avoids_every_port_held(tmp_path, monkeypatch, edit, slot):
    """A slot is taken only where every url of the pool, raised by it, is free: the terrace
    asserting the pool's first plain and TLS ports pushes the sensing world one slot on, and
    asserting the first plain and the second TLS pushes it two."""
    from onboarding import installation

    _installed(tmp_path, monkeypatch, edit)
    assert installation.derive(remember=False)[_SENSING_BROKER] == [f"mqtt://localhost:{slot}", f"mqtts://localhost:{slot + 7000}"]


@pytest.mark.parametrize("edit, clash", [
    ({("greenhouse", "deployment.ttl"): lambda text: text.replace("1889", "1888")}, "localhost:1888"),
    ({("allotment", "deployment.ttl"): lambda text: text.replace("8890", "8086")}, "localhost:8086"),
    ({("greenhouse", "deployment.ttl"): lambda text: text.replace("1889", "1884")}, "localhost:1884"),
    ({("greenhouse", "deployment.ttl"): lambda text: text.replace("mqtt://localhost:1889", "mqtt://localhost"),
      ("allotment", "deployment.ttl"): lambda text: text.replace("1890", "1883")}, "localhost:1883"),
], ids=["two-worlds-assert-one-port", "a-world-asserts-a-service-port", "a-world-asserts-an-allocated-port",
        "a-default-port"])
def test_a_collision_is_refused(tmp_path, monkeypatch, edit, clash):
    """What no world can see and the installation can: two brokers on one port, or a broker on the
    series store's. Refused and named, never resolved — a world asserting the port already
    allocated to the sensing world is refused rather than moving it, since its board is flashed
    with that port. A url stating no port takes its scheme's, so a clash cannot hide behind an
    omission."""
    from onboarding import installation

    _installed(tmp_path, monkeypatch, edit)
    with pytest.raises(SystemExit, match=rf"{clash} is held by .* and by "):
        installation.derive()


def test_one_port_on_two_hosts_is_no_clash(tmp_path, monkeypatch):
    """A port is unique per HOST, and the host is in the url, so an installation split over two
    machines may give two brokers one port."""
    from onboarding import installation, mqtt

    _installed(tmp_path, monkeypatch, {("greenhouse", "deployment.ttl"): lambda text: text.replace("localhost:1889", "elsewhere:1888")
                                       .replace("localhost:8889", "elsewhere:8889")})
    installation.derive()
    assert mqtt.broker("greenhouse") == ("elsewhere", 1888, 8889)


@pytest.mark.parametrize("where", ["installation", "world"])
def test_a_credential_in_a_url_is_refused(tmp_path, monkeypatch, where):
    """A deployment graph says where, never what may be done there: a password in a url would be in
    every compose file and config.h written from it, one careless copy from leaving."""
    from onboarding import installation

    if where == "installation":
        _installed(tmp_path, monkeypatch, installation=lambda text: text.replace("http://localhost:8086", "http://admin:secret@localhost:8086"))
        ask = lambda: installation.series("METRICS")
    else:
        _installed(tmp_path, monkeypatch, {("terrace", "deployment.ttl"): lambda text: text.replace("mqtt://localhost", "mqtt://terrace:secret@localhost")})
        ask = installation.derive
    with pytest.raises(SystemExit, match="credential"):
        ask()


#  WHAT THE INSTALLATION MAY SAY. A token is refused as a url's userinfo above; this is the other
#  half — no predicate but these, so a credential cannot arrive under a new name either.
_RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
_ONBOARDING = "http://example.org/orexis/onboarding#"
_INSTALLATION_SAYS = {_RDF_TYPE, "https://schema.org/url", _ONBOARDING + "organisation", _ONBOARDING + "image",
                      _ONBOARDING + "allocatesFrom", _ONBOARDING + "serves", _ONBOARDING + "retentionDays",
                      _ONBOARDING + "intervalSeconds"}


def test_the_installation_and_its_derivation_say_where_and_nothing_else():
    """The installation states its services, the purposes each store serves, how long a purpose is
    kept and how long a window of metrics is, and its pool, in eight words, and what was derived from
    it states urls alone, each on a broker some world's society names and whose world asserts none —
    so an allocation left behind by a world that has gone, or made under a misspelled IRI, is caught."""
    import pyoxigraph as ox

    from agent.store import document
    from onboarding import installation
    from onboarding.reading import world as read

    said = {q.predicate.value for q in document(REPO_ROOT / "infra" / "installation.ttl") if not isinstance(q.graph_name, ox.DefaultGraph)}
    assert said and said <= _INSTALLATION_SAYS, f"the installation says {sorted(said - _INSTALLATION_SAYS)}"
    derivation = [q for q in document(REPO_ROOT / "infra" / "installation.derived.ttl") if not isinstance(q.graph_name, ox.DefaultGraph)]
    assert derivation and {q.predicate.value for q in derivation} == {_URL}
    unasserted = set()
    for w in _worlds():
        store = read(REPO_ROOT / "world" / w)
        unasserted |= {b for b in installation.brokers_of(store) if not installation.asserted_on(store, b)}
    assert unasserted, "no world leaves its broker's url to the installation — the allocation checks nothing"
    assert {q.subject.value for q in derivation} == unasserted


def test_the_committed_infra_compose_is_what_the_installation_renders():
    """`infra/compose.yaml` says GENERATED — do not edit; held to it as a world's compose file is."""
    from onboarding import installation

    assert (REPO_ROOT / "infra" / "compose.yaml").read_text() == installation.render(), \
        "infra/compose.yaml is not what `orexis-infra-compose` renders — regenerate it"


# --- a society the agents read, a deployment only onboarding reads (#823) -----------------------

_MQTT4SSN = "https://www.w3id.org/MQTT4SSN-Ontology#"
_URL = "https://schema.org/url"


def test_no_agent_holds_where_its_broker_listens():
    """The broker is two things and goes to two graphs: the rendezvous every client is connected to
    is in the society, which an agent reads, and the `schema:url` it listens on is in a deployment
    graph — the world's own, or the installation's derivation — a kind no agent's vocabulary
    declares. Booted from its directory, as a container boots, every agent of every world with a
    bus holds the broker and not one url on it — it is told where through its environment, and
    cannot read it off the world."""
    import pyoxigraph as ox

    from agent.runtime import boot
    from onboarding.compose import roster

    rdf_type, broker_class, url = (ox.NamedNode(i) for i in (
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", _MQTT4SSN + "Broker", _URL))
    booted = []
    for world in _worlds():
        here = REPO_ROOT / "world" / world
        for agent in roster(world):
            store = boot(here, agent)
            brokers = {q.subject for q in store.quads_for_pattern(None, rdf_type, broker_class, None)}
            if not brokers:
                continue                     # a world with no bus
            held = sorted(f"{q.subject.value} {q.object.value}" for b in brokers
                          for q in store.quads_for_pattern(b, url, None, None))
            assert not held, f"{world}/{agent} holds where its broker listens: {held}"
            booted.append(f"{world}/{agent}")
    assert len(booted) >= 6, f"only {booted} hold a broker — the guard would check almost nothing"


def test_a_world_graph_states_no_wiring_and_only_a_deployment_graph_an_address():
    """What keeps the split from eroding: every MQTT4SSN word a world states — a client, a topic,
    a filter, which device speaks on which — is in its society graph, so its world graph holds the
    subjects, sensors and systems alone; and a `schema:url` is stated in a deployment graph or
    nowhere, since in any other kind some agent would load it."""
    import pyoxigraph as ox

    from agent.store import document, kinds_in

    society, deployment = "http://example.org/orexis#SocietyGraph", _ONBOARDING + "DeploymentGraph"
    seen, wrong = {"society": 0, "deployment": 0}, []
    for world in _worlds():
        here = REPO_ROOT / "world" / world
        for path in sorted([*here.glob("*.ttl"), *here.glob("*.trig"), *here.glob("beliefs/*.ttl")]):
            doc = document(path)
            for graph, kinds in kinds_in(doc).items():
                quads = list(doc.quads_for_pattern(None, None, None, ox.NamedNode(graph)))
                speaks = any(isinstance(t, ox.NamedNode) and t.value.startswith(_MQTT4SSN)
                             for q in quads for t in (q.predicate, q.object))
                addresses = any(q.predicate.value == _URL for q in quads)
                seen["society"] += society in kinds and speaks
                seen["deployment"] += deployment in kinds and addresses
                if speaks and society not in kinds:
                    wrong.append(f"{world}/{path.name} speaks MQTT4SSN in a graph of {sorted(kinds)}")
                if addresses and deployment not in kinds:
                    wrong.append(f"{world}/{path.name} states a schema:url in a graph of {sorted(kinds)}")
    assert seen["society"] >= 4 and seen["deployment"] >= 3, f"the guard found {seen} — it would check nothing"
    assert not wrong, "\n".join(wrong)


def test_a_committed_compose_file_is_what_onboarding_renders():
    """A compose file says GENERATED — do not edit, and nothing held it to that. It is what hands a
    container its documents, so one left behind by a change to the documents boots an agent that
    cannot find itself: a society graph unmounted is an agent the world says nothing about. Every
    world has one, a world with no bus as well — onboarding writes it for every world, so a world
    without one committed is a tree left dirty by the first `orexis-onboard`."""
    from onboarding import compose

    composed = sorted(p.parent.name for p in (REPO_ROOT / "world").glob("*/compose.yaml"))
    assert composed == _worlds(), f"a world with no committed compose file: {sorted(set(_worlds()) - set(composed))}"
    #  A MOUNT OF A SECRET DOCUMENT is set aside on both sides: it is rendered where this checkout holds
    #  the document and not where it does not, so it cannot be committed either way (#860).
    private = lambda text: "\n".join(line for line in text.splitlines()
                                     if not (line.strip().startswith("- ./secrets/") and ".ttl:" in line))
    for world in composed:
        assert private((REPO_ROOT / "world" / world / "compose.yaml").read_text()) == private(compose.render(world)), \
            f"world/{world}/compose.yaml is not what `orexis-compose {world}` renders — regenerate it"


def test_every_shipped_world_with_a_bus_states_one_broker_address():
    """The other direction: the refusal must not fire on a world that is right. A world with no bus
    — hanoi — states no broker and is refused for that, as before: `broker` is asked for an address
    that does not exist, and the tools stop asking it for such a world (below)."""
    from onboarding import mqtt

    answered = []
    for world in _worlds():
        try:
            host, plain, _tls = mqtt.broker(world)
        except SystemExit as refused:
            assert "states no mqtt4ssn:Broker" in str(refused), f"{world}: {refused}"
            continue
        assert host and plain, f"{world}: no address"
        answered.append(world)
    assert len(answered) >= 4, f"only {answered} state a broker — the guard would check nothing"


# --- a step runs where the world has what it serves: the bus is a premise -----------------------

def test_the_bus_is_a_premise_that_holds_exactly_where_a_world_names_a_broker():
    """`reading.PREMISES` answers the bus off the world, as the runtime's premises answer a package
    (#824): it holds for every world whose society names a broker, and for no other — and there is
    a world of each kind, or the steps it gates would be checked on one side alone."""
    from onboarding import installation, reading

    held = {w for w in _worlds() if reading.BUS in reading.premises(REPO_ROOT / "world" / w)}
    named = {w for w in _worlds() if installation.brokers_of(reading.world(REPO_ROOT / "world" / w))}
    assert held == named == set(_BUS_WORLDS), (held, named)
    assert set(_worlds()) - held, "every world has a bus — nothing checks a world without one"


def _onboarded(tmp_path, monkeypatch, world: str, caplog):
    """`orexis-onboard <world>` run whole, in-process, on a copy of the world beside the worlds with
    a bus and a copy of the installation: the series store answered by a stub that records what it
    was asked, the broker never signalled, and everything minted written into the copy. Answers the
    copy of the world, what the store was asked, and which brokers were to be reloaded."""
    import logging

    from onboarding import certs, compose, dashboards, influx, mqtt, onboard

    root = _installed(tmp_path, monkeypatch, {(world, "world.ttl"): lambda text: text})
    for module in (onboard, certs, dashboards, influx):
        monkeypatch.setattr(module, "world_dir", lambda name: root / name)
    for module in (compose, mqtt, dashboards):
        monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(dashboards, "DASHBOARD_ROOT", tmp_path / "dashboards")
    asked, reloaded = [], []
    monkeypatch.setattr(influx, "_provision", lambda w, agents, purpose, rotate: asked.append(("grant", purpose, tuple(agents))))
    monkeypatch.setattr(influx, "_withdraw", lambda w, agents, purpose: asked.append(("withdraw", purpose, tuple(agents))))
    #  THE REPORT'S STORE HALF asks the series store with the admin token; here it answers nothing
    #  stale and records that it was asked, so a host holding an admin token asks no real store.
    monkeypatch.setattr(influx, "stale_grants", lambda w: asked.append(("stale", w)) or [])
    monkeypatch.setattr(mqtt, "reload_broker", lambda w: reloaded.append(w) or True)
    with caplog.at_level(logging.DEBUG):
        onboard.onboard(world)
    #  WHAT ONBOARDING'S OWN READS PASS OVER is the kinds it reads next, and is not said at INFO.
    passed = [r for r in caplog.records if r.getMessage().startswith("passed over")]
    assert passed, "nothing was passed over — the guard below would check nothing"
    assert not [r.getMessage() for r in passed if r.levelno >= logging.INFO]
    return root / world, asked, reloaded


@pytest.mark.parametrize("world", ["hanoi", "courier", "tower", "driver"])
def test_a_world_with_no_bus_is_onboarded_without_one(tmp_path, monkeypatch, caplog, world):
    """Hanoi, the courier and the tower name no broker, and `orexis-onboard` refused all three at the
    first tool that asked for an address, so none could run in a container; the driver world, which
    imports a domain document its domain's ontology does not, is onboarded the same way. Onboarded now: history
    granted, metrics withdrawn since none is monitored, no broker credential, ACL or certificate, and
    the one line saying so — and a compose file of its agents alone, which is the one committed."""
    import yaml

    from agent.series import HISTORY, METRICS
    from onboarding.compose import roster

    here, asked, reloaded = _onboarded(tmp_path, monkeypatch, world, caplog)
    agents = tuple(roster(world))
    assert agents, f"{world} has no agents — the grants below would check nothing"
    assert asked == [("grant", HISTORY, agents), ("withdraw", METRICS, agents), ("stale", world)]
    assert reloaded == []
    secrets = sorted(p.name for p in (here / "secrets").glob("*")) if (here / "secrets").exists() else []
    assert not [s for s in secrets if s.startswith("mqtt-") or s.endswith((".crt", ".key"))], secrets
    assert not (here / "mosquitto").exists()
    said = [r.getMessage() for r in caplog.records if "no bus" in r.getMessage()]
    assert len(said) == 1 and "mqtt4ssn:Broker" in said[0], said

    written = (here / "compose.yaml").read_text()
    assert written == (REPO_ROOT / "world" / world / "compose.yaml").read_text(), "not the committed compose file"
    composed = yaml.safe_load(written)
    assert set(composed["services"]) == {f"agent-{a}" for a in agents}, "a service that is not an agent"
    assert set(composed["volumes"]) == {f"orexis-{world}-{a}" for a in agents}
    for name, service in composed["services"].items():
        assert not [k for k in service["environment"] if k.startswith("MQTT_")], name
        assert service["env_file"] == [f"./secrets/influx-history-{name.removeprefix('agent-')}.env"], name
        assert not [v for v in service["volumes"] if "/app/secrets/" in v], name


def test_a_world_with_a_bus_is_onboarded_with_everything(tmp_path, monkeypatch, caplog):
    """The other side: the sensing world names a broker, so it is granted the bus as before — a
    credential per principal, the ACL and the broker's config, the authority and every agent's
    certificate, the broker reloaded — and its compose file carries the broker, and its agent the
    broker's address."""
    import yaml

    from agent.series import HISTORY, METRICS
    from onboarding import mqtt
    from onboarding.compose import roster

    here, asked, reloaded = _onboarded(tmp_path, monkeypatch, "sensing", caplog)
    agents, _devices = mqtt.grants("sensing")
    assert asked == [("grant", HISTORY, tuple(roster("sensing"))), ("withdraw", METRICS, tuple(roster("sensing"))),
                     ("stale", "sensing")]
    assert reloaded == ["sensing"]
    for agent in agents:
        for minted in (f"mqtt-{agent}.env", f"{agent}.crt", f"{agent}.key"):
            assert (here / "secrets" / minted).exists(), minted
    for minted in ("secrets/ca.crt", "secrets/broker.crt", "mosquitto/acl.conf", "mosquitto/orexis.conf", "mosquitto/crl.pem"):
        assert (here / minted).exists(), minted
    assert [r for r in caplog.records if "nothing stale" in r.getMessage()], "a fresh onboarding reports nothing stale"
    assert not [r for r in caplog.records if "no bus" in r.getMessage()]
    written = (here / "compose.yaml").read_text()
    assert written == (REPO_ROOT / "world" / "sensing" / "compose.yaml").read_text(), "not the committed compose file"
    services = yaml.safe_load(written)["services"]
    assert "mosquitto" in services and "MQTT_HOST" in services["agent-fern"]["environment"]


def test_a_simulator_with_no_broker_to_connect_to_is_refused(tmp_path, monkeypatch):
    """Broken on purpose: the allotment with its broker's type struck from the society. Its systems
    are still simulated, by a client that connects to a broker, so a compose file of agents alone
    would drop the simulator in silence; it is refused, and the world named."""
    from onboarding import compose

    _installed(tmp_path, monkeypatch, {("allotment", "society.ttl"): lambda text: text.replace(":broker a mqtt4ssn:Broker .", "")})
    with pytest.raises(SystemExit, match="names no mqtt4ssn:Broker for its simulator"):
        compose.render("allotment")


def test_orexis_mqtt_grants_a_world_with_no_bus_nothing_and_says_so(tmp_path, monkeypatch, caplog):
    """Run alone on a world with no bus, `orexis-mqtt` answers rather than refuses — nothing to grant,
    as `orexis-onboard` says of the same world — and `provision`, asked directly, refuses before a
    credential is minted for a bus that is not there: it asks the broker's address first."""
    import logging

    from onboarding import mqtt

    root = _installed(tmp_path, monkeypatch, {("hanoi", "world.ttl"): lambda text: text})
    monkeypatch.setattr(mqtt, "reload_broker", lambda w: pytest.fail("a world with no bus had its broker reloaded"))
    with caplog.at_level(logging.INFO):
        mqtt.main(["hanoi"])
    assert [r for r in caplog.records if "no bus" in r.getMessage()]
    with pytest.raises(SystemExit, match="states no mqtt4ssn:Broker"):
        mqtt.provision("hanoi")
    assert not (root / "hanoi" / "secrets").exists(), "credentials minted for a world with no bus"


# --- revocation: a CRL always, a report that takes nothing, and --revoke that does ---------------

def _crl_of(here):
    from cryptography import x509

    return x509.load_pem_x509_crl((here / "mosquitto" / "crl.pem").read_bytes())


def test_a_crl_is_written_empty_where_nobody_is_revoked_and_the_config_always_names_it(tmp_path, monkeypatch, caplog):
    """`crlfile` makes OpenSSL demand a CRL from the issuer on every handshake, so a config naming a
    file that is absent, or a CRL past its nextUpdate, refuses the whole society (#29). Onboarded
    fresh, the sensing world's broker config names the CRL, the compose file mounts it, and the file
    is there: signed by the world's authority, naming no serial, and good for as long as the
    authority is."""
    from cryptography import x509

    here, _asked, _reloaded = _onboarded(tmp_path, monkeypatch, "sensing", caplog)
    #  WHOLE LINES, not substrings: the first cut of this asked `in config`, and the config's own
    #  comment names the option, so the guard stayed green with the line struck out.
    directives = [line for line in (here / "mosquitto" / "orexis.conf").read_text().splitlines() if not line.startswith("#")]
    assert "crlfile /etc/mosquitto/crl.pem" in directives, directives
    assert directives.index("cafile /etc/mosquitto/clients-ca.crt") < directives.index("crlfile /etc/mosquitto/crl.pem") \
        < directives.index("acl_file /etc/mosquitto/acl.conf"), "the CRL is the TLS listener's"
    mounts = [line.strip() for line in (here / "compose.yaml").read_text().splitlines()]
    assert "- ./mosquitto/crl.pem:/etc/mosquitto/crl.pem:ro" in mounts
    crl = _crl_of(here)
    ca = x509.load_pem_x509_certificate((here / "secrets" / "ca.crt").read_bytes())
    assert list(crl) == [], "nobody was revoked"
    assert crl.issuer == ca.subject and crl.is_signature_valid(ca.public_key())
    assert crl.next_update_utc == ca.not_valid_after_utc, "the CRL's horizon is the authority's"
    assert crl.extensions.get_extension_for_class(x509.CRLNumber).value.crl_number == 1


def test_revoking_an_agent_puts_its_serial_on_the_crl_and_takes_its_credential(tmp_path, monkeypatch, caplog):
    """`orexis-mqtt sensing --revoke fern`: fern's certificate is on the CRL by serial, its files
    and its broker credential are gone, the passwd and the ACL no longer name it, and the output
    says the broker must restart, since SIGHUP reloads no TLS material. Onboarded again, the
    wiring still implies fern, so it gets a NEW certificate — and the old serial stays on the CRL,
    carried forward from the file, so the revoked one stays refused."""
    import logging

    from cryptography import x509

    from onboarding import mqtt

    here, _asked, _reloaded = _onboarded(tmp_path, monkeypatch, "sensing", caplog)
    secrets = here / "secrets"
    old = x509.load_pem_x509_certificate((secrets / "fern.crt").read_bytes())
    assert "sensing-fern" in (here / "mosquitto" / "passwd").read_text()
    caplog.clear()
    with caplog.at_level(logging.INFO):
        mqtt.main(["sensing", "--revoke", "fern", "--no-reload"])
    said = [r.getMessage() for r in caplog.records]
    assert [r.serial_number for r in _crl_of(here)] == [old.serial_number]
    assert _crl_of(here).extensions.get_extension_for_class(x509.CRLNumber).value.crl_number == 2
    for gone in ("fern.crt", "fern.key", "mqtt-fern.env"):
        assert not (secrets / gone).exists(), gone
    assert "sensing-fern" not in (here / "mosquitto" / "passwd").read_text()
    assert "user sensing-fern" not in (here / "mosquitto" / "acl.conf").read_text()
    assert [s for s in said if "restart" in s and "SIGHUP" in s], said
    assert [s for s in said if "still implies fern" in s], said

    #  A DEVICE has a credential and no certificate: the credential goes, the CRL is unchanged.
    device = next(p.name[len("mqtt-"):-len(".env")] for p in secrets.glob("mqtt-*.env"))
    mqtt.main(["sensing", "--revoke", device, "--no-reload"])
    assert not (secrets / f"mqtt-{device}.env").exists()
    assert [r.serial_number for r in _crl_of(here)] == [old.serial_number]
    with pytest.raises(SystemExit, match="nothing to revoke"):
        mqtt.main(["sensing", "--revoke", "nobody", "--no-reload"])

    mqtt.provision("sensing")
    new = x509.load_pem_x509_certificate((secrets / "fern.crt").read_bytes())
    assert new.serial_number != old.serial_number
    assert [r.serial_number for r in _crl_of(here)] == [old.serial_number], "carried forward, not re-made"
    assert (secrets / f"mqtt-{device}.env").exists(), "the wiring still implies the device, so it is granted again"


def test_a_crl_that_will_not_parse_is_refused_not_rewritten(tmp_path, monkeypatch, caplog):
    """The CRL is the record of what was revoked; rewritten from nothing it would re-admit every
    certificate it named, in silence."""
    from onboarding import mqtt

    here, _asked, _reloaded = _onboarded(tmp_path, monkeypatch, "sensing", caplog)
    (here / "mosquitto" / "crl.pem").write_text("not a CRL\n")
    with pytest.raises(SystemExit, match="will not parse"):
        mqtt.provision("sensing")


def test_the_report_names_a_stale_credential_and_takes_nothing(tmp_path, monkeypatch, caplog):
    """A principal with files under `secrets/` and no agent or device in the society: `ghost` has a
    broker credential, a certificate not on the CRL, and a history token's file. `orexis-onboard`
    names all three, says the certificate still opens a session, names the command for each, and
    removes none of them."""
    import logging
    import shutil

    from onboarding import influx, onboard

    asks_the_store = influx.stale_grants
    here, _asked, _reloaded = _onboarded(tmp_path, monkeypatch, "sensing", caplog)
    secrets = here / "secrets"
    planted = ["mqtt-ghost.env", "ghost.crt", "ghost.key", "influx-history-ghost.env"]
    shutil.copy(secrets / "mqtt-fern.env", secrets / "mqtt-ghost.env")
    shutil.copy(secrets / "fern.crt", secrets / "ghost.crt")
    shutil.copy(secrets / "fern.key", secrets / "ghost.key")
    (secrets / "influx-history-ghost.env").write_text("INFLUX_HISTORY_BUCKET=sensing-ghost\nINFLUX_HISTORY_TOKEN=x\n")
    caplog.clear()
    with caplog.at_level(logging.INFO):
        found = onboard.report("sensing")
    assert len(found) == 4 and all("ghost" in line for line in found), found
    assert [line for line in found if "ghost.crt" in line and "NOT on the CRL" in line], found
    assert [line for line in found if "mqtt-ghost.env" in line and "orexis-mqtt sensing --revoke ghost" in line], found
    assert [line for line in found if "influx-history-ghost.env" in line and "orexis-influx sensing --revoke ghost" in line
            and "keeps the bucket" in line], found
    assert not [line for line in found if "fern" in line], "a principal the wiring implies is not stale"
    assert all((secrets / name).exists() for name in planted), "the report took something"
    assert [r for r in caplog.records if r.levelno == logging.WARNING and "stale" in r.getMessage()]

    #  NO ADMIN TOKEN HERE: the real store half refuses to ask, the report says so and goes on with
    #  what the files alone say, so a report never fails the onboarding it ends.
    monkeypatch.setattr(influx, "stale_grants", asks_the_store)
    monkeypatch.setattr(influx, "ADMIN_ENV", REPO_ROOT / "infra" / "secrets" / "no-such-admin.env")
    caplog.clear()
    with caplog.at_level(logging.INFO):
        assert onboard.report("sensing") == found
    assert [r for r in caplog.records if "was not asked" in r.getMessage()], [r.getMessage() for r in caplog.records]
    #  AND A STORE THAT IS DOWN — a token in hand, nothing listening — is said and gone on from.
    monkeypatch.setattr(influx, "_admin_token", lambda: "a-token")
    monkeypatch.setattr(influx.installation, "served", lambda purpose: ("http://127.0.0.1:9", "orexis"))
    caplog.clear()
    with caplog.at_level(logging.INFO):
        assert onboard.report("sensing") == found
    assert [r for r in caplog.records if "could not be asked" in r.getMessage() and "127.0.0.1:9" in r.getMessage()], \
        [r.getMessage() for r in caplog.records]


def test_influx_revoke_deletes_the_tokens_and_keeps_the_bucket(tmp_path, monkeypatch, caplog):
    """The store half, against a stub of the authorizations API: every token described as the
    principal's in this world goes, whatever its purpose and one made before purposes with them,
    no other world's or agent's does, and nothing asks the buckets API at all — a bucket is
    history, and history that was true stays."""
    import logging

    from onboarding import influx

    class Auth:
        def __init__(self, description):
            self.description = description

    class Stub:
        def __init__(self):
            self.held = [Auth("orexis sensing/ghost history"), Auth("orexis sensing/ghost metrics"),
                         Auth("orexis sensing/ghost"), Auth("orexis sensing/ghostly history"),
                         Auth("orexis terrace/ghost history"), Auth("orexis sensing/fern history"), Auth(None)]
            self.deleted = []

        def find_authorizations(self):
            return list(self.held)

        def delete_authorization(self, auth):
            self.held.remove(auth)
            self.deleted.append(auth.description)

    stub = Stub()
    assert influx._revoke_grants(stub, "sensing", "ghost") == ["orexis sensing/ghost history", "orexis sensing/ghost metrics",
                                                                "orexis sensing/ghost"]
    assert [a.description for a in stub.held] == ["orexis sensing/ghostly history", "orexis terrace/ghost history",
                                                  "orexis sensing/fern history", None]

    #  THE FILE HALF, with the store unreachable by design: `served` answers no store, so nothing is
    #  asked, the credential files go, and the bucket is said to be kept.
    root = _installed(tmp_path, monkeypatch, {("sensing", "world.ttl"): lambda text: text})
    monkeypatch.setattr(influx, "world_dir", lambda name: root / name)
    monkeypatch.setattr(influx.installation, "served", lambda purpose: None)
    secrets = root / "sensing" / "secrets"
    secrets.mkdir()
    for name in ("influx-history-ghost.env", "influx-metrics-ghost.env", "influx-ghost.env", "influx-history-fern.env"):
        (secrets / name).write_text("INFLUX_HISTORY_TOKEN=x\n")
    with caplog.at_level(logging.INFO):
        influx.revoke("sensing", "ghost")
    assert sorted(p.name for p in secrets.iterdir()) == ["influx-history-fern.env"]
    assert [r for r in caplog.records if "bucket sensing-ghost kept" in r.getMessage()]
    assert influx.stale_files("sensing") == []
    (secrets / "influx-metrics-ghost.env").write_text("x\n")
    assert len(influx.stale_files("sensing")) == 1 and "'ghost'" in influx.stale_files("sensing")[0]
    with pytest.raises(SystemExit, match="nothing to revoke"):
        influx.revoke("sensing", "nobody")


def test_onboarding_passes_over_its_own_kinds_quietly_and_an_unknown_kind_aloud(tmp_path, caplog):
    """Onboarding reads a world as an agent boots it and then its own kinds, so the first half passes
    over the deployment and the hardware every time — about ten lines a run, each for a graph the
    second half reads. Those are DEBUG; a kind no reader declares is still said at INFO, since that
    is the one `unread` refuses."""
    import logging

    from onboarding import reading

    with caplog.at_level(logging.DEBUG, logger="runtime"):
        reading.world(REPO_ROOT / "world" / "terrace")
    passed = [r for r in caplog.records if r.getMessage().startswith("passed over")]
    assert {r.levelno for r in passed} == {logging.DEBUG} and len(passed) >= 2, [(r.levelname, r.getMessage()) for r in passed]

    caplog.clear()
    world = tmp_path / "hanoi"
    world.mkdir()
    domain = (REPO_ROOT / "domains" / "hanoi" / "ontology.ttl").as_uri()
    hanoi = REPO_ROOT / "world" / "hanoi"
    (world / "world.ttl").write_text((hanoi / "world.ttl").read_text().replace("<../../domains/hanoi/ontology.ttl>", f"<{domain}>"))
    (world / "state.ttl").write_text((hanoi / "state.ttl").read_text().replace("orexis:StateGraph", "orexis:StateGrpah"))
    with caplog.at_level(logging.DEBUG, logger="runtime"):
        reading.world(world)
    aloud = [r for r in caplog.records if r.getMessage().startswith("passed over") and r.levelno >= logging.INFO]
    assert len(aloud) == 1 and "StateGrpah" in aloud[0].getMessage(), [r.getMessage() for r in aloud]


# --- an agent that finishes is not restarted ---------------------------------------------------

#  Every shipped agent holding wants alone and reached by no transport: the runtime lets each exit.
_FINISHING = {("courier", "courier"), ("hanoi", "hanoi"), ("tower", "mover")}


def test_an_agent_that_finishes_is_not_restarted():
    """The runtime stops an agent holding no desire and reached by no transport once every want is
    reached, so `unless-stopped` would boot it again for ever to find nothing and exit. Rendered for
    every world: `restart: "no"` for exactly those agents, and `unless-stopped` for every other —
    those holding a desire, and the sensing world's and the terrace's, which hold none and are kept
    running by their transport alone."""
    import yaml

    from onboarding import compose

    policies = {(world, name.removeprefix("agent-")): service["restart"]
                for world in _worlds()
                for name, service in yaml.safe_load(compose.render(world))["services"].items()
                if name.startswith("agent-")}
    assert {agent for agent, policy in policies.items() if policy == "no"} == _FINISHING, policies
    assert {policy for agent, policy in policies.items() if agent not in _FINISHING} == {"unless-stopped"}, policies
    assert {("sensing", "fern"), ("terrace", "terrace")} <= set(policies), "no agent lasts by its transport alone"


def test_every_service_that_lasts_says_so():
    """After a boot the host starts again what says it lasts (`podman-restart`, run-a-world), and
    nothing else: the installation's two services said nothing, so no setting of the host could
    have brought the series store back after the power cut of 2026-10-03. Every service the
    installation renders, and every service of a world that is no agent — its broker, its
    simulator — says `unless-stopped`; an agent says it or `"no"`, which the test above holds."""
    import yaml

    from onboarding import compose, installation

    shared = {name: service.get("restart") for name, service in yaml.safe_load(installation.render())["services"].items()}
    assert shared and set(shared.values()) == {"unless-stopped"}, shared
    beside = {(world, name): service.get("restart")
              for world in _worlds()
              for name, service in yaml.safe_load(compose.render(world))["services"].items()
              if not name.startswith("agent-")}
    assert beside and set(beside.values()) == {"unless-stopped"}, beside


def test_an_agent_holding_a_desire_is_restarted_with_no_transport(tmp_path, monkeypatch):
    """The other premise alone: every shipped agent holding a desire is reached by a transport too,
    so the desire could go unread and the test above stay green. Hanoi's mover, given a desire
    beside its want, holds one and no transport, and lasts."""
    import yaml

    from onboarding import compose, reading

    desire = ("@prefix : <http://example.org/orexis/world/hanoi#> .\n"
              "@prefix hanoi: <http://example.org/orexis/hanoi#> .\n"
              "@prefix planning: <http://example.org/orexis/planning#> .\n"
              "<> a planning:DesireGraph .\n"
              ":hanoi planning:holds :the_tower_stands .\n"
              ":the_tower_stands a planning:Desire ; planning:metWhen hanoi:solved .\n")
    root = _installed(tmp_path, monkeypatch, {("hanoi", "desires.ttl"): lambda _text: desire})
    assert reading.lasts(root / "hanoi", "hanoi")
    assert not reading.lasts(REPO_ROOT / "world" / "hanoi", "hanoi"), "the shipped mover was to finish"
    assert yaml.safe_load(compose.render("hanoi"))["services"]["agent-hanoi"]["restart"] == "unless-stopped"


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


#  Code names AGENTS.md spells on purpose though nothing in the tree does — SPARQL's own functions,
#  today; it held nine retired identifiers as well while the principles narrated what WAS, until the
#  narration moved to the commit messages that already carried it. Retiring a name AGENTS.md uses is
#  adding it here or rewording the line, and either is a choice.
_NAMED_AS_HISTORY = {"HOURS", "MINUTES"}


def test_agents_md_names_code_that_exists():
    """Every backticked code name in AGENTS.md is spelled somewhere in the tracked tree, or is listed
    above as named on purpose. Written after finding the principles saying in the present tense that
    `Deliberator.pursued` plans every want and that the container calls `pursuit.consider`, both
    retired: the prose was wrong rather than broken, and the term census above reads `prefix:Term`
    alone."""
    text = (REPO_ROOT / "AGENTS.md").read_text()
    named = {n for n in re.findall(r"`([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)(?:\(\))?`", text)}
    assert len(named) > 50, "AGENTS.md names almost no code — this guard checks nothing"
    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                             cwd=REPO_ROOT, check=True).stdout.split()
    corpus = "\n".join((REPO_ROOT / f).read_text(errors="ignore") for f in tracked
                       if f.endswith((".py", ".toml", ".ttl", ".ru", ".trig", ".yml", ".yaml", ".sh"))
                       or f.endswith("Containerfile"))
    words = set(re.findall(r"\w+", corpus))
    missing = sorted(n for n in named - _NAMED_AS_HISTORY if not set(n.split(".")) <= words)
    assert not missing, (f"AGENTS.md names {missing}, spelled nowhere in the tree. Reword the line, or, "
                         f"where it says what WAS, add the name to _NAMED_AS_HISTORY.")
    stale = sorted(n for n in _NAMED_AS_HISTORY if n not in named)
    assert not stale, f"_NAMED_AS_HISTORY lists {stale}, which AGENTS.md no longer names — drop them"


# --- a graph of drifts says so -----------------------------------------------------------------------

def test_a_document_holding_drifts_is_a_drift_graph():
    """`predict` reads drifts from `orexis:DriftGraph` graphs alone, as the planner reads actions from
    `orexis:ActionGraph` alone — so a drifts file left typed the bare `orexis:PublicGraph` is a file the
    predictor passes over in silence, every public graph having been where it looked before. Every
    document under `domains/` and `world/` carrying a `prediction:Drift` row says the kind."""
    import rdflib

    PREDICTION, OREXIS = rdflib.Namespace("http://example.org/orexis/prediction#"), rdflib.Namespace("http://example.org/orexis#")
    holding = []
    for path in sorted([*REPO_ROOT.glob("domains/*/*.ttl"), *REPO_ROOT.glob("world/*/*.ttl")]):
        if "prediction:Drift" not in path.read_text():
            continue
        g = rdflib.Graph()
        g.parse(path, format="turtle", publicID=path.as_uri())
        if (None, rdflib.RDF.type, PREDICTION.Drift) not in g:
            continue
        holding.append(path)
        kinds = set(g.objects(rdflib.URIRef(path.as_uri()), rdflib.RDF.type))
        assert OREXIS.DriftGraph in kinds, f"{path.relative_to(REPO_ROOT)} holds drifts and says {kinds} — the predictor reads orexis:DriftGraph alone"
    assert holding, "no document holds a drift — this guard checks nothing"


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

