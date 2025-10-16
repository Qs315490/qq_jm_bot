import re
from os import path, mkdir
from pathlib import Path
from sys import platform
from collections.abc import Callable

import jmcomic

from type import CommandResult, CommandResultFile

JM_OPTIONS = jmcomic.create_option_by_file("jm_options.yml")
PDF_DIR = "./tmp/pdfs"
tmp: list[dict] = JM_OPTIONS.plugins.get("after_photo", [])
for pl in tmp:
    if pl.get("plugin") == "img2pdf":
        PDF_DIR = pl.get("kwargs", {}).get("pdf_dir")
        break
del tmp
TMP_PATH = Path(PDF_DIR).parent
if not path.exists(TMP_PATH):
    mkdir(TMP_PATH)


def download_jm_as_pdf(id: str) -> CommandResult:
    try:
        result = jmcomic.download_album(id, JM_OPTIONS)
    except (
        jmcomic.PartialDownloadFailedException,
        jmcomic.RequestRetryAllFailException,
    ) as e:
        # TODO: send message to user
        print(e)
        return CommandResult(text=e.description)
    if isinstance(result, tuple):
        name = result[0].name
        id = result[0].id
        file_name = f"{id}.pdf"
        file_path = path.join(PDF_DIR, file_name)
        file_abspath = path.abspath(file_path)
        if platform == "win32":
            file_abspath = file_abspath.replace("\\", "/")
        return CommandResult(
            text=name,
            file=CommandResultFile(name=file_name, path=f"file://{file_abspath}"),
        )
    return CommandResult(text="下载失败，未知错误")


def command_jm_parse(command: str):
    match = re.match(r"jm *(\d+)", command)
    if match:
        id = match.group(1)
        return download_jm_as_pdf(id)
    return CommandResult(text="命令格式错误")


def command_help(_):
    return CommandResult(
        text="""
命令列表：
/jm <id> 下载漫画为pdf格式
"""
    )


command_list:dict[str, Callable[[str], CommandResult]] = {"help": command_help, "jm": command_jm_parse}

if __name__ == "__main__":
    # TEST
    download_jm_as_pdf("485647")
