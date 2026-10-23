from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .adc_client import AdCClient, CannotConnect, InvalidAuth
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def _async_fetch_subscriptions(username: str, password: str) -> dict[str, str]:
    """Log in and return the account subscriptions as {id: label}."""
    session = aiohttp.ClientSession()
    try:
        client = AdCClient(username, password, 1, False, session=session)
        await client.login()
        await client.get_subscription_ids()
        return client.subscription_choices
    finally:
        await session.close()


def _subscription_selector(choices: dict[str, str], default: str) -> SelectSelector:
    """Return a dropdown selector for the account subscriptions."""
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                {"value": subscription_id, "label": label}
                for subscription_id, label in choices.items()
            ],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


class ADCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Águas de Coimbra."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        self._user_input: dict = {}
        self._choices: dict[str, str] = {}

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        if user_input is not None:
            self._user_input = user_input
            try:
                self._choices = await _async_fetch_subscriptions(
                    user_input["username"], user_input["password"]
                )
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error fetching the subscriptions")
                errors["base"] = "unknown"
            else:
                if not self._choices:
                    errors["base"] = "no_subscriptions"
                elif len(self._choices) > 1:
                    return await self.async_step_subscription()
                else:
                    return self._async_create_entry(next(iter(self._choices)))

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Required("billing_cycle_start_day", default=1): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=28)
                    ),
                    vol.Optional("social_tariff", default=False): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_subscription(self, user_input=None) -> FlowResult:
        """Let the user pick which subscription to read, when there is more than one."""
        if user_input is not None:
            return self._async_create_entry(user_input["subscription_id"])

        default = next(iter(self._choices))
        return self.async_show_form(
            step_id="subscription",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "subscription_id", default=default
                    ): _subscription_selector(self._choices, default)
                }
            ),
        )

    def _async_create_entry(self, subscription_id: str) -> FlowResult:
        options = dict(self._user_input)
        options["subscription_id"] = int(subscription_id)
        return self.async_create_entry(
            title="Águas de Coimbra", data={}, options=options
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        # HA 2024.11+ injects the entry: OptionsFlow.config_entry is read-only
        # and the flow must be built without arguments.
        return ADCOptionsFlowHandler()


class ADCOptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Handle config options for Águas de Coimbra."""

    def __init__(self) -> None:
        self._choices: dict[str, str] = {}

    async def _async_load_choices(
        self, username: str, password: str, errors: dict
    ) -> None:
        try:
            self._choices = await _async_fetch_subscriptions(username, password)
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Could not fetch the subscriptions")
            errors["base"] = "cannot_connect"

    def _show_form(self, values: dict, errors: dict):
        ids = list(self._choices)
        current_id = str(values.get("subscription_id") or (ids[0] if ids else ""))
        schema = {
            vol.Required("username", default=values.get("username", "")): str,
            # Left blank, the stored password is kept (see async_step_init).
            vol.Required("password", description={"suggested_value": ""}): str,
            vol.Required(
                "billing_cycle_start_day",
                default=values.get("billing_cycle_start_day", 1),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=28)),
            vol.Optional(
                "social_tariff", default=values.get("social_tariff", False)
            ): bool,
        }
        if ids:
            schema[vol.Required("subscription_id", default=current_id)] = (
                _subscription_selector(self._choices, current_id)
            )
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(schema), errors=errors
        )

    async def async_step_init(self, user_input=None):
        entry = self.config_entry
        current = {**entry.data, **entry.options}
        errors = {}

        if user_input is None:
            await self._async_load_choices(
                current.get("username", ""), current.get("password", ""), errors
            )
            return self._show_form(current, errors)

        username = user_input.get("username") or current.get("username", "")
        password = user_input.get("password") or current.get("password", "")
        await self._async_load_choices(username, password, errors)

        if not errors:
            chosen = user_input.get("subscription_id") or current.get("subscription_id")
            if chosen is not None and (
                not self._choices or str(chosen) in self._choices
            ):
                options = {**current, **user_input}
                options["username"] = username
                options["password"] = password
                options["subscription_id"] = int(chosen)
                return self.async_create_entry(title="", data=options)
            errors["base"] = "subscription_required"

        return self._show_form({**current, **user_input}, errors)
