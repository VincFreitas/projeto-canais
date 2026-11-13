# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
# Setup do canais-dark. Rode de novo para atualizar o yt-dlp (o YouTube muda com frequencia).
param([string]$Atalhos = "", [switch]$SemApps)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
function Falhou($msg) { Write-Host "ERRO: $msg"; exit 1 }  # codigo de saida != 0: agentes de IA e scripts sabem que parou

# Tudo que a automacao precisa e instalado sozinho, dentro da pasta do projeto (dados\apps): sem administrador,
# sem mexer no PATH e longe do AppData (o terminal do app Claude desvia o AppData para uma pasta virtual).
# Fica com o usuario so o que e conta: login do Claude Code, conta do n8n, chaves e contas das plataformas.
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$apps = Join-Path $PSScriptRoot "dados\apps"
$pythonVersao = "3.13.7"

if (-not (Test-Path ".venv")) {
    # "python" pode ser o atalho da Microsoft Store (nao instala nada); o "py" e o lancador do python.org
    $base = $null
    foreach ($c in @((Join-Path $apps "python\python.exe"), "python", "py")) {
        try { if ((& $c -c "import sys; print(sys.version_info >= (3, 11))" 2>$null) -eq "True") { $base = $c; break } } catch {}
    }
    if (-not $base) {
        # sem Python: instalador oficial do python.org, aceito so com a assinatura da Python Software Foundation
        Write-Host "Python nao encontrado: instalando o Python $pythonVersao na pasta do projeto (cerca de 30 MB)..."
        New-Item -ItemType Directory -Force $apps | Out-Null
        $instalador = Join-Path $apps "python-$pythonVersao-amd64.exe"
        Invoke-WebRequest "https://www.python.org/ftp/python/$pythonVersao/python-$pythonVersao-amd64.exe" -OutFile $instalador -UseBasicParsing
        $s = Get-AuthenticodeSignature -LiteralPath $instalador
        if ($s.Status -ne "Valid" -or $s.SignerCertificate.Subject -notmatch "Python Software Foundation") {
            Remove-Item $instalador; Falhou "o instalador do Python nao tem a assinatura da Python Software Foundation; descartado"
        }
        $alvo = Join-Path $apps "python"
        # WaitForExit, nao -Wait: o -Wait espera tambem os processos-filhos do instalador e pode nao voltar nunca
        $p = Start-Process $instalador -PassThru -ArgumentList @("/quiet", "InstallAllUsers=0", "TargetDir=`"$alvo`"",
            "PrependPath=0", "Include_launcher=0", "Shortcuts=0", "AssociateFiles=0", "Include_test=0", "Include_doc=0")
        if (-not $p.WaitForExit(900000)) { Falhou "o instalador do Python passou de 15 minutos" }
        Remove-Item $instalador -ErrorAction SilentlyContinue
        $base = Join-Path $alvo "python.exe"
        if ($p.ExitCode -or -not (Test-Path $base)) { Falhou "o instalador do Python terminou com erro ($($p.ExitCode))" }
    }
    & $base -m venv .venv
    if ($LASTEXITCODE) { Falhou "nao consegui criar o .venv" }
}
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $py -m pip install -q --upgrade pip
& $py -m pip install -q --upgrade -r requirements.txt
if ($LASTEXITCODE) { Falhou "pip nao instalou os pacotes de requirements.txt (veja a mensagem acima)" }
if (-not (Test-Path "assets/vozes/pt_BR-faber-medium.onnx")) {
    New-Item -ItemType Directory -Force "assets/vozes" | Out-Null
    & $py -c "from pathlib import Path; from piper.download_voices import download_voice; download_voice('pt_BR-faber-medium', Path('assets/vozes'))"
    if ($LASTEXITCODE) { Falhou "nao consegui baixar a voz offline (Piper); confira a internet e rode de novo" }
}
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

# Atalhos para abrir o Projeto Canais com um clique (dá para mudar depois em Estúdio > Configurações).
# Sem perguntar: .\instalar.ps1 -Atalhos "area,menu,barra"  (ou -Atalhos nenhum)
# Rodando por um agente de IA ou script (sem teclado), nao pergunta: cria na Area de Trabalho e no Menu Iniciar.
$semTeclado = [Console]::IsInputRedirected -or -not [Environment]::UserInteractive -or
    ([Environment]::GetCommandLineArgs() -match '^-NonI').Count -gt 0
if (-not $Atalhos -and $semTeclado) {
    $Atalhos = "area,menu"
    Write-Host "Sem terminal interativo: atalhos na Area de Trabalho e no Menu Iniciar (mude em Estudio > Configuracoes)."
}
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

# Node.js portatil, n8n (com o workflow importado e ligado, iniciando com o Windows) e Claude Code.
# Cada etapa e independente; o que falhar aparece no diagnostico e basta rodar o instalador de novo.
if (-not $SemApps) {
    & $py -m darkops instalar-apps
    $appsFalhou = [bool]$LASTEXITCODE
}
Write-Host ""
Write-Host "Pronto. Fica com voce so o que e conta:"
Write-Host "  1. Login do Claude Code: rode  claude  uma vez e entre na sua conta"
Write-Host "  2. Abra o atalho 'Projeto Canais' e siga o Progresso da configuracao (chaves e contas das plataformas)"
& $py -m darkops diagnostico
if ($appsFalhou) { exit 1 }
