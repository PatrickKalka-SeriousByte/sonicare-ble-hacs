"""Data coordinator for receiving SonicareBLETB updates."""

import logging

from sonicare_bletb import SonicareBLETB, SonicareBLETBState

from homeassistant.core import HomeAssistant, callback
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

    async def stop(self):
        if this._sonicare_ble is not None:
            _LOGGER.warning('sonicare coordinator stopping')
            await this._sonicare_ble.stop()
            this._sonicare_ble = None
        else:
            _LOGGER.warning('sonicare coordinator not active, nothing to stop')

        # Unregister callbacks in order to prevent memory leak through circular references
        if self._unregister_async_handle_update is not None:
            self._unregister_async_handle_update()
            self._unregister_async_handle_update = None
        if self._unregister_async_handle_disconnect is not None:
            self._unregister_async_handle_disconnect()
            self._unregister_async_handle_disconnect = None
