"""Coordinator for Reolink ISP data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ReolinkIspClient
from .const import CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, DOMAIN
from .errors import ReolinkIspError

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ReolinkIspSnapshot:
    """Current snapshot of the device state."""

    isp: dict[str, Any]
    dev_info: dict[str, Any]


class ReolinkIspCoordinator(DataUpdateCoordinator[ReolinkIspSnapshot]):
    """Poll the camera for current ISP state."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: ReolinkIspClient,
    ) -> None:
        poll_interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            config_entry=entry,
            update_interval=timedelta(seconds=poll_interval),
            always_update=False,
        )
        self.client = client
        self._entry = entry

    async def _async_update_data(self) -> ReolinkIspSnapshot:
        try:
            isp, dev_info = await self.client.async_fetch_snapshot()
        except ReolinkIspError as err:
            raise UpdateFailed(str(err)) from err
        return ReolinkIspSnapshot(isp=isp, dev_info=dev_info)