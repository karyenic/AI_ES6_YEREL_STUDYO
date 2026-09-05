@echo off
chcp 65001 >nul
setlocal EnableExtensions

title GK AI STUDIO - Intel Arc IPEX GPU
cd /d "C:\AI_YEREL\AI_ES6_YEREL_STUDYO"

set "IPEX_DIR=C:\AI_IPEX\Ollama\portable"
set "RUNNER=%IPEX_DIR%\ollama-lib.exe"
set "MODEL=C:\Users\karye\.ollama\models\blobs\sha256-60e05f2100071479f596b964f89f510f057ce397ea22f2833a0cfe029bfc2463"
set "RUNNER_PORT=59584"
set "BRIDGE_PORT=11434"
set "OLLAMA_NUM_GPU=999"
set "ONEAPI_DEVICE_SELECTOR=level_zero:0"
set "ZES_ENABLE_SYSMAN=1"
set "SYCL_CACHE_PERSISTENT=1"
set "OLLAMA_FLASH_ATTENTION=false"
set "NO_PROXY=localhost,127.0.0.1"

if not exist "%RUNNER%" (
  echo [HATA] IPEX runner bulunamadi: %RUNNER%
  pause
  exit /b 1
)
if not exist "%MODEL%" (
  echo [HATA] Qwen model blob bulunamadi.
  echo %MODEL%
  pause
  exit /b 1
)

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%RUNNER_PORT% .*LISTENING"') do set "RUNNER_PID=%%P"

if defined RUNNER_PID (
  echo [1/4] Mevcut IPEX runner bulundu: PID %RUNNER_PID%
) else (
  echo [1/4] IPEX GPU runner baslatiliyor...
  start "GK IPEX GPU Runner" cmd /k "cd /d %IPEX_DIR% && set OLLAMA_NUM_GPU=999&& set ONEAPI_DEVICE_SELECTOR=level_zero:0&& set ZES_ENABLE_SYSMAN=1&& set SYCL_CACHE_PERSISTENT=1&& "%RUNNER%" runner --model "%MODEL%" --ctx-size 4096 --batch-size 512 --n-gpu-layers 999 --threads 4 --no-mmap --parallel 1 --port %RUNNER_PORT% --verbose"
)

echo [2/4] Runner hazirligi kontrol ediliyor...
set "READY="
for /l %%N in (1,1,30) do (
  if not defined READY (
    curl -s --max-time 2 http://127.0.0.1:%RUNNER_PORT%/health | findstr /C:"\"status\":0" >nul 2>&1 && set "READY=1"
    if not defined READY timeout /t 1 /nobreak >nul
  )
)
if not defined READY (
  echo [HATA] IPEX runner 30 saniye icinde hazir olmadi.
  echo Runner penceresindeki loglari kontrol edin.
  pause
  exit /b 2
)
echo [OK] IPEX runner hazir: 127.0.0.1:%RUNNER_PORT%

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%BRIDGE_PORT% .*LISTENING"') do set "BRIDGE_PID=%%P"
if defined BRIDGE_PID (
  echo [3/4] 11434 zaten kullanimda: PID %BRIDGE_PID%
  echo [UYARI] Normal Ollama serve calisiyor olabilir. Bridge testinde 11434 cakismasi olabilir.
) else (
  echo [3/4] IPEX API bridge baslatiliyor...
  start "GK AI Bridge" cmd /k "cd /d C:\AI_YEREL\AI_ES6_YEREL_STUDYO && set GK_IPEX_RUNNER_URL=http://127.0.0.1:%RUNNER_PORT%&& set GK_BRIDGE_PORT=%BRIDGE_PORT%&& set GK_IPEX_MODEL=qwen2.5-coder:7b&& python ai_bridge.py"
)

timeout /t 2 /nobreak >nul

echo [4/4] GK AI STUDIO baslatiliyor...
start "GK AI STUDIO" cmd /k "cd /d C:\AI_YEREL\AI_ES6_YEREL_STUDYO && python app.py"
start http://127.0.0.1:5000

echo.
echo ============================================================
echo GK AI STUDIO - Intel Arc IPEX zinciri baslatildi.
echo Runner : 127.0.0.1:%RUNNER_PORT%
echo Bridge : 127.0.0.1:%BRIDGE_PORT%
echo Studio : 127.0.0.1:5000
echo ============================================================
echo.
pause
