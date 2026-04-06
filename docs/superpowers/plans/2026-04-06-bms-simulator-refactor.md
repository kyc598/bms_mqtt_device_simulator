# BMS MQTT 设备模拟器重构实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 P0/P1/P2 三阶段重构 BMS 模拟器，改进安全性、代码质量和可维护性。

**Architecture:** P0 阶段将硬编码配置移至环境变量，强制 TLS 验证；P1 阶段拆分为模块化结构，添加 logging 和线程安全；P2 阶段添加配置热加载和运行指标。

**Tech Stack:** Python 3.x, paho-mqtt, pytz, python-dotenv, watchdog (P2), pytest (P1 测试)

---

## Chunk 1: P0 安全修复

### Task 1: 创建配置文件和依赖清单

**Files:**
- Create: `.env.example`
- Create: `.gitignore`
- Create: `requirements.txt`

- [ ] **Step 1: 创建 `.env.example` 配置模板**

```ini
# MQTT Broker 配置
MQTT_HOST=k5f33d11.ala.cn-hangzhou.emqxsl.cn
MQTT_PORT=8883
MQTT_USERNAME=mike
MQTT_PASSWORD=

# TLS 配置
MQTT_USE_TLS=true
# 调试模式可设为 true（不推荐生产环境）
MQTT_TLS_INSECURE=false

# 设备配置
DEFAULT_BATTERY_TYPE=LI
DEFAULT_HEARTBEAT_INTERVAL=60
DEFAULT_TELEMETRY_INTERVAL=15
DEFAULT_STATUS_INTERVAL=60
```

- [ ] **Step 2: 创建 `.gitignore`**

```gitignore
# 环境配置
.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 测试
.pytest_cache/
.coverage
htmlcov/
```

- [ ] **Step 3: 创建 `requirements.txt`**

```txt
# MQTT 客户端
paho-mqtt>=2.0.0

# 时区处理（用于日志时间戳）
pytz>=2024.1

# 环境变量配置
python-dotenv>=1.0.0

# P2 阶段：配置热加载（预留给未来）
# watchdog>=4.0.0
```

- [ ] **Step 4: 提交**

```bash
git add .env.example .gitignore requirements.txt
git commit -m "feat(p0): 添加配置模板和依赖清单"
```

---

### Task 2: 创建配置加载模块

**Files:**
- Create: `config.py`

- [ ] **Step 1: 编写 `config.py` 配置加载模块**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add config.py
git commit -m "feat(p0): 添加配置加载模块，支持环境变量和必填项验证"
```

---

### Task 3: 更新 `device_simulator.py` 使用配置模块

**Files:**
- Modify: `device_simulator.py`

- [ ] **Step 1: 修改导入语句（文件开头）**

```python
# 原代码：
# 全局 MQTT 配置（可修改或从配置文件加载）
# MQTT_CONFIG = { ... }

# 替换为：
from config import get_mqtt_config, get_default_device_config, ConfigError

# 全局 MQTT 配置（从环境变量加载）
MQTT_CONFIG = get_mqtt_config()
```

- [ ] **Step 2: 修改 `__init__` 方法，从配置模块读取默认间隔（行 73-75 附近）**

```python
# 原代码：
# self.heartbeat_interval = 60  # 默认心跳间隔（秒）
# self.telemetry_interval = 15  # 遥测上报间隔（秒）
# self.status_interval = 60     # 遥信上报间隔（秒）

# 替换为：
default_cfg = get_default_device_config()
self.heartbeat_interval = default_cfg["heartbeat_interval"]
self.telemetry_interval = default_cfg["telemetry_interval"]
self.status_interval = default_cfg["status_interval"]
self.battery_type_default = default_cfg["battery_type"]
```

- [ ] **Step 3: 修改 TLS 配置（行 153-157 附近）**

```python
# 原代码：
# if MQTT_CONFIG["use_tls"]:
#     self.client.tls_set(
#         cert_reqs=mqtt.ssl.CERT_NONE if MQTT_CONFIG["insecure"] else mqtt.ssl.CERT_REQUIRED,
#         tls_version=MQTT_CONFIG["tls_version"]
#     )

# 替换为：
if MQTT_CONFIG["use_tls"]:
    # 强制证书验证，除非明确启用不安全模式
    cert_reqs = mqtt.ssl.CERT_NONE if MQTT_CONFIG["tls_insecure"] else mqtt.ssl.CERT_REQUIRED
    self.client.tls_set(
        cert_reqs=cert_reqs,
        tls_version=mqtt.ssl.PROTOCOL_TLSv1_2
    )
```

- [ ] **Step 4: 修改 main 函数，添加配置验证（行 538-542 附近）**

```python
# 在 main() 函数开头添加：
def main():
    # 验证配置
    try:
        mqtt_cfg = get_mqtt_config()
        if not mqtt_cfg.get("password"):
            print("错误：MQTT_PASSWORD 未设置，请在 .env 文件中配置")
            return
    except ConfigError as e:
        print(f"配置错误：{e}")
        return
    
    print("=" * 60)
    print("户用储能 BMS 模拟器 (四遥接口规范 v1.2)")
    print("=" * 60)
```

- [ ] **Step 5: 提交**

```bash
git add device_simulator.py
git commit -m "refactor(p0): 使用配置模块替代硬编码，强制 TLS 证书验证"
```

---

### Task 4: 创建 `.env` 文件并验证 P0

**Files:**
- Create: `.env`

- [ ] **Step 1: 复制 `.env.example` 为 `.env`**

复制模板文件内容，确保 `MQTT_PASSWORD` 有值：

```ini
# MQTT Broker 配置
MQTT_HOST=k5f33d11.ala.cn-hangzhou.emqxsl.cn
MQTT_PORT=8883
MQTT_USERNAME=mike
MQTT_PASSWORD=Password123

# TLS 配置
MQTT_USE_TLS=true
MQTT_TLS_INSECURE=false

# 设备配置
DEFAULT_BATTERY_TYPE=LI
DEFAULT_HEARTBEAT_INTERVAL=60
DEFAULT_TELEMETRY_INTERVAL=15
DEFAULT_STATUS_INTERVAL=60
```

- [ ] **Step 2: 安装依赖**

```bash
pip install -r requirements.txt
```

- [ ] **Step 3: 运行程序验证**

```bash
python device_simulator.py
```

Expected: 程序启动，显示"MQTT 连接成功"（如果 Broker 可用）

- [ ] **Step 4: 测试配置验证**

```bash
# 临时重命名 .env
mv .env .env.bak
python device_simulator.py
```

Expected: 显示"配置错误：MQTT_PASSWORD 环境变量未设置"

```bash
# 恢复 .env
mv .env.bak .env
```

- [ ] **Step 5: 创建 P0 完成标签**

```bash
git tag v0.1.0-p0-security
git push origin v0.1.0-p0-security
```

---

## Chunk 2: P1 代码质量

### Task 5: 创建模块目录结构

**Files:**
- Create: `simulator/__init__.py`
- Create: `simulator/device.py`
- Create: `simulator/mqtt_handler.py`
- Create: `simulator/data_gen.py`
- Create: `simulator/handlers.py`

- [ ] **Step 1: 创建 `simulator/` 目录**

```bash
mkdir simulator
```

- [ ] **Step 2: 创建 `simulator/__init__.py`**

```python
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
```

- [ ] **Step 3: 提交**

```bash
git add simulator/__init__.py
git commit -m "refactor(p1): 创建模拟器模块目录结构"
```

---

### Task 6: 创建数据生成模块

**Files:**
- Create: `simulator/data_gen.py`

- [ ] **Step 1: 创建 `data_gen.py`（从 `device_simulator.py` 提取）**

```python
"""
遥测/遥信数据生成模块
纯函数，无外部依赖
"""
import random
from typing import Dict, Any


# 信号 ID 常量
SIGNAL = {
    # 遥测 (模拟量)
    "TOTAL_VOLTAGE": "01111001",
    "TOTAL_CURRENT": "01112001",
    "SOC": "01113001",
    "REMAIN_CAPACITY": "01115001",
    "CYCLE_COUNT": "01114001",
    "ENV_TEMP": "01120001",
    "POWER_TEMP": "01118001",
    "CELL_COUNT": "01116001",
    "CELL_VOLTAGE_PREFIX": "011170",
    "TEMP_SENSOR_COUNT": "01121001",
    "CELL_TEMP_PREFIX": "011190",
    "CELL_SOC_PREFIX": "011290",
    "BMS_MODE": "01122001",
    "BALANCE_FLAG": "01123001",
    "DISCHARGE_AH": "01124001",
    "CHARGE_AH": "01125001",

    # 遥信 (状态量、告警)
    "RUN_STATE": "TS001",
    "CHARGE_STATE": "TS002",
    "GRID_STATE": "TS003",
    "CONTACTOR_STATE": "TS004",
    "EMERGENCY_STOP": "TS005",
    "BALANCE_BITS": "TS006",
    "BMS_FAULT": "01002001",
    "BMS_WARNING": "01003001",
}


def generate_telemetry(
    config: Dict[str, Any],
    cycle_count: int,
    total_discharge_ah: int,
    total_charge_ah: int
) -> Dict[str, Any]:
    """
    生成遥测数据（模拟量）
    
    :param config: 设备配置
    :param cycle_count: 循环次数
    :param total_discharge_ah: 总放电量 (0.01Ah 单位)
    :param total_charge_ah: 总充电量 (0.01Ah 单位)
    :return: 信号 ID 到值的字典
    """
    cells = config["number_of_cells"]
    temp_sensors = config["number_of_temperature_sensors"]
    batt_type = config.get("battery_type", "LI")

    # 电压范围
    if batt_type == "LI":
        v_range = (3500, 4200)  # mV
        soc_range = (20, 95)
    else:
        v_range = (1200, 1400)  # 铅酸单格 mV
        soc_range = (10, 90)

    # 基础电压
    base_voltage = random.randint(*v_range)
    cell_voltages = []
    for i in range(cells):
        var = random.randint(-50, 50)
        v = max(v_range[0], min(v_range[1], base_voltage + var))
        cell_voltages.append(v)

    # 总电压 = 总 mV 转成 0.01V 单位
    total_voltage_mv = sum(cell_voltages)
    total_voltage_v100 = int(total_voltage_mv * 0.1)

    # 电流 (A×100)
    current_a100 = random.randint(-5000, 5000)

    # SOC
    base_soc = random.randint(*soc_range)
    soc_tenth = base_soc * 10

    # 剩余容量 (Ah×100)
    remain_cap_ah100 = int(config["rated_capacity"] * base_soc / 100 * 100)

    # 温度 (℃×10)
    env_temp_x10 = random.randint(150, 350)
    power_temp_x10 = random.randint(200, 400)
    cell_temps_x10 = [random.randint(150, 350) for _ in range(temp_sensors)]

    # 单体 SOC 模拟
    cell_socs = []
    for i in range(cells):
        var = random.randint(-50, 50)
        cell_soc = base_soc * 10 + var
        cell_soc = max(0, min(1000, cell_soc))
        cell_socs.append(cell_soc)

    # BMS 模式
    bms_mode = random.choice([0, 1, 2])
    balance_flag = random.choice([0, 1])

    # 构建 data 字典
    data = {
        SIGNAL["TOTAL_VOLTAGE"]: total_voltage_v100,
        SIGNAL["TOTAL_CURRENT"]: current_a100,
        SIGNAL["SOC"]: soc_tenth,
        SIGNAL["REMAIN_CAPACITY"]: remain_cap_ah100,
        SIGNAL["CYCLE_COUNT"]: cycle_count,
        SIGNAL["ENV_TEMP"]: env_temp_x10,
        SIGNAL["POWER_TEMP"]: power_temp_x10,
        SIGNAL["CELL_COUNT"]: cells,
        SIGNAL["TEMP_SENSOR_COUNT"]: temp_sensors,
        SIGNAL["BMS_MODE"]: bms_mode,
        SIGNAL["BALANCE_FLAG"]: balance_flag,
        SIGNAL["DISCHARGE_AH"]: total_discharge_ah,
        SIGNAL["CHARGE_AH"]: total_charge_ah,
    }

    # 单芯电压
    for idx, v in enumerate(cell_voltages, start=1):
        sig = f"{SIGNAL['CELL_VOLTAGE_PREFIX']}{idx:02d}"
        data[sig] = v

    # 单芯温度
    for idx, t in enumerate(cell_temps_x10, start=1):
        sig = f"{SIGNAL['CELL_TEMP_PREFIX']}{idx:02d}"
        data[sig] = t

    # 单芯 SOC
    for idx, soc in enumerate(cell_socs, start=1):
        sig = f"{SIGNAL['CELL_SOC_PREFIX']}{idx:02d}"
        data[sig] = soc

    return data


def generate_status(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成遥信数据（状态量、告警）
    
    :param config: 设备配置
    :return: 信号 ID 到值的字典
    """
    run_state = random.choice([1, 2, 3])
    charge_state = random.choice([0, 1, 2])
    grid_state = random.choice([0, 1])
    contactor_state = random.choice([0, 1])
    emergency_stop = random.choice([0, 1])
    balance_bits = random.randint(0, (1 << config["number_of_cells"]) - 1)

    bms_fault = random.choice([0, 0x01, 0x02, 0x04])
    bms_warning = random.choice([0, 0x01, 0x02, 0x04])

    data = {
        SIGNAL["RUN_STATE"]: run_state,
        SIGNAL["CHARGE_STATE"]: charge_state,
        SIGNAL["GRID_STATE"]: grid_state,
        SIGNAL["CONTACTOR_STATE"]: contactor_state,
        SIGNAL["EMERGENCY_STOP"]: emergency_stop,
        SIGNAL["BALANCE_BITS"]: balance_bits,
        SIGNAL["BMS_FAULT"]: bms_fault,
        SIGNAL["BMS_WARNING"]: bms_warning,
    }
    return data


def get_accumulator_updates():
    """
    生成累积量更新
    
    :return: (discharge_delta, charge_delta, cycle_delta)
    """
    discharge_delta = random.randint(0, 10) * 100
    charge_delta = random.randint(0, 5) * 100
    cycle_delta = 1 if random.random() < 0.01 else 0
    return discharge_delta, charge_delta, cycle_delta
```

- [ ] **Step 2: 提交**

```bash
git add simulator/data_gen.py
git commit -m "feat(p1): 提取数据生成模块为纯函数"
```

---

### Task 7: 创建消息处理模块

**Files:**
- Create: `simulator/handlers.py`

- [ ] **Step 1: 创建 `handlers.py`**

```python
"""
下行消息处理模块（遥控、遥调）
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
beijing_tz = pytz.timezone('Asia/Shanghai')


def get_timestamp() -> str:
    """返回 ISO8601 带时区时间戳"""
    return datetime.now(beijing_tz).replace(microsecond=0).isoformat()


def handle_remote_control(
    dev_id: str,
    payload: Dict[str, Any],
    client,
    parameters: Dict[str, Any]
) -> None:
    """
    处理遥控命令并发送响应
    
    :param dev_id: 设备 ID
    :param payload: 下行消息 payload
    :param client: MQTT 客户端
    :param parameters: 设备参数（用于扩展命令）
    """
    seq = payload.get("seqNo")
    data = payload.get("data", {})
    command = data.get("command")
    params = data.get("params", {})

    logger.info(f"[{dev_id}] 执行遥控命令：{command}, 参数：{params}")
    
    # 构造响应
    response = {
        "msgType": 401,
        "devId": dev_id,
        "timestamp": get_timestamp(),
        "data": {
            "result": 1,  # 假设成功
            "command": command,
            "execTime": get_timestamp()
        },
        "seqNo": seq
    }
    client.publish(f"ess/bms/{dev_id}/up", json.dumps(response), qos=1)


def handle_remote_adjust(
    dev_id: str,
    payload: Dict[str, Any],
    client,
    parameters: Dict[str, Any]
) -> None:
    """
    处理遥调参数下发并发送响应
    
    :param dev_id: 设备 ID
    :param payload: 下行消息 payload
    :param client: MQTT 客户端
    :param parameters: 设备参数字典（会被修改）
    """
    seq = payload.get("seqNo")
    data = payload.get("data", {})
    failed_params = []

    for param_id, value in data.items():
        if param_id in parameters or param_id.startswith("01308"):
            parameters[param_id] = value
            logger.info(f"[{dev_id}] 设置参数 {param_id} = {value}")
        else:
            failed_params.append(param_id)

    response = {
        "msgType": 501,
        "devId": dev_id,
        "timestamp": get_timestamp(),
        "data": {
            "result": 1 if not failed_params else 0,
            "failedParams": failed_params
        },
        "seqNo": seq
    }
    client.publish(f"ess/bms/{dev_id}/up", json.dumps(response), qos=1)


def handle_login_response(
    dev_id: str,
    payload: Dict[str, Any]
) -> Optional[int]:
    """
    处理登录响应
    
    :param dev_id: 设备 ID
    :param payload: 登录响应 payload
    :return: 心跳间隔（秒），登录失败返回 None
    """
    data = payload.get("data", {})
    if data.get("result") == 1:
        heartbeat_interval = data.get("heartbeatInterval", 60)
        logger.info(f"[{dev_id}] 登录成功，心跳间隔：{heartbeat_interval}s")
        return heartbeat_interval
    else:
        logger.warning(f"[{dev_id}] 登录失败，结果：{data.get('result')}")
        return None
```

- [ ] **Step 2: 提交**

```bash
git add simulator/handlers.py
git commit -m "feat(p1): 创建消息处理模块（遥控/遥调/登录响应）"
```

---

### Task 8: 创建 MQTT 处理模块

**Files:**
- Create: `simulator/mqtt_handler.py`

- [ ] **Step 1: 创建 `mqtt_handler.py`**

```python
"""
MQTT 连接处理模块
"""
import json
import logging
from typing import Dict, Any, Callable, Optional
import paho.mqtt.client as mqtt
from config import get_mqtt_config

logger = logging.getLogger(__name__)


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
    
    def connect(self) -> bool:
        """连接 MQTT Broker"""
        self._cleanup()
        
        try:
            client_id = self.dev_id
            self._client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=client_id
            )

            # 设置遗嘱消息
            will_topic = f"ess/bms/{self.dev_id}/will"
            from datetime import datetime
            import pytz
            beijing_tz = pytz.timezone('Asia/Shanghai')
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
                self._client.tls_set(
                    cert_reqs=cert_reqs,
                    tls_version=mqtt.ssl.PROTOCOL_TLSv1_2
                )

            self._client.connect(self._host, self._port, 60)
            self._client.loop_start()
            return True
        except Exception as e:
            logger.error(f"[{self.dev_id}] 连接异常：{e}")
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        self._cleanup()
    
    def publish(self, topic: str, payload: str, qos: int = 0) -> None:
        """发布消息"""
        if self._client:
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
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
        self._connected = False
```

- [ ] **Step 2: 提交**

```bash
git add simulator/mqtt_handler.py
git commit -m "feat(p1): 创建 MQTT 连接管理模块"
```

---

### Task 9: 重构 DeviceSimulator 类

**Files:**
- Create: `simulator/device.py`

- [ ] **Step 1: 创建 `device.py`（使用新模块重构）**

由于代码较长，分步创建。先写类定义和初始化：

```python
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
        self._connected = False
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
```

- [ ] **Step 2: 继续 `device.py` - 辅助方法**

```python
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
```

- [ ] **Step 3: 继续 `device.py` - MQTT 设置和回调**

```python
    def setup_mqtt(self):
        """初始化 MQTT 客户端并设置回调"""
        self._mqtt = MQTTHandler(
            dev_id=self.devId,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
            on_message=self._on_message
        )

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info(f"[{self.devId}] MQTT 连接成功")
            self.connected = True
            down_topic = f"ess/bms/{self.devId}/down"
            self._mqtt.subscribe(down_topic, qos=1)
            logger.info(f"[{self.devId}] 订阅下行主题：{down_topic}")
        else:
            logger.error(f"[{self.devId}] MQTT 连接失败，返回码：{rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        logger.info(f"[{self.devId}] MQTT 连接断开")
        self.connected = False
        self.logged_in = False

    def _on_message(self, client, userdata, msg):
        """处理下行消息"""
        try:
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
        heartbeat_interval = handle_login_response(self.devId, payload)
        if heartbeat_interval is not None:
            self.logged_in = True
            self.heartbeat_interval = heartbeat_interval
            self._login_sent_time = 0
        else:
            self._login_sent_time = 0
```

- [ ] **Step 4: 继续 `device.py` - 连接和发送方法**

```python
    def connect(self) -> bool:
        """连接 MQTT Broker"""
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
        payload = {
            "msgType": 100,
            "devId": self.devId,
            "timestamp": self._get_timestamp(),
            "data": {
                "authKey": "simulator_auth_key_1",
                "hwVersion": "V1.0",
                "fwVersion": "V1.2"
            },
            "seqNo": self._next_seqno()
        }
        self._mqtt.publish(f"ess/bms/{self.devId}/up", json.dumps(payload), qos=1)
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
```

- [ ] **Step 5: 继续 `device.py` - 主循环**

```python
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

            time.sleep(1)

        logger.info(f"[{self.devId}] 模拟线程结束")

    def start(self):
        """启动设备模拟（非阻塞）"""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread
```

- [ ] **Step 6: 提交**

```bash
git add simulator/device.py
git commit -m "feat(p1): 创建 DeviceSimulator 类，使用新模块重构"
```

---

### Task 10: 更新主程序入口

**Files:**
- Modify: `device_simulator.py`

- [ ] **Step 1: 重写 `device_simulator.py`（精简为主程序入口）**

```python
"""
BMS MQTT 设备模拟器 - 主程序入口
"""
import json
import logging
from typing import List

from config import get_mqtt_config, ConfigError
from simulator.device import DeviceSimulator

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

    # 加载设备配置
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

    try:
        devices_config = load_devices_from_config("devices.json")
        logger.info("从 devices.json 加载设备配置")
    except FileNotFoundError:
        logger.info("未找到 devices.json，使用默认配置")
    except json.JSONDecodeError as e:
        logger.error(f"devices.json 格式错误：{e}，使用默认配置")

    simulators = []
    threads = []

    for cfg in devices_config:
        sim = DeviceSimulator(cfg)
        simulators.append(sim)
        logger.info(f"启动设备 {cfg['devId']}...")
        if sim.connect():
            thread = sim.start()
            threads.append(thread)
        else:
            logger.error(f"设备 {cfg['devId']} 连接失败")

    print("\n所有设备模拟器已启动，按 Ctrl+C 停止\n")

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止所有模拟器...")
        for sim in simulators:
            sim.disconnect()
        for t in threads:
            t.join(timeout=5)
            if t.is_alive():
                logger.warning(f"线程 {t.name} 未在 5 秒内退出")
        logger.info("模拟器已停止")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 提交**

```bash
git add device_simulator.py
git commit -m "refactor(p1): 精简主程序入口，使用 simulator 模块"
```

---

### Task 11: 创建基础单元测试

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`
- Create: `tests/test_data_gen.py`
- Create: `tests/test_handlers.py`
- Create: `tests/conftest.py`
- Create: `pytest.ini`

- [ ] **Step 1: 创建测试目录结构**

```bash
mkdir tests
```

- [ ] **Step 2: 创建 `tests/__init__.py`**

```python
"""
测试模块
"""
```

- [ ] **Step 3: 创建 `tests/conftest.py`**

```python
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
```

- [ ] **Step 4: 创建 `tests/test_config.py`**

```python
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
```

- [ ] **Step 5: 创建 `tests/test_data_gen.py`**

```python
"""
数据生成模块测试
"""
from simulator.data_gen import (
    generate_telemetry,
    generate_status,
    get_accumulator_updates,
    SIGNAL
)


def test_generate_telemetry_returns_dict():
    """测试遥测数据返回字典"""
    config = {
        "number_of_cells": 16,
        "number_of_temperature_sensors": 8,
        "rated_voltage": 48.0,
        "rated_capacity": 100,
        "battery_type": "LI"
    }
    data = generate_telemetry(config, 0, 0, 0)
    assert isinstance(data, dict)
    assert SIGNAL["TOTAL_VOLTAGE"] in data
    assert SIGNAL["SOC"] in data


def test_generate_telemetry_cell_voltages():
    """测试单体电压生成"""
    config = {
        "number_of_cells": 8,
        "number_of_temperature_sensors": 4,
        "rated_voltage": 24.0,
        "rated_capacity": 50,
        "battery_type": "LI"
    }
    data = generate_telemetry(config, 0, 0, 0)
    # 检查 8 个单体电压信号
    for i in range(1, 9):
        sig = f"{SIGNAL['CELL_VOLTAGE_PREFIX']}{i:02d}"
        assert sig in data
        assert 3500 <= data[sig] <= 4200  # mV 范围


def test_generate_status_returns_dict():
    """测试遥信数据返回字典"""
    config = {
        "number_of_cells": 16,
    }
    data = generate_status(config)
    assert isinstance(data, dict)
    assert SIGNAL["RUN_STATE"] in data
    assert SIGNAL["BMS_FAULT"] in data


def test_get_accumulator_updates():
    """测试累积量更新"""
    discharge, charge, cycle = get_accumulator_updates()
    assert discharge >= 0
    assert charge >= 0
    assert cycle in [0, 1]
```

- [ ] **Step 6: 创建 `tests/test_handlers.py`**

```python
"""
消息处理模块测试
"""
import json
from unittest.mock import MagicMock
from simulator.handlers import (
    handle_remote_control,
    handle_remote_adjust,
    handle_login_response
)


def test_handle_login_response_success():
    """测试登录响应处理（成功）"""
    payload = {
        "data": {"result": 1, "heartbeatInterval": 60}
    }
    interval = handle_login_response("TEST001", payload)
    assert interval == 60


def test_handle_login_response_failure():
    """测试登录响应处理（失败）"""
    payload = {
        "data": {"result": 0}
    }
    interval = handle_login_response("TEST001", payload)
    assert interval is None


def test_handle_remote_adjust_success():
    """测试遥调处理（成功）"""
    payload = {
        "seqNo": "000001",
        "data": {"01308002": 4000}
    }
    parameters = {}
    client = MagicMock()
    
    handle_remote_adjust("TEST001", payload, client, parameters)
    
    assert parameters["01308002"] == 4000
    client.publish.assert_called_once()
    
    # 验证响应
    call_args = client.publish.call_args
    response = json.loads(call_args[0][1])
    assert response["msgType"] == 501
    assert response["data"]["result"] == 1


def test_handle_remote_adjust_unknown_param():
    """测试遥调处理（未知参数）"""
    payload = {
        "seqNo": "000001",
        "data": {"UNKNOWN_PARAM": 999}
    }
    parameters = {}
    client = MagicMock()
    
    handle_remote_adjust("TEST001", payload, client, parameters)
    
    # 未知参数应该被拒绝
    call_args = client.publish.call_args
    response = json.loads(call_args[0][1])
    assert response["data"]["result"] == 0
    assert "UNKNOWN_PARAM" in response["data"]["failedParams"]
```

- [ ] **Step 7: 创建 `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

- [ ] **Step 8: 安装 pytest 并运行测试**

```bash
pip install pytest
pytest tests/ -v
```

Expected: 所有测试通过

- [ ] **Step 9: 提交**

```bash
git add tests/ pytest.ini
git commit -m "test(p1): 添加基础单元测试（配置/数据生成/消息处理）"
```

---

### Task 12: P1 完成标记

- [ ] **Step 1: 创建 P1 完成标签**

```bash
git tag v0.2.0-p1-quality
git push origin v0.2.0-p1-quality
```

---

## Chunk 3: P2 可维护性

### Task 13: 添加配置热加载

**Files:**
- Modify: `device_simulator.py`
- Create: `simulator/config_reloader.py`
- Modify: `requirements.txt`

- [ ] **Step 1: 更新 `requirements.txt` 添加 watchdog**

```txt
# MQTT 客户端
paho-mqtt>=2.0.0

# 时区处理
pytz>=2024.1

# 环境变量配置
python-dotenv>=1.0.0

# P2 配置热加载
watchdog>=4.0.0

# 测试
pytest>=8.0.0
```

- [ ] **Step 2: 创建 `simulator/config_reloader.py`**

```python
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
```

- [ ] **Step 3: 提交**

```bash
git add simulator/config_reloader.py requirements.txt
git commit -m "feat(p2): 添加配置热加载模块"
```

---

### Task 14: 更新主程序支持热加载

**Files:**
- Modify: `device_simulator.py`

- [ ] **Step 1: 修改 `device_simulator.py` 添加热加载支持**

在导入部分添加：

```python
from simulator.config_reloader import ConfigManager, ConfigReloader
from watchdog.observers import Observer
```

修改 main 函数中的设备启动逻辑：

```python
def main():
    # ... 配置验证代码 ...
    
    # 配置管理器
    config_manager = ConfigManager("devices.json")
    simulators = []
    threads = []
    
    def on_config_reload(old_config, new_config):
        """配置重载回调"""
        logger.info("配置重载回调被调用")
        # TODO: 实现设备动态添加/移除逻辑
    
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
    observer = Observer()
    observer.schedule(ConfigReloader(config_manager), path=".", recursive=False)
    observer.start()
    logger.info("配置热加载监听已启动")
    
    print("\n所有设备模拟器已启动，按 Ctrl+C 停止\n")
    
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止...")
        observer.stop()
        observer.join()
        for sim in simulators:
            sim.disconnect()
        for t in threads:
            t.join(timeout=5)
        logger.info("模拟器已停止")
```

- [ ] **Step 2: 提交**

```bash
git add device_simulator.py
git commit -m "feat(p2): 主程序集成配置热加载"
```

---

### Task 15: 创建 README 文档

**Files:**
- Create: `README.md`

- [ ] **Step 1: 创建 `README.md`**

```markdown
# BMS MQTT 设备模拟器

户用储能 BMS（电池管理系统）设备模拟器，用于模拟 BMS 设备通过 MQTT 协议与云端平台进行"四遥"（遥测、遥信、遥控、遥调）数据交互。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并填写必要配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少设置 `MQTT_PASSWORD`：

```ini
MQTT_HOST=k5f33d11.ala.cn-hangzhou.emqxsl.cn
MQTT_PORT=8883
MQTT_USERNAME=mike
MQTT_PASSWORD=your_password_here
```

### 3. 配置设备

编辑 `devices.json` 添加设备：

```json
[
  {
    "devId": "ESS12345678901201",
    "number_of_cells": 16,
    "number_of_temperature_sensors": 8,
    "rated_voltage": 48.0,
    "rated_capacity": 100,
    "battery_type": "LI"
  }
]
```

### 4. 运行

```bash
python device_simulator.py
```

## 配置说明

### 环境变量

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| MQTT_HOST | 是 | - | MQTT Broker 地址 |
| MQTT_PORT | 否 | 1883 | MQTT Broker 端口 |
| MQTT_USERNAME | 否 | - | 用户名 |
| MQTT_PASSWORD | 是 | - | 密码 |
| MQTT_USE_TLS | 否 | true | 是否启用 TLS |
| MQTT_TLS_INSECURE | 否 | false | 跳过证书验证（调试用） |

### 设备配置

| 字段 | 类型 | 说明 |
|------|------|------|
| devId | string | 16 位设备 ID |
| number_of_cells | int | 电芯数量 |
| number_of_temperature_sensors | int | 温度传感器数量 |
| rated_voltage | float | 额定电压 (V) |
| rated_capacity | float | 额定容量 (Ah) |
| battery_type | string | 电池类型：LI(锂电) 或 PB(铅酸) |

## 运行测试

```bash
pytest tests/ -v
```

## 协议说明

详见 [docs/protocol.md](docs/protocol.md)

## 版本

- v0.1.0 (P0): 安全修复 - 环境变量配置，TLS 强制验证
- v0.2.0 (P1): 代码质量 - 模块化重构，logging，单元测试
- v0.3.0 (P2): 可维护性 - 配置热加载，运行指标
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs(p2): 添加 README 文档"
```

---

### Task 16: 创建协议文档

**Files:**
- Create: `docs/protocol.md`

- [ ] **Step 1: 创建 `docs/protocol.md`**

```markdown
# 四遥接口协议规范

## 概述

本协议定义 BMS 设备与云端平台之间的 MQTT 通信接口。

## 主题命名

- 上行：`ess/bms/{devId}/up`
- 下行：`ess/bms/{devId}/down`
- 遗嘱：`ess/bms/{devId}/will`

## 消息格式

所有消息为 JSON 格式，包含以下字段：

```json
{
  "msgType": 100,
  "devId": "ESS12345678901201",
  "timestamp": "2024-01-01T12:00:00+08:00",
  "data": { ... },
  "seqNo": "000001"
}
```

## 消息类型

### 登录 (100/101)

**请求 (上行)**
```json
{
  "msgType": 100,
  "devId": "ESS12345678901201",
  "timestamp": "2024-01-01T12:00:00+08:00",
  "data": {
    "authKey": "signature",
    "hwVersion": "V1.0",
    "fwVersion": "V1.2"
  },
  "seqNo": "000001"
}
```

**响应 (下行)**
```json
{
  "msgType": 101,
  "devId": "ESS12345678901201",
  "timestamp": "2024-01-01T12:00:01+08:00",
  "data": {
    "result": 1,
    "heartbeatInterval": 60
  },
  "seqNo": "000001"
}
```

### 心跳 (200)

**请求 (上行)**
```json
{
  "msgType": 200,
  "devId": "ESS12345678901201",
  "timestamp": "2024-01-01T12:01:00+08:00",
  "data": {},
  "seqNo": "000002"
}
```

### 遥测 (300)

**上报 (上行)**

模拟量数据：电压、电流、SOC、温度等。

```json
{
  "msgType": 300,
  "devId": "ESS12345678901201",
  "timestamp": "2024-01-01T12:01:15+08:00",
  "data": {
    "01111001": 7200,    // 总电压 72.00V (×100)
    "01112001": 1500,    // 电流 15.00A (×100)
    "01113001": 850,     // SOC 85.0% (×10)
    "01117001": 3700,    // 单体 1 电压 3.700V
    "01117002": 3710     // 单体 2 电压 3.710V
  },
  "seqNo": "000003"
}
```

### 遥信 (310)

**上报 (上行)**

状态量、告警数据。

```json
{
  "msgType": 310,
  "devId": "ESS12345678901201",
  "timestamp": "2024-01-01T12:01:00+08:00",
  "data": {
    "TS001": 1,          // 运行状态：1-运行
    "TS002": 2,          // 充电状态：2-恒压
    "01002001": 0,       // 故障码：无故障
    "01003001": 0        // 告警码：无告警
  },
  "seqNo": "000004"
}
```

### 遥控 (400/401)

**命令 (下行)**
```json
{
  "msgType": 400,
  "devId": "ESS12345678901201",
  "timestamp": "2024-01-01T12:02:00+08:00",
  "data": {
    "command": "breaker_close",
    "params": {}
  },
  "seqNo": "000005"
}
```

**响应 (上行)**
```json
{
  "msgType": 401,
  "devId": "ESS12345678901201",
  "timestamp": "2024-01-01T12:02:01+08:00",
  "data": {
    "result": 1,
    "command": "breaker_close",
    "execTime": "2024-01-01T12:02:01+08:00"
  },
  "seqNo": "000005"
}
```

### 遥调 (500/501)

**命令 (下行)**
```json
{
  "msgType": 500,
  "devId": "ESS12345678901201",
  "timestamp": "2024-01-01T12:03:00+08:00",
  "data": {
    "01308002": 4000,    // 单体过压阈值 4000mV
    "01308003": 2800     // 单体欠压阈值 2800mV
  },
  "seqNo": "000006"
}
```

**响应 (上行)**
```json
{
  "msgType": 501,
  "devId": "ESS12345678901201",
  "timestamp": "2024-01-01T12:03:01+08:00",
  "data": {
    "result": 1,
    "failedParams": []
  },
  "seqNo": "000006"
}
```

## 信号 ID 规范

### 遥测信号

| 信号 ID | 名称 | 单位 | 缩放 |
|--------|------|------|------|
| 01111001 | 总电压 | V | ×100 |
| 01112001 | 总电流 | A | ×100 |
| 01113001 | SOC | % | ×10 |
| 01115001 | 剩余容量 | Ah | ×100 |
| 01114001 | 循环次数 | - | - |
| 011170XX | 单体电压 | mV | - |
| 011190XX | 单体温度 | ℃ | ×10 |
| 011290XX | 单体 SOC | 0.1% | - |

### 遥信信号

| 信号 ID | 名称 | 说明 |
|--------|------|------|
| TS001 | 运行状态 | 1-运行，2-待机，3-故障 |
| TS002 | 充电状态 | 0-停止，1-恒流，2-恒压 |
| 01002001 | 故障码 | 位图 |
| 01003001 | 告警码 | 位图 |

## 错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 失败 |
| 1 | 成功 |
```

- [ ] **Step 2: 提交**

```bash
git add docs/protocol.md
git commit -m "docs(p2): 添加四遥协议文档"
```

---

### Task 17: P2 完成标记

- [ ] **Step 1: 创建 P2 完成标签**

```bash
git tag v0.3.0-p2-maintainability
git push origin v0.3.0-p2-maintainability
```

- [ ] **Step 2: 验证所有测试通过**

```bash
pytest tests/ -v
```

---

## 验收检查清单

### P0 验收

- [ ] `.env.example` 存在
- [ ] `requirements.txt` 存在
- [ ] `.gitignore` 排除 `.env`
- [ ] `config.py` 有必填项验证
- [ ] `device_simulator.py` 从 config 读取配置
- [ ] TLS 默认强制证书验证
- [ ] 运行 `python device_simulator.py` 正常启动
- [ ] 未设置密码时显示明确错误

### P1 验收

- [ ] `simulator/` 目录包含 5 个模块文件
- [ ] 无 `print()` 语句
- [ ] 共享状态有锁保护
- [ ] `pytest tests/ -v` 全部通过

### P2 验收

- [ ] `README.md` 存在
- [ ] `docs/protocol.md` 存在
- [ ] 修改 `devices.json` 触发重新加载
- [ ] `watchdog` 在 `requirements.txt` 中
