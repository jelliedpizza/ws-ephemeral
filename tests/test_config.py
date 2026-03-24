import os
import pytest
from config import Config, load_config

def test_config_defaults(monkeypatch):
    """Test that Config uses reasonable defaults when env vars are empty."""
    monkeypatch.setenv("QBIT_HOST", "127.0.0.1")
    monkeypatch.setenv("ONESHOT", "false")
    
    config = Config()
    
    assert config.qbit_host == "127.0.0.1"
    assert config.oneshot is False
    assert config.qbit_configured is False
    assert config.days == 6
    assert config.time == "02:00"

def test_config_oneshot(monkeypatch):
    """Test boolean parsing of environment variables."""
    monkeypatch.setenv("ONESHOT", "true")
    monkeypatch.setenv("QBIT_PRIVATE_TRACKER", "True")
    
    config = Config()
    assert config.oneshot is True
    assert config.qbit_private_tracker is True

def test_qbit_configured(monkeypatch):
    monkeypatch.setenv("QBIT_USERNAME", "admin")
    monkeypatch.setenv("QBIT_PASSWORD", "secret")
    
    config = Config()
    assert config.qbit_configured is True
