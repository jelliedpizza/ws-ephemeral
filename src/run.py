"""
Module that runs the setup for Windscribe's ephemeral port
"""

import logging
import time
from datetime import datetime, timedelta

import schedule

import config
from lib.gluetun import GluetunManager
from lib.qbit import QbitManager
from logger import setup_logging
from monitor import HEARTBEAT, monitor
from util import catch_exceptions
from ws import Windscribe

setup_logging()

logger = logging.getLogger("main")


def check_and_run() -> None:
    """Run health check. If healthy, run main and reschedule for next run."""
    logger.info("Running health check...")

    if not monitor():
        logger.debug("Health check failed, will retry in 1 minute")
        return

    logger.info("Health check passed, running main automation...")

    try:
        main()
    except Exception as e:
        logger.error("Main automation failed: %s", e)

    logger.info("Stopping health check loop and scheduling next run")

    schedule.clear()

    next_run_time = datetime.now() + timedelta(days=config.DAYS)
    next_run_date = next_run_time.date()
    run_time = datetime.strptime(str(config.TIME), "%H:%M").time()
    next_run_datetime = datetime.combine(next_run_date, run_time)

    if next_run_datetime <= datetime.now():
        next_run_datetime += timedelta(days=1)

    logger.info(f"Next run scheduled for {next_run_datetime}")

    schedule.every(config.DAYS).days.at(config.TIME).do(check_and_run)


def run_loop() -> None:
    """Main loop that handles scheduling."""
    schedule.every(1).minutes.do(check_and_run)
    schedule.run_all()

    if not config.ONESHOT:
        logger.info("Starting 1-minute health check loop")
        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        logger.info("ONESHOT mode: running once")
        schedule.run_all()


@catch_exceptions(cancel_on_failure=False)
def main() -> None:
    """Main function responsible for setting up ws and qbit."""
    if not HEARTBEAT:
        msg = (
            "From heartbeat check, "
            "qBittorrent wasn't accessible. "
            "Can't run ephemeral renewal right now."
        )
        logger.error(msg)
        return

    logger.info("Running automation...")

    try:
        with Windscribe() as ws:
            if not ws.is_authenticated:
                logger.error("Session authentication failed. Please update WS_SESSION_COOKIE.")
                return
            port = ws.setup()
            logger.info("Successfully set up ephemeral port: %s", port)
    except Exception as e:
        logger.error("Failed to set up ephemeral port: %s", e)
        return

    if not config.qbit_found:
        logger.warning(
            "QBitTorrent credentials not configured - skipping qBittorrent setup. "
            "Set QBIT_USERNAME and QBIT_PASSWORD in .env"
        )
        return

    try:
        qbit = QbitManager(
            host=config.QBIT_HOST,
            port=config.QBIT_PORT,
            username=config.QBIT_USERNAME,
            password=config.QBIT_PASSWORD,
        )
    except Exception as e:
        logger.error("Failed to connect to qBittorrent: %s", e)
        return

    try:
        qbit.set_listen_port(port)
        logger.info("Updated qBittorrent listen port to %s", port)
    except Exception as e:
        logger.error("Failed to update qBittorrent listen port: %s", e)
        return

    if config.QBIT_PRIVATE_TRACKER:
        try:
            qbit.setup_private_tracker()
            logger.info("Configured qBittorrent for private tracker")
        except Exception as e:
            logger.error("Failed to configure private tracker settings: %s", e)

    try:
        gluetun = GluetunManager(
            host=config.GLUETUN_HOST,
            port=config.GLUETUN_PORT,
            auth_type=config.GLUETUN_AUTH_TYPE,
            username=config.GLUETUN_USERNAME,
            password=config.GLUETUN_PASSWORD,
            api_key=config.GLUETUN_API_KEY,
        )
        if not gluetun.set_port(port):
            logger.error("Failed to update Gluetun port forward")
            return
        logger.info("Updated Gluetun port forward to %s", port)
    except Exception as e:
        logger.error("Failed to update Gluetun port: %s", e)
        return

    logger.info("Port setup completed.")


if __name__ == "__main__":
    run_loop()
