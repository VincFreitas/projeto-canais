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

$n8n = Join-Path $env:APPDATA 'npm\n8n.cmd'
if (-not (Test-Path $n8n)) { Write-Error "n8n nao encontrado em $n8n. Rode: npm install -g n8n"; exit 1 }

if (Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host 'n8n ja esta rodando em http://localhost:5678'
    if (-not $NoOpen) { Start-Process 'http://localhost:5678' }
    exit 0
}

if (-not $NoOpen) {
    Start-Job -ScriptBlock {
        for ($i = 0; $i -lt 120; $i++) {
            Start-Sleep -Seconds 1
            try { Invoke-WebRequest 'http://localhost:5678/healthz' -UseBasicParsing -TimeoutSec 2 | Out-Null; Start-Process 'http://localhost:5678'; break } catch {}
        }
    } | Out-Null
}

& $n8n start
