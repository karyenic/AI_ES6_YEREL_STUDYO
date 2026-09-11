# C:\AI_YEREL\AI_ES6_YEREL_STUDYO\baslat.ps1
# -*- coding: utf-8 -*-
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "GK AI STUDIO - Intel Arc 140V (Unified Console)"

Set-Location "C:\AI_YEREL\AI_ES6_YEREL_STUDYO"

Write-Host "============================================================" -ForegroundColor DarkMagenta
Write-Host " GK AI STUDIO - INTEL ARC 140V (32GB VRAM / 32K CONTEXT)    " -ForegroundColor DarkMagenta
Write-Host "============================================================" -ForegroundColor DarkMagenta

# 1. Dosya Kontrolleri
$IPEX_DIR = "C:\AI_IPEX\Ollama\portable"
$RUNNER_EXE = "$IPEX_DIR\ollama-lib.exe"
$MODEL_BLOB = "C:\Users\karye\.ollama\models\blobs\sha256-60e05f2100071479f596b964f89f510f057ce397ea22f2833a0cfe029bfc2463"

if (-not (Test-Path $RUNNER_EXE)) {
    Write-Host "[HATA] IPEX Runner dosyasi bulunamadi: $RUNNER_EXE" -ForegroundColor Red
    Read-Host "Kapatmak icin Enter'a basin..."
    Exit
}

if (-not (Test-Path $MODEL_BLOB)) {
    Write-Host "[HATA] Qwen Model Blob dosyasi bulunamadi: $MODEL_BLOB" -ForegroundColor Red
    Read-Host "Kapatmak icin Enter'a basin..."
    Exit
}

# 2. Temizlik
Write-Host "[1/4] Cakisabilecek eski surecler temizleniyor..." -ForegroundColor Cyan
Get-Process -Name "ollama-lib" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# 3. Akıllı Tarayıcı Başlatıcı (Arka Planda Port 5000 Bekler)
Write-Host "[2/4] Arayuz bekleme gorevi arka plana atiliyor..." -ForegroundColor Green
$BrowserScript = {
    $flaskReady = $false
    $retryCount = 0
    while (-not $flaskReady -and $retryCount -lt 40) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $tcp.Connect("127.0.0.1", 5000)
            if ($tcp.Connected) {
                $flaskReady = $true
                $tcp.Close()
            }
        } catch {
            Start-Sleep -Seconds 1
            $retryCount++
        }
    }
    if ($flaskReady) {
        Start-Process "http://127.0.0.1:5000"
    }
}
Start-Job -ScriptBlock $BrowserScript | Out-Null

# 4. Orkestrator Başlatma
Write-Host "[3/4] Orkestrator baslatiliyor (32K Context / Tek Konsol Log Akisi)..." -ForegroundColor Yellow
Write-Host "[4/4] Sunucu hazır olduğunda tarayıcı otomatik açılacaktır..." -ForegroundColor Cyan

python orchestrator.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "[HATA] Python orchestrator.py calisirken bir hata olustu." -ForegroundColor Red
}

Read-Host "Surec sonlandi. Pencereyi kapatmak icin Enter'a basin..."