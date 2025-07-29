import re
from os import path, mkdir
from sys import platform
import jmcomic

JM_OPTIONS = jmcomic.create_option_by_file("jm_options.yml")
PDF_DIR = "./tmp/pdfs"
tmp: list[dict] = JM_OPTIONS.plugins.get("after_photo", [])
for pl in tmp:
    if pl.get("plugin") == "img2pdf":
        PDF_DIR = pl.get("kwargs", {}).get("pdf_dir")
        break
del tmp
TMP_PATH = path.join(PDF_DIR, "..")
if not path.exists(TMP_PATH):
    mkdir(TMP_PATH)


def download_jm_as_pdf(id: str):
    try:
        result = jmcomic.download_album(id, JM_OPTIONS)
    except (
        jmcomic.PartialDownloadFailedException,
        jmcomic.RequestRetryAllFailException,
    ) as e:
        # TODO: send message to user
        print(e)
        return {"text": e.description}
    if isinstance(result, tuple):
        name = result[0].name
        file_name = f"{name}.pdf"
        file_path = path.join(PDF_DIR, file_name)
        file_abspath = path.abspath(file_path)
        if platform == "win32":
            file_abspath = file_abspath.replace("\\", "/")
        return {
            "text": name,
            "file": (file_name, f"file://{file_abspath}"),
        }


def command_jm_parse(command: str):
    match = re.match(r"jm *(\d+)", command)
    if match:
        id = match.group(1)
        return download_jm_as_pdf(id)


def command_help():
    return {
        "text": """"
            命令列表：
            jm <id> 下载漫画为pdf格式
        """
    }


command_list = {"help": command_help, "jm": command_jm_parse}
