# BMS MQTT 设备模拟器重构设计

**日期**: 2026-04-06  
**状态**: 已批准

---

## 概述

本项目是一个 BMS（电池管理系统）设备模拟器，用于模拟 BMS 设备通过 MQTT 协议与云端平台进行"四遥"（遥测、遥信、遥控、遥调）数据交互。

本次重构目标：按优先级分阶段改进安全性、代码质量和可维护性。

---

## P0 阶段：安全修复

### 目标

1. 移除硬编码凭证
2. 强制 TLS 证书验证
3. 添加依赖管理

### 文件结构

```
bms_mqtt_device_simulator/
├── .env.example          # 新增：配置模板
├── .env                  # 新增：实际配置（不提交）
├── .gitignore            # 更新：排除 .env
├── requirements.txt      # 新增：依赖清单
├── config.py             # 新增：配置加载模块
├── device_simulator.py   # 更新：使用 config 模块
└── devices.json          # 不变
```

### .env.example

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

### config.py

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

### device_simulator.py 改动

- 移除 `MQTT_CONFIG` 常量，改用 `from config import get_mqtt_config`
- TLS 配置：`cert_reqs=mqtt.ssl.CERT_REQUIRED`（除非 `MQTT_TLS_INSECURE=true`）
- 从配置模块读取默认间隔参数

### requirements.txt

```
# MQTT 客户端
paho-mqtt>=2.0.0

# 时区处理（用于日志时间戳）
pytz>=2024.1

# 环境变量配置
python-dotenv>=1.0.0

# P2 阶段：配置热加载
watchdog>=4.0.0
```

**依赖说明：**
- `pytz`：用于日志时间戳的时区处理（Asia/Shanghai）
- `watchdog`：P2 阶段用于配置文件热加载

---

## P1 阶段：代码质量

### 目标

1. 模块拆分，提高可维护性
2. 使用 logging 替换 print
3. 添加线程安全保护
4. 完善异常处理
5. 添加基础单元测试

### 文件结构与模块依赖

```
bms_mqtt_device_simulator/
├── config.py               # 无依赖，被所有模块引用
├── device_simulator.py     # 依赖 simulator/* 模块，主循环协调
├── devices.json
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── simulator/
│   ├── __init__.py         # 导出 DeviceSimulator，配置 logging
│   ├── device.py           # 依赖：mqtt_handler, data_gen, handlers
│   ├── mqtt_handler.py     # 依赖：config (仅)
│   ├── data_gen.py         # 无外部依赖 (纯函数)
│   └── handlers.py         # 依赖：data_gen (部分)
└── tests/
    ├── __init__.py
    ├── test_data_gen.py    # 测试 data_gen.py
    ├── test_handlers.py    # 测试 handlers.py (Mock MQTT)
    └── test_config.py      # 测试 config.py
```

**模块依赖图：**
```
config.py (基础层)
    ↓
mqtt_handler.py
    ↓
device.py ←── data_gen.py (纯函数，无依赖)
    ↓           ↑
handlers.py ────┘
    ↓
device_simulator.py (主程序入口)
```

### logging 配置

```python
# simulator/__init__.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 线程安全

**并发场景分析：**
- MQTT 回调函数（`on_message`、`on_connect`、`on_disconnect`）在 MQTT 客户端线程中执行
- 主循环线程读取/修改共享状态
- 需要保护的共享状态：`parameters`、`seqno`、累积量（`total_discharge_ah` 等）

**锁策略：**
```python
# 使用单一锁保护所有共享状态，避免死锁
self._lock = threading.Lock()

# 使用示例
with self._lock:
    self.seqno += 1
    seqno = self.seqno

# 或在 MQTT 回调中
def _handle_remote_adjust(self, payload):
    with self._lock:
        self.parameters[param_id] = value
```

**死锁预防：**
- 单一锁，无嵌套锁
- 锁内操作尽量简短，不包含 I/O 或网络调用

### 异常处理

```python
# 替换
except:
    pass

# 为
except Exception as e:
    logger.error(f"具体错误信息：{e}")
    raise  # 或适当的错误处理
```

---

## P2 阶段：可维护性

### 目标

1. 配置热加载
2. 运行指标统计
3. 完善文档

### 配置热加载

使用 `watchdog` 库监听 `devices.json` 变化：

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json
import copy

class ConfigReloader(FileSystemEventHandler):
    def __init__(self, device_manager):
        self.device_manager = device_manager
        self._last_valid_config = None  # 保存最后有效配置用于回滚
    
    def on_modified(self, event):
        if event.src_path.endswith('devices.json'):
            try:
                with open('devices.json', 'r', encoding='utf-8') as f:
                    new_config = json.load(f)
                # 验证配置格式
                self._validate_config(new_config)
                # 保存备份
                self._last_valid_config = copy.deepcopy(new_config)
                # 应用新配置
                self.device_manager.reload_config(new_config)
                logging.info("配置热加载成功")
            except json.JSONDecodeError as e:
                logging.error(f"配置文件格式错误：{e}，回滚到旧配置")
                # 保持旧配置不变
            except Exception as e:
                logging.error(f"配置加载失败：{e}，回滚到旧配置")
    
    def _validate_config(self, config: list):
        """验证配置格式"""
        for dev in config:
            if 'devId' not in dev:
                raise ValueError("设备配置缺少 devId")
```

### 运行指标

```python
# metrics.py
import threading
import json
from typing import Dict, Any

class Metrics:
    """运行指标统计（内存 + 可选持久化）"""
    def __init__(self, persist_path: str = None):
        self._lock = threading.Lock()
        self.telemetry_sent = 0
        self.telemetry_failed = 0
        self.status_sent = 0
        self.status_failed = 0
        self.total_latency_ms = 0
        self.latency_count = 0
        self._persist_path = persist_path  # 如果设置，定期持久化到文件
    
    def record_telemetry(self, success: bool, latency_ms: int = 0):
        with self._lock:
            if success:
                self.telemetry_sent += 1
            else:
                self.telemetry_failed += 1
            if latency_ms > 0:
                self.total_latency_ms += latency_ms
                self.latency_count += 1
    
    def get_success_rate(self) -> float:
        with self._lock:
            total = self.telemetry_sent + self.telemetry_failed
            return self.telemetry_sent / total if total > 0 else 0.0
    
    def get_avg_latency(self) -> float:
        with self._lock:
            return self.total_latency_ms / self.latency_count if self.latency_count > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "telemetry_sent": self.telemetry_sent,
                "telemetry_failed": self.telemetry_failed,
                "status_sent": self.status_sent,
                "status_failed": self.status_failed,
                "success_rate": self.get_success_rate(),
                "avg_latency_ms": self.get_avg_latency(),
            }
    
    def save(self):
        """持久化到文件（可选）"""
        if self._persist_path:
            with open(self._persist_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
```

**说明**：指标默认存储在内存中，重启后丢失。如需持久化，可设置 `persist_path` 参数定期保存。

### 文档

- `README.md`: 项目说明、快速开始、配置说明
- `docs/protocol.md`: 四遥协议消息类型、信号 ID 规范

---

## 测试策略

### P0 测试

- 手动测试：使用正确/错误凭证连接 MQTT Broker
- 配置验证测试：未设置 `MQTT_PASSWORD` 时启动报错

### P1 测试

- 单元测试：数据生成函数、配置加载、消息处理
- 集成测试：单设备完整流程（连接→登录→上报→响应）
- **覆盖率目标：核心模块（data_gen.py, handlers.py, config.py）≥ 80%**

### P2 测试

- 配置热加载：修改 devices.json 后观察设备列表变化
- 指标准确性：验证统计值与实际行为一致
- 错误恢复：注入非法 JSON 验证回滚机制

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| .env 配置遗漏 | P0 后无法启动 | 提供 .env.example 模板，启动时检查必填项 |
| 模块拆分引入 bug | P1 后功能异常 | 保持行为不变，仅重构结构 |
| logging 输出过多 | 日志噪音 | 使用适当日志级别，INFO/WARN/ERROR 区分 |
| 配置热加载失败 | P2 后设备状态异常 | 配置校验失败时回滚到旧配置 |

## 回滚计划

**Git 分支策略：**
- `main` - 稳定版本
- `feature/p0-security` - P0 阶段开发分支
- `feature/p1-quality` - P1 阶段开发分支
- `feature/p2-maintainability` - P2 阶段开发分支

**回滚步骤：**
1. 每个阶段在独立分支开发
2. 阶段完成后合并到 main，打标签 `v0.1.0`, `v0.2.0`, `v0.3.0`
3. 如发现问题，回退标签到上一版本

---

## 验收标准

### P0

- [ ] `.env.example` 存在且包含所有必填配置项
- [ ] `requirements.txt` 存在
- [ ] `config.py` 正确加载环境变量
- [ ] `config.py` 对 `MQTT_HOST` 和 `MQTT_PASSWORD` 进行必填验证
- [ ] `device_simulator.py` 从 config 模块读取配置
- [ ] TLS 默认强制证书验证（`CERT_REQUIRED`）
- [ ] `.gitignore` 包含 `.env` 条目
- [ ] 启动时未设置 `MQTT_PASSWORD` 抛出明确的 `ConfigError`

### P1

- [ ] `simulator/` 目录包含 4 个模块文件（`__init__.py`, `device.py`, `mqtt_handler.py`, `data_gen.py`, `handlers.py`）
- [ ] 无 `print()` 语句，全部使用 `logging`
- [ ] 共享状态（`parameters`, `seqno`, 累积量）有锁保护
- [ ] `tests/` 目录包含基础测试
- [ ] 核心模块测试覆盖率 ≥ 80%

### P2

- [ ] 修改 `devices.json` 后无需重启生效
- [ ] 配置文件格式错误时回滚到旧配置
- [ ] 可查询运行指标（成功率、延迟）
- [ ] 指标数据支持持久化（可选，见下文说明）
- [ ] `README.md` 包含快速开始指南
- [ ] `docs/protocol.md` 说明消息格式

---

## 时间估算

| 阶段 | 估算时间 |
|------|----------|
| P0 | 1-2 小时 |
| P1 | 4-6 小时 |
| P2 | 3-4 小时 |

---

## 附录：消息类型参考

| 类型 | 上行 | 下行 | 说明 |
|------|------|------|------|
| 登录 | 100 | 101 | 设备认证（101 响应带 result 字段，0=失败，1=成功） |
| 心跳 | 200 | 200 | 保活 |
| 遥测 | 300 | - | 模拟量上报（电压、电流、SOC、温度等） |
| 遥信 | 310 | - | 状态量上报（运行状态、故障码、告警码） |
| 遥控 | - | 400 | 远程控制命令（断路器、均衡等） |
| 遥控响应 | 401 | - | 遥控执行结果（result: 0=失败，1=成功） |
| 遥调 | - | 500 | 远程参数下发（保护阈值、SOC 校准等） |
| 遥调响应 | 501 | - | 遥调确认（failedParams 列表） |

**错误处理说明：**
- 登录失败：101 响应中 `data.result = 0`，可附带 `data.errorCode`
- 遥控/遥调失败：401/501 响应中 `data.result = 0`，附带失败原因
