"""Select entities for Reolink ISP."""

from __future__ import annotations

from copy import deepcopy

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ReolinkIspConfigEntry
from .const import DOMAIN, EXPOSURE_OPTIONS
from .entity import ReolinkIspEntity
from .errors import ReolinkIspError

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ReolinkIspConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Reolink ISP select entities."""
    async_add_entities([ReolinkExposureSelect(entry)])


class ReolinkExposureSelect(ReolinkIspEntity, SelectEntity):
    """Exposure mode selector."""

    _attr_name = "Exposure"
    _attr_options = EXPOSURE_OPTIONS

    def __init__(self, entry: ReolinkIspConfigEntry) -> None:
        super().__init__(entry, "exposure")

    @property
    def current_option(self) -> str | None:
        return str(self._isp.get("exposure", "")) or None

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise HomeAssistantError(f"Unsupported exposure mode: {option}")

        isp = deepcopy(self._isp)
        isp["exposure"] = option

        try:
            await self.coordinator.client.async_apply_full_isp(isp)
        except ReolinkIspError as err:
            raise HomeAssistantError(str(err)) from err

        await self.coordinator.async_request_refresh()
