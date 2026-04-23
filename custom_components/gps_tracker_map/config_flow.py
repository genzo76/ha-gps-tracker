"""Config flow for GPS Tracker Map."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import DOMAIN, CONF_ENTITY_ID, CONF_DAYS, DEFAULT_DAYS


class GpsTrackerMapFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            entity_id = user_input[CONF_ENTITY_ID]
            state = self.hass.states.get(entity_id)
            if state is None:
                errors[CONF_ENTITY_ID] = "entity_not_found"
            else:
                await self.async_set_unique_id(entity_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"GPS Tracker — {entity_id}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="device_tracker")
                    ),
                    vol.Optional(CONF_DAYS, default=DEFAULT_DAYS): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=30)
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "entity_example": "device_tracker.il_mio_telefono"
            },
        )
