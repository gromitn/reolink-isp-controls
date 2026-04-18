"""Config flow for Reolink ISP."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .api import ReolinkIspClient
from .const import (
    CONF_CHANNEL,
    CONF_POLL_INTERVAL,
    CONF_PROTOCOL,
    CONF_VERIFY_SSL,
    DEFAULT_CHANNEL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PROTOCOL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from .errors import CannotConnect, InvalidAuth, ReolinkIspError


def _device_unique_id(dev_info: dict[str, Any], host: str) -> str:
    """Build the most stable unique ID we can from DevInfo."""
    for key in ("uid", "UID", "serial", "Serial", "serialNumber", "SerialNumber"):
        value = dev_info.get(key)
        if value:
            return str(value)
    model = str(dev_info.get("model", "reolink"))
    name = str(dev_info.get("name", "camera"))
    return f"{model}_{name}_{host}".replace(" ", "_")


def _entry_title(dev_info: dict[str, Any], host: str) -> str:
    """Return a friendly title for the entry."""
    model = str(dev_info.get("model", "Reolink")).strip()
    name = str(dev_info.get("name", "")).strip()
    if model and name:
        return f"{model} ({name})"
    if model:
        return model
    return host


class ReolinkIspConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Reolink ISP."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = ReolinkIspClient(
                session,
                protocol=user_input[CONF_PROTOCOL],
                host=user_input[CONF_HOST],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                verify_ssl=user_input[CONF_VERIFY_SSL],
                channel=user_input[CONF_CHANNEL],
            )
            try:
                dev_info = await client.async_test_connection()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except ReolinkIspError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                unique_id = _device_unique_id(dev_info, user_input[CONF_HOST])
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=_entry_title(dev_info, user_input[CONF_HOST]),
                    data=user_input,
                    options={CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): vol.In(["http", "https"]),
                    vol.Required(CONF_USERNAME, default="admin"): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
                    vol.Optional(CONF_CHANNEL, default=DEFAULT_CHANNEL): vol.All(
                        vol.Coerce(int), vol.Range(min=0)
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ReolinkIspOptionsFlow:
        """Return the options flow."""
        return ReolinkIspOptionsFlow(config_entry)


class ReolinkIspOptionsFlow(config_entries.OptionsFlow):
    """Handle Reolink ISP options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_poll = self._config_entry.options.get(
            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=current_poll,
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                }
            ),
        )