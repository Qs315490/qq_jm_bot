import asyncio
import json
import os
from http.client import HTTPConnection, HTTPException
from shutil import rmtree
from threading import Lock
from traceback import print_exc

import websockets
from pydantic import ValidationError

from command import TMP_PATH, command_list
from func import (
    FileMessage,
    SendGroupMessage,
    SendPrivateMessage,
    SetOnlineStatus,
    timer_func,
)
from type import (
    BaseEvent,
    CommandResult,
    Event,
    GroupMessageEvent,
    HeartbeatEvent,
    MessageObject,
    MetaEvent,
    PrivateMessageEvent,
    Result,
)

URI = "ws://napcat:3001/"
try:
    import config

    PRIVATE_IDS = config.PRIVATE_IDS
    GROUP_IDS = config.GROUP_IDS
    URI = getattr(config, "URI", URI)
    TOKEN = getattr(config, "TOKEN", None)
except ImportError:
    PRIVATE_IDS = []
    GROUP_IDS = []
    TOKEN = None

# 创建用于协调清理任务的全局变量
command_cleanup_running = Lock()
is_online: bool = False


def command_run(command: str) -> CommandResult | None:
    for cmd in command_list.keys():
        if command.startswith(cmd):
            return command_list[cmd](command)


def msg_is_command(
    message: list[MessageObject],
) -> tuple[bool, str | None]:
    for msg in message:
        if msg.type == "text":
            data = msg.data
            data = data.text
            if data is None:
                continue
            if data.startswith("/"):
                return True, data[1:]
    return False, None


async def msg_handler(event: Event):
    if isinstance(event, GroupMessageEvent):
        if event.group_id not in GROUP_IDS:
            # 如果群聊消息发送者不在白名单中，则不处理
            return
        if event.sub_type != "normal":
            # 只处理普通群聊消息
            return
    elif isinstance(event, PrivateMessageEvent):
        if event.user_id not in PRIVATE_IDS:
            # 如果私聊消息发送者不在白名单中，则不处理
            return
    else:
        return

    is_command, command = msg_is_command(event.message)
    if not is_command or command is None:
        return

    print(f"Received command: {command} from user: {event.user_id}")
    result = command_run(command)
    if result is None:
        return

    if result.text is not None:
        if isinstance(event, GroupMessageEvent):
            send_data = SendGroupMessage(result.text, event.group_id, event.message_id)
        else:
            send_data = SendPrivateMessage(result.text, event.user_id, event.message_id)

        send_data_json = json.dumps(send_data)
        await ws.send(send_data_json)

    if result.file is not None:
        file_name = result.file.name
        file_path = result.file.path
        if isinstance(event, GroupMessageEvent):
            send_data = SendGroupMessage(
                FileMessage(file_path, file_name), event.group_id
            )
        else:
            send_data = SendPrivateMessage(
                FileMessage(file_path, file_name), event.user_id
            )

        send_data_json = json.dumps(send_data)
        await ws.send(send_data_json)


def meta_event_handler(event: MetaEvent):
    match event.meta_event_type:
        case "heartbeat":
            assert isinstance(event, HeartbeatEvent)
            # 心跳事件，可以在这里处理心跳逻辑
            global is_online  # noqa: PLW0603
            is_online = event.status.online


def result_handler(event: Result):
    if event.retcode != 0:
        print(f"Action '{event.echo}' failed <{event.retcode}>: {event.message}")
        return

    match event.echo:
        case _:
            pass


async def event_handler(event: Event):
    if isinstance(event, Result):
        result_handler(event)
        return

    if isinstance(event, MetaEvent):
        meta_event_handler(event)
        return

    if event.post_type == "message":
        # 等待清理任务完成
        with command_cleanup_running:
            await msg_handler(event)


def parse_event(data: dict) -> Event:
    """根据数据内容自动判断事件类型"""

    if data.get("echo") is not None:
        try:
            return Result(**data)
        except ValidationError:
            pass

    # 先创建基础事件对象
    base_event = BaseEvent(**data)

    # 根据 post_type 判断具体事件类型
    match base_event.post_type:
        case "message":
            # 根据 message_type 进一步判断
            message_type = data.get("message_type")
            if message_type == "private":
                try:
                    return PrivateMessageEvent(**data)
                except ValidationError:
                    pass
            elif message_type == "group":
                try:
                    return GroupMessageEvent(**data)
                except ValidationError:
                    pass
        case "meta_event":
            match data.get("meta_event_type"):
                case "heartbeat":
                    return HeartbeatEvent(**data)
            return MetaEvent(**data)
    # 如果无法匹配具体类型，返回基础事件
    return base_event


async def ws_handler(websocket_uri: str, token: str | None = None):
    global ws
    if token is not None:
        websocket_uri = f"{websocket_uri}/?access_token={token}"
    async with websockets.connect(websocket_uri) as ws:
        print("Connected to websocket server.")
        # 启动自动登录任务
        await auto_login()

        while True:
            # 等待新消息
            msg = await ws.recv()
            msg_json: dict = json.loads(msg)
            await event_handler(parse_event(msg_json))


# 清理任务 （每6小时执行一次）
@timer_func(6 * 60 * 60)
def cleanup_task():
    """异步执行文件清理任务"""

    print("Starting cleanup task...")
    # 等待当前命令处理完成
    command_cleanup_running.acquire()

    try:
        # 安全清理临时目录
        for root, dirs, files in os.walk(TMP_PATH):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                rmtree(os.path.join(root, name), ignore_errors=True)
        print(f"Cleaned temporary directory: {TMP_PATH}")
    except Exception as e:
        print(f"Cleanup error: {e}")
    finally:
        # 重置状态
        command_cleanup_running.release()

    print("Cleanup task completed.")


# 自动登录任务（每15分钟执行一次）
@timer_func(15 * 60)
async def auto_login():
    """自动登录任务"""

    # 如果在线状态为离线，则尝试重新登录
    if is_online:
        return

    # 检查网络连接
    try:
        http = HTTPConnection("wifi.vivo.com.cn", timeout=5)
        http.request("GET", "/")
        response = http.getresponse()
    except HTTPException as e:
        print(f"auto_login: {e}")
        return
    if 204 != response.getcode():
        print("auto_login: Network error")
        return

    print("auto_login: set login status...")
    # 设置在线状态
    msg = SetOnlineStatus(status=10, echo="auto_login")
    await ws.send(json.dumps(msg))


async def main():
    # 启动清理任务
    cleanup_task()

    while True:
        try:
            await ws_handler(URI, TOKEN)
        except Exception:
            print_exc()
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
