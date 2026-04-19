"""Constants for the Reolink ISP integration."""

from __future__ import annotations

DOMAIN = "reolink_isp"
PLATFORMS: list[str] = ["select", "number"]

DEFAULT_PROTOCOL = "http"
DEFAULT_VERIFY_SSL = False
DEFAULT_CHANNEL = 0
DEFAULT_POLL_INTERVAL = 30

CONF_PROTOCOL = "protocol"
CONF_VERIFY_SSL = "verify_ssl"
CONF_CHANNEL = "channel"
CONF_POLL_INTERVAL = "poll_interval"

EXPOSURE_OPTIONS = ["Auto", "LowNoise", "Anti-Smearing", "Manual"]

PROFILE_DAY = "day"
PROFILE_GLOOMY = "gloomy"
PROFILE_NIGHT = "night"

PROFILE_OPTIONS = [PROFILE_DAY, PROFILE_GLOOMY, PROFILE_NIGHT]

OPTION_PROFILES = "profiles"
OPTION_LAST_APPLIED_PROFILE = "last_applied_profile"

SERVICE_SAVE_PROFILE = "save_profile"
SERVICE_APPLY_PROFILE = "apply_profile"
ATTR_PROFILE = "profile"

SERVICE_APPLY_SETTINGS = "apply_settings"
ATTR_EXPOSURE = "exposure"
ATTR_SHUTTER_MIN = "shutter_min"
ATTR_SHUTTER_MAX = "shutter_max"
ATTR_GAIN_MIN = "gain_min"
ATTR_GAIN_MAX = "gain_max"