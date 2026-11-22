from pathlib import Path

root = Path(SPECPATH).resolve().parents[1]
analysis = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    datas=[(str(root / "resources" / "style.qss"), "resources")],
)
archive = PYZ(analysis.pure)
exe = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="TodoQuadrant",
    console=False,
    upx=False,
)
bundle = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    name="TodoQuadrant",
    upx=False,
)
