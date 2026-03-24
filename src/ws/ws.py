"""Windscribe module to setup ephemeral ports.

This module provides the Windscribe class to interact with the Windscribe API,
allowing users to manage ephemeral ports and handle authentication.
"""

import logging
import re
from types import TracebackType
from typing import TypedDict, final

import httpx

import config

from .cookie import load_cookie


class Csrf(TypedDict):
    """CSRF type dict"""

    csrf_time: int
    csrf_token: str


@final
class Windscribe:
    """Windscribe API to enable ephemeral ports.

    This class handles authentication and API requests to set or delete
    ephemeral ports using cookies exported from browser.

    Attributes:
        client (httpx.Client): The HTTP client for making requests.
        csrf (Csrf): The CSRF token and time.
        logger (logging.Logger): Logger for the class.
    """

    # pylint: disable=redefined-outer-name
    def __init__(self) -> None:
        headers = {
            "origin": config.BASE_URL,
            "referer": config.LOGIN_URL,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",  # ruff: noqa: E501
        }

        cookie = load_cookie()

        self.client = httpx.Client(
            headers=headers, cookies=cookie, timeout=config.REQUEST_TIMEOUT
        )

        # Logger must be initialized before any method that uses it
        self.logger = logging.getLogger(self.__class__.__name__)

        self._is_authenticated = self._validate_session()
        self.csrf: Csrf = self.get_csrf()

    def _validate_session(self) -> bool:
        """Validate the session by making a test request to the account page.

        Returns:
            bool: True if session is valid, False otherwise.
        """
        try:
            resp = self.client.get(config.MYACT_URL)
            if resp.status_code == 200 and "csrf_time" in resp.text:
                self.logger.debug("Session validation successful")
                return True
            self.logger.warning("Session validation failed - status: %s", resp.status_code)
            return False
        except httpx.RequestError as e:
            self.logger.error("Session validation failed: %s", e)
            return False

    def __enter__(self) -> "Windscribe":
        """Context manager entry.

        Returns:
            Windscribe: The Windscribe instance.
        """
        return self

    def __exit__(
        self,
        exc_type: BaseException | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Context manager exit.

        Closes the HTTP client session.

        Args:
            exc_type (BaseException | None): The exception type, if any.
            exc_value (BaseException | None): The exception value, if any.
            traceback (TracebackType | None): The traceback, if any.
        """
        self.close()

    @property
    def is_authenticated(self) -> bool:
        """Check if session is authenticated.

        Returns:
            bool: True if authenticated, False otherwise.
        """
        return self._is_authenticated

    @is_authenticated.setter
    def is_authenticated(self, value: bool) -> None:
        """Set authentication status.

        Args:
            value (bool): The new authentication status.
        """
        self._is_authenticated = value

    def get_csrf(self) -> Csrf:
        """Get CSRF token.

        Makes a request to the Windscribe API to get the CSRF token.

        Returns:
            Csrf: The CSRF token and time.

        Raises:
            httpx.RequestError: If the request fails.
        """
        try:
            resp = self.client.post(config.CSRF_URL)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            self.logger.error("Failed to get CSRF token: %s - %s", e.response.status_code, e.response.text)
            raise
        except httpx.RequestError as e:
            self.logger.error("Failed to get CSRF token: %s", e)
            raise

    def _check_authenticated(self) -> None:
        """Check if session is authenticated, raise if not."""
        if not self._is_authenticated:
            raise ValueError("Not authenticated - session cookie may be invalid")

    def renew_csrf(self) -> Csrf:
        """Renew CSRF token.

        After login, Windscribe issues a new CSRF token within JavaScript.

        Returns:
            Csrf: The new CSRF token and time.

        Raises:
            ValueError: If CSRF time or token is not found.
            httpx.RequestError: If the request fails.
        """
        self._check_authenticated()

        try:
            resp = self.client.get(config.MYACT_URL)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            self.logger.error("Failed to renew CSRF token: %s - %s", e.response.status_code, e.response.text)
            raise
        except httpx.RequestError as e:
            self.logger.error("Failed to renew CSRF token: %s", e)
            raise

        csrf_time = re.search(r"csrf_time = (?P<ctime>\d+)", resp.text)
        if csrf_time is None:
            raise ValueError("Can not work further, csrf_time not found, exited.")

        csrf_token = re.search(r"csrf_token = \'(?P<ctoken>\w+)\'", resp.text)
        if csrf_token is None:
            raise ValueError("Can not work further, csrf_token not found, exited.")

        new_csrf: Csrf = {
            "csrf_time": int(csrf_time.groupdict()["ctime"]),
            "csrf_token": csrf_token.groupdict()["ctoken"],
        }

        self.logger.debug("csrf renewed successfully.")
        return new_csrf

    def delete_ephemeral_port(self) -> dict[str, bool | int]:
        """Delete ephemeral port.

        Ensures that any existing ephemeral port setting is deleted.

        Returns:
            dict[str, bool | int]: The response from the API.

        Raises:
            httpx.RequestError: If the request fails.
        """
        self._check_authenticated()

        data = {
            "ctime": self.csrf["csrf_time"],
            "ctoken": self.csrf["csrf_token"],
        }

        try:
            resp = self.client.post(config.DEL_EPHEM_URL, data=data)
            resp.raise_for_status()
            res = resp.json()
            self.logger.debug("ephimeral port deleted: %s", res)
            return res
        except httpx.HTTPStatusError as e:
            self.logger.error("Failed to delete ephemeral port: %s - %s", e.response.status_code, e.response.text)
            raise
        except httpx.RequestError as e:
            self.logger.error("Failed to delete ephemeral port: %s", e)
            raise

    def set_matching_port(self) -> int:
        """Set matching ephemeral port.

        Sets up a matching ephemeral port on Windscribe.

        Returns:
            int: The matching ephemeral port.

        Raises:
            ValueError: If unable to set up a matching ephemeral port or if the external and internal ports do not match.
            httpx.RequestError: If the request fails.
        """
        self._check_authenticated()

        data = {
            # keeping port empty makes it to request matching port
            "port": "",
            "ctime": self.csrf["csrf_time"],
            "ctoken": self.csrf["csrf_token"],
        }

        try:
            resp = self.client.post(config.SET_EPHEM_URL, data=data)
            resp.raise_for_status()
            res = resp.json()
            self.logger.debug("new ephimeral port set: %s", res)
        except httpx.HTTPStatusError as e:
            self.logger.error("Failed to set matching port: %s - %s", e.response.status_code, e.response.text)
            raise
        except httpx.RequestError as e:
            self.logger.error("Failed to set matching port: %s", e)
            raise

        if res.get("success") != 1:
            error_msg = res.get("message", "Unknown error")
            raise ValueError(f"Not able to setup matching ephemeral port: {error_msg}")

        # lets make sure we actually had matching port
        external: int = res["epf"]["ext"]
        internal: int = res["epf"]["int"]

        if external != internal:
            raise ValueError("Port setup done but matching port not found.")

        return internal

    def setup(self) -> int:
        """Perform ephemeral port setup.

        Deletes any existing ephemeral port and creates a new matching port.

        Returns:
            int: The matching ephemeral port.
        """
        # After login we need to update the csrf token again,
        # Windscribe puts new csrf token in the javascript
        self.csrf = self.renew_csrf()

        self.logger.info("Creating new ephemeral port")
        _ = self.delete_ephemeral_port()
        return self.set_matching_port()

    def close(self) -> None:
        """Close HTTP client session.

        Closes the HTTP client session and logs the action.
        """
        self.logger.debug("closing session")
        self.client.close()
