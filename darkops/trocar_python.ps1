# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
# Troca o Python do app por uma versão nova da mesma série (instalador do python.org, assinatura já conferida por
# terceiros._preparar_python). Disparado pelo Estúdio livre (terceiros.trocar_python_agora): espera o Estúdio fechar,
# só instala se nenhum outro programa estiver usando este Python e abre o Estúdio de novo. O resultado fica em
# dados\rotinas\trocar-python.json e aparece em Saúde do app.
param(
    [int]$Esperar,
    [string]$Instalador,
    [string]$Base,
    [string]$Raiz,
    [string]$Pythonw
)
$ErrorActionPreference = 'Continue'
$registro = Join-Path $Raiz 'dados\rotinas\trocar-python.json'

function Gravar([string]$situacao, [string]$texto) {
    $dados = @{ situacao = $situacao; texto = $texto; quando = (Get-Date).ToString('s') }
    $dados | ConvertTo-Json | Set-Content -LiteralPath $registro -Encoding UTF8
}

try { Wait-Process -Id $Esperar -Timeout 120 -ErrorAction SilentlyContinue } catch { }
Start-Sleep -Seconds 2

$dll = Get-ChildItem -LiteralPath $Base -Filter 'python3*.dll' | Where-Object { $_.Name -ne 'python3.dll' } |
    Select-Object -First 1
# Quem usa este Python agora. Os apps de Python do próprio usuário sem janela (pythonw de um .venv, como o Estúdio e o
# app de e-mails) são fechados e reabertos do mesmo jeito em volta da troca; qualquer outro uso (um terminal, uma tarefa
# rodando) adia a troca para o dia seguinte.
$reabrir = @{}
$bloqueiam = @()
if ($dll) {
    $usando = @(Get-Process | Where-Object {
        try { $_.Modules | Where-Object { $_.FileName -eq $dll.FullName } } catch { $null }
    })
    foreach ($p in $usando) {
        $eu = Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)"
        $pai = if ($eu) { Get-CimInstance Win32_Process -Filter "ProcessId = $($eu.ParentProcessId)" } else { $null }
        # no Windows o pythonw do .venv é um lançador: quem carrega o Python é o filho dele
        $app = @($pai, $eu) | Where-Object { $_ -and $_.ExecutablePath -like '*\.venv\Scripts\pythonw.exe' } |
            Select-Object -First 1
        if ($app) { $reabrir[$app.ProcessId] = $app } else { $bloqueiam += $p.ProcessName }
    }
}

if ($bloqueiam.Count -gt 0) {
    Gravar 'adiado' ("outro programa está usando o Python agora (" + (($bloqueiam | Select-Object -Unique) -join ', ') + "); tento de novo amanhã")
    $reabrir = @{}
} else {
    foreach ($app in $reabrir.Values) { & taskkill /PID $app.ProcessId /T /F | Out-Null }
    Start-Sleep -Seconds 2
    $p = Start-Process -FilePath $Instalador -ArgumentList '/quiet' -Wait -PassThru
    if ($p.ExitCode -eq 0 -or $p.ExitCode -eq 3010) {
        & (Join-Path $Base 'python.exe') -m venv --upgrade (Join-Path $Raiz '.venv') | Out-Null
        $versao = & (Join-Path $Base 'python.exe') -c "import platform; print(platform.python_version())"
        $texto = "Python atualizado para a $versao"
        if ($p.ExitCode -eq 3010) { $texto += '; reinicie o PC para terminar' }
        if ($reabrir.Count -gt 0) { $texto += ' (' + $reabrir.Count + ' app(s) de Python reaberto(s))' }
        Gravar 'ok' $texto
        Remove-Item -LiteralPath $Instalador -ErrorAction SilentlyContinue
    } else {
        Gravar 'falhou' ("o instalador do Python saiu com o código " + $p.ExitCode + "; o Python anterior continua")
    }
}

# reabre os outros apps de Python do usuário como estavam (o Estúdio é reaberto logo abaixo)
foreach ($app in $reabrir.Values) {
    $linha = $app.CommandLine
    if (-not $linha -or $linha -match '-m\s+darkops\s+(abrir|estudio)') { continue }
    $resto = if ($linha.StartsWith('"')) { $linha.Substring($linha.IndexOf('"', 1) + 1) } else {
        $i = $linha.IndexOf(' '); if ($i -lt 0) { '' } else { $linha.Substring($i) } }
    $pasta = Split-Path (Split-Path (Split-Path $app.ExecutablePath))
    if ($resto.Trim()) {
        Start-Process -FilePath $app.ExecutablePath -ArgumentList $resto.Trim() -WorkingDirectory $pasta
    } else {
        Start-Process -FilePath $app.ExecutablePath -WorkingDirectory $pasta
    }
}

$env:DARKOPS_REINICIO = '1'
Start-Process -FilePath $Pythonw -ArgumentList '-m', 'darkops', 'abrir' -WorkingDirectory $Raiz
