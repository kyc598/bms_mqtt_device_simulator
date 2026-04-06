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
        # 支持两种命名风格：heartbeatInterval 或 heartbeat_interval
        heartbeat_interval = data.get("heartbeatInterval") or data.get("heartbeat_interval", 60)
        logger.info(f"[{dev_id}] 登录成功，心跳间隔：{heartbeat_interval}s")
        return heartbeat_interval
    else:
        logger.warning(f"[{dev_id}] 登录失败，结果：{data.get('result')}")
        return None
