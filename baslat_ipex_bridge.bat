@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

title GK AI STUDIO - Intel Arc IPEX
cd /d "C:\AI_YEREL\AI_ES6_YEREL_STUDYO" || goto :error_studio

set "STUDIO=C:\AI_YEREL\AI_ES6_YEREL_STUDYO"
set "IPEX_DIR=C:\AI_IPEX\Ollama\portable"
set "RUNNER=%IPEX_DIR%\ollama-lib.exe"
set "MODEL=C:\Users\karye\.ollama\models\blobs\sha256-60e05f2100071479f596b964f89f510f057ce397ea22f2833a0cfe029bfc2463"
set "RUNNER_PORT=59584"
set "BRIDGE_PORT=11434"
set "STUDIO_PORT=5000"
set "GK_IPEX_MODEL=qwen2.5-coder:7b"
set "GK_IPEX_CTX=4096"
set "GK_IPEX_N_PREDICT=512"
set "OLLAMA_NUM_GPU=999"
set "ONEAPI_DEVICE_SELECTOR=level_zero:0"
set "ZES_ENABLE_SYSMAN=1"
set "SYCL_CACHE_PERSISTENT=1"
set "OLLAMA_FLASH_ATTENTION=false"
set "NO_PROXY=localhost,127.0.0.1"
set "no_proxy=localhost,127.0.0.1"

set "RUNNER_STARTED=0"
set "BRIDGE_STARTED=0"
set "STUDIO_STARTED=0"

cls
echo ============================================================
echo   GK AI STUDIO - INTEL ARC IPEX
 echo ============================================================
echo.
echo [KONTROL] Dizinler ve dosyalar kontrol ediliyor...
if not exist "%RUNNER%" goto :error_runner_file
if not exist "%MODEL%" goto :error_model_file
if not exist "%STUDIO%\ai_bridge.py" goto :error_bridge_file
if not exist "%STUDIO%\app.py" goto :error_app_file
echo [OK] Dosyalar hazir.
echo.

echo [1/3] IPEX runner kontrol ediliyor...
set "RUNNER_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%RUNNER_PORT% .*LISTENING"') do if not defined RUNNER_PID set "RUNNER_PID=%%P"
if defined RUNNER_PID (
    echo [OK] Mevcut IPEX runner bulundu: PID !RUNNER_PID!
) else (
    echo [..] IPEX GPU runner arka planda baslatiliyor...
    start "" /b "%RUNNER%" runner --model "%MODEL%" --ctx-size %GK_IPEX_CTX% --batch-size 512 --n-gpu-layers 999 --threads 4 --no-mmap --parallel 1 --port %RUNNER_PORT% --verbose > "%STUDIO%\ipex_runner.log" 2>&1
    set "RUNNER_STARTED=1"
)

set "READY="
for /l %%N in (1,1,30) do (
    if not defined READY (
        curl -s --max-time 2 http://127.0.0.1:%RUNNER_PORT%/health | findstr /C:"\"status\":0" >nul 2>&1 && set "READY=1"
        if not defined READY timeout /t 1 /nobreak >nul
    )
)
if not defined READY goto :error_runner_ready
echo [OK] IPEX runner hazir: 127.0.0.1:%RUNNER_PORT%
echo.

echo [2/3] IPEX API bridge kontrol ediliyor...
set "BRIDGE_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%BRIDGE_PORT% .*LISTENING"') do if not defined BRIDGE_PID set "BRIDGE_PID=%%P"
if defined BRIDGE_PID (
    echo [OK] 11434 zaten aktif: PID !BRIDGE_PID!
) else (
    echo [..] Bridge arka planda baslatiliyor...
    start "" /b cmd /c "cd /d "%STUDIO%" && set GK_IPEX_RUNNER_URL=http://127.0.0.1:%RUNNER_PORT% && set GK_BRIDGE_PORT=%BRIDGE_PORT% && set GK_IPEX_MODEL=%GK_IPEX_MODEL% && set GK_IPEX_CTX=%GK_IPEX_CTX% && set GK_IPEX_N_PREDICT=%GK_IPEX_N_PREDICT% && python ai_bridge.py > "%STUDIO%\ai_bridge.log" 2>&1"
    set "BRIDGE_STARTED=1"
)

set "BRIDGE_READY="
for /l %%N in (1,1,15) do (
    if not defined BRIDGE_READY (
        curl -s --max-time 2 http://127.0.0.1:%BRIDGE_PORT%/api/version >nul 2>&1 && set "BRIDGE_READY=1"
        if not defined BRIDGE_READY timeout /t 1 /nobreak >nul
    )
)
if not defined BRIDGE_READY goto :error_bridge_ready
echo [OK] Bridge hazir: 127.0.0.1:%BRIDGE_PORT%
echo.

echo [3/3] GK AI STUDIO baslatiliyor...
start "" /b cmd /c "cd /d "%STUDIO%" && python app.py > "%STUDIO%\studio.log" 2>&1"
set "STUDIO_STARTED=1"

timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:%STUDIO_PORT%
echo [OK] Studio: 127.0.0.1:%STUDIO_PORT%
echo.
echo ============================================================
echo   GK AI STUDIO CALISIYOR
 echo ============================================================
echo   Runner : 127.0.0.1:%RUNNER_PORT%
echo   Bridge : 127.0.0.1:%BRIDGE_PORT%
echo   Studio : 127.0.0.1:%STUDIO_PORT%
echo   Model  : %GK_IPEX_MODEL%
echo.
echo   Loglar:
echo     ipex_runner.log
echo     ai_bridge.log
echo     studio.log
echo.
echo   Bu pencereyi kapatmak yerine asagidaki secenegi kullanin.
echo   [K] Sistemi kapat ve bu oturumda baslatilan servisleri durdur
 echo ============================================================
echo.
:menu
choice /C KQ /N /M "K=Kapat  Q=Konsolda kal: "
if errorlevel 2 goto :menu
if errorlevel 1 goto :shutdown

:shutdown
echo.
echo [KAPAT] GK AI STUDIO durduruluyor...
if defined STUDIO_STARTED (
    for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%STUDIO_PORT% .*LISTENING"') do taskkill /PID %%P /F >nul 2>&1
)
if defined BRIDGE_STARTED (
    for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%BRIDGE_PORT% .*LISTENING"') do taskkill /PID %%P /F >nul 2>&1
)
if defined RUNNER_STARTED (
    for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%RUNNER_PORT% .*LISTENING"') do taskkill /PID %%P /F >nul 2>&1
)
echo [OK] Bu oturumda baslatilan servisler durduruldu.
echo.
pause
exit /b 0

:error_studio
echo [HATA] Studio klasoru bulunamadi: %STUDIO%
goto :fail
:error_runner_file
echo [HATA] IPEX runner bulunamadi: %RUNNER%
goto :fail
:error_model_file
echo [HATA] Qwen model blob bulunamadi: %MODEL%
goto :fail
:error_bridge_file
echo [HATA] ai_bridge.py bulunamadi.
goto :fail
:error_app_file
echo [HATA] app.py bulunamadi.
goto :fail
:error_runner_ready
echo [HATA] IPEX runner 30 saniye icinde hazir olmadi.
echo ipex_runner.log dosyasini kontrol edin.
goto :fail
:error_bridge_ready
echo [HATA] Bridge 15 saniye icinde hazir olmadi.
echo ai_bridge.log dosyasini kontrol edin.
goto :fail
:fail
echo.
pause
exit /b 1
