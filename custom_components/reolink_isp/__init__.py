"""The Reolink ISP integration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ReolinkIspClient
from .const import (
    ATTR_EXPOSURE,
    ATTR_GAIN_MAX,
    ATTR_GAIN_MIN,
    ATTR_SHUTTER_MAX,
    ATTR_SHUTTER_MIN,
    CONF_CHANNEL,
    CONF_PROTOCOL,
    CONF_VERIFY_SSL,
    DEFAULT_CHANNEL,
    DEFAULT_PROTOCOL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    EXPOSURE_OPTIONS,
    PLATFORMS,
    SERVICE_APPLY_SETTINGS,
    ATTR_PROFILE,
    OPTION_LAST_APPLIED_PROFILE,
    OPTION_PROFILES,
    PROFILE_OPTIONS,
    SERVICE_APPLY_PROFILE,
    SERVICE_SAVE_PROFILE,
)
from .coordinator import ReolinkIspCoordinator
from .errors import CannotConnect, InvalidAuth, ReolinkIspError

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): vol.Any(cv.string, [cv.string]),
        vol.Optional(ATTR_EXPOSURE): vol.In(EXPOSURE_OPTIONS),
        vol.Optional(ATTR_SHUTTER_MIN): vol.Coerce(int),
        vol.Optional(ATTR_SHUTTER_MAX): vol.Coerce(int),
        vol.Optional(ATTR_GAIN_MIN): vol.Coerce(int),
        vol.Optional(ATTR_GAIN_MAX): vol.Coerce(int),
    }
)

PROFILE_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): vol.Any(cv.string, [cv.string]),
        vol.Required(ATTR_PROFILE): vol.In(PROFILE_OPTIONS),
    }
)

@dataclass(slots=True)
class ReolinkIspRuntimeData:
    """Runtime data kept on the config entry."""

    client: ReolinkIspClient
    coordinator: ReolinkIspCoordinator


type ReolinkIspConfigEntry = ConfigEntry[ReolinkIspRuntimeData]


async def async_setup(hass: HomeAssistant, _config: dict[str, Any]) -> bool:
    """Set up the Reolink ISP integration."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault("entries", {})

    if not hass.services.has_service(DOMAIN, SERVICE_APPLY_SETTINGS):

        async def async_handle_apply_settings(call: ServiceCall) -> None:
            await _async_handle_apply_settings(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_APPLY_SETTINGS,
            async_handle_apply_settings,
            schema=SERVICE_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SAVE_PROFILE):

        async def async_handle_save_profile(call: ServiceCall) -> None:
            await _async_handle_save_profile(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SAVE_PROFILE,
            async_handle_save_profile,
            schema=PROFILE_SERVICE_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_APPLY_PROFILE):

        async def async_handle_apply_profile(call: ServiceCall) -> None:
            await _async_handle_apply_profile(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_APPLY_PROFILE,
            async_handle_apply_profile,
            schema=PROFILE_SERVICE_SCHEMA,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ReolinkIspConfigEntry) -> bool:
    """Set up Reolink ISP from a config entry."""
    session = async_get_clientsession(hass)
    client = ReolinkIspClient(
        session,
        protocol=entry.data.get(CONF_PROTOCOL, DEFAULT_PROTOCOL),
        host=entry.data[CONF_HOST],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        verify_ssl=entry.options.get(
            CONF_VERIFY_SSL,
            entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        ),
        channel=entry.data.get(CONF_CHANNEL, DEFAULT_CHANNEL),
    )

    coordinator = ReolinkIspCoordinator(hass, entry, client)

    try:
        await coordinator.async_config_entry_first_refresh()
    except InvalidAuth as err:
        raise ConfigEntryAuthFailed from err
    except CannotConnect as err:
        raise ConfigEntryNotReady from err

    entry.runtime_data = ReolinkIspRuntimeData(client=client, coordinator=coordinator)
    hass.data[DOMAIN]["entries"][entry.entry_id] = entry.runtime_data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ReolinkIspConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).get("entries", {}).pop(entry.entry_id, None)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ReolinkIspConfigEntry) -> None:
    """Reload when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)

def _profile_payload_from_isp(isp: dict[str, Any]) -> dict[str, Any]:
    """Extract the profile-relevant ISP values we own."""
    exposure = str(isp.get("exposure", "")).strip()

    payload: dict[str, Any] = {
        ATTR_EXPOSURE: exposure,
    }

    if exposure in {"Manual", "Anti-Smearing"}:
        shutter = isp.get("shutter", {}) or {}
        if "min" in shutter:
            payload[ATTR_SHUTTER_MIN] = int(shutter["min"])
        if "max" in shutter:
            payload[ATTR_SHUTTER_MAX] = int(shutter["max"])

    if exposure == "Manual":
        gain = isp.get("gain", {}) or {}
        if "min" in gain:
            payload[ATTR_GAIN_MIN] = int(gain["min"])
        if "max" in gain:
            payload[ATTR_GAIN_MAX] = int(gain["max"])

    return payload


def _get_saved_profiles(entry: ConfigEntry) -> dict[str, dict[str, Any]]:
    """Return saved profiles from entry options."""
    profiles = entry.options.get(OPTION_PROFILES, {})
    if isinstance(profiles, dict):
        return deepcopy(profiles)
    return {}

async def _async_handle_apply_settings(hass: HomeAssistant, call: ServiceCall) -> None:
    """Apply multiple ISP settings in one atomic camera write."""
    device_ids = call.data[ATTR_DEVICE_ID]
    if isinstance(device_ids, str):
        device_ids = [device_ids]

    if len(device_ids) != 1:
        raise HomeAssistantError("Select exactly one Reolink ISP device")

    runtime = _runtime_from_device_id(hass, device_ids[0])
    coordinator = runtime.coordinator

    isp = deepcopy(coordinator.data.isp)
    final_exposure = str(call.data.get(ATTR_EXPOSURE, isp.get("exposure", ""))).strip()

    if ATTR_EXPOSURE in call.data:
        isp["exposure"] = final_exposure

    if ATTR_SHUTTER_MIN in call.data or ATTR_SHUTTER_MAX in call.data:
        if final_exposure not in {"Manual", "Anti-Smearing"}:
            raise HomeAssistantError(
                "Shutter settings can only be applied when Exposure is Manual or Anti-Smearing"
            )
        isp.setdefault("shutter", {})
        if ATTR_SHUTTER_MIN in call.data:
            isp["shutter"]["min"] = call.data[ATTR_SHUTTER_MIN]
        if ATTR_SHUTTER_MAX in call.data:
            isp["shutter"]["max"] = call.data[ATTR_SHUTTER_MAX]
        _ensure_min_max_order(isp, "shutter")

    if ATTR_GAIN_MIN in call.data or ATTR_GAIN_MAX in call.data:
        if final_exposure != "Manual":
            raise HomeAssistantError(
                "Gain settings can only be applied when Exposure is Manual"
            )
        isp.setdefault("gain", {})
        if ATTR_GAIN_MIN in call.data:
            isp["gain"]["min"] = call.data[ATTR_GAIN_MIN]
        if ATTR_GAIN_MAX in call.data:
            isp["gain"]["max"] = call.data[ATTR_GAIN_MAX]
        _ensure_min_max_order(isp, "gain")

    if not any(
        key in call.data
        for key in (
            ATTR_EXPOSURE,
            ATTR_SHUTTER_MIN,
            ATTR_SHUTTER_MAX,
            ATTR_GAIN_MIN,
            ATTR_GAIN_MAX,
        )
    ):
        raise HomeAssistantError("No ISP settings were provided")

    try:
        await runtime.client.async_apply_full_isp(isp)
    except ReolinkIspError as err:
        raise HomeAssistantError(str(err)) from err

    await coordinator.async_request_refresh()

async def _async_handle_save_profile(hass: HomeAssistant, call: ServiceCall) -> None:
    """Save the current camera settings into a named profile slot."""
    device_ids = call.data[ATTR_DEVICE_ID]
    if isinstance(device_ids, str):
        device_ids = [device_ids]

    if len(device_ids) != 1:
        raise HomeAssistantError("Select exactly one Reolink ISP device")

    profile = str(call.data[ATTR_PROFILE]).strip().lower()

    runtime = _runtime_from_device_id(hass, device_ids[0])
    entry = _entry_from_device_id(hass, device_ids[0])

    profiles = _get_saved_profiles(entry)
    profiles[profile] = _profile_payload_from_isp(runtime.coordinator.data.isp)

    new_options = dict(entry.options)
    new_options[OPTION_PROFILES] = profiles

    hass.config_entries.async_update_entry(entry, options=new_options)

async def _async_handle_apply_profile(hass: HomeAssistant, call: ServiceCall) -> None:
    """Apply a previously saved named profile."""
    device_ids = call.data[ATTR_DEVICE_ID]
    if isinstance(device_ids, str):
        device_ids = [device_ids]

    if len(device_ids) != 1:
        raise HomeAssistantError("Select exactly one Reolink ISP device")

    profile = str(call.data[ATTR_PROFILE]).strip().lower()

    runtime = _runtime_from_device_id(hass, device_ids[0])
    entry = _entry_from_device_id(hass, device_ids[0])

    profiles = _get_saved_profiles(entry)
    payload = profiles.get(profile)

    if not isinstance(payload, dict) or not payload:
        raise HomeAssistantError(f"Profile '{profile}' has not been saved yet")

    coordinator = runtime.coordinator
    isp = deepcopy(coordinator.data.isp)
    final_exposure = str(payload.get(ATTR_EXPOSURE, isp.get("exposure", ""))).strip()

    if ATTR_EXPOSURE in payload:
        isp["exposure"] = final_exposure

    if ATTR_SHUTTER_MIN in payload or ATTR_SHUTTER_MAX in payload:
        if final_exposure not in {"Manual", "Anti-Smearing"}:
            raise HomeAssistantError(
                "Shutter settings can only be applied when Exposure is Manual or Anti-Smearing"
            )
        isp.setdefault("shutter", {})
        if ATTR_SHUTTER_MIN in payload:
            isp["shutter"]["min"] = payload[ATTR_SHUTTER_MIN]
        if ATTR_SHUTTER_MAX in payload:
            isp["shutter"]["max"] = payload[ATTR_SHUTTER_MAX]
        _ensure_min_max_order(isp, "shutter")

    if ATTR_GAIN_MIN in payload or ATTR_GAIN_MAX in payload:
        if final_exposure != "Manual":
            raise HomeAssistantError(
                "Gain settings can only be applied when Exposure is Manual"
            )
        isp.setdefault("gain", {})
        if ATTR_GAIN_MIN in payload:
            isp["gain"]["min"] = payload[ATTR_GAIN_MIN]
        if ATTR_GAIN_MAX in payload:
            isp["gain"]["max"] = payload[ATTR_GAIN_MAX]
        _ensure_min_max_order(isp, "gain")

    try:
        await runtime.client.async_apply_full_isp(isp)
    except ReolinkIspError as err:
        raise HomeAssistantError(str(err)) from err

    await coordinator.async_request_refresh()

def _entry_from_device_id(hass: HomeAssistant, device_id: str) -> ConfigEntry:
    """Resolve a Reolink ISP config entry from a device ID."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    if device is None:
        raise HomeAssistantError("Device not found")

    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and entry.domain == DOMAIN:
            return entry

    raise HomeAssistantError("Selected device is not managed by Reolink ISP Controls")

def _runtime_from_device_id(hass: HomeAssistant, device_id: str) -> ReolinkIspRuntimeData:
    """Resolve a Reolink ISP runtime instance from a device ID."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    if device is None:
        raise HomeAssistantError("Device not found")

    entries: dict[str, ReolinkIspRuntimeData] = hass.data.get(DOMAIN, {}).get("entries", {})

    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and entry.domain == DOMAIN and entry_id in entries:
            return entries[entry_id]

    raise HomeAssistantError("Selected device is not managed by Reolink ISP Controls")


def _ensure_min_max_order(isp: dict[str, Any], block_name: str) -> None:
    """Keep min/max pairs sane before writing."""
    block = isp.get(block_name, {}) or {}
    min_value = block.get("min")
    max_value = block.get("max")
    if isinstance(min_value, int) and isinstance(max_value, int) and min_value > max_value:
        block["min"], block["max"] = max_value, min_value
