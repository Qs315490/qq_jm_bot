import asyncio
import json
import websockets
import os
from shutil import rmtree
from threading import Timer

from pydantic import ValidationError

from command import command_list, TMP_PATH
from func import FileMessage, SendPrivateMessage, SendGroupMessage
from type import (
    MessageObject,
    PrivateMessageEvent,
    GroupMessageEvent,
    BaseEvent,
    Event,
    Result,
    CommandResult,
)


try:
    import config

    PRIVATE_IDS = config.PRIVATE_IDS
    GROUP_IDS = config.GROUP_IDS
    URI = config.URI
except ImportError:
    URI = "ws://napcat:3001/"
    PRIVATE_IDS = [1]
    GROUP_IDS = [1]

# 创建用于协调清理任务的全局变量
cleanup_event = asyncio.Event()
command_running = asyncio.Event()


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


async def event_handler(event: Event):
    if isinstance(event, Result):
        # TODO: echo handler
        return

    if event.post_type == "message":
        # 等待清理任务完成
        if cleanup_event.is_set():
            print("Cleanup task is running. Waiting to resume command processing.")
            await cleanup_event.wait()
            print("Cleanup task completed. Resuming command processing.")
        command_running.set()
        await msg_handler(event)
        command_running.clear()


def parse_event(data: dict) -> Event:
    """根据数据内容自动判断事件类型"""
    # 先创建基础事件对象
    base_event = BaseEvent(**data)

    # 根据 post_type 判断具体事件类型
    if base_event.post_type == "message":
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
    elif data.get("echo") is not None:
        try:
            return Result(**data)
        except ValidationError:
            pass
    # 如果无法匹配具体类型，返回基础事件
    return base_event


async def cleanup_task():
    """异步执行文件清理任务"""

    print("Starting cleanup task...")
    # 等待当前命令处理完成
    if command_running.is_set():
        print("Command is running. Waiting to complete.")
        await command_running.wait()
        print("Command completed. Proceeding with cleanup.")
    cleanup_event.set()

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
        cleanup_event.clear()


async def main():
    global ws

    # 启动清理任务 （每6小时执行一次）
    Timer(6 * 60 * 60, cleanup_task).start()

    async with websockets.connect(URI) as ws:
        print("Connected to websocket server.")
        while True:
            # 等待新消息
            msg = await ws.recv()
            msg_json: dict = json.loads(msg)
            await event_handler(parse_event(msg_json))


if __name__ == "__main__":
    asyncio.run(main())
