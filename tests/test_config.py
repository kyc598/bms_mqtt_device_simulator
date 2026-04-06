"""
配置模块测试
"""
import pytest
from config import get_mqtt_config, get_default_device_config, ConfigError


def test_get_mqtt_config_required_fields(monkeypatch):
    """测试必填字段验证"""
    monkeypatch.delenv("MQTT_HOST", raising=False)
    with pytest.raises(ConfigError, match="MQTT_HOST"):
        get_mqtt_config()


def test_get_mqtt_config_password_required(monkeypatch):
    """测试密码必填"""
    monkeypatch.setenv("MQTT_HOST", "test")
    monkeypatch.delenv("MQTT_PASSWORD", raising=False)
    with pytest.raises(ConfigError, match="MQTT_PASSWORD"):
        get_mqtt_config()


def test_get_mqtt_config_success(monkeypatch):
    """测试成功加载配置"""
    monkeypatch.setenv("MQTT_HOST", "test_host")
    monkeypatch.setenv("MQTT_PASSWORD", "test_pass")
    monkeypatch.setenv("MQTT_PORT", "1883")

    config = get_mqtt_config()
    assert config["host"] == "test_host"
    assert config["password"] == "test_pass"
    assert config["port"] == 1883


def test_get_default_device_config(monkeypatch):
    """测试默认设备配置"""
    config = get_default_device_config()
    assert config["battery_type"] == "LI"
    assert config["heartbeat_interval"] == 60
