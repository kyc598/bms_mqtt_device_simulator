"""
BMS 设备模拟器模块
"""
import logging

# 配置根日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 导出主类
from simulator.device import DeviceSimulator

__all__ = ['DeviceSimulator']
