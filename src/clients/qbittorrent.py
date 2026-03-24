import logging
from typing import Any

import httpx
from config import Config


class QbitManager:
    """Async qBittorrent client wrapping only the required endpoints."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_url = f"http://{config.qbit_host}:{config.qbit_port}/api/v2"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.config.request_timeout
        )

    async def __aenter__(self) -> "QbitManager":
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.client.aclose()

    async def login(self) -> None:
        """Authenticate with the qBittorrent REST API."""
        try:
            resp = await self.client.post(
                "/auth/login",
                data={"username": self.config.qbit_username, "password": self.config.qbit_password},
                headers={"Referer": self.base_url}
            )
            resp.raise_for_status()
            if resp.text == "Fails.":
                raise ValueError("qBittorrent authentication failed.")
            self.logger.debug("Successfully authenticated with qBittorrent")
        except httpx.HTTPError as e:
            self.logger.error(f"Failed to connect to qBittorrent: {e}")
            raise

    async def _set_preferences(self, prefs: dict[str, Any]) -> None:
        import json
        try:
            resp = await self.client.post(
                "/app/setPreferences",
                data={"json": json.dumps(prefs)}
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            self.logger.error(f"Failed to set preferences: {e}")
            raise

    async def _get_preferences(self) -> dict:
        try:
            resp = await self.client.get("/app/preferences")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            self.logger.error(f"Failed to get preferences: {e}")
            raise

    async def set_listen_port(self, port: int) -> bool:
        """Set the listen port obtained from Windscribe."""
        await self._set_preferences({"listen_port": port})
        
        # Verify
        prefs = await self._get_preferences()
        current_port = prefs.get("listen_port")
        self.logger.info(f"Verified qBittorrent listen port: {current_port}")
        return current_port == port

    async def setup_private_tracker(self) -> bool:
        """Disable DHT, PeX, and LSD for private trackers."""
        self.logger.info("Setting qBittorrent preferences for private tracker (disabling DHT/PeX/LSD)")
        await self._set_preferences({"dht": False, "pex": False, "lsd": False})
        
        # Verify
        prefs = await self._get_preferences()
        dht = prefs.get("dht")
        pex = prefs.get("pex")
        lsd = prefs.get("lsd")
        
        return not (dht or pex or lsd)
