# 群核心科技
基于 OneBot V11 协议的QQ机器人WebSocket客户端  
实现了 `/jm xxxx` 命令，用于在群内快速调用 [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python) 的 API  
实现群内快速调用 [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python) API下载漫画，并转成 `PDF` 文件发送到群聊

## 使用方法
* 安装依赖
```bash
# 使用 pip 安装依赖, 不一定成功
pip install -r pyproject.toml
# 使用 pip 指定安装依赖
pip install jmcomic img2pdf websockets
# 使用 uv 安装依赖
uv sync
```
1. 向 `config.py` 中添加 `URI="ws://napcat:3001/"`, `napcat:3001` 为你的 OneBot 服务器地址
2. 向 `config.py` 中添加 `PRIVATE_IDS=[10086]`, QQ号白名单，只有白名单中的QQ号才相应 `/jm` 命令
3. 向 `config.py` 中添加 `GROUP_IDS=[10000]`, 群号白名单，只有白名单中的群号才相应 `/jm` 命令
4. 运行 `main.py`
```bash
python main.py
# 使用 uv 运行
uv run main.py
```
在群内发送 `/jm xxxx` 命令，即可下载并发送漫画到群聊

## 注意事项
1. 下载漫画需要一定时间，请耐心等待
2. 下载漫画时，如果遇到网络问题，可能会导致下载失败，请重试
3. 需要能连接到 `JMComic` 的网络环境，否则无法下载漫画
4. 因为文件大小问题，采用本地文件上传方式。需要和server在同一个主机上，对于docker来说就是互相访问对应目录的文件