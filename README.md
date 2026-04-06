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
python main.py
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
