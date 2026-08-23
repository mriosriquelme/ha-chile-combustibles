"""Config flow for Chile Combustibles."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import callback
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

_LOGGER = logging.getLogger(__name__)

SETTINGS_KEYS = (
    CONF_RADIUS_KM,
    CONF_INCLUDE_ASSISTED,
    CONF_INCLUDE_SELF_SERVICE,
    CONF_UPDATE_INTERVAL_HOURS,
    CONF_TOP_STATIONS,
    CONF_TANK_CAPACITY_L,
)


def _number_selector(
    minimum: float, maximum: float, unit: str
) -> selector.NumberSelector:
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


def _validate_settings(user_input: dict[str, Any]) -> str | None:
    """Return an error key when the chosen filters would match no prices."""
    if not user_input.get(CONF_INCLUDE_ASSISTED) and not user_input.get(
        CONF_INCLUDE_SELF_SERVICE
    ):
        return "select_service_type"
    return None


class CNECombustiblesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Chile Combustibles."""

    VERSION = 2

    async def _async_validate_credentials(
        self, email: str, password: str
    ) -> str | None:
        """Try to log in and return an error key when it fails."""
        try:
            client = CNEApiClient(async_get_clientsession(self.hass), email, password)
            await client.async_login()
        except CNEAuthenticationError:
            return "invalid_auth"
        except CNEError:
            return "cannot_connect"
        except Exception:
            _LOGGER.exception("Error inesperado al validar las credenciales CNE")
            return "unknown"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            await self.async_set_unique_id(email)
            self._abort_if_unique_id_configured()
            error = _validate_settings(user_input)
            if not error:
                error = await self._async_validate_credentials(
                    email, user_input[CONF_PASSWORD]
                )
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=NAME,
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        **{key: user_input[key] for key in SETTINGS_KEYS},
                    },
                )
            return self.async_show_form(
                step_id="user",
                data_schema=_settings_schema(user_input).extend(
                    {
                        vol.Required(CONF_EMAIL): str,
                        vol.Required(CONF_PASSWORD): str,
                    }
                ),
                errors=errors,
            )

        schema = _settings_schema({}).extend(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user for a fresh password."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            if error := await self._async_validate_credentials(
                entry.data[CONF_EMAIL], user_input[CONF_PASSWORD]
            ):
                errors["base"] = error
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

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user change credentials and settings of an existing entry."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        current = {**entry.data, **entry.options}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            await self.async_set_unique_id(email)
            self._abort_if_unique_id_mismatch()
            error = _validate_settings(user_input)
            if not error:
                error = await self._async_validate_credentials(
                    email, user_input[CONF_PASSWORD]
                )
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        **{key: user_input[key] for key in SETTINGS_KEYS},
                    },
                )
            current = user_input

        schema = _settings_schema(current).extend(
            {
                vol.Required(CONF_EMAIL, default=current.get(CONF_EMAIL, "")): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> CNECombustiblesOptionsFlow:
        """Return the options flow."""
        return CNECombustiblesOptionsFlow()


class CNECombustiblesOptionsFlow(OptionsFlow):
    """Handle Chile Combustibles options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            if error := _validate_settings(user_input):
                return self.async_show_form(
                    step_id="init",
                    data_schema=_settings_schema(user_input),
                    errors={"base": error},
                )
            return self.async_create_entry(title="", data=user_input)
        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=_settings_schema(current)
        )
