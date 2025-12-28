@echo off
setlocal
















:: Create venv and install requirements if missing
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    echo Upgrading pip...
    .venv\Scripts\python -m pip install --upgrade pip
    echo Installing requirements...
    .venv\Scripts\python -m pip install -r requirements.txt
) else (
    echo Using existing virtual environment.
)

call .venv\Scripts\activate
python run.py
endlocal