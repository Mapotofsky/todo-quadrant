from pathlib import Path

root = Path(SPECPATH).resolve().parents[1]
analysis = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    datas=[
        (str(root / "resources" / "style.qss"), "resources"),
        (str(root / "resources" / "todo-quadrant.png"), "resources"),
    ],
)
archive = PYZ(analysis.pure)
exe = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="TodoQuadrant",
    icon=str(Path(SPECPATH) / "TodoQuadrant.ico"),
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
