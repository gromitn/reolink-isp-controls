"""Coordinator for Reolink ISP data."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
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
        self._write_lock = asyncio.Lock()
        self._write_in_progress = False

    @property
    def write_in_progress(self) -> bool:
        """Return whether a write/verify cycle is currently running."""
        return self._write_in_progress

    async def async_run_serialized_write(
        self,
        write_operation: Callable[[], Awaitable[None]],
    ) -> None:
        """Run a camera write in a serialized block, then refresh with retry."""
        async with self._write_lock:
            self._write_in_progress = True
            try:
                await write_operation()
                await self._async_refresh_after_write()
            finally:
                self._write_in_progress = False

    async def _async_refresh_after_write(self) -> None:
        """Refresh after a write, allowing the camera a brief moment to settle."""
        last_err: Exception | None = None

        for delay in (0.75, 1.5):
            try:
                await asyncio.sleep(delay)
                await self.async_refresh()
                return
            except Exception as err:  # noqa: BLE001
                last_err = err
                _LOGGER.warning("Post-write refresh failed, retrying: %s", err)

        if last_err is not None:
            raise last_err

    async def _async_update_data(self) -> ReolinkIspSnapshot:
        if self._write_in_progress and self.data is not None:
            _LOGGER.debug("Skipping poll during active write/verify cycle")
            return self.data

        try:
            isp, dev_info = await self.client.async_fetch_snapshot()
        except ReolinkIspError as err:
            raise UpdateFailed(str(err)) from err
        return ReolinkIspSnapshot(isp=isp, dev_info=dev_info)