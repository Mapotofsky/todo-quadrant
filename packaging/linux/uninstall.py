#!/usr/bin/env python3
"""卸载当前用户安装的四象限待办，默认保留任务数据库。"""
import argparse
import shutil
import subprocess
from pathlib import Path

APP_DIR_NAME = "todo-quadrant"
DESKTOP_NAME = "todo-quadrant.desktop"
ICON_NAME = "todo-quadrant.png"


def _run_quiet(command):
    if shutil.which(command[0]) is None:
        return
    try:
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purge", action="store_true", help="同时删除 ~/.config/todo-quadrant 中的数据")
    args = parser.parse_args()

    app_dir = Path(__file__).resolve().parent
    if app_dir.name != APP_DIR_NAME:
        raise SystemExit("拒绝卸载：安装目录不符合预期（%s）" % app_dir)
    data_home = app_dir.parent
    desktop = data_home / "applications" / DESKTOP_NAME
    icon = data_home / "icons" / "hicolor" / "256x256" / "apps" / ICON_NAME

    if desktop.is_file():
        try:
            text = desktop.read_text(encoding="utf-8")
        except OSError:
            text = ""
        if str(app_dir / "main.py") in text:
            desktop.unlink()
    if icon.is_file():
        icon.unlink()
    shutil.rmtree(app_dir)

    config = Path.home() / ".config" / "todo-quadrant"
    if args.purge:
        shutil.rmtree(config, ignore_errors=True)
        print("已删除任务数据库 %s" % config)
    else:
        print("已保留任务数据库 %s" % config)
    _run_quiet(["update-desktop-database", str(data_home / "applications")])
    print("已卸载四象限待办")


if __name__ == "__main__":
    main()
