#!/usr/bin/env python3
"""构建最小可用的 Linux .deb 安装包（不依赖 debian/ 目录和 debhelper）。

只做一件事：把仓库里运行所需的 Python 文件和资源装进 /usr/share/todo-quadrant，
再交给 dpkg-deb 打包。不生成 apt 源、签名、AppStream 或发行版维护元数据。
"""
import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEB_DIR = Path(__file__).resolve().parent
PACKAGE = "todo-quadrant"
DEFAULT_VERSION = "1.0.1"
DEFAULT_ARCH = "all"
FALLBACK_MAINTAINER = "ZGYD <noreply@example.com>"
VERSION_RE = re.compile(r"^[0-9][A-Za-z0-9.+~-]*$")
FORBIDDEN_NAMES = ("api-key.txt", "__pycache__", ".DS_Store")
FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".db")


def _ignore(directory, names):
    return [name for name in names
            if name in FORBIDDEN_NAMES or name.endswith(FORBIDDEN_SUFFIXES)]


def _git_output(*args):
    try:
        result = subprocess.run(["git", "-C", str(ROOT)] + list(args),
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8", "replace").strip()


def _maintainer():
    """复用仓库 git 作者信息，取不到时用占位值。"""
    author = _git_output("log", "-1", "--format=%an <%ae>")
    if author and "\n" not in author:
        return author
    name = _git_output("config", "user.name")
    email = _git_output("config", "user.email")
    if name and email:
        return "%s <%s>" % (name, email)
    return FALLBACK_MAINTAINER


def _render_control(version, arch, maintainer):
    template = (DEB_DIR / "control.in").read_text(encoding="utf-8")
    control = (template
               .replace("@VERSION@", version)
               .replace("@ARCH@", arch)
               .replace("@MAINTAINER@", maintainer))
    for placeholder in ("@VERSION@", "@ARCH@", "@MAINTAINER@"):
        if placeholder in control:
            raise SystemExit("control 模板仍有未替换的占位符：%s" % placeholder)
    if not control.endswith("\n"):
        control += "\n"
    return control


def _copy_payload(app_dir):
    shutil.copy2(ROOT / "main.py", app_dir / "main.py")
    shutil.copytree(ROOT / "app", app_dir / "app", ignore=_ignore)
    shutil.copytree(ROOT / "resources", app_dir / "resources", ignore=_ignore)


def _check_no_forbidden(stage):
    for path in stage.rglob("*"):
        if path.name in FORBIDDEN_NAMES or path.name.endswith(FORBIDDEN_SUFFIXES):
            raise SystemExit("拒绝打包用户数据或缓存：%s" % path)


def _apply_modes(stage, executable):
    for path in sorted(stage.rglob("*")):
        if path.is_dir():
            path.chmod(0o755)
        else:
            path.chmod(0o755 if path in executable else 0o644)
    stage.chmod(0o755)


def _root_owner_group_supported():
    """dpkg 1.19 起支持 --root-owner-group；以 help 输出为准，避免解析本地化版本号。"""
    try:
        result = subprocess.run(["dpkg-deb", "--help"],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except OSError as exc:
        raise SystemExit("未找到 dpkg-deb：%s" % exc)
    return result.returncode == 0 and b"--root-owner-group" in result.stdout


def _build(stage, output):
    dpkg = shutil.which("dpkg-deb")
    if dpkg is None:
        raise SystemExit("未找到 dpkg-deb，请先安装 dpkg")

    if _root_owner_group_supported():
        owner = "root-owner-group"
        command = [dpkg, "--build", "--root-owner-group", "-Zxz", str(stage), str(output)]
    else:
        fakeroot = shutil.which("fakeroot")
        if fakeroot is None:
            raise SystemExit("dpkg-deb 不支持 --root-owner-group，且未安装 fakeroot")
        owner = "fakeroot"
        command = [fakeroot, "--", dpkg, "--build", "-Zxz", str(stage), str(output)]

    print("OWNER %s" % owner)
    result = subprocess.run(command)
    if result.returncode != 0:
        raise SystemExit("dpkg-deb 构建失败（退出码 %d）" % result.returncode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--arch", default=DEFAULT_ARCH, help="默认 all（纯 Python + 图片）")
    args = parser.parse_args()

    version = args.version.strip()
    arch = args.arch.strip()
    if not VERSION_RE.match(version):
        raise SystemExit("版本号不合法：%s（需以数字开头，只含 0-9 A-Z a-z . + ~ -）" % version)
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9-]*$", arch):
        raise SystemExit("架构名不合法：%s" % arch)

    stage = ROOT / ".build" / "linux" / "deb"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    root = stage / "root"
    app_dir = root / "usr" / "share" / "todo-quadrant"
    doc_dir = root / "usr" / "share" / "doc" / "todo-quadrant"
    desktop_dir = root / "usr" / "share" / "applications"
    icon_dir = root / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
    control_dir = root / "DEBIAN"
    for directory in (app_dir, doc_dir, desktop_dir, icon_dir, control_dir):
        directory.mkdir(parents=True, exist_ok=True)

    _copy_payload(app_dir)
    shutil.copy2(ROOT / "README.md", doc_dir / "README.md")
    shutil.copy2(DEB_DIR / "todo-quadrant.desktop", desktop_dir / "todo-quadrant.desktop")
    shutil.copy2(ROOT / "resources" / "todo-quadrant.png", icon_dir / "todo-quadrant.png")
    control = _render_control(version, arch, _maintainer())
    (control_dir / "control").write_text(control, encoding="utf-8")
    shutil.copy2(DEB_DIR / "postinst", control_dir / "postinst")

    _check_no_forbidden(stage)
    _apply_modes(root, {control_dir / "postinst"})

    output = ROOT / "dist" / "linux" / ("%s_%s_%s.deb" % (PACKAGE, version, arch))
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    _build(root, output)

    print("STAGE %s" % root)
    print("BUILT %s" % output)
    print("SIZE %d" % output.stat().st_size)
    print("SHA256 %s" % hashlib.sha256(output.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
