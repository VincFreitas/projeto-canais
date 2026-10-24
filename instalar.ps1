# Setup do canais-dark. Rode de novo para atualizar o yt-dlp (o YouTube muda com frequencia).
param([string]$Atalhos = "")
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

# Atalhos para abrir o Projeto Canais com um clique (dá para mudar depois em Estúdio > Configurações).
# Sem perguntar: .\instalar.ps1 -Atalhos "area,menu,barra"  (ou -Atalhos nenhum)
if (-not $Atalhos) {
    Write-Host ""
    Write-Host "Onde criar o atalho do Projeto Canais?"
    $area = Read-Host "  Na Area de Trabalho? (S/n)"
    $menu = Read-Host "  No Menu Iniciar? (S/n)"
    $barra = Read-Host "  Quer fixar na barra de tarefas? (s/N)"
    $Atalhos = @()
    if ($area -notmatch '^[nN]') { $Atalhos += 'area' }
    if ($menu -notmatch '^[nN]') { $Atalhos += 'menu' }
    if ($barra -match '^[sS]') { $Atalhos += 'barra' }
    $Atalhos = $Atalhos -join ','
}
$opcoes = @()
if ($Atalhos -match 'area') { $opcoes += '--area-de-trabalho' }
if ($Atalhos -match 'menu') { $opcoes += '--menu-iniciar' }
if ($Atalhos -match 'barra') { $opcoes += '--barra-de-tarefas' }
if ($opcoes.Count -gt 0) { & $py -m darkops atalhos @opcoes }
Write-Host ""
Write-Host "Pronto. Proximos passos:"
Write-Host "  Atalho 'Projeto Canais' (ou: .\.venv\Scripts\python.exe -m darkops abrir)   abre o painel"
Write-Host "  .\.venv\Scripts\python.exe -m darkops diagnostico   (o que falta configurar)"
& $py -m darkops diagnostico
