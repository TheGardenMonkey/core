"""Component to embed TP-Link smart home devices."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .common import SmartDevices, async_discover_devices, get_static_devices
from .const import (
    CONF_DIMMER,
    CONF_DISCOVERY,
    CONF_LIGHT,
    CONF_RETRY_DELAY,
    CONF_RETRY_MAX_ATTEMPTS,
    CONF_STRIP,
    CONF_SWITCH,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_RETRY_DELAY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

TPLINK_HOST_SCHEMA = vol.Schema({vol.Required(CONF_HOST): cv.string})

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_LIGHT, default=[]): vol.All(
                    cv.ensure_list, [TPLINK_HOST_SCHEMA]
                ),
                vol.Optional(CONF_SWITCH, default=[]): vol.All(
                    cv.ensure_list, [TPLINK_HOST_SCHEMA]
                ),
                vol.Optional(CONF_STRIP, default=[]): vol.All(
                    cv.ensure_list, [TPLINK_HOST_SCHEMA]
                ),
                vol.Optional(CONF_DIMMER, default=[]): vol.All(
                    cv.ensure_list, [TPLINK_HOST_SCHEMA]
                ),
                vol.Optional(CONF_DISCOVERY, default=True): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the TP-Link component."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={
                CONF_DIMMER: conf[CONF_DIMMER],
                CONF_DISCOVERY: conf[CONF_DISCOVERY],
                CONF_LIGHT: conf[CONF_LIGHT],
                CONF_STRIP: conf[CONF_STRIP],
                CONF_SWITCH: conf[CONF_SWITCH],
                CONF_RETRY_DELAY: DEFAULT_RETRY_DELAY,
                CONF_RETRY_MAX_ATTEMPTS: DEFAULT_MAX_ATTEMPTS,
            },
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigType):
    """Set up TPLink from a config entry."""
    config_data = config_entry.data
    hass.data.setdefault(DOMAIN, {})
    lights = hass.data[DOMAIN][CONF_LIGHT] = []
    switches = hass.data[DOMAIN][CONF_SWITCH] = []

    # Add static devices
    static_devices = SmartDevices()
    if config_data is not None:
        static_devices = get_static_devices(config_data)

        lights.extend(static_devices.lights)
        switches.extend(static_devices.switches)

    # Add discovered devices
    if config_data is None or config_data[CONF_DISCOVERY]:
        discovered_devices = await async_discover_devices(hass, static_devices)

        lights.extend(discovered_devices.lights)
        switches.extend(discovered_devices.switches)

    forward_setup = hass.config_entries.async_forward_entry_setup
    if lights:
        _LOGGER.debug(
            "Got %s lights: %s", len(lights), ", ".join([d.host for d in lights])
        )
        hass.async_create_task(forward_setup(config_entry, "light"))
    if switches:
        _LOGGER.debug(
            "Got %s switches: %s", len(switches), ", ".join([d.host for d in switches])
        )
        hass.async_create_task(forward_setup(config_entry, "switch"))

    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    platforms = [platform for platform in PLATFORMS if hass.data[DOMAIN].get(platform)]
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data[DOMAIN].clear()

    return unload_ok
