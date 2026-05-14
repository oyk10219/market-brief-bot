param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$env:SUMMARY_PROVIDER = "codex"
$env:CODEX_MODEL = "gpt-5.2"
$env:PYTHONDONTWRITEBYTECODE = "1"

$PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python virtual environment not found: $PythonPath"
}

$RunArgs = @("-m", "src.main", "--debug", "--save-md")
if ($DryRun) {
    $RunArgs += "--dry-run"
}

& $PythonPath @RunArgs
exit $LASTEXITCODE
