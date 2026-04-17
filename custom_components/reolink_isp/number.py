"""Number entities for Reolink ISP."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ReolinkIspConfigEntry
from .entity import ReolinkIspEntity
from .errors import ReolinkIspError

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class ReolinkIspNumberDescription(NumberEntityDescription):
    """Description for a Reolink ISP number entity."""

    block: str
    item: str
    allowed_exposures: tuple[str, ...]


DESCRIPTIONS = (
    ReolinkIspNumberDescription(
        key="gain_min",
        name="Gain Min",
        block="gain",
        item="min",
        native_min_value=1,
        native_max_value=62,
        mode=NumberMode.BOX,
        allowed_exposures=("Manual",),
    ),
    ReolinkIspNumberDescription(
        key="gain_max",
        name="Gain Max",
        block="gain",
        item="max",
        native_min_value=1,
        native_max_value=62,
        mode=NumberMode.BOX,
        allowed_exposures=("Manual",),
    ),
    ReolinkIspNumberDescription(
        key="shutter_min",
        name="Shutter Min",
        block="shutter",
        item="min",
        native_min_value=0,
        native_max_value=125,
        mode=NumberMode.BOX,
        allowed_exposures=("Manual", "Anti-Smearing"),
    ),
    ReolinkIspNumberDescription(
        key="shutter_max",
        name="Shutter Max",
        block="shutter",
        item="max",
        native_min_value=0,
        native_max_value=125,
        mode=NumberMode.BOX,
        allowed_exposures=("Manual", "Anti-Smearing"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ReolinkIspConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Reolink ISP number entities."""
    async_add_entities(ReolinkIspNumber(entry, description) for description in DESCRIPTIONS)


class ReolinkIspNumber(ReolinkIspEntity, NumberEntity):
    """Numeric ISP setting entity."""

    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        entry: ReolinkIspConfigEntry,
        description: ReolinkIspNumberDescription,
    ) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_native_min_value = description.native_min_value
        self._attr_native_max_value = description.native_max_value
        self._attr_mode = description.mode

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self._isp.get("exposure") in self.entity_description.allowed_exposures

    @property
    def native_value(self) -> float | None:
        block = self._isp.get(self.entity_description.block, {}) or {}
        value = block.get(self.entity_description.item)
        if value is None:
            return None
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        exposure = str(self._isp.get("exposure", ""))
        if exposure not in self.entity_description.allowed_exposures:
            allowed = ", ".join(self.entity_description.allowed_exposures)
            raise HomeAssistantError(
                f"{self.entity_description.name} is only available when Exposure is {allowed}"
            )

        isp = deepcopy(self._isp)
        isp.setdefault(self.entity_description.block, {})
        isp[self.entity_description.block][self.entity_description.item] = int(value)

        if self.entity_description.block == "gain":
            _ensure_min_max_order(isp, "gain")
        if self.entity_description.block == "shutter":
            _ensure_min_max_order(isp, "shutter")

        try:
            await self.coordinator.client.async_apply_full_isp(isp)
        except ReolinkIspError as err:
            raise HomeAssistantError(str(err)) from err

        await self.coordinator.async_request_refresh()


def _ensure_min_max_order(isp: dict, block_name: str) -> None:
    """Keep min/max pairs sane before writing."""
    block = isp.get(block_name, {}) or {}
    min_value = block.get("min")
    max_value = block.get("max")
    if isinstance(min_value, int) and isinstance(max_value, int) and min_value > max_value:
        block["min"], block["max"] = max_value, min_value
