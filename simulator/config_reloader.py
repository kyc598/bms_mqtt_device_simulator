"""
配置文件热加载模块
"""
import json
import copy
import logging
import threading
from typing import Dict, Any, List, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器，支持热加载"""

    def __init__(self, config_path: str = "devices.json"):
        self._config_path = config_path
        self._config: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._reload_callbacks: List[Callable] = []

    def load(self) -> List[Dict[str, Any]]:
        """加载配置"""
        with open(self._config_path, 'r', encoding='utf-8') as f:
            self._config = json.load(f)
        logger.info(f"从 {self._config_path} 加载配置：{len(self._config)} 个设备")
        return self._config

    def get_config(self) -> List[Dict[str, Any]]:
        """获取当前配置"""
        with self._lock:
            return copy.deepcopy(self._config)

    def register_reload_callback(self, callback: Callable):
        """注册配置重载回调"""
        self._reload_callbacks.append(callback)

    def reload(self) -> List[Dict[str, Any]]:
        """重新加载配置并通知回调"""
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                new_config = json.load(f)
            self._validate_config(new_config)

            with self._lock:
                old_config = copy.deepcopy(self._config)
                self._config = new_config

            # 通知回调
            for callback in self._reload_callbacks:
                callback(old_config, new_config)

            logger.info(f"配置热加载成功：{len(new_config)} 个设备")
            return new_config
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误：{e}，保持旧配置")
            raise
        except Exception as e:
            logger.error(f"配置加载失败：{e}，保持旧配置")
            raise

    def _validate_config(self, config: list):
        """验证配置格式"""
        for dev in config:
            if 'devId' not in dev:
                raise ValueError("设备配置缺少 devId")
            if 'number_of_cells' not in dev:
                raise ValueError("设备配置缺少 number_of_cells")


class ConfigReloader(FileSystemEventHandler):
    """配置文件监听器"""

    def __init__(self, config_manager: ConfigManager):
        self._config_manager = config_manager

    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent):
            if event.src_path.endswith('devices.json'):
                logger.info("检测到 devices.json 变化，重新加载...")
                try:
                    self._config_manager.reload()
                except Exception:
                    pass  # 错误已记录
