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
            if status and status.get("status") == "running":
                logging.debug("Gluetun heartbeat: OK (VPN running)")
                return True
            logging.warning("Gluetun health check: VPN not connected")
            return False
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