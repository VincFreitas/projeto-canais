# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
# Cria (ou remove, com -Remover) o atalho na pasta Inicializar do Windows que liga o n8n
# escondido no logon, para o workflow dos seus canais postar nos horários marcados.
# Rode você mesmo:  powershell -ExecutionPolicy Bypass -File .\n8n\iniciar-com-windows.ps1
param([switch]$Remover)

$pasta = [Environment]::GetFolderPath('Startup')
$atalho = Join-Path $pasta 'n8n (Projeto Canais).lnk'
# nome antigo do atalho (antes da v0.54.1): sai para não ligar o n8n duas vezes
Remove-Item (Join-Path $pasta 'n8n (Pulga do Saber).lnk') -ErrorAction SilentlyContinue

if ($Remover) {
    Remove-Item $atalho -ErrorAction SilentlyContinue
    Write-Host "Atalho removido: o n8n não inicia mais com o Windows."
    exit 0
}

$shell = New-Object -ComObject WScript.Shell
$s = $shell.CreateShortcut($atalho)
$s.TargetPath = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$lancador = Join-Path $PSScriptRoot 'n8n.ps1'
$s.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$lancador`" -NoOpen"
$s.WorkingDirectory = $PSScriptRoot
$s.WindowStyle = 7
$s.Description = 'Inicia o n8n no logon para a postagem automática do Projeto Canais'
$s.Save()
Write-Host "Pronto: o n8n vai iniciar sozinho no próximo logon ($atalho)."
