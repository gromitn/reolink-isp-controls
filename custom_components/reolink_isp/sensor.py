"""Sensor entities for Reolink ISP."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import ReolinkIspConfigEntry
from .const import OPTION_PROFILES, PROFILE_OPTIONS
from .entity import ReolinkIspEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ReolinkIspConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Reolink ISP sensor entities."""
    async_add_entities(
        [
            ReolinkIspLastAppliedProfileSensor(entry),
            ReolinkIspSavedProfileSlotsSensor(entry),
        ]
    )


class ReolinkIspLastAppliedProfileSensor(
    ReolinkIspEntity,
    SensorEntity,
    RestoreEntity,
):
    """Show the last applied profile name."""

    _attr_name = "Last Applied Profile"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:label-outline"

    def __init__(self, entry: ReolinkIspConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(entry, "last_applied_profile")
        self._restored_value: str | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the previous value on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in ("unknown", "unavailable"):
            self._restored_value = last_state.state

    @property
    def native_value(self) -> str | None:
        """Return the last applied profile."""
        return self.coordinator.last_applied_profile or self._restored_value


class ReolinkIspSavedProfileSlotsSensor(ReolinkIspEntity, SensorEntity):
    """Show which named profile slots currently have saved values."""

    _attr_name = "Saved Profile Slots"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:content-save-cog-outline"

    def __init__(self, entry: ReolinkIspConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(entry, "saved_profile_slots")

    @property
    def native_value(self) -> str:
        """Return a comma-separated list of saved profile slots."""
        profiles = self._entry.options.get(OPTION_PROFILES, {})
        if not isinstance(profiles, dict):
            return "none"

        saved = [
            profile
            for profile in PROFILE_OPTIONS
            if isinstance(profiles.get(profile), dict) and profiles.get(profile)
        ]
        return ", ".join(saved) if saved else "none"