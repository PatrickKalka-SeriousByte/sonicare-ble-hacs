"""Data coordinator for receiving SonicareBLETB updates."""

import logging

from sonicare_bletb import SonicareBLETB, SonicareBLETBState

from homeassistant.core import HomeAssistant, callback
from homeassistant.components import bluetooth
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SonicareBLETBCoordinator(DataUpdateCoordinator[None]):
    """Data coordinator for receiving SonicareBLETB updates."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
        self.address = address
        self.connected = True
        self.state = None
        self._sonicare_ble = None
        self._unregister_async_handle_update = None
        self._unregister_async_handle_disconnect = None

    async def connect(self, ble_device):
        self.stop()
        _LOGGER.warning('sonicare coordinator: connecting to %s', ble_device)
        sonicare_ble = SonicareBLETB(ble_device)
        self._sonicare_ble = sonicare_ble
        self._unregister_async_handle_update = sonicare_ble.register_callback(self._async_handle_update)
        self._unregister_async_handle_disconnect = sonicare_ble.register_disconnected_callback(self._async_handle_disconnect)
        await sonicare_ble.initialise()


    @callback
    def _async_handle_update(self, state: SonicareBLETBState) -> None:
        """Just trigger the callbacks."""
        _LOGGER.warning("_async_handle_update")
        self.state = state
        self.connected = True
        self.async_set_updated_data(None)

    @callback
    def _async_handle_disconnect(self) -> None:
        """Trigger the callbacks for disconnected."""
        _LOGGER.warning("_async_handle_disconnect")
        self.connected = False
        self.async_update_listeners()
        if self._sonicare_ble is not None:
            # We cannot rely on `await self._sonicare_ble.stop()`, because it is called asynchronously.
            # However, the reconnect is performed just after all disconnect callbacks are processed.
            # I know that relying on internal property is wrong, but I see no better way to do it.
            self._sonicare_ble._expected_disconnect = True
        self.hass.async_create_task(self._retry())

    async def _retry(self):
        # We want to stop the library from polling, which might spam and consume Bluetooth connection slots
        await self.stop()
        # Let's not ignore advertisments
        # seems to cause BLE proxy crashes: bluetooth.async_rediscover_address(self.hass, self.address)

    async def stop(self):
        # Unregister callbacks in order to prevent memory leak through circular references
        if self._unregister_async_handle_update is not None:
            self._unregister_async_handle_update()
            self._unregister_async_handle_update = None
        if self._unregister_async_handle_disconnect is not None:
            self._unregister_async_handle_disconnect()
            self._unregister_async_handle_disconnect = None

        if self._sonicare_ble is not None:
            _LOGGER.warning('sonicare coordinator stopping')
            await self._sonicare_ble.stop()
            _LOGGER.warning('sonicare coordinator stopped')
            self._sonicare_ble = None
        else:
            _LOGGER.warning('sonicare coordinator not active, nothing to stop')
