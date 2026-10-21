$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $py -m darkops @args
exit $LASTEXITCODE
