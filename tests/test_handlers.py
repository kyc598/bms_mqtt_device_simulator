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
    assert response["msgType"] == 501
    assert response["data"]["result"] == 0
    assert "UNKNOWN_PARAM" in response["data"]["failedParams"]
