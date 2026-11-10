# Start both local servers. Ctrl+C stops the frontend and its backend.
$ErrorActionPreference = 'Stop'
$env:DJANGO_DEBUG = '1'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot 'backend\.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python)) { throw 'Missing backend virtual environment. See RUN_LOCAL.md.' }
if (!(Test-Path -LiteralPath 'node_modules')) { throw 'Missing frontend dependencies. Run npm.cmd install first.' }
if (!(Test-Path -LiteralPath '.env')) { Set-Content -LiteralPath '.env' -Value 'VITE_API_BASE_URL=http://127.0.0.1:8000' }
& $python backend\manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
$api = Start-Process -FilePath $python -ArgumentList @('manage.py', 'runserver', '127.0.0.1:8000', '--noreload') -WorkingDirectory (Join-Path $PSScriptRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'backend-stdout.log') -RedirectStandardError (Join-Path $PSScriptRoot 'backend-stderr.log')
try {
    Start-Sleep -Seconds 2
    if ($api.HasExited) { throw 'Backend failed to start. See backend-stderr.log.' }
    Write-Host 'Open http://127.0.0.1:8080/axes/cerebellar-dysfunction'
    npm.cmd run dev -- --host 127.0.0.1 --port 8080 --strictPort
} finally {
    if (!$api.HasExited) { Stop-Process -Id $api.Id }
}
