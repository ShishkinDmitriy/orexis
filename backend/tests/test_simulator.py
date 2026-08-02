"""Tests for the virtual-plant soil model (pure, no MQTT)."""

from agora.simulator import SimPlant, _clamp


def test_drying_reduces_moisture():
    p = SimPlant("fern", moisture=0.50, dry_rate=0.02, ml_to_fraction=0.0005)
    p.dry()
    assert p.moisture == 0.48


def test_watering_raises_moisture():
    p = SimPlant("fern", moisture=0.20, dry_rate=0.01, ml_to_fraction=0.0005)
    p.water(400)  # 400 ml * 0.0005 = +0.20
    assert p.moisture == 0.40


def test_moisture_clamps_to_unit_interval():
    dry = SimPlant("x", moisture=0.005, dry_rate=0.02, ml_to_fraction=0.0005)
    dry.dry()
    assert dry.moisture == 0.0  # can't go negative
    wet = SimPlant("y", moisture=0.9, dry_rate=0.0, ml_to_fraction=0.001)
    wet.water(1000)  # would be +1.0
    assert wet.moisture == 1.0  # can't exceed 1


def test_clamp():
    assert _clamp(-0.1) == 0.0
    assert _clamp(1.5) == 1.0
    assert _clamp(0.3) == 0.3
