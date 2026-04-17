"""The Reolink ISP integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ReolinkIspClient
from .const import (
    CONF_CHANNEL,
    CONF_PROTOCOL,
    CONF_VERIFY_SSL,
    DEFAULT_CHANNEL,
    DEFAULT_PROTOCOL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import ReolinkIspCoordinator
from .errors import CannotConnect, InvalidAuth

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ReolinkIspRuntimeData:
    """Runtime data kept on the config entry."""

    client: ReolinkIspClient
    coordinator: ReolinkIspCoordinator


type ReolinkIspConfigEntry = ConfigEntry[ReolinkIspRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: ReolinkIspConfigEntry) -> bool:
    """Set up Reolink ISP from a config entry."""
    session = async_get_clientsession(hass)
    client = ReolinkIspClient(
        session,
        protocol=entry.data.get(CONF_PROTOCOL, DEFAULT_PROTOCOL),
        host=entry.data[CONF_HOST],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
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
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ReolinkIspConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ReolinkIspConfigEntry) -> None:
    """Reload when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
