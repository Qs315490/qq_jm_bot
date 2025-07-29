class MessageBody(dict):
    def __init__(self, type: str, data: dict | str):
        super().__init__()
        self["type"] = type
        if isinstance(data, dict):
            self["data"] = data
            return
        if isinstance(data, str):
            self["data"] = {"text": data}
            return
        raise TypeError("data is not a dict or str")


class StrMessage(MessageBody):
    def __init__(self, msg: str):
        super().__init__("text", msg)


class FileMessage(MessageBody):
    def __init__(self, file: str, file_name: str | None = None):
        super().__init__(
            "file",
            {"file": file} if file_name is None else {"file": file, "name": file_name},
        )


class ReplyMessage(list):
    # 定义一个继承自dict的类ReplyMessage
    def __init__(
        self,
        reply_msg_id: int,
        message: dict | str | StrMessage,
    ):
        # 初始化方法，接收两个参数：reply_msg_id和message
        super().__init__()
        # 调用父类的初始化方法
        self.append(MessageBody("reply", {"id": reply_msg_id}))
        if isinstance(message, dict):
            self.append(message)
            return
        if isinstance(message, str):
            self.append(StrMessage(message))
            return
        if isinstance(message, StrMessage):
            self.append(message)
            return


class SendPrivateMessage(dict):
    def __init__(
        self,
        message: dict | list | str | StrMessage | FileMessage,
        user_id: int,
        reply_msg_id: int | None = None,
        echo: str | None = None,
    ):
        super().__init__()
        self["action"] = "send_private_msg"
        self["params"] = {"user_id": user_id, "message": None}
        if (
            isinstance(message, dict)
            or isinstance(message, list)
            or isinstance(message, StrMessage)
            or isinstance(message, FileMessage)
        ):
            self["params"]["message"] = message

        elif reply_msg_id is not None:
            self["params"]["message"] = ReplyMessage(reply_msg_id, message)

        elif isinstance(message, str):
            self["params"]["message"] = StrMessage(message)

        if echo is None:
            if reply_msg_id is not None:
                self["echo"] = f"{user_id}_{reply_msg_id}"
            else:
                self["echo"] = str(user_id)
        else:
            self["echo"] = echo


class SendGroupMessage(SendPrivateMessage):
    def __init__(
        self,
        message: dict | list | str | StrMessage | FileMessage,
        group_id: int,
        reply_msg_id: int | None = None,
        echo: str | None = None,
    ):
        super().__init__(message, group_id, reply_msg_id, echo)
        self["action"] = "send_group_msg"
        self["params"].pop("user_id")
        self["params"].update({"group_id": group_id})
