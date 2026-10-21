# Cria (ou remove, com -Remover) o atalho na pasta Inicializar do Windows que liga o n8n
# escondido no logon, para o workflow do Pulga do Saber postar nos horários marcados.
# Rode você mesmo:  powershell -ExecutionPolicy Bypass -File .\n8n\iniciar-com-windows.ps1
param([switch]$Remover)

$atalho = Join-Path ([Environment]::GetFolderPath('Startup')) 'n8n (Pulga do Saber).lnk'

if ($Remover) {
    Remove-Item $atalho -ErrorAction SilentlyContinue
    Write-Host "Atalho removido: o n8n não inicia mais com o Windows."
    exit 0
}

$shell = New-Object -ComObject WScript.Shell
$s = $shell.CreateShortcut($atalho)
$s.TargetPath = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$s.Arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Users\Vinic\n8n\n8n.ps1" -NoOpen'
$s.WorkingDirectory = 'C:\Users\Vinic\n8n'
$s.WindowStyle = 7
$s.Description = 'Inicia o n8n no logon para a postagem automática do Pulga do Saber'
$s.Save()
Write-Host "Pronto: o n8n vai iniciar sozinho no próximo logon ($atalho)."
