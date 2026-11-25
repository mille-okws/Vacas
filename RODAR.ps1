# Uso: .\RODAR.ps1            (abre o app no navegador)
#      .\RODAR.ps1 -Porta 8791
# Cria o ambiente Python, instala e abre o Vacas V2. A interface ja vem compilada (nao precisa de Node).
# (Texto sem acentos de proposito: o PowerShell 5.1 le .ps1 sem BOM como ANSI.)
param([int]$Porta = 8790)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python 3.11 ou superior nao foi encontrado. Instale Python e habilite o comando python.'
}
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    python -m venv .venv
}

$Python = Join-Path $Root '.venv\Scripts\python.exe'
& $Python -m pip install --disable-pip-version-check -e .
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependencias.' }

$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
& $Python -m vacas app --port $Porta
exit $LASTEXITCODE