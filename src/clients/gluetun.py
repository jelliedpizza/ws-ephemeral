import logging
from typing import Any

import httpx
from config import Config


class GluetunManager:
    """Async wrapper for the Gluetun Control Server."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_url = f"http://{config.gluetun_host}:{config.gluetun_port}/v1"
        self.client = httpx.AsyncClient()

    async def __aenter__(self) -> "GluetunManager":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.client.aclose()

    def _get_headers(self) -> dict[str, str]:
        if self.config.gluetun_auth_type == "none":
            return {}
            
        import base64
        if self.config.gluetun_auth_type == "basic":
            auth = f"{self.config.gluetun_username}:{self.config.gluetun_password}"
            return {"Authorization": f"Basic {base64.b64encode(auth.encode()).decode()}"}
            
        if self.config.gluetun_auth_type == "apikey":
            return {"X-API-Key": self.config.gluetun_api_key or ""}
            
        return {}

    async def _request(self, method: str, endpoint: str, json_data: dict | None = None) -> dict | None:
        url = f"{self.base_url}{endpoint}"
        try:
            resp = await self.client.request(
                method, 
                url, 
                headers=self._get_headers(), 
                json=json_data,
                timeout=self.config.request_timeout
            )
            # Some endpoints might not return JSON
            if resp.status_code == 200 and resp.text:
                return resp.json()
            resp.raise_for_status()
            return None
        except httpx.HTTPError as e:
            self.logger.error(f"Gluetun API request failed ({method} {endpoint}): {e}")
            raise

    async def get_vpn_status(self) -> dict | None:
        """Get the openvpn VPN connection status."""
        try:
            return await self._request("GET", "/openvpn/status")
        except httpx.HTTPError:
            self.logger.warning("Falling back to Wireguard status probe.")
            try:
                return await self._request("GET", "/wireguard/status")
            except httpx.HTTPError:
                return None

    async def get_port(self) -> int:
        """Get the current forwarded port from Gluetun."""
        resp = await self._request("GET", "/portforward")
        if resp and "port" in resp:
            return int(resp["port"])
        return 0

    async def set_port(self, port: int) -> bool:
        """Set the Gluetun port forward."""
        await self._request("PUT", "/portforward", json_data={"port": port})
        current_port = await self.get_port()
        if current_port == port:
            self.logger.info(f"Verified Gluetun forwarded port: {current_port}")
            return True
        elif current_port == 0:
            self.logger.warning(f"Gluetun reported port 0 instead of {port} (ignoring due to known issue #3178)")
            return True
        
        self.logger.error(f"Gluetun reported port {current_port}, expected {port}")
        return False
