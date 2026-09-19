"""The W3C's own SSN descriptions, dropped into a world and held to our shapes.

These are not our files. `tests/fixtures/w3c-ssn/` holds two documents from `w3c/sdw` — the
repository behind the 2017 SSN Recommendation — describing a DHT22, which is the KY-015's
sibling and the part `packages/orexis-part-dht11/` was modelled against. They are byte-identical to
upstream; see the README beside them.

They are here to answer one question that reasoning could not: **can a description written by
the people who wrote the vocabulary be deployed in a world without editing it?**

The answer turns out to be *yes for the description, no for the illustration*, and the boundary
is worth pinning:

- a vendor describes a PART — what it is, what its channels can do, how accurate they are. That
  is theirs and it is complete.
- a world adds the DEPLOYMENT — a name on our wire, who drives it, whose plant it watches, which
  topic it publishes on. A vendor cannot know any of that, and its absence from their file is
  correct rather than a gap.

The first test is the deliverable. The rest say what breaks when it stops being true.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import rdflib
from pyshacl import validate as shacl_validate

from agent import genesis
from orexis_agent_progression.ontology import picks_graph
from orexis_agent_progression.store import Store
from agent.validate import _shapes_and_vocabulary, conforms, graph_from

from conftest import WORLDS_ROOT
from orexis_agent_progression.ontology import PUBLIC

FIXTURES = Path(__file__).parent / "fixtures" / "w3c-ssn"

#  THEIR FILE DOES NOT PARSE, and this is the one character we change.
#
#  `<observation/1087>` ends with `;` and never receives its `.`, so the next subject begins
#  mid-statement. Every Turtle parser rejects it; ours is not being strict. The fixture stays
#  byte-identical to upstream and the repair lives here, in code, where it is reviewable —
#  rather than being edited into the file where it would read as theirs.
#
#  Asserted rather than applied blindly: if W3C ever fixes it, `_repaired` fails and tells us,
#  instead of a silent no-op leaving a patch nobody needs.
_MALFORMED = "  ssn-system:qualityOfObservation <observation/1087#quality> ;\n"
_REPAIRED = "  ssn-system:qualityOfObservation <observation/1087#quality> .\n"


def _repaired(name: str) -> str:
    src = (FIXTURES / name).read_text()
    assert _MALFORMED in src, (
        f"{name} no longer carries the malformed statement this repair exists for — upstream "
        f"has probably fixed it, and this patch should go with it"
    )
    return src.replace(_MALFORMED, _REPAIRED, 1)


def _world_with(tmp_path, **files: str):
    """`world/sensing` plus some extra Turtle, built the way `orexis-validate` builds a world.

    Through the real path on purpose. The derivation runs, so a sensor gets its codec and its
    scaling, and `agent/inference.py`'s closure runs, so the legacy schema.org bridge takes
    effect — validating the fixture as a bare graph would measure neither and report violations
    no deployment would ever see.
    """
    world = tmp_path / "probe"
    shutil.copytree(WORLDS_ROOT / "sensing", world)
    for name, ttl in files.items():
        (world / f"{name}.ttl").write_text(ttl)

    st = Store()
    genesis.refresh_public(st, world)
    everyone = [genesis.agent_id_of(p) for p in sorted(world.glob(genesis.BELIEFS_GLOB))]
    for agent_id in everyone:
        genesis.birth(st, world, agent_id)
    return graph_from(st, *st.graphs_of(PUBLIC), st.catalogue,
                      *(picks_graph(a) for a in everyone))


_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")


def _by_severity(data: rdflib.Graph) -> dict[str, set[str]]:
    """Focus nodes that drew a result, split by severity.

    `conforms` returns one verdict and the report as text; this test needs to say WHICH nodes
    and how badly, because the whole point is that the residue is one specific node.
    """
    ontology, shapes = _shapes_and_vocabulary()
    data = data + ontology
    _, results, _ = shacl_validate(data, shacl_graph=shapes, ont_graph=ontology,
                                   inference="none", advanced=True)
    out: dict[str, set[str]] = {"Violation": set(), "Warning": set()}
    for result in results.subjects(rdflib.RDF.type, _SH.ValidationResult):
        severity = str(results.value(result, _SH.resultSeverity)).rsplit("#", 1)[-1]
        out.setdefault(severity, set()).add(str(results.value(result, _SH.focusNode)))
    return out


# --- the deliverable -------------------------------------------------------------------------

def test_a_standard_deployment_description_needs_no_editing_at_all(tmp_path):
    """`dht22-deployment.ttl` is dropped into a world verbatim and the world still conforms.

    Rooms, walls, boards and deployments, written by the SSN authors — and every shape this
    project owns is satisfied by it untouched. Nothing was relaxed to get here and no overlay
    supplies anything.

    It works because that file describes PLATFORMS and SYSTEMS and declares no `sosa:Sensor`:
    our sensor shapes ask for deployment facts, and there is no sensor to ask about. Which is
    the boundary this whole fixture set exists to draw — a description of where things are
    mounted is complete on its own; a description of a sensor is not, and should not be.
    """
    data = _world_with(tmp_path, vendor=(FIXTURES / "dht22-deployment.ttl").read_text())
    ok, report = conforms(data)
    assert ok, report


def test_their_device_description_deploys_once_our_half_is_supplied(tmp_path):
    """Their two DHT22 channels, plus `deploy-dht22.ttl`, satisfy every shape that targets them.

    Focused on their nodes, because that is the claim: a part described by a vendor becomes a
    sensor this society can drive, once the society says the things only it knows. Their file
    supplies the frequency floor, the accuracy and the operating range; ours supplies the name,
    the clock, the subject and the topic. Neither restates the other.
    """
    data = _world_with(tmp_path,
                       a_vendor=_repaired("dht22.ttl"),
                       b_deploy=(FIXTURES / "deploy-dht22.ttl").read_text())
    for channel in ("TemperatureSensor", "HumiditySensor"):
        iri = f"http://example.org/data/DHT22/4578#{channel}"
        ok, report = conforms(data, focus=iri)
        assert ok, f"{channel} did not conform:\n{report}"


# --- what is left, and why it is right to be left ---------------------------------------------

def test_the_only_thing_left_refusing_is_their_illustrative_reading(tmp_path):
    """One violating node in the whole world: `<observation/1087>`, and it SHOULD be refused.

    Their file bundles a device description with a sample observation, included to illustrate
    `ssn-system:qualityOfObservation`. It states a sensor and a procedure and nothing else — no
    result, no time, no feature of interest, no author.

    A reading here carries all of those, and the shape is right to refuse one that does not.
    Completing it in the overlay would have made this test green by **fabricating provenance for
    a reading nobody took**, which is precisely what `prov:wasGeneratedBy` is on a reading to
    prevent. So it stays refused, and this test names it so the residue can never grow quietly.

    The warnings are a different matter and are correct: deploying a second DHT22 beside the
    board's own puts two sensors on one property of one subject, which is the legitimate rig
    `sensing:DuplicateSensorShape` warns about rather than forbids.
    """
    data = _world_with(tmp_path,
                       a_vendor=_repaired("dht22.ttl"),
                       b_deploy=(FIXTURES / "deploy-dht22.ttl").read_text())
    found = _by_severity(data)

    assert found["Violation"] == {"http://example.org/data/observation/1087"}, (
        "the residue moved: something other than their illustrative observation is now refused"
    )
    assert any("DHT22" in n for n in found["Warning"]), (
        "the duplicate-rig warning stopped firing — two sensors on one property of one subject "
        "is exactly what it is for"
    )


def test_a_vendor_description_alone_is_missing_only_deployment_facts(tmp_path):
    """Without our overlay, their sensors fail for exactly the facts that are ours to supply.

    This is the characterisation: it says what a standard description does NOT contain, so that
    a future change adding a requirement has to come past this test and say so. Every one of
    these is a fact about *this* deployment that no vendor could know.

    The clock left this list with #96, and its absence is the assertion now: who holds the
    clock is the BOARD's fact, demanded of the connecting device by the speaking-device shape —
    a vendor's channel is not asked how it is driven, because that was never the part's to say.
    """
    data = _world_with(tmp_path, vendor=_repaired("dht22.ttl"))
    ok, report = conforms(data)
    assert not ok

    for expected in ("sensing:monitors", "sosa:observes"):
        assert expected in report, f"{expected} stopped being required of a deployed sensor"
    assert "who holds its clock" not in report and "how it is driven" not in report, (
        "the clock is being demanded of a vendor channel again — it is the device's fact, "
        "and #96 moved it there"
    )

    #  And NOT for anything about the datasheet. Their frequency is stated in the legacy
    #  schema.org namespace and in QUDT 1.1, and both are understood — see the bridge in
    #  `capabilities/sensing/ontology.ttl` and `sh:in` in its shapes.
    assert "frequency" not in report, (
        "a datasheet figure stopped being readable — the legacy schema.org bridge or the QUDT "
        "1.1 unit is no longer accepted, and a vendor's file now fails for a fact it DOES state"
    )


def test_the_legacy_schema_org_spelling_is_what_their_frequency_uses(tmp_path):
    """The bridge earns its place, and this is the evidence.

    schema.org's canonical namespace is `https:`; the W3C's example is written in `http:`. They
    are two IRIs, so without the bridge their `schema:value` and `schema:unitCode` are simply
    absent and the shape reports the node as missing figures it plainly states.

    Asserted against their file rather than a mock, so it stops being true the day they migrate.
    """
    src = (FIXTURES / "dht22.ttl").read_text()
    assert "@prefix schema: <http://schema.org/>" in src
    assert "https://schema.org/" not in src


# --- what the standard says a part DOES, and where we put it -----------------------------------
#
# The W3C's DHT22 states `ssn:implements` on both channels, pointing each at one shared
# `<DHT22#Procedure>`. That is the relation this project used only for sense modes until
# a-procedure-belongs-to-whatever-performs-it, and their file is the evidence that it is the
# ordinary way to say what a system does.
#
# We put the combined read on the WHOLE PART rather than on each channel, and the difference is
# not cosmetic — see the record. These tests pin both halves: theirs, so a change upstream is
# noticed, and ours, so a declaration nobody queries cannot quietly disappear.

_SSN = rdflib.Namespace("http://www.w3.org/ns/ssn/")
_SOSA = rdflib.Namespace("http://www.w3.org/ns/sosa/")
_DHT11 = rdflib.Namespace("http://example.org/orexis/dht11#")
_ONEWIRE = rdflib.Namespace("http://example.org/orexis/onewire#")
_MQTT = rdflib.Namespace("http://example.org/orexis/mqtt#")
_MC = rdflib.Namespace("http://example.org/orexis/microcontroller#")
_OWL = rdflib.Namespace("http://www.w3.org/2002/07/owl#")
_DCTERMS = rdflib.Namespace("http://purl.org/dc/terms/")


def test_their_channels_implement_a_procedure_and_ours_is_on_the_part(tmp_path):
    """One 40-bit frame is a fact about the DEVICE, so it is stated once and not twice.

    Their two channels each cite the same `<DHT22#Procedure>`, which says what a channel does.
    That leaves the thing this part's single message actually turns on — that neither value can
    be had without the other — expressible only by two nodes happening to name one procedure,
    and nothing makes them.

    So `dht11:CombinedRead` sits on `dht11:Dht11`. The channels keep their own sense mode, which
    is a different question with a different predicate and a cardinality of one.

    Our channels DO implement something now — each its own half of the frame — which does not
    weaken the claim: what may not move onto a channel is the COMBINED read, because putting it
    there says a channel could be read alone. That is what is asserted below.

    Read through the restriction rather than off a bare triple. `dht11:Dht11 ssn:implements …`
    was punning and entailed nothing about any device; see
    knowledge/decisions/a-part-is-described-once-and-fitted-many-times.md.
    """
    theirs = rdflib.Graph().parse(data=_repaired("dht22.ttl"), format="turtle")
    channels = set(theirs.subjects(_SSN.implements, None))
    assert len(channels) == 2, f"upstream moved its implements: {channels}"

    ours = _world_with(tmp_path)

    def implemented_by(cls):
        """What every instance of `cls` implements, per its owl:hasValue restrictions."""
        found = set()
        for restriction in ours.objects(cls, rdflib.RDFS.subClassOf):
            if (restriction, _OWL.onProperty, _SSN.implements) in ours:
                found |= set(ours.objects(restriction, _OWL.hasValue))
        return found

    assert implemented_by(_DHT11.Dht11) == {_DHT11.CombinedRead, _ONEWIRE.Transaction}
    assert implemented_by(_DHT11.TemperatureSensor) == {_DHT11.TemperatureRead}
    assert implemented_by(_DHT11.HumiditySensor) == {_DHT11.HumidityRead}

    for channel in (_DHT11.TemperatureSensor, _DHT11.HumiditySensor):
        assert _DHT11.CombinedRead not in implemented_by(channel), (
            "the combined read leaked onto a channel — it is what the PART does, and putting it "
            "on a channel says a channel could be read alone, which is the thing it denies")


def test_the_combined_read_has_the_two_halves_as_parts(tmp_path):
    """SOSA and SSN relate a Procedure to nothing. All 44 of their object properties were checked
    when this was written: the nearest is `ssn:hasSubSystem`, which is System to System.

    So the link is `dcterms:hasPart` — standard generic mereology, no domain, no range, defined as
    "included either physically or logically in the described resource". Deliberately NOT a step
    or an invocation: performing the combined read CONSTITUTES performing both halves, and neither
    can be performed alone, because there is one 40-bit frame and no way to ask for a piece of it.

    Asserted here rather than left to prose because the direction is the whole of it. Reversed, it
    would say the two reads each contain the conversation.
    """
    ours = _world_with(tmp_path)
    assert set(ours.objects(_DHT11.CombinedRead, _DCTERMS.hasPart)) == {
        _DHT11.TemperatureRead, _DHT11.HumidityRead}

    for half in (_DHT11.TemperatureRead, _DHT11.HumidityRead):
        assert not set(ours.objects(half, _DCTERMS.hasPart)), (
            f"<{half}> was given parts — it names one sensor's share of a single frame, "
            "and nothing is inside it")
        assert set(ours.subjects(_DCTERMS.hasPart, half)) == {_DHT11.CombinedRead}, (
            "a half belongs to exactly one conversation")


def test_every_declared_procedure_is_one(tmp_path):
    """A `sosa:Procedure` that was never typed is a dangling IRI no query will ever match.

    Cheap and worth having: the failure mode of a hand-written alignment triple is a typo that
    validates perfectly, because an unrecognised object is not an error in RDF.
    """
    ours = _world_with(tmp_path)
    declared = {_DHT11.CombinedRead, _DHT11.TemperatureRead, _DHT11.HumidityRead,
                _ONEWIRE.Transaction, _MQTT.Publishing}
    untyped = {p for p in declared if (p, rdflib.RDF.type, _SOSA.Procedure) not in ours}
    assert not untyped, f"declared but never typed a sosa:Procedure: {untyped}"


def test_a_board_is_both_a_platform_and_a_system(tmp_path):
    """It carries things AND it does things, and one class cannot say both.

    `ssn:implements` has `ssn:System` as its domain, so a board typed only `sosa:Platform` can
    be said to publish nowhere. SSN declares no disjointness, and the W3C's own boards are typed
    both — asserted here against their file so this stops being true if they change it.

    Only SOME of their Platforms are Systems, and that is the finding rather than a wrinkle in
    the test: a wall is a Platform and does nothing, a board is a Platform and does plenty. The
    two classes answer different questions, so which nodes carry both is a real distinction and
    a blanket assertion would have hidden it.
    """
    theirs = rdflib.Graph().parse(
        data=(FIXTURES / "dht22-deployment.ttl").read_text(), format="turtle")
    platforms = set(theirs.subjects(rdflib.RDF.type, _SOSA.Platform))
    assert platforms, "upstream has no Platform to compare against"
    both = {p for p in platforms if (p, rdflib.RDF.type, _SSN.System) in theirs}
    assert both and both < platforms, (
        f"upstream no longer shows the split this rests on — {len(both)} of {len(platforms)} "
        f"Platforms are Systems, and the point is that it is some rather than all or none")

    ours = _world_with(tmp_path)
    supers = set(ours.objects(_MC.Microcontroller, rdflib.RDFS.subClassOf))
    assert {_SOSA.Platform, _SSN.System} <= supers, f"a board is only {supers}"
