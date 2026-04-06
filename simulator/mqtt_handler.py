"""
MQTT 连接处理模块
"""
import json
import logging
from typing import Dict, Any, Callable, Optional
import paho.mqtt.client as mqtt
from config import get_mqtt_config
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
beijing_tz = pytz.timezone('Asia/Shanghai')


class MQTTHandler:
    """MQTT 连接管理器"""

    def __init__(
        self,
        dev_id: str,
        on_connect: Callable,
        on_disconnect: Callable,
        on_message: Callable
    ):
        """
        :param dev_id: 设备 ID
        :param on_connect: 连接成功回调
        :param on_disconnect: 断开连接回调
        :param on_message: 收到消息回调
        """
        self.dev_id = dev_id
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._on_message = on_message
        self._client: Optional[mqtt.Client] = None
        self._connected = False

        mqtt_config = get_mqtt_config()
        self._host = mqtt_config["host"]
        self._port = mqtt_config["port"]
        self._username = mqtt_config["username"]
        self._password = mqtt_config["password"]
        self._use_tls = mqtt_config["use_tls"]
        self._tls_insecure = mqtt_config["tls_insecure"]

        # 调试标记：跟踪 on_disconnect 调用来源
        self._cleanup_in_progress = False

    def connect(self) -> bool:
        """连接 MQTT Broker"""
        logger.debug(f"[{self.dev_id}] connect() 被调用")
        self._cleanup()

        try:
            # 使用固定客户端 ID，这样新连接会自动踢掉旧连接（EMQX 默认行为）
            client_id = self.dev_id
            logger.info(f"[{self.dev_id}] 使用客户端 ID: {client_id}")

            self._client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=client_id
            )

            # 设置日志回调
            self._client.on_log = self._on_log

            # 设置遗嘱消息
            will_topic = f"ess/bms/{self.dev_id}/will"
            will_payload = json.dumps({
                "devId": self.dev_id,
                "timestamp": datetime.now(beijing_tz).replace(microsecond=0).isoformat(),
                "reason": "unexpected disconnect"
            })
            self._client.will_set(will_topic, will_payload, qos=1, retain=False)

            # 设置回调
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message

            # 认证
            self._client.username_pw_set(self._username, self._password)

            # TLS 配置
            if self._use_tls:
                cert_reqs = mqtt.ssl.CERT_NONE if self._tls_insecure else mqtt.ssl.CERT_REQUIRED
                logger.debug(f"[{self.dev_id}] TLS 配置：cert_reqs={cert_reqs}")
                self._client.tls_set(
                    cert_reqs=cert_reqs,
                    tls_version=mqtt.ssl.PROTOCOL_TLSv1_2
                )

            logger.info(f"[{self.dev_id}] 正在连接 {self._host}:{self._port}")
            self._client.connect(self._host, self._port, 60)
            self._client.loop_start()
            logger.debug(f"[{self.dev_id}] loop_start() 已调用")
            return True
        except Exception as e:
            logger.error(f"[{self.dev_id}] 连接异常：{e}")
            return False

    def disconnect(self) -> None:
        """断开连接"""
        logger.info(f"[{self.dev_id}] disconnect() 被调用")
        self._cleanup()

    def publish(self, topic: str, payload: str, qos: int = 0) -> None:
        """发布消息"""
        if self._client:
            # 检查客户端是否Connected
            if not self._client.is_connected():
                logger.warning(f"[{self.dev_id}] 尝试发布消息但未连接")
            self._client.publish(topic, payload, qos=qos)

    def subscribe(self, topic: str, qos: int = 0) -> None:
        """订阅主题"""
        if self._client:
            self._client.subscribe(topic, qos=qos)

    @property
    def connected(self) -> bool:
        return self._connected

    @connected.setter
    def connected(self, value: bool):
        self._connected = value

    def _cleanup(self):
        """清理 MQTT 客户端"""
        logger.debug(f"[{self.dev_id}] _cleanup 被调用")
        if self._client:
            try:
                self._cleanup_in_progress = True
                self._client.loop_stop()
                self._client.disconnect()
            except Exception as e:
                logger.error(f"[{self.dev_id}] _cleanup 异常：{e}")
            finally:
                self._client = None
                self._cleanup_in_progress = False
        self._connected = False

    def _on_log(self, client, userdata, level, buf):
        """MQTT 库内部日志回调"""
        logger.debug(f"[{self.dev_id}] MQTT log: {buf}")
