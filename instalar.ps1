# Setup do canais-dark. Rode de novo para atualizar o yt-dlp (o YouTube muda com frequencia).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv")) { python -m venv .venv }
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $py -m pip install -q --upgrade pip
& $py -m pip install -q --upgrade -r requirements.txt
if (-not (Test-Path "assets/vozes/pt_BR-faber-medium.onnx")) {
    New-Item -ItemType Directory -Force "assets/vozes" | Out-Null
    & $py -c "from pathlib import Path; from piper.download_voices import download_voice; download_voice('pt_BR-faber-medium', Path('assets/vozes'))"
}
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
Write-Host "Pronto. Teste com: .\dark.ps1 nichos"
