"""
Gluetun VPN container manager
"""

import logging

import httpx


class GluetunManager:
    """Manages Gluetun VPN container port forwarding."""

    def __init__(
        self,
        host: str,
        port: int,
        auth_type: str = "none",
        username: str = "",
        password: str = "",
        api_key: str | None = None,
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_url = f"http://{host}:{port}"
        self.auth_type = auth_type
        self.username = username
        self.password = password
        self.api_key = api_key

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_type == "apikey" and self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _get_auth(self) -> httpx.Auth | None:
        if self.auth_type == "basic" and self.username and self.password:
            return httpx.BasicAuth(self.username, self.password)
        return None

    def get_port(self) -> int | None:
        """Get current port forwarding from Gluetun.

        Returns:
            int | None: The currently forwarded port, or None if not set.
        """
        try:
            auth = self._get_auth()
            resp = httpx.get(
                f"{self.base_url}/v1/portforward",
                headers=self._get_headers(),
                auth=auth,
            )
            resp.raise_for_status()
            data = resp.json()
            port = data.get("port")
            self.logger.info("Gluetun current port: %s", port)
            return port
        except Exception as e:
            self.logger.error("Failed to get port from Gluetun: %s", e)
            return None

    def get_vpn_status(self) -> dict | None:
        """Get VPN connection status from Gluetun.

        Returns:
            dict with 'status' key (e.g., 'running', 'stopped'), or None if unavailable.
        """
        try:
            auth = self._get_auth()
            resp = httpx.get(
                f"{self.base_url}/v1/vpn/status",
                headers=self._get_headers(),
                auth=auth,
            )
            resp.raise_for_status()
            data = resp.json()
            self.logger.debug("Gluetun VPN status: %s", data)
            return data
        except Exception as e:
            self.logger.error("Failed to get VPN status from Gluetun: %s", e)
            return None

    def set_port(self, port: int) -> bool:
        """Set port forwarding in Gluetun.

        Args:
            port: The port to forward through Gluetun.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            auth = self._get_auth()
            resp = httpx.put(
                f"{self.base_url}/v1/portforward",
                headers=self._get_headers(),
                json={"ports": [port]},
                auth=auth,
            )
            resp.raise_for_status()
            self.logger.info("Gluetun port set to: %s", port)
            return True
        except Exception as e:
            self.logger.error("Failed to set port in Gluetun: %s", e)
            return False