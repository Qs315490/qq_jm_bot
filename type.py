from pydantic import BaseModel


class MessageData(BaseModel):
    """接收事件中message的data字段"""

    text: str | None = None
    file: str | None = None
    qq: int | None = None
    id: int | None = None


class MessageObject(BaseModel):
    """接收事件中message字段"""

    type: str
    data: MessageData


class FriendSender(BaseModel):
    """接收事件中sender字段"""

    user_id: int
    "发送者 QQ 号"
    nickname: str
    "发送者昵称"
    sex: str
    "发送者性别"
    group_id: int | None = None
    "群临时会话群号（可选）"


class BaseEvent(BaseModel):
    """接收事件"""

    time: int
    "事件发生的时间戳（秒）"
    post_type: str
    "事件类型"
    self_id: int
    "收到事件的机器人 QQ 号"


class MetaEvent(BaseEvent):
    """元事件"""

    meta_event_type: str
    "子类型"


class Status(BaseModel):
    "状态"

    online: bool
    "是否在线"
    good: bool


class HeartbeatEvent(MetaEvent):
    """心跳事件"""

    status: Status
    "状态"
    interval: int
    "心跳间隔"


class PrivateMessageEvent(BaseEvent):
    """接收私聊消息事件"""

    message_type: str
    "消息类型"
    sub_type: str
    "消息子类型"
    message_id: int
    "消息 ID"
    user_id: int
    "发送者 QQ 号"
    message: list[MessageObject]
    "消息内容"
    raw_message: str
    "原始消息内容"
    font: int
    "字体"
    target_id: int | None = None
    "临时会话目标 QQ 号（可选）"
    temp_source: int | None = None
    "临时会话来源（可选）"
    sender: dict
    "发送者信息"


class GroupMessageEvent(PrivateMessageEvent):
    "接收群聊消息事件"

    group_id: int
    "群号"


class Result(BaseModel):
    "发送消息的返回值"

    status: str
    "发送状态"
    retcode: int
    "返回码"
    data: dict | None = None
    "返回数据"
    message: str | None = None
    "返回信息"
    wording: str | None = None
    "错误信息"
    echo: str
    "自定义标识"


type Event = BaseEvent | MetaEvent | Result


class CommandResultFile(BaseModel):
    name: str
    path: str


class CommandResult(BaseModel):
    text: str | dict | None = None
    file: CommandResultFile | None = None
