from httpx import Cookies

from config import Config

def load_cookie(config: Config) -> Cookies:
    """Load session cookie from configuration."""
    cookie = Cookies()
    cookie.set("i_can_has_cookie", "1", domain=".windscribe.com", path="/")
    cookie.set("ref", "https://windscribe.com/", domain=".windscribe.com", path="/")
    cookie.set("ws_session_auth_hash", config.ws_session_cookie, domain=".windscribe.com", path="/")
    return cookie
