"""Asynchronous client for the CNE Combustibles API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import BASE_URL, DEFAULT_TIMEOUT, LOGIN_ENDPOINT, STATIONS_ENDPOINT
from .exceptions import (
    CNEAuthenticationError,
    CNEConnectionError,
    CNEInvalidResponseError,
)

_LOGGER = logging.getLogger(__name__)


class CNEApiClient:
    """Client for api.cne.cl."""

    def __init__(
        self,
        session: ClientSession,
        email: str,
        password: str,
        *,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._timeout = timeout
        self._token: str | None = None

    async def async_login(self) -> None:
        """Authenticate and store a bearer token."""
        try:
            async with asyncio.timeout(self._timeout):
                response = await self._session.post(
                    f"{BASE_URL}{LOGIN_ENDPOINT}",
                    data={"email": self._email, "password": self._password},
                    headers={"Accept": "application/json"},
                )
                if response.status in (401, 403, 422):
                    await response.read()
                    raise CNEAuthenticationError("Credenciales CNE inválidas")
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except CNEAuthenticationError:
            raise
        except (TimeoutError, ClientError, ClientResponseError) as err:
            raise CNEConnectionError(f"No fue posible autenticar con CNE: {err}") from err
        except ValueError as err:
            raise CNEInvalidResponseError("La respuesta de login no es JSON válido") from err

        token = payload.get("token") if isinstance(payload, dict) else None
        if not token or not isinstance(token, str):
            raise CNEInvalidResponseError("La respuesta de login no contiene token")
        self._token = token

    async def async_get_stations(self) -> list[dict[str, Any]]:
        """Return all fuel stations, refreshing the token once on 401."""
        if not self._token:
            await self.async_login()

        for attempt in range(2):
            try:
                async with asyncio.timeout(self._timeout):
                    response = await self._session.get(
                        f"{BASE_URL}{STATIONS_ENDPOINT}",
                        headers={
                            "Accept": "application/json",
                            "Authorization": f"Bearer {self._token}",
                        },
                    )
                    if response.status == 401 and attempt == 0:
                        await response.read()
                        await self.async_login()
                        continue
                    if response.status in (401, 403):
                        await response.read()
                        raise CNEAuthenticationError("Token CNE inválido o expirado")
                    response.raise_for_status()
                    payload = await response.json(content_type=None)
            except CNEAuthenticationError:
                raise
            except (TimeoutError, ClientError, ClientResponseError) as err:
                raise CNEConnectionError(f"Error consultando estaciones CNE: {err}") from err
            except ValueError as err:
                raise CNEInvalidResponseError(
                    "La respuesta de estaciones no es JSON válido"
                ) from err

            if not isinstance(payload, list):
                raise CNEInvalidResponseError(
                    "La API CNE devolvió una estructura inesperada para estaciones"
                )

            return [item for item in payload if isinstance(item, dict)]

        raise CNEAuthenticationError("No fue posible renovar el token CNE")
