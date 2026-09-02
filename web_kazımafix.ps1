# ==========================================
# GK AI STÜDYO — OTOMATİK URL ALGILAMA YAMASI
# ==========================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$rootDir = "C:\AI_YEREL\AI_ES6_YEREL_STUDYO"
Set-Location $rootDir

$appPyPath = "$rootDir\app.py"
if (Test-Path $appPyPath) {
    Copy-Item $appPyPath "$appPyPath.bak" -Force
    $content = Get-Content $appPyPath -Raw -Encoding UTF8

    # Eski kısıtlayıcı koşulu, URL tespiti ile otomatik çalışacak şekilde değiştiriyoruz
    $oldBlock = '    web_context = ""
    if use_web_search:'
    
    $newBlock = '    web_context = ""
    url_match = re.search(r"https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", prompt)
    if use_web_search or url_match:'

    if ($content -like "*if use_web_search:*") {
        $content = $content.Replace($oldBlock, $newBlock)
        Set-Content -Path $appPyPath -Value $content -Encoding UTF8
        Write-Host "[BAŞARILI] app.py içerisindeki web kazıma tetikleyicisi URL algılayacak şekilde güncellendi." -ForegroundColor Green
    } else {
        Write-Host "[BİLGİ] İlgili blok zaten güncellenmiş veya farklı formatta." -ForegroundColor Yellow
    }
} else {
    Write-Host "[HATA] app.py bulunamadı!" -ForegroundColor Red
}

Write-Host "Şimdi 'baslat.bat' ile sistemi yeniden başlatıp test edebilirsiniz." -ForegroundColor Cyan