param(
    [Parameter(Mandatory)][string]$Python,
    [Parameter(Mandatory)][string]$Iscc,
    [ValidatePattern('^\d+\.\d+\.\d+$')][string]$Version = '1.0.1'
)

$ErrorActionPreference = 'Stop'
$Python = (Resolve-Path -LiteralPath $Python).Path
$Iscc = (Resolve-Path -LiteralPath $Iscc).Path
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$build = Join-Path $root '.build/windows'

& $Python -c "import platform, sys; sys.exit(0 if sys.platform == 'win32' and platform.machine().upper() in ('AMD64', 'X86_64') and sys.maxsize > 2**32 else 'Windows x64 Python required')"
if ($LASTEXITCODE -ne 0) { throw 'Windows x64 Python required' }

$previousCache = $env:PYINSTALLER_CONFIG_DIR
try {
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $build 'cache'
    & $Python -m PyInstaller --clean --noconfirm --workpath (Join-Path $build 'work') --distpath (Join-Path $build 'dist') (Join-Path $PSScriptRoot 'TodoQuadrant.spec')
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed ($LASTEXITCODE)" }
}
finally {
    $env:PYINSTALLER_CONFIG_DIR = $previousCache
}

& $Iscc "/DAppVersion=$Version" (Join-Path $PSScriptRoot 'TodoQuadrant.iss')
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed ($LASTEXITCODE)" }
