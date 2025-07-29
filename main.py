import asyncio
import json
import websockets
import os
from shutil import rmtree

from command import command_list, TMP_PATH
from func import FileMessage, SendPrivateMessage, SendGroupMessage
from type import (
    MessageObject,
    PrivateMessageEvent,
    GroupMessageEvent,
    EventBase,
    Result,
)

URI = "ws://192.168.0.2:3001/"
PRIVATE_IDS = [1]
GROUP_IDS = [1]

# 创建用于协调清理任务的全局变量
cleanup_event = asyncio.Event()
pending_cleanup = False


def command_run(command: str):
    for cmd in command_list.keys():
        if command.startswith(cmd):
            return command_list[cmd](command)


def msg_is_command(
    message: list[MessageObject],
) -> tuple[bool, str | None]:
    for msg in message:
        if msg["type"] == "text":
            data = msg["data"]
            data = data["text"]
            if data.startswith("/"):
                return True, data[1:]
    return False, None


async def chat_msg_handler(event: PrivateMessageEvent):
    sender_id: int = event["user_id"]
    if sender_id not in PRIVATE_IDS:
        # 如果私聊消息发送者不在白名单中，则不处理
        return

    is_command, command = msg_is_command(event["message"])
    if not is_command or command is None:
        return

    result = command_run(command)
    if result is None:
        return

    message_id: int = event["message_id"]
    if result.get("text") is not None:
        relay_data = SendPrivateMessage(result["text"], sender_id, message_id)
        relay_data_json = json.dumps(relay_data)
        await ws.send(relay_data_json)
    if result.get("file") is not None:
        send_data = SendPrivateMessage(
            FileMessage(result["file"][1], result["file"][0]), sender_id
        )
        send_data_json = json.dumps(send_data)
        await ws.send(send_data_json)


async def group_msg_handler(event: GroupMessageEvent):
    if event["sub_type"] != "normal":
        # 只处理普通群聊消息
        return

    group_id: int = event["group_id"]
    if group_id not in GROUP_IDS:
        # 如果群聊消息发送者不在白名单中，则不处理
        return

    is_command, command = msg_is_command(event["message"])
    if not is_command or command is None:
        return

    result = command_run(command)
    message_id: int = event["message_id"]
    if result is None:
        return

    if result.get("text") is not None:
        send_data = SendGroupMessage(result["text"], group_id, message_id)
        send_data_json = json.dumps(send_data)
        await ws.send(send_data_json)
    if result.get("file") is not None:
        send_data = SendGroupMessage(
            FileMessage(result["file"][1], result["file"][0]), group_id
        )
        send_data_json = json.dumps(send_data)
        await ws.send(send_data_json)


async def event_handler(event: EventBase | Result):
    if event.get("echo") is not None:
        # TODO: echo handler
        return

    if event.get("post_type") == "message":
        global pending_cleanup
        # 只有处理消息前检查是否需要清理
        if not pending_cleanup:
            pending_cleanup = True
            cleanup_event.set()

        # 等待清理任务完成
        while cleanup_event.is_set():
            await asyncio.sleep(1)

        message_type = event.get("message_type")
        if message_type == "private":
            await chat_msg_handler(event)  # pyright: ignore[reportArgumentType]
        elif message_type == "group":
            await group_msg_handler(event)  # pyright: ignore[reportArgumentType]
        else:
            print("unknown message type")


async def cleanup_task():
    """异步执行文件清理任务"""
    global pending_cleanup
    while True:
        # 等待清理信号
        await cleanup_event.wait()

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
            pending_cleanup = False


async def main():
    global ws

    # 启动清理任务
    asyncio.create_task(cleanup_task())

    async with websockets.connect(URI) as ws:
        while True:
            # 等待新消息
            msg = await ws.recv()
            msg_json = json.loads(msg)
            await event_handler(msg_json)


if __name__ == "__main__":
    asyncio.run(main())
