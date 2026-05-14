param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$CodexBase = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { $ProjectRoot }
$PreferredCodexHome = Join-Path $CodexBase "MarketBriefBot\codex"
try {
    New-Item -ItemType Directory -Force -Path $PreferredCodexHome | Out-Null
    $CodexHome = $PreferredCodexHome
}
catch {
    $CodexHome = Join-Path $ProjectRoot ".codex-runtime"
    New-Item -ItemType Directory -Force -Path $CodexHome | Out-Null
}
New-Item -ItemType Directory -Force -Path (Join-Path $CodexHome "sessions") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $CodexHome "tmp") | Out-Null

foreach ($ProxyName in @("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")) {
    $ProxyValue = [Environment]::GetEnvironmentVariable($ProxyName)
    if ($ProxyValue -and ($ProxyValue.Contains("127.0.0.1:9") -or $ProxyValue.Contains("localhost:9"))) {
        Remove-Item "Env:\$ProxyName" -ErrorAction SilentlyContinue
    }
}

$env:SUMMARY_PROVIDER = "codex"
$env:CODEX_MODEL = "gpt-5.2"
$env:CODEX_HOME = $CodexHome
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
