"""
配置加载模块
从环境变量加载配置，支持 .env 文件（python-dotenv）
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


class ConfigError(ValueError):
    """配置错误异常"""
    pass


def get_mqtt_config() -> Dict[str, Any]:
    """获取 MQTT 配置，验证必填项"""
    host = os.getenv("MQTT_HOST")
    password = os.getenv("MQTT_PASSWORD")

    # 验证必填项
    if not host:
        raise ConfigError("MQTT_HOST 环境变量未设置")
    if not password:
        raise ConfigError("MQTT_PASSWORD 环境变量未设置")

    use_tls = os.getenv("MQTT_USE_TLS", "true").lower() == "true"
    tls_insecure = os.getenv("MQTT_TLS_INSECURE", "false").lower() == "true"

    return {
        "host": host,
        "port": int(os.getenv("MQTT_PORT", "1883")),
        "username": os.getenv("MQTT_USERNAME", ""),
        "password": password,
        "use_tls": use_tls,
        "tls_insecure": tls_insecure,
        # TLS 禁用时证书相关参数设为 None
        "ca_certs": None if not use_tls else os.getenv("MQTT_CA_CERTS"),
        "certfile": None if not use_tls else os.getenv("MQTT_CERTFILE"),
        "keyfile": None if not use_tls else os.getenv("MQTT_KEYFILE"),
    }


def get_default_device_config() -> Dict[str, Any]:
    """获取默认设备配置"""
    return {
        "battery_type": os.getenv("DEFAULT_BATTERY_TYPE", "LI"),
        "heartbeat_interval": int(os.getenv("DEFAULT_HEARTBEAT_INTERVAL", "60")),
        "telemetry_interval": int(os.getenv("DEFAULT_TELEMETRY_INTERVAL", "15")),
        "status_interval": int(os.getenv("DEFAULT_STATUS_INTERVAL", "60")),
    }
