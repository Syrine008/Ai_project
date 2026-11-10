$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (!(Test-Path -LiteralPath ".env")) { Copy-Item -LiteralPath ".env.example" -Destination ".env" }
if (!(Test-Path -LiteralPath "node_modules")) {
    npm.cmd ci --legacy-peer-deps
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
}
npm.cmd run dev
