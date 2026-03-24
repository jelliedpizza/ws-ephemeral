"""
config module
"""

import os
import sys
from pathlib import Path

# only run once
# allows wg-ephemeral to be used as a cronjob
_ONESHOT: str = os.getenv("ONESHOT", "false")
ONESHOT: bool = True if _ONESHOT.lower() == "true" else False

# https://www.python-httpx.org/advanced/#timeout-configuration
_REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "5"))
# timeouts are disabled if None is used
REQUEST_TIMEOUT: int | None = None if _REQUEST_TIMEOUT == -1 else _REQUEST_TIMEOUT

BASE_PATH: Path = Path(".")

# common config
CSRF_URL: str = "https://res.windscribe.com/res/logintoken"

BASE_URL: str = "https://windscribe.com/"
LOGIN_URL: str = BASE_URL + "login"
MYACT_URL: str = BASE_URL + "myaccount"

STATICIP: str = BASE_URL + "staticips/"
EPHEM_URL: str = STATICIP + "load"
DEL_EPHEM_URL: str = STATICIP + "deleteEphPort"
SET_EPHEM_URL: str = STATICIP + "postEphPort"

# WS config
WS_USERNAME: str = os.getenv("WS_USERNAME", "")
WS_PASSWORD: str = os.getenv("WS_PASSWORD", "")
WS_TOTP: str | None = os.getenv("WS_TOTP", None)
WS_COOKIE = Path(os.getenv("WS_COOKIE_PATH", ".")) / "cookie.pkl"

if not all([WS_USERNAME, WS_PASSWORD]):
    print("ENV: WS_USERNAME and WS_PASSWORD need to be set")
    sys.exit(1)

# some HTML id for the login purpose
# TODO: expose via config file
USERNAME_ID: str = "username"
PASSWORD_ID: str = "password"


# fmt: off
# some qbit config
QBIT_USERNAME: str = os.getenv("QBIT_USERNAME", "default123!!")
QBIT_PASSWORD: str = os.getenv("QBIT_PASSWORD", "default123!!")
QBIT_HOST: str     = os.getenv("QBIT_HOST", "127.0.0.1")
QBIT_PORT: int     = int(os.getenv("QBIT_PORT", "8080"))
# fmt: on

qbit_found = True
# if user is running latest build without qbit env then let them run but disable the
# qbit functions
if QBIT_USERNAME == "default123!!" or QBIT_PASSWORD == "default123!!":
    print("QBIT related setup not found, setup env as soon as possible")
    qbit_found = False

_QBIT_PRIVATE_TRACKER: str = os.getenv("QBIT_PRIVATE_TRACKER", "false")
QBIT_PRIVATE_TRACKER: bool = True if _QBIT_PRIVATE_TRACKER.lower() == "true" else False


# Gluetun config
GLUETUN_HOST: str = os.getenv("GLUETUN_HOST", "localhost")
GLUETUN_PORT: int = int(os.getenv("GLUETUN_PORT", "8000"))
GLUETUN_AUTH_TYPE: str = os.getenv("GLUETUN_AUTH_TYPE", "none")
GLUETUN_USERNAME: str = os.getenv("GLUETUN_USERNAME", "")
GLUETUN_PASSWORD: str = os.getenv("GLUETUN_PASSWORD", "")
GLUETUN_API_KEY: str | None = os.getenv("GLUETUN_API_KEY", None)
try:
    DAYS: int = int(os.getenv("DAYS", 6))
except TypeError:
    print("DAYS must be integer")
TIME: str = os.getenv("TIME", "02:00")
