"""Provides the mammotion DataUpdateCoordinator."""

from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from typing import TYPE_CHECKING

from bleak_retry_connector import BleakError, BleakNotFoundError
from pyluba.mammotion.devices import MammotionBaseBLEDevice
from pyluba.mammotion.devices.luba import CharacteristicMissingError
from pyluba.proto.luba_msg import LubaMsg

from homeassistant.components import bluetooth
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from . import MammotionConfigEntry

SCAN_INTERVAL = timedelta(minutes=1)
UPDATE_EXCEPTIONS = (
    BleakNotFoundError,
    CharacteristicMissingError,
    BleakError,
    TimeoutError,
)


class MammotionDataUpdateCoordinator(DataUpdateCoordinator[LubaMsg]):
    """Class to manage fetching mammotion data."""

    address: str
    config_entry: MammotionConfigEntry
    device_name: str
    device: MammotionBaseBLEDevice


    def __init__(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Initialize global mammotion data updater."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.update_failures = 0

    async def async_setup(self) -> None:
        """Set coordinator up."""

        address = self.config_entry.data[CONF_ADDRESS]
        ble_device = bluetooth.async_ble_device_from_address(self.hass, address)
        if not ble_device:
            raise ConfigEntryNotReady(
                f"Could not find Mammotion lawn mower with address {address}"
            )
        self.device = MammotionBaseBLEDevice(ble_device)
        self.device_name = ble_device.name or "Unknown"
        self.address = ble_device.address
        self.device.update_device(ble_device)
        try:
            await self.device.start_sync(0)
        except UPDATE_EXCEPTIONS as exc:
            raise ConfigEntryNotReady("Unable to setup Mammotion device") from exc

    async def _async_update_data(self) -> LubaMsg:
        """Get data from the device."""
        if ble_device := bluetooth.async_ble_device_from_address(
            self.hass, self.address
        ):
            self.device.update_device(ble_device)
            try:
                await self.device.command("get_report_cfg")
            except UPDATE_EXCEPTIONS as exc:
                self.update_failures += 1
                raise UpdateFailed(f"Updating Mammotion device failed: {exc}") from exc

            LOGGER.debug("Updated Mammotion device %s", self.device_name)
            LOGGER.debug("================= Debug Log =================")
            LOGGER.debug("Mammotion device data: %s", asdict(self.device.luba_msg))
            LOGGER.debug("==================================")

            self.update_failures = 0
            return self.device.luba_msg

        self.update_failures += 1
        raise UpdateFailed("Could not find device")
