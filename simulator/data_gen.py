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
