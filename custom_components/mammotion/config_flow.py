"""Config flow for Mammotion Luba."""

import logging
from typing import Any

import voluptuous as vol
from bleak import BLEDevice
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothServiceInfo,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DEVICE_SUPPORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


def format_unique_id(address: str) -> str:
    """Format the unique ID for a mammotion lawnmower."""
    return address.replace(":", "").lower()


class MammotionConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mammotion."""

    VERSION = 1

    _address: str | None = None
    _discovered_devices: dict[str, BLEDevice] = {}

    def __init__(self) -> None:
        """Initialize the config flow."""

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfo
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        _LOGGER.debug("Discovered bluetooth device: %s", discovery_info)
        await self.async_set_unique_id(format_unique_id(discovery_info.address))
        self._abort_if_unique_id_configured()

        device = bluetooth.async_ble_device_from_address(
            self.hass, discovery_info.address
        )
        if device is None:
            return self.async_abort(reason="unknown")

        match_found = device.name.startswith(DEVICE_SUPPORT)
        if not match_found:
            return self.async_abort(reason="not_supported")

        self._address = device.address
        self._discovered_devices = {device.address: device}

        self.context["title_placeholders"] = {"name": device.name}

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        assert self._address
        device = self._discovered_devices[self._address]

        if user_input is not None:
            return self.async_create_entry(
                title=device.name,
                data={
                    CONF_ADDRESS: device.address,
                },
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders=self.context["title_placeholders"],
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()

            name = self._discovered_devices[address]
            self.context["title_placeholders"] = {
                "name": name,
            }

            return self.async_create_entry(
                title=name,
                data={
                    CONF_ADDRESS: address,
                },
            )

        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue

            self._discovered_devices[address] = discovery_info.name

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(self._discovered_devices),
                },
            ),
        )
