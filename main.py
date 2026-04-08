"""
BMS MQTT 设备模拟器 - 主程序入口
支持配置热加载
"""
import json
import logging
import time
from typing import List, Dict

from config import get_mqtt_config, ConfigError
from simulator.device import DeviceSimulator
from simulator.config_reloader import ConfigManager, ConfigReloader
from watchdog.observers import Observer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_devices_from_config(file_path: str) -> List[Dict]:
    """从 JSON 文件加载设备配置列表"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    # 验证配置
    try:
        mqtt_cfg = get_mqtt_config()
        if not mqtt_cfg.get("password"):
            logger.error("MQTT_PASSWORD 未设置，请在 .env 文件中配置")
            return
    except ConfigError as e:
        logger.error(f"配置错误：{e}")
        return

    print("=" * 60)
    print("户用储能 BMS 模拟器 (四遥接口规范 v1.2)")
    print("=" * 60)

    # 生成实例 ID 用于追踪
    import uuid
    import os
    instance_id = uuid.uuid4().hex[:8]
    hostname = os.getenv("HOSTNAME", "local")
    logger.info(f"实例启动：hostname={hostname}, instance_id={instance_id}")

    # 配置管理器
    config_manager = ConfigManager("devices.json")
    simulators = []
    threads = []
    observer = None

    def on_config_reload(old_config, new_config):
        """配置重载回调"""
        logger.info(f"配置重载：{len(old_config)} -> {len(new_config)} 个设备")
        # 注：完整的设备动态添加/移除逻辑需要额外实现
        # 当前版本仅记录日志，设备列表保持不变

    config_manager.register_reload_callback(on_config_reload)

    # 初始加载
    try:
        devices_config = config_manager.load()
    except FileNotFoundError:
        logger.info("未找到 devices.json，使用默认配置")
        devices_config = [
            {
                "devId": "ESS12345678901203",
                "number_of_cells": 24,
                "number_of_temperature_sensors": 6,
                "rated_voltage": 72.0,
                "rated_capacity": 150,
                "battery_type": "LI"
            }
        ]
    except json.JSONDecodeError as e:
        logger.error(f"devices.json 格式错误：{e}，使用默认配置")

    # 启动设备
    for cfg in devices_config:
        sim = DeviceSimulator(cfg)
        simulators.append(sim)
        logger.info(f"启动设备 {cfg['devId']}...")
        if sim.connect():
            thread = sim.start()
            threads.append(thread)
        else:
            logger.error(f"设备 {cfg['devId']} 连接失败")

    # 启动配置监听
    try:
        observer = Observer()
        observer.schedule(ConfigReloader(config_manager), path=".", recursive=False)
        observer.start()
        logger.info("配置热加载监听已启动")
    except Exception as e:
        logger.warning(f"配置热加载启动失败：{e}")

    print("\n所有设备模拟器已启动，按 Ctrl+C 停止\n")

    import signal
    import sys

    def signal_handler(sig, frame):
        logger.info("收到中断信号，正在停止...")
        if observer:
            observer.stop()
        for sim in simulators:
            sim.disconnect()
        for t in threads:
            t.join(timeout=2)
            if t.is_alive():
                logger.warning(f"线程 {t.name} 未在 2 秒内退出")
        logger.info("模拟器已停止")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 主循环 - 等待所有设备线程
    while True:
        time.sleep(0.5)


if __name__ == "__main__":
    main()
