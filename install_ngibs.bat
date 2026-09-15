@echo off
setlocal EnableExtensions DisableDelayedExpansion

rem ===== User configuration =====
set "REPO_URL=https://github.com/avarshvir/NGIBS.git"
set "INSTALL_ROOT=%LOCALAPPDATA%\NGIBS"
set "REMOTE_APP_DIR=%INSTALL_ROOT%\app"
set "PYTHON_DOWNLOAD_VERSION=3.11.9"
set "PYTHON_MIN_MAJOR=3"
set "PYTHON_MIN_MINOR=10"
set "OLLAMA_MODEL=llama3.1:latest"
set "OLLAMA_PORT=11434"
set "PYTHON_INSTALLER=%TEMP%\ngibs-python-%PYTHON_DOWNLOAD_VERSION%.exe"
set "OLLAMA_INSTALLER=%TEMP%\ngibs-ollama-setup.exe"
set "SOURCE_ZIP=%TEMP%\ngibs-source.zip"
set "SOURCE_EXTRACT=%TEMP%\ngibs-source"

rem Use the checkout containing this script when it is available.
if exist "%~dp0main.py" (
    set "APP_DIR=%~dp0"
) else (
    set "APP_DIR=%REMOTE_APP_DIR%"
)
set "VENV_PY=%APP_DIR%\.venv\Scripts\python.exe"
set "OLLAMA_EXE="
set "PYTHON_EXE="

title NGIBS Setup
echo.
echo  NGIBS - first-run setup and launcher
echo  Application folder: %APP_DIR%
echo.

call :ensure_repository || goto :failed
call :ensure_python || goto :failed
call :ensure_ollama || goto :failed
call :ensure_model || goto :failed
call :ensure_virtualenv || goto :failed
call :ensure_dependencies || goto :failed
call :launch || goto :failed
exit /b 0

:ensure_repository
if exist "%APP_DIR%\main.py" exit /b 0

echo [1/6] Repository not found. Cloning it...
if not exist "%INSTALL_ROOT%" mkdir "%INSTALL_ROOT%" >nul 2>&1
where git >nul 2>&1
if errorlevel 1 (
    echo Git was not found. Downloading the repository archive instead...
    call :download "%SOURCE_ZIP%" "https://github.com/avarshvir/NGIBS/archive/refs/heads/main.zip" || exit /b 1
    if exist "%SOURCE_EXTRACT%" rmdir /s /q "%SOURCE_EXTRACT%"
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%SOURCE_ZIP%' -DestinationPath '%SOURCE_EXTRACT%' -Force"
    if errorlevel 1 (
        echo ERROR: The repository archive could not be extracted.
        exit /b 1
    )
    mkdir "%APP_DIR%" >nul 2>&1
    move "%SOURCE_EXTRACT%\NGIBS-main\*" "%APP_DIR%" >nul
    if not exist "%APP_DIR%\main.py" (
        echo ERROR: The repository archive did not contain main.py.
        exit /b 1
    )
    exit /b 0
)
if exist "%APP_DIR%" (
    echo ERROR: The target folder exists but does not contain main.py:
    echo        %APP_DIR%
    echo Remove or repair that folder, then run this file again.
    exit /b 1
)
git clone "%REPO_URL%" "%APP_DIR%"
if errorlevel 1 (
    echo ERROR: Repository cloning failed. Check your network connection.
    exit /b 1
)
if not exist "%APP_DIR%\main.py" (
    echo ERROR: The repository was cloned, but main.py is missing.
    exit /b 1
)
exit /b 0

:ensure_python
echo [2/6] Checking Python %PYTHON_MIN_MAJOR%.%PYTHON_MIN_MINOR% or newer...
call :find_python
if defined PYTHON_EXE exit /b 0

echo Python was not found. Downloading Python %PYTHON_DOWNLOAD_VERSION%...
call :download "%PYTHON_INSTALLER%" "https://www.python.org/ftp/python/%PYTHON_DOWNLOAD_VERSION%/python-%PYTHON_DOWNLOAD_VERSION%-amd64.exe" || exit /b 1
start /wait "NGIBS Python installer" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
if errorlevel 1 (
    echo ERROR: Python installation failed.
    exit /b 1
)
call :find_python
if not defined PYTHON_EXE (
    echo ERROR: Python was installed, but no usable Python interpreter was found.
    exit /b 1
)
exit /b 0

:find_python
set "PYTHON_EXE="
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (%PYTHON_MIN_MAJOR%, %PYTHON_MIN_MINOR%) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=py -3"
)
if defined PYTHON_EXE exit /b 0
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (%PYTHON_MIN_MAJOR%, %PYTHON_MIN_MINOR%) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=python"
)
exit /b 0

:ensure_ollama
echo [3/6] Checking Ollama...
call :find_ollama
if not defined OLLAMA_EXE (
    echo Ollama was not found. Downloading the official installer...
    call :download "%OLLAMA_INSTALLER%" "https://ollama.com/download/OllamaSetup.exe" || exit /b 1
    start /wait "NGIBS Ollama installer" "%OLLAMA_INSTALLER%" /SILENT /NORESTART
    if errorlevel 1 (
        echo ERROR: Ollama installation failed.
        exit /b 1
    )
    call :find_ollama
)
if not defined OLLAMA_EXE (
    echo ERROR: Ollama was installed, but ollama.exe was not found.
    exit /b 1
)

curl.exe -fsS "http://127.0.0.1:%OLLAMA_PORT%/api/tags" >nul 2>&1
if errorlevel 1 (
    echo Starting the Ollama service...
    start "NGIBS Ollama" /b "%OLLAMA_EXE%" serve
    call :wait_for_ollama
    if errorlevel 1 exit /b 1
)
exit /b 0

:wait_for_ollama
set /a OLLAMA_TRIES=0
:wait_for_ollama_loop
timeout /t 2 /nobreak >nul
curl.exe -fsS "http://127.0.0.1:%OLLAMA_PORT%/api/tags" >nul 2>&1
if not errorlevel 1 exit /b 0
set /a OLLAMA_TRIES+=1
if %OLLAMA_TRIES% GEQ 30 (
    echo ERROR: Ollama did not become ready on port %OLLAMA_PORT%.
    echo Start Ollama manually and run this file again.
    exit /b 1
)
goto wait_for_ollama_loop

:find_ollama
set "OLLAMA_EXE="
where ollama.exe >nul 2>&1
if not errorlevel 1 for /f "delims=" %%O in ('where ollama.exe') do if not defined OLLAMA_EXE set "OLLAMA_EXE=%%O"
if defined OLLAMA_EXE exit /b 0
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if defined OLLAMA_EXE exit /b 0
if exist "%ProgramFiles%\Ollama\ollama.exe" set "OLLAMA_EXE=%ProgramFiles%\Ollama\ollama.exe"
exit /b 0

:ensure_model
echo [4/6] Checking Ollama model %OLLAMA_MODEL%...
"%OLLAMA_EXE%" list 2>nul | findstr /b /c:"%OLLAMA_MODEL%" >nul
if not errorlevel 1 exit /b 0
echo Model is missing. Pulling %OLLAMA_MODEL%...
"%OLLAMA_EXE%" pull "%OLLAMA_MODEL%"
if errorlevel 1 (
    echo ERROR: Ollama could not download model %OLLAMA_MODEL%.
    exit /b 1
)
exit /b 0

:ensure_virtualenv
echo [5/6] Checking the application virtual environment...
if exist "%VENV_PY%" exit /b 0
%PYTHON_EXE% -m venv "%APP_DIR%\.venv"
if errorlevel 1 (
    echo ERROR: Could not create the Python virtual environment.
    exit /b 1
)
if not exist "%VENV_PY%" (
    echo ERROR: The virtual environment was created without a Python executable.
    exit /b 1
)
exit /b 0

:ensure_dependencies
echo [6/6] Checking Python dependencies...
"%VENV_PY%" -m pip install --disable-pip-version-check -r "%APP_DIR%\requirements.txt"
if errorlevel 1 (
    echo ERROR: Python dependencies could not be installed.
    exit /b 1
)
rem These two imports are used by main.py but are not direct requirements in older checkouts.
"%VENV_PY%" -c "import PyQt6, markdown" >nul 2>&1
if errorlevel 1 (
    echo Installing GUI runtime packages...
    "%VENV_PY%" -m pip install --disable-pip-version-check PyQt6 Markdown
    if errorlevel 1 (
        echo ERROR: GUI runtime packages could not be installed.
        exit /b 1
    )
)
exit /b 0

:download
set "DOWNLOAD_TARGET=%~1"
set "DOWNLOAD_URL=%~2"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing -Uri '%DOWNLOAD_URL%' -OutFile '%DOWNLOAD_TARGET%'; exit 0 } catch { Write-Error $_; exit 1 }"
if errorlevel 1 (
    echo ERROR: Download failed:
    echo        %DOWNLOAD_URL%
    exit /b 1
)
exit /b 0

:launch
echo.
echo NGIBS is ready. Launching the application...
pushd "%APP_DIR%" >nul
"%VENV_PY%" "%APP_DIR%\main.py"
set "APP_EXIT_CODE=%ERRORLEVEL%"
popd >nul
if not "%APP_EXIT_CODE%"=="0" (
    echo.
    echo ERROR: NGIBS exited with code %APP_EXIT_CODE%.
    pause
    exit /b 1
)
exit /b 0

:failed
echo.
echo Setup could not be completed. No application was launched.
pause
exit /b 1