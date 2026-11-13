# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $py -m darkops @args
exit $LASTEXITCODE
