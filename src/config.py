"""
config module
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass(kw_only=True)
class Config:
    # App Settings
    oneshot: bool = field(
        default_factory=lambda: os.getenv("ONESHOT", "false").lower() == "true"
    )
    request_timeout: int | None = field(
        default_factory=lambda: None if int(os.getenv("REQUEST_TIMEOUT", "5")) == -1 else int(os.getenv("REQUEST_TIMEOUT", "5"))
    )
    days: int = field(default_factory=lambda: int(os.getenv("DAYS", "6")))
    time: str = field(default_factory=lambda: os.getenv("TIME", "02:00"))
    base_path: Path = field(default_factory=lambda: Path("."))
    
    # Windscribe URLs
    base_url: str = "https://windscribe.com/"
    login_url: str = "https://windscribe.com/login"
    myact_url: str = "https://windscribe.com/myaccount"
    csrf_url: str = "https://res.windscribe.com/res/logintoken"
    del_ephem_url: str = "https://windscribe.com/staticips/deleteEphPort"
    set_ephem_url: str = "https://windscribe.com/staticips/postEphPort"

    # Windscribe Auth
    ws_session_cookie: str = field(default_factory=lambda: os.getenv("WS_SESSION_COOKIE", ""))

    # qBittorrent Settings
    qbit_host: str = field(default_factory=lambda: os.getenv("QBIT_HOST", "localhost"))
    qbit_port: int = field(default_factory=lambda: int(os.getenv("QBIT_PORT", "8080")))
    qbit_username: str = field(default_factory=lambda: os.getenv("QBIT_USERNAME", "default123!!"))
    qbit_password: str = field(default_factory=lambda: os.getenv("QBIT_PASSWORD", "default123!!"))
    qbit_private_tracker: bool = field(
        default_factory=lambda: os.getenv("QBIT_PRIVATE_TRACKER", "false").lower() == "true"
    )

    # Gluetun Settings
    gluetun_host: str = field(default_factory=lambda: os.getenv("GLUETUN_HOST", "localhost"))
    gluetun_port: int = field(default_factory=lambda: int(os.getenv("GLUETUN_PORT", "8000")))
    gluetun_auth_type: str = field(default_factory=lambda: os.getenv("GLUETUN_AUTH_TYPE", "none"))
    gluetun_username: str = field(default_factory=lambda: os.getenv("GLUETUN_USERNAME", ""))
    gluetun_password: str = field(default_factory=lambda: os.getenv("GLUETUN_PASSWORD", ""))
    gluetun_api_key: str | None = field(default_factory=lambda: os.getenv("GLUETUN_API_KEY", None))

    @property
    def qbit_configured(self) -> bool:
        return bool(self.qbit_username and self.qbit_password and self.qbit_username != "default123!!")


def load_config() -> Config:
    config = Config()
    if not config.ws_session_cookie:
        print("ENV: WS_SESSION_COOKIE not set. Set to your ws_session_auth_hash cookie value.", file=sys.stderr)
        sys.exit(1)
        
    if not config.qbit_configured:
        print("QBIT related setup not found, setup env as soon as possible", file=sys.stderr)
        
    return config
