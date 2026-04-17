"""Shared entity helpers for Reolink ISP."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ReolinkIspConfigEntry
from .const import DOMAIN
from .coordinator import ReolinkIspCoordinator


class ReolinkIspEntity(CoordinatorEntity[ReolinkIspCoordinator]):
    """Base entity for Reolink ISP entities."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: ReolinkIspConfigEntry, key: str) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._entry = entry
        self._key = key
        self._attr_unique_id = f"{self._device_id}-{key}"

    @property
    def _dev_info(self) -> dict[str, Any]:
        return self.coordinator.data.dev_info

    @property
    def _isp(self) -> dict[str, Any]:
        return self.coordinator.data.isp

    @property
    def _device_id(self) -> str:
        dev_info = self._dev_info
        for key in ("uid", "UID", "serial", "Serial", "serialNumber", "SerialNumber"):
            value = dev_info.get(key)
            if value:
                return str(value)
        model = str(dev_info.get("model", "reolink"))
        name = str(dev_info.get("name", self._entry.data.get("host", "camera")))
        return f"{model}_{name}".replace(" ", "_")

    @property
    def device_info(self) -> DeviceInfo:
        dev_info = self._dev_info
        model = str(dev_info.get("model", "Reolink"))
        name = str(dev_info.get("name", model)).strip() or model
        sw_version = (
            dev_info.get("firmVer")
            or dev_info.get("firmwareVer")
            or dev_info.get("firmware_version")
        )
        hw_version = dev_info.get("hardVer") or dev_info.get("hardwareVer")

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer="Reolink",
            model=model,
            name=name,
            sw_version=str(sw_version) if sw_version else None,
            hw_version=str(hw_version) if hw_version else None,
        )
