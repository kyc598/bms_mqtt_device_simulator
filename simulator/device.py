"""
BMS 设备模拟器主类
"""
import json
import time
import random
import threading
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import pytz

from config import get_default_device_config
from simulator.mqtt_handler import MQTTHandler
from simulator.data_gen import (
    generate_telemetry,
    generate_status,
    get_accumulator_updates,
    SIGNAL
)
from simulator.handlers import (
    handle_login_response,
    handle_remote_control,
    handle_remote_adjust,
    get_timestamp
)

logger = logging.getLogger(__name__)
beijing_tz = pytz.timezone('Asia/Shanghai')


class DeviceSimulator:
    """单个 BMS 设备模拟器"""

    def __init__(self, config: Dict[str, Any]):
        """
        :param config: 设备配置
        """
        self.devId = config["devId"]
        self.config = config
        self.running = False
        self._logged_in = False
        self._seqno = 0
        self._lock = threading.Lock()  # 线程安全锁

        # 间隔配置
        default_cfg = get_default_device_config()
        self.heartbeat_interval = default_cfg["heartbeat_interval"]
        self.telemetry_interval = default_cfg["telemetry_interval"]
        self.status_interval = default_cfg["status_interval"]

        self._last_telemetry_time = 0
        self._last_heartbeat_time = 0
        self._last_status_time = 0

        # MQTT 客户端
        self._mqtt: Optional[MQTTHandler] = None

        # 本地存储的参数
        self._parameters: Dict[str, Any] = {
            "01308002": 3650,
            "01308003": 2800,
            "01308004": 20,
            "01308008": 450,
            "01308009": 0,
            "01308010": 550,
            "01308011": -100,
        }

        # 模拟数据累积值
        self._total_discharge_ah = random.randint(0, 10000) * 100
        self._total_charge_ah = random.randint(0, 5000) * 100
        self._cycle_count = random.randint(0, 100)

        # 线程事件
        self._stop_event = threading.Event()

        # 登录重试相关
        self._last_login_attempt = 0
        self._login_retry_interval = 30
        self._login_sent_time = 0
        self._login_timeout = 10

    def _get_timestamp(self) -> str:
        """返回 ISO8601 带时区时间戳"""
        return datetime.now(beijing_tz).replace(microsecond=0).isoformat()

    def _next_seqno(self) -> str:
        """生成递增的序列号"""
        with self._lock:
            self._seqno += 1
            return f"{self._seqno:06d}"

    @property
    def connected(self) -> bool:
        return self._mqtt.connected if self._mqtt else False

    @connected.setter
    def connected(self, value: bool):
        if self._mqtt:
            self._mqtt.connected = value

    @property
    def logged_in(self) -> bool:
        with self._lock:
            return self._logged_in

    @logged_in.setter
    def logged_in(self, value: bool):
        with self._lock:
            self._logged_in = value

    def setup_mqtt(self):
        """初始化 MQTT 客户端并设置回调"""
        self._mqtt = MQTTHandler(
            dev_id=self.devId,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
            on_message=self._on_message
        )

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        # rc=0 连接成功，其他值表示失败
        # flags: 包含 session present 等信息
        rc_value = rc if isinstance(rc, int) else getattr(rc, 'value', rc)
        logger.info(f"[{self.devId}] MQTT 连接回调，rc={rc_value}, flags={flags}")
        if rc_value == 0:
            logger.info(f"[{self.devId}] MQTT 连接成功")
            self.connected = True
            # 短暂延迟后再订阅，避免服务器立即断开
            time.sleep(0.1)
            if self._mqtt and self._mqtt.connected:
                down_topic = f"ess/bms/{self.devId}/down"
                logger.info(f"[{self.devId}] 正在订阅：{down_topic}")
                self._mqtt.subscribe(down_topic, qos=1)
                logger.info(f"[{self.devId}] 已订阅下行主题：{down_topic}")
            else:
                logger.warning(f"[{self.devId}] 订阅前检查发现已断开，跳过订阅")
        else:
            logger.error(f"[{self.devId}] MQTT 连接失败，返回码：{rc_value}")
            self.connected = False

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        # rc 参数说明：
        # 0 = 正常断开（客户端主动调用 disconnect()）
        # 1 = 连接被拒绝（认证失败等）
        # 2-16 = 各种错误码
        # paho-mqtt 2.x 中，rc 可能是一个 ReasonCodes 对象
        rc_value = rc if isinstance(rc, int) else getattr(rc, 'value', rc)
        logger.info(f"[{self.devId}] MQTT 连接断开，rc={rc_value}, flags={flags}")
        self.connected = False
        self.logged_in = False

    def _on_message(self, client, userdata, msg):
        """处理下行消息"""
        try:
            logger.info(f"[{self.devId}] 收到下行消息：topic={msg.topic}, payload={msg.payload.decode('utf-8')}")
            payload = json.loads(msg.payload.decode('utf-8'))
            msg_type = payload.get("msgType")
            logger.debug(f"[{self.devId}] 收到下行消息 type={msg_type}")

            if msg_type == 101:
                self._handle_login_response(payload)
            elif msg_type == 400:
                handle_remote_control(self.devId, payload, self._mqtt, self._parameters)
            elif msg_type == 500:
                handle_remote_adjust(self.devId, payload, self._mqtt, self._parameters)
        except Exception as e:
            logger.error(f"[{self.devId}] 处理下行消息异常：{e}")

    def _handle_login_response(self, payload):
        """处理登录响应"""
        # 如果已经登录成功，忽略重复的登录响应
        if self._logged_in:
            logger.debug(f"[{self.devId}] 忽略重复的登录响应")
            return
        heartbeat_interval = handle_login_response(self.devId, payload)
        if heartbeat_interval is not None:
            self.logged_in = True
            self.heartbeat_interval = heartbeat_interval
            self._login_sent_time = 0
        else:
            self._login_sent_time = 0

    def connect(self) -> bool:
        """连接 MQTT Broker"""
        # 避免重复连接
        if self._mqtt is not None:
            logger.debug(f"[{self.devId}] 已存在 MQTT 客户端，跳过连接")
            return True
        self.setup_mqtt()
        return self._mqtt.connect()

    def disconnect(self):
        """断开连接，停止线程"""
        self.running = False
        self._stop_event.set()
        if self._mqtt:
            self._mqtt.disconnect()
        logger.info(f"[{self.devId}] 已断开")

    def send_login(self):
        """发送登录请求"""
        # 为每个设备生成唯一的 authKey（实际项目中应使用动态签名）
        import hashlib
        auth_key = hashlib.md5(f"simulator_{self.devId}_{time.time()}".encode()).hexdigest()[:16]

        payload = {
            "msgType": 100,
            "devId": self.devId,
            "timestamp": self._get_timestamp(),
            "data": {
                "authKey": auth_key,
                "hwVersion": "V1.0",
                "fwVersion": "V1.2"
            },
            "seqNo": self._next_seqno()
        }
        topic = f"ess/bms/{self.devId}/up"
        logger.info(f"[{self.devId}] 发送登录请求到 topic={topic}")
        self._mqtt.publish(topic, json.dumps(payload), qos=1)
        self._login_sent_time = time.time()
        logger.info(f"[{self.devId}] 发送登录请求")

    def send_heartbeat(self):
        """发送心跳"""
        if not self.logged_in:
            return
        payload = {
            "msgType": 200,
            "devId": self.devId,
            "timestamp": self._get_timestamp(),
            "data": {},
            "seqNo": self._next_seqno()
        }
        self._mqtt.publish(f"ess/bms/{self.devId}/up", json.dumps(payload), qos=0)
        logger.debug(f"[{self.devId}] 发送心跳")

    def send_telemetry(self):
        """发送遥测数据"""
        if not self.logged_in:
            return
        with self._lock:
            data = generate_telemetry(
                self.config,
                self._cycle_count,
                self._total_discharge_ah,
                self._total_charge_ah
            )
            # 累积量更新
            discharge_delta, charge_delta, cycle_delta = get_accumulator_updates()
            self._total_discharge_ah += discharge_delta
            self._total_charge_ah += charge_delta
            self._cycle_count += cycle_delta

        payload = {
            "msgType": 300,
            "devId": self.devId,
            "timestamp": self._get_timestamp(),
            "data": data,
            "seqNo": self._next_seqno()
        }
        self._mqtt.publish(f"ess/bms/{self.devId}/up", json.dumps(payload), qos=1)
        total_v = data.get(SIGNAL["TOTAL_VOLTAGE"], 0) / 100
        soc = data.get(SIGNAL["SOC"], 0) / 10
        logger.info(f"[{self.devId}] 发送遥测 (300): 总电压={total_v:.2f}V, SOC={soc:.1f}%")

    def send_status(self):
        """发送遥信数据"""
        if not self.logged_in:
            return
        data = generate_status(self.config)
        payload = {
            "msgType": 310,
            "devId": self.devId,
            "timestamp": self._get_timestamp(),
            "data": data,
            "seqNo": self._next_seqno()
        }
        self._mqtt.publish(f"ess/bms/{self.devId}/up", json.dumps(payload), qos=1)
        run_state = data.get(SIGNAL["RUN_STATE"], 0)
        fault = data.get(SIGNAL["BMS_FAULT"], 0)
        logger.info(f"[{self.devId}] 发送遥信 (310): 运行状态={run_state}, 故障码={fault:#04x}")

    def run(self):
        """设备主循环"""
        self.running = True
        self._last_heartbeat_time = time.time()
        self._last_telemetry_time = time.time()
        self._last_status_time = time.time()

        while self.running and not self._stop_event.is_set():
            now = time.time()

            # 发送登录请求（重试机制）
            if self.connected and not self.logged_in:
                if self._login_sent_time > 0 and now - self._login_sent_time > self._login_timeout:
                    logger.warning(f"[{self.devId}] 登录响应超时，将重新尝试")
                    self._login_sent_time = 0
                if now - self._last_login_attempt >= self._login_retry_interval:
                    self.send_login()
                    self._last_login_attempt = now

            # 心跳发送
            if self.logged_in and now - self._last_heartbeat_time >= self.heartbeat_interval:
                self.send_heartbeat()
                self._last_heartbeat_time = now

            # 遥测发送
            if self.logged_in and now - self._last_telemetry_time >= self.telemetry_interval:
                self.send_telemetry()
                self._last_telemetry_time = now

            # 遥信发送
            if self.logged_in and now - self._last_status_time >= self.status_interval:
                self.send_status()
                self._last_status_time = now

            # 检查连接状态
            if not self.connected and self.running:
                logger.info(f"[{self.devId}] 连接断开，尝试重连...")
                self.connect()
                time.sleep(5)

            # 使用短睡眠 + 事件等待，加快退出响应
            self._stop_event.wait(timeout=0.1)

        logger.info(f"[{self.devId}] 模拟线程结束")

    def start(self):
        """启动设备模拟（非阻塞）"""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread
