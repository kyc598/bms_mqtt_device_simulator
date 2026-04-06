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
