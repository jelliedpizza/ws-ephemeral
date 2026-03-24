#!/usr/bin/env python3
"""
Test script for ws-ephemeral components.
Run individual tests by passing the test name as argument.
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenv not installed")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent
ENV_FILE = PROJECT_ROOT / ".env"

if not ENV_FILE.exists():
    print(f".env not found at {ENV_FILE}")
    sys.exit(1)

load_dotenv(ENV_FILE)
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import config
from ws.ws import Windscribe


def test_windscribe_auth():
    """Test Windscribe authentication."""
    print("\n=== Test: Windscribe Auth ===")
    with Windscribe() as ws:
        print(f"Authenticated: {ws.is_authenticated}")
        print(f"CSRF: {ws.csrf}")
    print("PASS")


def test_get_ephem_port():
    """Test getting existing ephemeral port."""
    print("\n=== Test: Get Ephemeral Port ===")
    with Windscribe() as ws:
        existing = ws.get_ephem_port()
        if existing:
            print(f"Existing port: {existing}")
        else:
            print("No existing port found")
    print("PASS")


def test_set_port():
    """Test creating a new ephemeral port."""
    print("\n=== Test: Set Port ===")
    with Windscribe() as ws:
        port = ws.setup()
        print(f"Port set: {port}")
    print("PASS")


def test_delete_port():
    """Test deleting ephemeral port."""
    print("\n=== Test: Delete Port ===")
    with Windscribe() as ws:
        result = ws.delete_ephm_port()
        print(f"Delete result: {result}")
    print("PASS")


def test_monitor():
    """Test monitor health checks."""
    print("\n=== Test: Monitor ===")
    from monitor import check_qbit, check_gluetun
    
    print("Checking qBitTorrent...")
    qbit_ok = check_qbit()
    print(f"qBitTorrent: {qbit_ok}")
    
    print("Checking Gluetun...")
    gluetun_ok = check_gluetun()
    print(f"Gluetun: {gluetun_ok}")
    
    print("PASS")


def test_gluetun_manager():
    """Test GluetunManager."""
    print("\n=== Test: Gluetun Manager ===")
    from lib.gluetun import GluetunManager
    
    gm = GluetunManager(
        host=config.GLUETUN_HOST,
        port=config.GLUETUN_PORT,
        auth_type=config.GLUETUN_AUTH_TYPE,
        api_key=config.GLUETUN_API_KEY,
    )
    
    print(f"Base URL: {gm.base_url}")
    
    status = gm.get_vpn_status()
    print(f"VPN Status: {status}")
    
    port = gm.get_port()
    print(f"Current Port: {port}")
    
    print("PASS")


def test_config():
    """Test config loading."""
    print("\n=== Test: Config ===")
    print(f"WS_SESSION_COOKIE set: {bool(config.WS_SESSION_COOKIE)}")
    print(f"QBIT_HOST: {config.QBIT_HOST}")
    print(f"QBIT_PORT: {config.QBIT_PORT}")
    print(f"GLUETUN_HOST: {config.GLUETUN_HOST}")
    print(f"GLUETUN_PORT: {config.GLUETUN_PORT}")
    print(f"GLUETUN_AUTH_TYPE: {config.GLUETUN_AUTH_TYPE}")
    print(f"GLUETUN_API_KEY set: {bool(config.GLUETUN_API_KEY)}")
    print("PASS")


TESTS = {
    "config": test_config,
    "auth": test_windscribe_auth,
    "set_port": test_set_port,
    "delete_port": test_delete_port,
    "monitor": test_monitor,
    "gluetun": test_gluetun_manager,
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Available tests:")
        for name in TESTS:
            print(f"  - {name}")
        print("\nUsage: python test.py <test_name>")
        sys.exit(1)
    
    test_name = sys.argv[1]
    if test_name not in TESTS:
        print(f"Unknown test: {test_name}")
        sys.exit(1)
    
    try:
        TESTS[test_name]()
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)