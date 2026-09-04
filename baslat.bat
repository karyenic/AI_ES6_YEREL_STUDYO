@echo off
chcp 65001 >nul
title GK AI STUDIO

cd /d "C:\AI_YEREL\AI_ES6_YEREL_STUDYO"

echo [1/4] Intel GPU ortam degiskenleri ayarlaniyor...
set OLLAMA_NUM_GPU=999
set ONEAPI_DEVICE_SELECTOR=level_zero:0
set ZES_ENABLE_SYSMAN=1
set SYCL_CACHE_PERSISTENT=1
set OLLAMA_INTEL_GPU=true
set OLLAMA_FLASH_ATTENTION=true

echo [2/4] Ollama (GPU destekli) arka planda baslatiliyor...
start /B "Ollama GPU" C:\AI_IPEX\Ollama\portable\ollama.exe serve

echo Bekleniyor (10 saniye)...
timeout /t 5 /nobreak >nul

echo [3/4] Web Studyo aciliyor...
start http://127.0.0.1:5000

echo [4/4] Flask calisiyor...
python app.py

echo.
echo Flask durduruldu. Ollama sunucusu kapatiliyor...
taskkill /IM ollama.exe /F >nul 2>&1
echo Temizlik tamamlandi.
pause