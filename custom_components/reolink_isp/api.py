"""Async Reolink ISP API client."""

from __future__ import annotations

from copy import deepcopy
import json
import logging
from typing import Any
from urllib.parse import quote

import aiohttp

from .errors import CannotConnect, InvalidAuth, InvalidResponse, ReolinkIspError

_LOGGER = logging.getLogger(__name__)


class ReolinkIspClient:
    """Tiny async client for the Reolink CGI calls this integration needs."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        protocol: str,
        host: str,
        username: str,
        password: str,
        verify_ssl: bool,
        channel: int = 0,
    ) -> None:
        self._session = session
        self.protocol = protocol.strip().lower()
        self.host = host.strip()
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.channel = channel

        if self.protocol not in {"http", "https"}:
            raise ValueError("Protocol must be http or https")
        if not self.host:
            raise ValueError("Host is required")
        if not self.username:
            raise ValueError("Username is required")

    @property
    def base_url(self) -> str:
        """Return the inline-auth CGI base URL."""
        user = quote(self.username, safe="")
        password = quote(self.password, safe="")
        return f"{self.protocol}://{self.host}/cgi-bin/api.cgi?user={user}&password={password}"

    @property
    def request_ssl(self) -> bool | None:
        """Return the SSL verification mode for aiohttp."""
        if self.protocol == "https" and not self.verify_ssl:
            return False
        return None

    async def _post(self, commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Post one or more CGI commands and normalize the response shape."""
        try:
            async with self._session.post(
                self.base_url,
                json=commands,
                headers={"Content-Type": "application/json"},
                ssl=self.request_ssl,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                raw = await response.text()
                if response.status in {401, 403}:
                    raise InvalidAuth("Authentication failed")
                response.raise_for_status()
        except aiohttp.ClientResponseError as err:
            raise CannotConnect(f"HTTP {err.status}: {err.message}") from err
        except aiohttp.ClientConnectionError as err:
            raise CannotConnect(f"Connection failed: {err}") from err
        except TimeoutError as err:
            raise CannotConnect("Connection timed out") from err
        except aiohttp.ClientError as err:
            raise CannotConnect(str(err)) from err

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as err:
            snippet = raw[:500].strip()
            raise InvalidResponse(f"Invalid JSON response: {snippet}") from err

        if isinstance(parsed, dict):
            parsed = [parsed]

        if not isinstance(parsed, list) or not parsed or not isinstance(parsed[0], dict):
            snippet = raw[:500].strip()
            raise InvalidResponse(f"Unexpected response shape: {snippet}")

        return parsed

    @staticmethod
    def _raise_for_item_error(item: dict[str, Any], command: str) -> None:
        if item.get("code") == 0:
            return

        error = item.get("error", {}) or {}
        detail = str(error.get("detail", "")).lower()
        rsp_code = error.get("rspCode")
        message = f"{command} failed: rspCode={rsp_code} detail={error.get('detail')}"

        if any(word in detail for word in ("login", "auth", "password", "user")):
            raise InvalidAuth(message)

        raise ReolinkIspError(message)

    async def async_get_isp(self) -> dict[str, Any]:
        """Fetch the current ISP block."""
        resp = await self._post([
            {"cmd": "GetIsp", "action": 1, "param": {"channel": self.channel}}
        ])
        item = resp[0]
        self._raise_for_item_error(item, "GetIsp")

        value = item.get("value")
        if not isinstance(value, dict):
            raise InvalidResponse(f"GetIsp missing value block: {item}")

        isp = value.get("Isp")
        if not isinstance(isp, dict):
            raise InvalidResponse(f"GetIsp missing Isp block: {value}")

        return isp

    async def async_get_dev_info(self) -> dict[str, Any]:
        """Fetch device information."""
        resp = await self._post([{"cmd": "GetDevInfo", "action": 1}])
        item = resp[0]
        self._raise_for_item_error(item, "GetDevInfo")

        value = item.get("value")
        if not isinstance(value, dict):
            raise InvalidResponse(f"GetDevInfo missing value block: {item}")

        dev_info = value.get("DevInfo")
        if not isinstance(dev_info, dict):
            raise InvalidResponse(f"GetDevInfo missing DevInfo block: {value}")

        return dev_info

    async def async_set_isp(self, isp: dict[str, Any]) -> dict[str, Any]:
        """Write an ISP block back to the camera."""
        resp = await self._post([
            {"cmd": "SetIsp", "action": 0, "param": {"Isp": isp}}
        ])
        item = resp[0]
        self._raise_for_item_error(item, "SetIsp")
        return item

    async def async_test_connection(self) -> dict[str, Any]:
        """Validate auth and API availability during config flow."""
        dev_info = await self.async_get_dev_info()
        await self.async_get_isp()
        return dev_info

    async def async_fetch_snapshot(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Fetch ISP plus device info."""
        isp = await self.async_get_isp()
        dev_info = await self.async_get_dev_info()
        return isp, dev_info

    async def async_apply_full_isp(self, isp: dict[str, Any]) -> dict[str, Any]:
        """Apply an ISP payload using the proven desktop-app workarounds."""
        await self._apply_write_workarounds(isp)
        await self.async_set_isp(isp)
        return await self.async_get_isp()

    async def _apply_write_workarounds(self, isp: dict[str, Any]) -> None:
        """Apply the locked-value staging workaround before a final write."""
        exposure = str(isp.get("exposure", "")).strip()

        shutter = isp.get("shutter", {}) or {}
        shutter_min = shutter.get("min")
        shutter_max = shutter.get("max")

        gain = isp.get("gain", {}) or {}
        gain_min = gain.get("min")
        gain_max = gain.get("max")

        if (
            exposure in {"Manual", "Anti-Smearing"}
            and isinstance(shutter_min, int)
            and isinstance(shutter_max, int)
            and shutter_min == shutter_max
        ):
            stage = deepcopy(isp)
            stage.setdefault("shutter", {})
            if shutter_max <= 1:
                stage["shutter"]["min"] = 0
                stage["shutter"]["max"] = 1
            else:
                stage["shutter"]["min"] = 1
                stage["shutter"]["max"] = shutter_max
            _LOGGER.debug("Applying shutter staging workaround before final write")
            await self.async_set_isp(stage)

        if (
            exposure == "Manual"
            and isinstance(gain_min, int)
            and isinstance(gain_max, int)
            and gain_min == gain_max
        ):
            stage = deepcopy(isp)
            stage.setdefault("gain", {})
            if gain_max <= 1:
                stage["gain"]["min"] = 1
                stage["gain"]["max"] = 62
            else:
                stage["gain"]["min"] = 1
                stage["gain"]["max"] = gain_max
            _LOGGER.debug("Applying gain staging workaround before final write")
            await self.async_set_isp(stage)
