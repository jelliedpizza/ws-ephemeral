"""Cookie handling for Windscribe authentication.

Uses WS_SESSION_COOKIE environment variable for authentication.
"""

from httpx import Cookies

import config


def load_cookie() -> Cookies:
    """Load session cookie from WS_SESSION_COOKIE environment variable.

    Returns:
        Cookies: The cookie object with session auth and default cookies.
    """
    cookie = Cookies()
    cookie.set("i_can_has_cookie", "1", domain=".windscribe.com", path="/")
    cookie.set("ref", "https://windscribe.com/", domain=".windscribe.com", path="/")
    cookie.set("ws_session_auth_hash", config.WS_SESSION_COOKIE, domain=".windscribe.com", path="/")
    return cookie