"""GPS Tracker Map - Custom Integration for Home Assistant."""
from __future__ import annotations

import logging
import os

from homeassistant.components.frontend import async_register_built_in_panel, async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PANEL_TITLE, PANEL_ICON, PANEL_URL_PATH

_LOGGER = logging.getLogger(__name__)

PANEL_DIR = os.path.join(os.path.dirname(__file__), "panel")
STATIC_URL = "/gps_tracker_map_static"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Serve static panel files
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, PANEL_DIR, cache_headers=False)]
    )

    # Register the sidebar panel (iframe)
    async_register_built_in_panel(
        hass,
        component_name="iframe",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL_PATH,
        config={
            "url": (
                f"{STATIC_URL}/index.html"
                f"?entity={entry.data['entity_id']}"
                f"&days={entry.data.get('days', 3)}"
            )
        },
        require_admin=False,
    )

    _LOGGER.info("GPS Tracker Map panel registered for entity: %s", entry.data["entity_id"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    try:
        async_remove_panel(hass, PANEL_URL_PATH)
    except Exception:
        pass
    return True
