#!/usr/bin/env python3
"""把四象限待办安装到当前用户的 ~/.local（无需 root）。

安装包由 packaging/linux/build.py 生成；安装后从开始菜单启动，
应用常驻通知区域。任务数据库仍保存在 ~/.config/todo-quadrant/todo.db。
"""
import argparse
import os
import shutil
import subprocess
from pathlib import Path

APP_NAME = "todo-quadrant"
DESKTOP_NAME = "todo-quadrant.desktop"
ICON_NAME = "todo-quadrant.png"


def _quote_exec_arg(path):
    """按 desktop 文件的 Exec 规则转义绝对路径。"""
    argument = "".join("\\" + c if c in '\\"$`' else c for c in path)
    return argument.replace("\\", "\\\\")


def _desktop_entry(app_dir):
    # Exec 中的 % 是 field code，必须写成 %%。
    exec_arg = _quote_exec_arg(str(app_dir / "main.py").replace("%", "%%"))
    icon = str(app_dir / "resources" / ICON_NAME).replace("\\", "\\\\")
    return (
        "[Desktop Entry]\n"
        "Version=1.0\n"
        "Type=Application\n"
        "Name=四象限待办\n"
        "GenericName=Todo Quadrant\n"
        "Comment=四象限待办悬浮窗\n"
        'Exec=/usr/bin/python3 "%s"\n'
        "Icon=%s\n"
        "Terminal=false\n"
        "Categories=Utility;\n"
        "StartupNotify=false\n"
    ) % (exec_arg, icon)


def _payload():
    payload = Path(__file__).resolve().parent / "payload"
    if not (payload / "main.py").is_file():
        raise SystemExit("安装包不完整：缺少 payload/main.py")
    return payload


def _data_home(prefix):
    if prefix:
        return Path(prefix).expanduser().resolve() / "share"
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))


def _run_quiet(command):
    if shutil.which(command[0]) is None:
        return
    try:
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default="",
                        help="安装前缀，默认 ~/.local；程序安装到 <prefix>/share/todo-quadrant")
    args = parser.parse_args()

    payload = _payload()
    data_home = _data_home(args.prefix)
    app_dir = data_home / APP_NAME
    desktop_dir = data_home / "applications"
    icon_dir = data_home / "icons" / "hicolor" / "256x256" / "apps"

    if app_dir.is_symlink():
        app_dir.unlink()
    elif app_dir.exists():
        shutil.rmtree(app_dir)
    shutil.copytree(payload, app_dir)

    desktop_dir.mkdir(parents=True, exist_ok=True)
    icon_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(app_dir / "resources" / ICON_NAME, icon_dir / ICON_NAME)
    desktop = desktop_dir / DESKTOP_NAME
    desktop.write_text(_desktop_entry(app_dir), encoding="utf-8")
    desktop.chmod(0o644)
    _run_quiet(["update-desktop-database", str(desktop_dir)])

    print("已安装到 %s" % app_dir)
    print("开始菜单入口 %s" % desktop)
    print("任务数据库仍为 ~/.config/todo-quadrant/todo.db（未改动）")
    print("启动后驻留通知区域；单击托盘图标显示浮窗。")
    print("卸载：/usr/bin/python3 %s" % (app_dir / "uninstall.py"))


if __name__ == "__main__":
    main()
