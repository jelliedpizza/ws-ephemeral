import logging
import re
from types import TracebackType
from typing import TypedDict, final

import httpx

from config import Config
from .cookie import load_cookie


class Csrf(TypedDict):
    csrf_time: int
    csrf_token: str


@final
class Windscribe:
    """Async Windscribe API client."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        headers = {
            "origin": self.config.base_url,
            "referer": self.config.login_url,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
        }
        
        cookie = load_cookie(self.config)
        
        self.client = httpx.AsyncClient(
            headers=headers,
            cookies=cookie,
            timeout=self.config.request_timeout
        )
        
        self._is_authenticated = False
        self.csrf: Csrf | None = None

    async def connect(self) -> bool:
        """Initialize the session and fetch CSRF token."""
        self._is_authenticated = await self._validate_session()
        if self._is_authenticated:
            try:
                self.csrf = await self.get_csrf()
                return True
            except Exception as e:
                self.logger.error(f"Failed to fetch CSRF after validation: {e}")
                self._is_authenticated = False
        return False

    async def _validate_session(self) -> bool:
        try:
            resp = await self.client.get(self.config.myact_url)
            if resp.status_code == 200 and "csrf_time" in resp.text:
                self.logger.debug("Session validation successful")
                return True
            self.logger.warning(f"Session validation failed - status: {resp.status_code}")
            return False
        except httpx.RequestError as e:
            self.logger.error(f"Session validation failed: {e}")
            return False

    async def __aenter__(self) -> "Windscribe":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    @property
    def is_authenticated(self) -> bool:
        return self._is_authenticated

    async def get_csrf(self) -> Csrf:
        try:
            resp = await self.client.post(self.config.csrf_url)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Failed to get CSRF token: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            self.logger.error(f"Failed to get CSRF token: {e}")
            raise

    def _check_authenticated(self) -> None:
        if not self._is_authenticated or not self.csrf:
            raise ValueError("Not authenticated - session cookie may be invalid or connect() not called")

    async def renew_csrf(self) -> Csrf:
        self._check_authenticated()
        try:
            resp = await self.client.get(self.config.myact_url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Failed to renew CSRF: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            self.logger.error(f"Failed to renew CSRF: {e}")
            raise

        csrf_time = re.search(r"csrf_time = (?P<ctime>\d+)", resp.text)
        csrf_token = re.search(r"csrf_token = \'(?P<ctoken>\w+)\'", resp.text)
        
        if not csrf_time or not csrf_token:
            raise ValueError("CSRF tokens missing from response, Windscribe structure may have changed.")

        new_csrf: Csrf = {
            "csrf_time": int(csrf_time.groupdict()["ctime"]),
            "csrf_token": csrf_token.groupdict()["ctoken"],
        }
        self.logger.debug("CSRF renewed successfully.")
        return new_csrf

    async def delete_ephemeral_port(self) -> dict:
        self._check_authenticated()
        assert self.csrf is not None
        data = {
            "ctime": self.csrf["csrf_time"],
            "ctoken": self.csrf["csrf_token"],
        }
        try:
            resp = await self.client.post(self.config.del_ephem_url, data=data)
            resp.raise_for_status()
            res = resp.json()
            self.logger.debug(f"Ephemeral port deleted: {res}")
            return res
        except httpx.HTTPError as e:
            self.logger.exception("Failed to delete ephemeral port")
            raise

    async def set_matching_port(self) -> int:
        self._check_authenticated()
        assert self.csrf is not None
        data = {
            "port": "",
            "ctime": self.csrf["csrf_time"],
            "ctoken": self.csrf["csrf_token"],
        }
        try:
            resp = await self.client.post(self.config.set_ephem_url, data=data)
            resp.raise_for_status()
            res = resp.json()
            self.logger.debug(f"New ephemeral port set: {res}")
        except httpx.HTTPError as e:
            self.logger.exception("Failed to set matching port")
            raise

        if res.get("success") != 1:
            raise ValueError(f"Unable to setup matching ephemeral port: {res.get('message', 'Unknown error')}")

        external_port = res["epf"]["ext"]
        internal_port = res["epf"]["int"]

        if external_port != internal_port:
            self.logger.warning(f"Port setup completed but external ({external_port}) and internal ({internal_port}) differ.")
            raise ValueError("Port setup done but matching port not found.")

        return internal_port

    async def setup(self) -> int:
        self.csrf = await self.renew_csrf()
        self.logger.info("Creating new ephemeral port...")
        await self.delete_ephemeral_port()
        return await self.set_matching_port()

    async def close(self) -> None:
        self.logger.debug("Closing session")
        await self.client.aclose()
