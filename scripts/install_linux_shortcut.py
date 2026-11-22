"""按当前源码位置生成 Linux 桌面快捷方式。"""
import argparse
import os
from pathlib import Path


def main():
    data_home = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path,
                        default=Path(data_home) / "applications")
    directory = parser.parse_args().directory.expanduser()
    root = Path(__file__).resolve().parents[1]
    template = (root / "todo-quadrant.desktop").read_text(encoding="utf-8")
    path = str(root / "main.py").replace("%", "%%")
    # Exec 参数的引号转义在 desktop 文件的通用转义之后解析。
    argument = "".join("\\" + c if c in '\\"$`' else c for c in path)
    argument = argument.replace("\\", "\\\\")
    directory.mkdir(parents=True, exist_ok=True)
    shortcut = directory / "todo-quadrant.desktop"
    shortcut.write_text(template.replace("@MAIN@", '"' + argument + '"'), encoding="utf-8")
    shortcut.chmod(0o755)
    print(shortcut)


if __name__ == "__main__":
    main()
