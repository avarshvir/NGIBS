@echo off
setlocal enabledelayedexpansion

set "APP_DIR=%~dp0"
set "APP_EXE=%APP_DIR%NGIBS.exe"
set "DEFAULT_MODEL=llama3.1:latest"

echo ============================================
echo NGIBS Windows bootstrap
echo ============================================

where ollama >nul 2>nul
if errorlevel 1 (
    echo Ollama not found. Installing Ollama...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue';" ^
    "$url = 'https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip';" ^
    "$zip = Join-Path $env:TEMP 'ollama-windows-amd64.zip';" ^
    "Invoke-WebRequest -Uri $url -OutFile $zip;" ^
    "$dest = Join-Path $env:TEMP 'ollama-install';" ^
    "if (!(Test-Path $dest)) { New-Item -ItemType Directory -Path $dest | Out-Null };" ^
    "Expand-Archive -Path $zip -DestinationPath $dest -Force;" ^
    "$exe = Join-Path $dest 'ollama.exe';" ^
    "if (Test-Path $exe) { Start-Process -FilePath $exe -ArgumentList '/S' -Wait -NoNewWindow };" ^
    "Start-Sleep -Seconds 5"
) else (
    echo Ollama already installed. Skipping install.
)

rem Ensure Ollama is on PATH even if installed in Program Files
set "OLLAMA_PATH=C:\Program Files\Ollama\ollama.exe"
if exist "%OLLAMA_PATH%" set "PATH=%PATH%;C:\Program Files\Ollama"
if exist "%USERPROFILE%\AppData\Local\Programs\Ollama\ollama.exe" set "PATH=%PATH%;%USERPROFILE%\AppData\Local\Programs\Ollama"

where ollama >nul 2>nul
if errorlevel 1 (
    echo Ollama still not found in PATH. Please install it manually.
    pause
    exit /b 1
)

echo Checking default model: %DEFAULT_MODEL%
ollama list 2>nul | findstr /C:"%DEFAULT_MODEL%" >nul
if errorlevel 1 (
    echo Model not found. Pulling default model...
    ollama pull %DEFAULT_MODEL%
) else (
    echo Default model already present. Skipping pull.
)

if not exist "%APP_EXE%" (
    echo ERROR: NGIBS.exe was not found in this release folder.
    echo Expected: "%APP_EXE%"
    pause
    exit /b 1
)

echo Launching NGIBS...
start "" "%APP_EXE%"
exit /b 0