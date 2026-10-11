$ErrorActionPreference = 'Stop'
$appRoot = $PSScriptRoot
$python = Join-Path $env:LOCALAPPDATA '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$pythonPrefix = @()
if (-not (Test-Path -LiteralPath $python)) {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) { $python = $launcher.Source; $pythonPrefix = @('-3') }
    else {
        $installed = Get-Command python.exe -ErrorAction SilentlyContinue | Where-Object { $_.Source -notlike '*WindowsApps*' } | Select-Object -First 1
        if ($installed) { $python = $installed.Source }
        else { throw 'Python 3.10+ was not found. Install Python or use the Python runtime included with Codex.' }
    }
}

$securePassword = Read-Host 'Choose your PortfolioOS editor password' -AsSecureString
$passwordPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try { $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPtr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPtr) }
if ($password.Length -lt 14) { throw 'Use a password with at least 14 characters, then run this launcher again.' }

$sessionSecret = (& $python @pythonPrefix -c 'import secrets; print(secrets.token_urlsafe(48))').Trim()
if (-not $sessionSecret) { throw 'Could not create a session secret.' }
$dataDir = Join-Path $env:LOCALAPPDATA 'PortfolioOS'
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
$env:PORTFOLIO_ADMIN_PASSWORD = $password
$env:PORTFOLIO_SESSION_SECRET = $sessionSecret
$env:DATABASE_PATH = Join-Path $dataDir 'portfolioos.db'
$env:PORT = '8000'
Write-Host ''
Write-Host 'PortfolioOS is starting. Keep this PowerShell window open.' -ForegroundColor Cyan
Write-Host 'Owner dashboard: http://localhost:8000/' -ForegroundColor Green
Write-Host 'Public portfolio: http://localhost:8000/portfolio' -ForegroundColor Green
Write-Host 'Press Ctrl+C in this window to stop the server.'
Write-Host ''
& $python @pythonPrefix (Join-Path $appRoot 'server.py')



