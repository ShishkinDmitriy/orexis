"""The virtual-plant soil model, and the cadence clamp a board applies (pure, no MQTT)."""

from agora.simulator import SimPlant, _clamp


def plant(moisture, dry_rate=0.01, ml_to_fraction=0.0005, min_sleep_s=10, max_sleep_s=900):
    return SimPlant("fern", moisture, dry_rate, ml_to_fraction, min_sleep_s, max_sleep_s)


def test_drying_reduces_moisture():
    p = plant(0.50, dry_rate=0.02)
    p.dry()
    assert p.moisture == 0.48


def test_watering_raises_moisture():
    p = plant(0.20)
    p.water(400)  # 400 ml * 0.0005 = +0.20
    assert p.moisture == 0.40


def test_moisture_clamps_to_unit_interval():
    dry = plant(0.005, dry_rate=0.02)
    dry.dry()
    assert dry.moisture == 0.0  # can't go negative
    wet = plant(0.9, dry_rate=0.0, ml_to_fraction=0.001)
    wet.water(1000)  # would be +1.0
    assert wet.moisture == 1.0  # can't exceed 1


def test_clamp():
    assert _clamp(-0.1) == 0.0
    assert _clamp(1.5) == 1.0
    assert _clamp(0.3) == 0.3


# --- the board clamps the cadence it is given, exactly as the firmware does ---

def test_board_clamps_a_reckless_cadence():
    p = plant(0.5)
    p.set_cadence(99999, now=0.0)   # an agent that wants to nap forever
    assert p.sleep_s == 900         # the constitutional ceiling wins
    p.set_cadence(1, now=0.0)       # or to hammer the sensor flat
    assert p.sleep_s == 10


def test_a_shorter_cadence_takes_effect_immediately():
    p = plant(0.5)
    p.set_cadence(600, now=0.0)
    p.next_sense_at = 600.0
    p.set_cadence(30, now=0.0)      # the agent grew worried
    assert p.next_sense_at == 30.0  # it does not wait out the old sleep


def test_sensing_is_not_due_before_its_time():
    p = plant(0.5)
    p.set_cadence(60, now=0.0)
    p.next_sense_at = 60.0
    assert not p.due_to_sense(59.0)
    assert p.due_to_sense(60.0)
