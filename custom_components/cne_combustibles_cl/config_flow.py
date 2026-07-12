"""Config flow for Chile Combustibles."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CNEApiClient
from .const import (
    CONF_EMAIL,
    CONF_INCLUDE_ASSISTED,
    CONF_INCLUDE_SELF_SERVICE,
    CONF_RADIUS_KM,
    CONF_TANK_CAPACITY_L,
    CONF_TOP_STATIONS,
    CONF_UPDATE_INTERVAL_HOURS,
    DEFAULT_INCLUDE_ASSISTED,
    DEFAULT_INCLUDE_SELF_SERVICE,
    DEFAULT_RADIUS_KM,
    DEFAULT_TANK_CAPACITY_L,
    DEFAULT_TOP_STATIONS,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
    MAX_RADIUS_KM,
    MAX_TANK_CAPACITY_L,
    MAX_TOP_STATIONS,
    MAX_UPDATE_INTERVAL_HOURS,
    MIN_RADIUS_KM,
    MIN_TANK_CAPACITY_L,
    MIN_TOP_STATIONS,
    MIN_UPDATE_INTERVAL_HOURS,
    NAME,
)
from .exceptions import CNEAuthenticationError, CNEError


def _number_selector(minimum: float, maximum: float, unit: str) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=1,
            unit_of_measurement=unit,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _settings_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_RADIUS_KM,
                default=defaults.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM),
            ): _number_selector(MIN_RADIUS_KM, MAX_RADIUS_KM, "km"),
            vol.Optional(
                CONF_INCLUDE_ASSISTED,
                default=defaults.get(CONF_INCLUDE_ASSISTED, DEFAULT_INCLUDE_ASSISTED),
            ): bool,
            vol.Optional(
                CONF_INCLUDE_SELF_SERVICE,
                default=defaults.get(
                    CONF_INCLUDE_SELF_SERVICE, DEFAULT_INCLUDE_SELF_SERVICE
                ),
            ): bool,
            vol.Optional(
                CONF_UPDATE_INTERVAL_HOURS,
                default=defaults.get(
                    CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS
                ),
            ): _number_selector(
                MIN_UPDATE_INTERVAL_HOURS, MAX_UPDATE_INTERVAL_HOURS, "h"
            ),
            vol.Optional(
                CONF_TOP_STATIONS,
                default=defaults.get(CONF_TOP_STATIONS, DEFAULT_TOP_STATIONS),
            ): _number_selector(MIN_TOP_STATIONS, MAX_TOP_STATIONS, "estaciones"),
            vol.Optional(
                CONF_TANK_CAPACITY_L,
                default=defaults.get(CONF_TANK_CAPACITY_L, DEFAULT_TANK_CAPACITY_L),
            ): _number_selector(MIN_TANK_CAPACITY_L, MAX_TANK_CAPACITY_L, "L"),
        }
    )


class CNECombustiblesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Chile Combustibles."""

    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            await self.async_set_unique_id(email)
            self._abort_if_unique_id_configured()
            try:
                client = CNEApiClient(
                    async_get_clientsession(self.hass),
                    email,
                    user_input[CONF_PASSWORD],
                )
                await client.async_login()
            except CNEAuthenticationError:
                errors["base"] = "invalid_auth"
            except CNEError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=NAME,
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_RADIUS_KM: user_input[CONF_RADIUS_KM],
                        CONF_INCLUDE_ASSISTED: user_input[CONF_INCLUDE_ASSISTED],
                        CONF_INCLUDE_SELF_SERVICE: user_input[
                            CONF_INCLUDE_SELF_SERVICE
                        ],
                        CONF_UPDATE_INTERVAL_HOURS: user_input[
                            CONF_UPDATE_INTERVAL_HOURS
                        ],
                        CONF_TOP_STATIONS: user_input[CONF_TOP_STATIONS],
                        CONF_TANK_CAPACITY_L: user_input[CONF_TANK_CAPACITY_L],
                    },
                )

        schema = _settings_schema({}).extend(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        entry = self._reauth_entry
        if user_input is not None:
            try:
                client = CNEApiClient(
                    async_get_clientsession(self.hass),
                    entry.data[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                )
                await client.async_login()
            except CNEAuthenticationError:
                errors["base"] = "invalid_auth"
            except CNEError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={"email": entry.data[CONF_EMAIL]},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> CNECombustiblesOptionsFlow:
        return CNECombustiblesOptionsFlow()


class CNECombustiblesOptionsFlow(config_entries.OptionsFlow):
    """Handle Chile Combustibles options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_settings_schema(current))
