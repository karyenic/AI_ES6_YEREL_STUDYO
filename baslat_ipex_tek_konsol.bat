@echo off
chcp 65001 >nul
setlocal EnableExtensions

title GK AI STUDIO - Intel Arc IPEX
set "STUDIO=C:\AI_YEREL\AI_ES6_YEREL_STUDYO"
set "IPEX_DIR=C:\AI_IPEX\Ollama\portable"
set "RUNNER=%IPEX_DIR%\ollama-lib.exe"
set "MODEL=C:\Users\karye\.ollama\models\blobs\sha256-60e05f2100071479f596b964f89f510f057ce397ea22f2833a0cfe029bfc2463"
set "RUNNER_PORT=59584"
set "BRIDGE_PORT=11434"
set "FLASK_PORT=5000"
set "LOG_DIR=%STUDIO%\logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
cd /d "%STUDIO%" || goto :FAIL

set "NO_PROXY=localhost,127.0.0.1"
set "no_proxy=localhost,127.0.0.1"
set "ZES_ENABLE_SYSMAN=1"
set "ONEAPI_DEVICE_SELECTOR=level_zero:0"
set "SYCL_CACHE_PERSISTENT=1"
set "OLLAMA_NUM_GPU=999"
set "OLLAMA_FLASH_ATTENTION=false"

cls
echo ============================================================
echo       GK AI STUDIO - INTEL ARC IPEX
echo ============================================================
echo.

echo [1/4] IPEX runner kontrol ediliyor...
set "RUNNER_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%RUNNER_PORT% .*LISTENING"') do set "RUNNER_PID=%%P"
if defined RUNNER_PID (
  echo [OK] Mevcut IPEX runner: PID %RUNNER_PID%
) else (
  if not exist "%RUNNER%" goto :RUNNER_ERROR
  if not exist "%MODEL%" goto :MODEL_ERROR
  echo [..] IPEX runner arka planda baslatiliyor...
  start "" /b powershell -NoProfile -WindowStyle Hidden -Command "$p=Start-Process -FilePath '%RUNNER%' -ArgumentList 'runner','--model','%MODEL%','--ctx-size','4096','--batch-size','512','--n-gpu-layers','999','--threads','4','--no-mmap','--parallel','1','--port','%RUNNER_PORT%','--verbose' -WorkingDirectory '%IPEX_DIR%' -RedirectStandardOutput '%LOG_DIR%\ipex_runner.log' -RedirectStandardError '%LOG_DIR%\ipex_runner_error.log' -PassThru; Set-Content -LiteralPath '%LOG_DIR%\ipex_runner.pid' -Value $p.Id -Encoding ascii"
)

echo [2/4] Runner hazirligi kontrol ediliyor...
set "READY="
for /l %%N in (1,1,45) do (
  if not defined READY (
    curl -s --max-time 2 http://127.0.0.1:%RUNNER_PORT%/health | findstr /C:"\"status\":0" >nul 2>&1 && set "READY=1"
    if not defined READY timeout /t 1 /nobreak >nul
  )
)
if not defined READY goto :RUNNER_TIMEOUT
echo [OK] IPEX runner hazir: 127.0.0.1:%RUNNER_PORT%
echo.

echo [3/4] API bridge kontrol ediliyor...
set "BRIDGE_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%BRIDGE_PORT% .*LISTENING"') do set "BRIDGE_PID=%%P"
if defined BRIDGE_PID (
  echo [OK] 11434 zaten kullanimda: PID %BRIDGE_PID%
) else (
  if not exist "%STUDIO%\ai_bridge.py" goto :BRIDGE_ERROR
  echo [..] IPEX bridge arka planda baslatiliyor...
  start "" /b powershell -NoProfile -WindowStyle Hidden -Command "$p=Start-Process -FilePath 'python' -ArgumentList 'ai_bridge.py' -WorkingDirectory '%STUDIO%' -RedirectStandardOutput '%LOG_DIR%\ai_bridge.log' -RedirectStandardError '%LOG_DIR%\ai_bridge_error.log' -PassThru; Set-Content -LiteralPath '%LOG_DIR%\ai_bridge.pid' -Value $p.Id -Encoding ascii"
  timeout /t 2 /nobreak >nul
)
curl -s --max-time 3 http://127.0.0.1:%BRIDGE_PORT%/api/version >nul 2>&1 || goto :BRIDGE_TIMEOUT
echo [OK] API bridge hazir: 127.0.0.1:%BRIDGE_PORT%
echo.

echo [4/4] GK AI STUDIO baslatiliyor...
echo.
echo ============================================================
echo   Runner : 127.0.0.1:%RUNNER_PORT%
echo   Bridge : 127.0.0.1:%BRIDGE_PORT%
echo   Studio : 127.0.0.1:%FLASK_PORT%
echo   Ekranda tek konsol acik kalir.
echo ============================================================
echo.
start "" http://127.0.0.1:%FLASK_PORT%
python app.py

call :STOP_OWNED_PROCESS "%LOG_DIR%\ai_bridge.pid" "AI Bridge"
call :STOP_OWNED_PROCESS "%LOG_DIR%\ipex_runner.pid" "IPEX Runner"
echo.
echo Temizlik tamamlandi.
pause
exit /b 0

:STOP_OWNED_PROCESS
set "PIDFILE=%~1"
set "LABEL=%~2"
if not exist "%PIDFILE%" exit /b 0
set /p PID=<"%PIDFILE%"
if defined PID (
  tasklist /FI "PID eq %PID%" | findstr /I /C:"%PID%" >nul 2>&1
  if not errorlevel 1 taskkill /PID %PID% /F >nul 2>&1
  echo [OK] %LABEL% kapatildi (PID %PID%)
)
del /q "%PIDFILE%" >nul 2>&1
exit /b 0

:RUNNER_ERROR
echo [HATA] IPEX runner bulunamadi: %RUNNER%
goto :FAIL
:MODEL_ERROR
echo [HATA] Qwen model blob bulunamadi: %MODEL%
goto :FAIL
:RUNNER_TIMEOUT
echo [HATA] IPEX runner 45 saniye icinde hazir olmadi.
echo Log: %LOG_DIR%\ipex_runner.log
goto :FAIL
:BRIDGE_ERROR
echo [HATA] ai_bridge.py bulunamadi: %STUDIO%\ai_bridge.py
goto :FAIL
:BRIDGE_TIMEOUT
echo [HATA] API bridge 11434'te hazir olmadi.
echo Log: %LOG_DIR%\ai_bridge.log
goto :FAIL
:FAIL
echo.
echo Baslatma basarisiz.
pause
exit /b 1
