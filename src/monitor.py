"""
Monitor that checks health of qBitTorrent and Gluetun VPN container.
"""

import logging
from typing import TypedDict

import config
from lib.gluetun import GluetunManager
from lib.qbit import QbitManager


class HealthStatus(TypedDict):
    """Health check result."""

    qbit: bool
    gluetun: bool


HEARTBEAT: bool = True


def check_qbit() -> bool:
    """Check if qBitTorrent is accessible.

    Returns:
        bool: True if qBitTorrent is healthy.
    """
    try:
        qbit = QbitManager(
            host=config.QBIT_HOST,
            port=config.QBIT_PORT,
            username=config.QBIT_USERNAME,
            password=config.QBIT_PASSWORD,
        )
        logging.debug("qBitTorrent heartbeat: OK")
        return True
    except Exception as e:
        logging.error("qBitTorrent health check failed: %s", e)
        return False


def check_gluetun() -> bool:
    """Check if Gluetun VPN is running and connected.

    Returns:
        bool: True if Gluetun is healthy (VPN connected).
    """
    try:
        gluetun = GluetunManager(
            host=config.GLUETUN_HOST,
            port=config.GLUETUN_PORT,
            auth_type=config.GLUETUN_AUTH_TYPE,
            username=config.GLUETUN_USERNAME,
            password=config.GLUETUN_PASSWORD,
            api_key=config.GLUETUN_API_KEY,
        )
        status = gluetun.get_vpn_status()
        if status and status.get("status") == "running":
            logging.debug("Gluetun heartbeat: OK (VPN running)")
            return True
        logging.warning("Gluetun health check: VPN not connected")
        return False
    except Exception as e:
        logging.error("Gluetun health check failed: %s", e)
        return False


def monitor() -> bool:
    """Monitor qBitTorrent and Gluetun health.

    Updates the global HEARTBEAT based on both services being healthy.
    Both qBitTorrent and Gluetun must be healthy for HEARTBEAT to be True.

    Returns:
        bool: True if both services are healthy.
    """
    global HEARTBEAT

    qbit_ok = check_qbit()
    gluetun_ok = check_gluetun()

    HEARTBEAT = qbit_ok and gluetun_ok

    if HEARTBEAT:
        logging.debug("All health checks passed")
    else:
        failures = []
        if not qbit_ok:
            failures.append("qBitTorrent")
        if not gluetun_ok:
            failures.append("Gluetun")
        logging.warning(f"Health check failures: {', '.join(failures)}")

    return HEARTBEAT