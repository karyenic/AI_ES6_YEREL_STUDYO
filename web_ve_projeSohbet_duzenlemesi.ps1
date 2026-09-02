# ==========================================
# GK AI STÜDYO — KESİN ÇÖZÜM YAMASI
# ==========================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$rootDir = "C:\AI_YEREL\AI_ES6_YEREL_STUDYO"
Set-Location $rootDir

Write-Host "[1/2] workspace.js ve ui.js senkronizasyonu güncelleniyor..." -ForegroundColor Cyan
$uiJsPath = "$rootDir\static\js\ui.js"
if (Test-Path $uiJsPath) {
    Copy-Item $uiJsPath "$uiJsPath.bak" -Force
    $content = Get-Content $uiJsPath -Raw -Encoding UTF8

    # Workspace.initWorkspaceUI çağrısını UI bileşenlerini yenileyecek şekilde güncelliyoruz
    $content = $content -replace 'Workspace\.initWorkspaceUI\(\(\) => this\.renderHistory\(\)\);', 'Workspace.initWorkspaceUI(() => { this.renderHistory(); this.renderChat(); this.updateTopBadge(State.conversations[State.currentId]); });'
    
    # Geçmiş tıklama olayındaki proje tetiklenmesini güncelliyoruz
    $oldClickBlock = 'if \(isProjectConv\) Workspace\.activateProject\(State\.projectConvMap\[id\], \(\) => this\.renderHistory\(\)\);'
    $newClickBlock = 'if (isProjectConv) Workspace.activateProject(State.projectConvMap[id], () => { this.renderHistory(); this.renderChat(); this.updateTopBadge(State.conversations[State.currentId]); });'
    
    $content = [System.Text.RegularExpressions.Regex]::Replace($content, $oldClickBlock, $newClickBlock)
    Set-Content -Path $uiJsPath -Value $content -Encoding UTF8
    Write-Host "  -> ui.js sohbet senkronizasyonu aktif edildi." -ForegroundColor Green
}

Write-Host "[2/2] app.py içindeki web arama filtrelemesi keskinleştiriliyor..." -ForegroundColor Cyan
$appPyPath = "$rootDir\app.py"
if (Test-Path $appPyPath) {
    Copy-Item $appPyPath "$appPyPath.bak" -Force
    $appContent = Get-Content $appPyPath -Raw -Encoding UTF8

    # Genel arama promptunu hedef odaklı filtreleme yapısına çeviriyoruz
    $oldSearchPayload = '"contents": \[\{"parts": \[\{"text": "Web üzerinde kapsamlı arama yap, resmi kaynakları, site yapısını ve indirme linklerini derle: " \+ prompt\}]\}]'
    $newSearchPayload = '"contents": [{"parts": [{"text": "Hedef Sorgu: " + prompt + "\n\nGörev: Bu sorgu için web üzerinde nokta atışı arama yap. Gürültülü içerikleri ve gereksiz metinleri ele. Doğrudan resmi kaynakları, site yapılarını, dosya ve katalog indirme linklerini net bir Markdown listesi olarak derle."}]}]'

    if ($appContent -like "*Web üzerinde kapsamlı arama yap*") {
        $appContent = [System.Text.RegularExpressions.Regex]::Replace($appContent, [regex]::Escape('"contents": [{"parts": [{"text": "Web üzerinde kapsamlı arama yap, resmi kaynakları, site yapısını ve indirme linklerini derle: " + prompt}]}]'), $newSearchPayload)
        Set-Content -Path $appPyPath -Value $appContent -Encoding UTF8
        Write-Host "  -> app.py web arama filtrelemesi optimize edildi." -ForegroundColor Green
    }
}

Write-Host "--------------------------------------------------" -ForegroundColor Yellow
Write-Host "Tüm düzeltmeler başarıyla tamamlandı!" -ForegroundColor Green
Write-Host "Tarayıcı önbelleğini temizlemek için sekmeyi [Ctrl + F5] ile yenileyin." -ForegroundColor Cyan