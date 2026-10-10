"""What two of the greenhouse's suites share: the world with a cold frame beside the bed.

`test_scaling.py` holds the soil's search flat under the aspect added, and `test_bench.py` times the
pass with the third scope in it. A fixture is the one door pytest opens between two test modules —
under `--import-mode=importlib` a sibling module is not importable — so the copy lives here, and
each suite asks for it by name.

THE ASPECT IS A SECOND SUBJECT'S AIR, a cold frame warmed by a heat lamp, and no longer the bed's
light (#944). The lamp was a second `climate:Heater` on the bed's `climate:Light`, a second filling of
the one heating action, while the heating took a reading and asked its side; it takes the subject now,
and speaks the air's state, cold or comfortable, which no light reading is judged into. A heater over
another subject's air keeps what the aspect was for: a third scope, by key, the heating's second
filling, admitted in that scope alone, and a sensor whose readings cross into no other imaginarium.
The grower's one desire is about every subject it acts for, so the frame needs no desire of its own.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

WORLD = Path(__file__).resolve().parents[1]

FRAME = '''
#  AN UNRELATED ASPECT: a cold frame beside the bed, its air read by a thermometer of its own and warmed
#  by a heat lamp — the heating's second filling, keyed by the frame.
:frame a sosa:FeatureOfInterest ; rdfs:label "the cold frame" ; ssn-system:hasOperatingRange :frame_operating .
:frame_operating a ssn-system:OperatingRange ;
    ssn-system:inCondition [ a ssn-system:Condition , schema:PropertyValue ; ssn:forProperty climate:AirTemperature ;
                             schema:minValue 10.0 ; schema:maxValue 20.0 ; schema:unitCode unit:DEG_C ] .
:frame_thermometer a sosa:Sensor ; orexis:localId "frame_thermometer" ; sosa:observes climate:AirTemperature ;
    sosa:isHostedBy :frame ;
    ssn-system:hasSystemCapability [ ssn-system:hasSystemProperty
        [ a ssn-system:Frequency , schema:PropertyValue ; schema:value 10 ; schema:unitCode unit:MIN ] ] .
:lamp a climate:Heater ; orexis:localId "lamp" ; climate:warms :frame ; climate:warmsProperty climate:AirTemperature ;
    climate:degreesPerHour 4.0 ; climate:maxHeatS 3600 .
'''
WIRED = '''
:frame_thermometer mqtt4ssn:observesTopic :frame_readings .
:frame_readings a mqtt4ssn:Topic .
:frame_filter a mqtt4ssn:TopicFilter ;
    mqtt4ssn:hasFilterPattern "sensors/frame_thermometer/reading" ; mqtt4ssn:matchesTopic :frame_readings .
:lamp mqtt4ssn:listensToTopic :lamp_commands .
:lamp_commands a mqtt4ssn:Topic .
:lamp_filter a mqtt4ssn:TopicFilter ;
    mqtt4ssn:hasFilterPattern "actuators/lamp/command" ; mqtt4ssn:matchesTopic :lamp_commands .
'''


@pytest.fixture
def framed_greenhouse(tmp_path):
    """The greenhouse with the cold frame added — a copy, since a world imports its domains by the tree's shape."""
    world = tmp_path / "world" / "greenhouse"
    shutil.copytree(WORLD, world, ignore=shutil.ignore_patterns("tests", "secrets", "__pycache__"))
    (tmp_path / "domains").symlink_to(WORLD.parents[1] / "domains")
    (world / "world.ttl").write_text((world / "world.ttl").read_text() + FRAME)
    society = world / "society.ttl"
    text = society.read_text()
    for old, new in (("orexis:actsFor :bed ;", "orexis:actsFor :bed , :frame ;"),
                     ("actuation:hasActuator :pump , :heater .", "actuation:hasActuator :pump , :heater , :lamp ."),
                     ("mqtt4ssn:hosts :moisture_probe , :thermometer , :pump , :heater ;",
                      "mqtt4ssn:hosts :moisture_probe , :thermometer , :pump , :heater , :frame_thermometer , :lamp ;")):
        assert old in text, old
        text = text.replace(old, new)
    society.write_text(text + WIRED)
    return world
