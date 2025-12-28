# PowerShell runner: creates .venv and installs requirements if needed, then runs the app
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$venv = Join-Path $root '.venv'
$pythonExe = Join-Path $venv 'Scripts\python.exe'














& $pythonExe (Join-Path $root 'run.py')# Run the application using the venv python (no activation required)}    Write-Host 'Using existing virtual environment.'} else {    & $pythonExe -m pip install -r (Join-Path $root 'requirements.txt')    Write-Host 'Installing requirements...'    & $pythonExe -m pip install --upgrade pip    Write-Host 'Upgrading pip...'    python -m venv $venv    Write-Host 'Creating virtual environment...' if (-not (Test-Path $pythonExe)) {