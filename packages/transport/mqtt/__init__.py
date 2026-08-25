"""The manifest: what this transport contributes to a build."""

from .driver import MqttDriver
from .module import MqttModule

PROVIDES = (MqttDriver, MqttModule)
