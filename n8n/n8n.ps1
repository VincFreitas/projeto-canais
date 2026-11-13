# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
# Lancador do n8n (instalado via npm global).
# Uso:  powershell -ExecutionPolicy Bypass -File n8n\n8n.ps1          -> inicia e abre o navegador
#       powershell -ExecutionPolicy Bypass -File n8n\n8n.ps1 -NoOpen  -> inicia sem abrir o navegador
param([switch]$NoOpen)

# Escuta so em loopback: ninguem da rede local acessa o editor.
$env:N8N_LISTEN_ADDRESS = '127.0.0.1'
$env:N8N_HOST = 'localhost'
$env:N8N_PORT = '5678'
$env:N8N_PROTOCOL = 'http'
$env:WEBHOOK_URL = 'http://localhost:5678/'

# Fuso dos gatilhos de agenda. Troque se precisar (lista: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).
$env:GENERIC_TIMEZONE = 'America/Sao_Paulo'
$env:TZ = 'America/Sao_Paulo'

# Sem telemetria nem avisos de versao.
$env:N8N_DIAGNOSTICS_ENABLED = 'false'
$env:N8N_VERSION_NOTIFICATIONS_ENABLED = 'false'
$env:N8N_PERSONALIZATION_ENABLED = 'false'

# Libera o no Execute Command (desligado por padrao no n8n 2.x) para o workflow do
# canais-dark rodar o pipeline Python local. Seguro aqui porque o editor so escuta em
# 127.0.0.1. O Local File Trigger continua bloqueado.
$env:NODES_EXCLUDE = '["n8n-nodes-base.localFileTrigger"]'
$env:PYTHONIOENCODING = 'utf-8'

# Limpa execucoes antigas para o SQLite nao crescer sem limite (14 dias).
$env:EXECUTIONS_DATA_PRUNE = 'true'
$env:EXECUTIONS_DATA_MAX_AGE = '336'

# Primeiro o n8n e o Node da pasta do projeto (python -m darkops instalar-apps): todo processo do Windows enxerga.
$apps = Join-Path (Split-Path $PSScriptRoot -Parent) 'dados\apps'
if (Test-Path (Join-Path $apps 'node\node.exe')) { $env:PATH = (Join-Path $apps 'node') + ';' + $env:PATH }
$n8n = Join-Path $apps 'n8n\node_modules\.bin\n8n.cmd'
if (-not (Test-Path $n8n)) { $n8n = Join-Path $env:APPDATA 'npm\n8n.cmd' }
if (-not (Test-Path $n8n)) {
    # instalado pelo terminal do app Claude (pacote MSIX): fica na pasta virtual do pacote, invisivel fora dele
    $virtual = Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Packages\Claude_*\LocalCache\Roaming\npm\n8n.cmd') -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($virtual) { $n8n = $virtual.FullName }
}
if (-not (Test-Path $n8n)) { Write-Error "n8n nao encontrado. Rode: .\.venv\Scripts\python.exe -m darkops instalar-apps"; exit 1 }

# Abertura mais rapida (medida com o disco ja aquecido; detalhes em n8n/acelerar.cjs):
# 1) desliga os modulos que o workflow nao usa (IA, MCP, chat, insights, tabelas). So entram os nomes que a
#    versao instalada conhece: um nome que ela nao conhece faria o n8n recusar abrir depois de uma atualizacao.
$pacote = Join-Path (Split-Path (Split-Path $n8n -Parent) -Parent) 'n8n'
$lista = Join-Path (Split-Path $pacote -Parent) '@n8n\backend-common\dist\modules\modules.config.js'
if (Test-Path $lista) {
    $conhecidos = [regex]::Matches((Get-Content $lista -Raw), "'([a-z0-9-]+)'") | ForEach-Object { $_.Groups[1].Value }
    $sem_uso = 'agents', 'agent-evals', 'insights', 'chat-hub', 'mcp', 'mcp-discovery', 'mcp-registry', 'instance-ai',
               'workflow-builder', 'quick-connect', 'data-table', 'inbox', 'otel'
    $env:N8N_DISABLED_MODULES = ($sem_uso | Where-Object { $conhecidos -contains $_ }) -join ','
}
# 2) cache de onde o Node acha cada modulo (n8n\acelerar.cjs). O nome muda com a versao do n8n e com a data
#    do .package-lock.json (o npm reescreve a cada instalacao); os caches velhos sao apagados.
$trava = Join-Path (Split-Path $pacote -Parent) '.package-lock.json'
if ((Test-Path (Join-Path $pacote 'package.json')) -and (Test-Path $trava)) {
    $versao = (Get-Content (Join-Path $pacote 'package.json') -Raw | ConvertFrom-Json).version
    $chave = "$versao-$((Get-Item $trava).LastWriteTimeUtc.Ticks)"
    $caches = Join-Path (Split-Path $PSScriptRoot -Parent) 'dados\cache'
    Get-ChildItem $caches -Filter 'n8n-modulos-*.json' -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -ne "n8n-modulos-$chave.json" } | Remove-Item -ErrorAction SilentlyContinue
    $env:DARKOPS_CACHE_N8N = Join-Path $caches "n8n-modulos-$chave.json"
    # barras normais: dentro das aspas do NODE_OPTIONS o Node trata a barra invertida como escape
    $env:NODE_OPTIONS = "--require `"$((Join-Path $PSScriptRoot 'acelerar.cjs') -replace '\\', '/')`""
}

if (Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host 'n8n ja esta rodando em http://localhost:5678'
    if (-not $NoOpen) { Start-Process 'http://localhost:5678' }
    exit 0
}

if (-not $NoOpen) {
    Start-Job -ScriptBlock {
        for ($i = 0; $i -lt 600; $i++) {  # logo depois de ligar o PC o n8n pode levar minutos
            Start-Sleep -Seconds 1
            try { Invoke-WebRequest 'http://localhost:5678/healthz' -UseBasicParsing -TimeoutSec 2 | Out-Null; Start-Process 'http://localhost:5678'; break } catch {}
        }
    } | Out-Null
}

$inicio = Get-Date
& $n8n start
if ($LASTEXITCODE -ne 0 -and $env:DARKOPS_CACHE_N8N -and ((Get-Date) - $inicio).TotalSeconds -lt 180) {
    # caiu logo ao abrir: o acelerar.cjs ja apagou o cache; tenta uma vez do jeito normal
    Remove-Item Env:NODE_OPTIONS, Env:DARKOPS_CACHE_N8N -ErrorAction SilentlyContinue
    & $n8n start
}
