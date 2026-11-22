#!/usr/bin/env python3
"""构建 Linux 用户级安装包（tar.gz，无需 root 安装）。"""
import argparse
import hashlib
import platform
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VERSION = "1.0.1"


def _arch():
    machine = platform.machine().lower()
    return {
        "aarch64": "arm64",
        "arm64": "arm64",
        "x86_64": "x86_64",
        "amd64": "x86_64",
    }.get(machine, machine)


def _ignore(directory, names):
    return [name for name in names
            if name == "__pycache__" or name.endswith(".pyc") or name == ".DS_Store"]


def _copy_tree(src, dst):
    shutil.copytree(src, dst, ignore=_ignore)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--arch", default="", help="默认按当前机器架构命名")
    args = parser.parse_args()

    version = args.version
    arch = args.arch or _arch()
    name = "todo-quadrant-%s-linux-%s" % (version, arch)
    stage = ROOT / ".build" / "linux" / name
    if stage.exists():
        shutil.rmtree(stage)
    payload = stage / "payload"
    payload.mkdir(parents=True)

    shutil.copy2(ROOT / "main.py", payload / "main.py")
    _copy_tree(ROOT / "app", payload / "app")
    _copy_tree(ROOT / "resources", payload / "resources")
    shutil.copy2(ROOT / "README.md", payload / "README.md")
    shutil.copy2(ROOT / "packaging" / "linux" / "install.py", stage / "install.py")
    shutil.copy2(ROOT / "packaging" / "linux" / "uninstall.py", payload / "uninstall.py")
    (payload / "VERSION").write_text(version + "\n", encoding="utf-8")

    forbidden = list(stage.rglob("api-key.txt"))
    if forbidden:
        raise SystemExit("拒绝打包用户密钥：%s" % forbidden[0])

    output = ROOT / "dist" / "linux" / (name + ".tar.gz")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        archive.add(stage, arcname=name)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print("BUILT %s" % output)
    print("SIZE %d" % output.stat().st_size)
    print("SHA256 %s" % digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
