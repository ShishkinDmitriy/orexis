"""The manifest: what this transport contributes to a build."""

from .driver import MqttDriver

PROVIDES = (MqttDriver,)
