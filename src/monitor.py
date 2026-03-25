"""
Monitor that checks health of qBitTorrent and Gluetun VPN container.
"""

import logging
from typing import TypedDict

from config import Config
from clients.gluetun import GluetunManager
from clients.qbittorrent import QbitManager


class HealthStatus(TypedDict):
    """Health check result."""
    qbit: bool
    gluetun: bool


async def check_qbit(config: Config) -> bool:
    """Check if qBitTorrent is accessible."""
    try:
        async with QbitManager(config):
            logging.debug("qBitTorrent heartbeat: OK")
            return True
    except Exception as e:
        logging.error(f"qBitTorrent health check failed: {e}")
        return False


async def check_gluetun(config: Config) -> bool:
    """Check if Gluetun VPN is running and connected."""
    try:
        async with GluetunManager(config) as gluetun:
            status = await gluetun.get_vpn_status()
            if not status or status.get("status") != "running":
                logging.warning("Gluetun health check: VPN not connected")
                return False
                
            try:
                # Issue an empty PUT to verify the port forwarding service has completed initialization.
                # Gluetun yields 500 Internal Server Error if the backend service is still booting.
                # If it is fully ready, it usually yields 400 (Bad Request for missing payload) or 200.
                resp = await gluetun.client.put(
                    f"{gluetun.base_url}/portforward",
                    headers=gluetun._get_headers(),
                    json={},
                    timeout=gluetun.config.request_timeout
                )
                if resp.status_code == 500:
                    logging.warning(f"Gluetun health check: Port forwarding service not ready (HTTP {resp.status_code})")
                    return False
            except Exception as e:
                logging.warning(f"Gluetun health check: Port forwarding ping failed ({e})")
                return False

            logging.debug("Gluetun heartbeat: OK (VPN and Port Forwarding ready)")
            return True
    except Exception as e:
        logging.error(f"Gluetun health check failed: {e}")
        return False


async def monitor(config: Config) -> bool:
    """Monitor qBitTorrent and Gluetun health.

    Both qBitTorrent and Gluetun must be healthy (if configured).
    
    Returns:
        bool: True if both services are healthy.
    """
    qbit_ok = await check_qbit(config)
    gluetun_ok = await check_gluetun(config)

    healthy = qbit_ok and gluetun_ok

    if healthy:
        logging.debug("All health checks passed")
    else:
        failures = []
        if not qbit_ok:
            failures.append("qBitTorrent")
        if not gluetun_ok:
            failures.append("Gluetun")
        logging.warning(f"Health check failures: {', '.join(failures)}")

    return healthy