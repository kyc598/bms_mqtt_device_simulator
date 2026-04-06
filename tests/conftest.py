"""
pytest 配置和 fixtures
"""
import pytest
import os


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """设置测试环境变量"""
    monkeypatch.setenv("MQTT_HOST", "test_host")
    monkeypatch.setenv("MQTT_PASSWORD", "test_password")
    monkeypatch.setenv("MQTT_PORT", "1883")
