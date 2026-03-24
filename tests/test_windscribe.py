from unittest.mock import AsyncMock, patch
import pytest

from clients.windscribe import Windscribe
from config import Config


@pytest.fixture
def mock_config():
    config = Config()
    config.ws_session_cookie = "fake-cookie-xyz"
    return config


@pytest.mark.asyncio
async def test_windscribe_init(mock_config):
    ws = Windscribe(mock_config)
    assert not ws.is_authenticated
    assert ws.csrf is None


@pytest.mark.asyncio
async def test_windscribe_connect_failure(mock_config):
    ws = Windscribe(mock_config)
    
    # Mock validation failure
    ws._validate_session = AsyncMock(return_value=False)
    
    connected = await ws.connect()
    assert connected is False
    assert ws.csrf is None
    assert ws.is_authenticated is False


@pytest.mark.asyncio
async def test_windscribe_connect_success(mock_config):
    ws = Windscribe(mock_config)
    
    ws._validate_session = AsyncMock(return_value=True)
    ws.get_csrf = AsyncMock(return_value={"csrf_time": 12345, "csrf_token": "abc"})
    
    connected = await ws.connect()
    assert connected is True
    assert ws.is_authenticated is True
    assert ws.csrf["csrf_time"] == 12345
    assert ws.csrf["csrf_token"] == "abc"
