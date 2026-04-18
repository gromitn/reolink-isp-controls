"""Constants for the Reolink ISP integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "reolink_isp"
PLATFORMS: list[str] = ["select", "number"]

DEFAULT_PROTOCOL = "http"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_VERIFY_SSL = False
DEFAULT_CHANNEL = 0

CONF_PROTOCOL = "protocol"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_CHANNEL = "channel"

UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

EXPOSURE_OPTIONS = ["Auto", "LowNoise", "Anti-Smearing", "Manual"]

SERVICE_APPLY_SETTINGS = "apply_settings"
ATTR_EXPOSURE = "exposure"
ATTR_SHUTTER_MIN = "shutter_min"
ATTR_SHUTTER_MAX = "shutter_max"
ATTR_GAIN_MIN = "gain_min"
ATTR_GAIN_MAX = "gain_max"
