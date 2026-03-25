"""
Module that runs the setup for Windscribe's ephemeral port
"""

import asyncio
import logging
import time

import schedule

from config import Config, load_config
from clients.gluetun import GluetunManager
from clients.qbittorrent import QbitManager
from clients.windscribe import Windscribe
from logger import setup_logging
from monitor import monitor

setup_logging()
logger = logging.getLogger("main")


async def run_automation(config: Config) -> None:
    """Main function responsible for setting up ws, qbit, and gluetun."""
    while True:
        logger.info("Running health check...")
        if await monitor(config):
            break
            
        if config.oneshot:
            logger.warning("Health check failed in ONESHOT mode. Exiting.")
            return
            
        logger.warning("Health check failed, retrying in 1 minute...")
        await asyncio.sleep(60)

    logger.info("Health check passed, running main automation...")

    try:
        async with Windscribe(config) as ws:
            if not await ws.connect():
                logger.error("Session authentication failed. Please update WS_SESSION_COOKIE.")
                return
            port = await ws.setup()
            logger.info(f"Successfully set up ephemeral port: {port}")
    except Exception as e:
        logger.error(f"Failed to set up ephemeral port: {e}")
        return

    try:
        async with QbitManager(config) as qbit:
            await qbit.set_listen_port(port)
            logger.info(f"Updated qBittorrent listen port to {port}")
            
            if config.qbit_private_tracker:
                await qbit.setup_private_tracker()
                logger.info("Configured qBittorrent for private tracker")
    except Exception as e:
        logger.error(f"Failed to update qBittorrent: {e}")

    try:
        async with GluetunManager(config) as gluetun:
            if not await gluetun.set_port(port):
                logger.error("Failed to update Gluetun port forward")
            else:
                logger.info(f"Updated Gluetun port forward to {port}")
    except Exception as e:
        logger.error(f"Failed to update Gluetun port: {e}")

    logger.info("Port setup completed.")


def run_sync_automation(config: Config) -> None:
    """Wrapper to run async automation from synchronous schedule library."""
    try:
        asyncio.run(run_automation(config))
    except Exception as e:
        logger.error(f"Scheduled automation run failed: {e}")


def main() -> None:
    config = load_config()

    if config.oneshot:
        logger.info("ONESHOT mode: running once")
        run_sync_automation(config)
        return

    logger.info("Running initial boot execution...")
    run_sync_automation(config)

    logger.info(f"Scheduling target run every {config.days} days at {config.time}")
    schedule.every(config.days).days.at(config.time).do(run_sync_automation, config=config)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down ws-ephemeral...")
