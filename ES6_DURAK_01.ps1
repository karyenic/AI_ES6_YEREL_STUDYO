#requires -Version 5.1
<#
ES6_DURAK_01.ps1
AI_ES6_YEREL_STUDYO - Güvenli Başlangıç / Envanter / Checkpoint

AMAÇ:
- Proje dizinini doğrulamak
- Git durumunu ve son commit bilgisini kaydetmek
- Dosya ağacını çıkarmak
- Kritik proje dosyalarını envantere almak
- _AI_STUDIO hafıza klasörünü oluşturmak
- DURUM / KARARLAR / YAPILACAKLAR / DEGISIKLIKLER / CHECKPOINT dosyalarını oluşturmak
- Uygulama kodlarına DOKUNMAMAK

NOT:
- Bu betik git commit/push YAPMAZ.
- Önce çıktıyı kontrol edeceğiz.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\AI_YEREL\AI_ES6_YEREL_STUDYO"
$MemoryDir   = Join-Path $ProjectRoot "_AI_STUDIO"
$ReportDir   = Join-Path $MemoryDir "reports"
$Now         = Get-Date
$Stamp       = $Now.ToString("yyyyMMdd_HHmmss")

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " ES6-DURAK-01 - GÜVENLİ BAŞLANGIÇ" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "Proje dizini bulunamadı: $ProjectRoot"
}

Set-Location -LiteralPath $ProjectRoot

New-Item -ItemType Directory -Path $MemoryDir -Force | Out-Null
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null

# ------------------------------------------------------------
# 1) Git bilgileri
# ------------------------------------------------------------
$gitAvailable = $false
$gitBranch = "BİLİNMİYOR"
$gitCommit = "BİLİNMİYOR"
$gitStatus = @()

try {
    $null = Get-Command git -ErrorAction Stop
    $gitAvailable = $true

    $gitBranch = (git branch --show-current 2>$null).Trim()
    if ([string]::IsNullOrWhiteSpace($gitBranch)) {
        $gitBranch = "BİLİNMİYOR"
    }

    $gitCommit = (git log -1 --pretty=format:"%H|%ad|%s" --date=iso 2>$null).Trim()
    if ([string]::IsNullOrWhiteSpace($gitCommit)) {
        $gitCommit = "COMMIT BULUNAMADI"
    }

    $gitStatus = @(git status --short 2>$null)
}
catch {
    $gitAvailable = $false
}

# ------------------------------------------------------------
# 2) Dosya envanteri
# ------------------------------------------------------------
$excludeDirs = @(
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    "node_modules"
)

$excludeExtensions = @(
    ".pyc",
    ".exe",
    ".dll",
    ".db",
    ".sqlite",
    ".sqlite3"
)

$allFiles = @(
    Get-ChildItem -LiteralPath $ProjectRoot -File -Recurse -Force |
    Where-Object {
        $relative = $_.FullName.Substring($ProjectRoot.Length).TrimStart('\')
        $parts = $relative -split '\\'
        ($parts | Where-Object { $excludeDirs -contains $_ }).Count -eq 0 -and
        ($excludeExtensions -notcontains $_.Extension.ToLowerInvariant())
    }
)

$fileCount = $allFiles.Count

# Uzantı özeti
$extensionSummary = $allFiles |
    Group-Object { if ([string]::IsNullOrWhiteSpace($_.Extension)) { "[uzantısız]" } else { $_.Extension.ToLowerInvariant() } } |
    Sort-Object Count -Descending |
    ForEach-Object { "{0,-12} {1,6}" -f $_.Name, $_.Count }

# ------------------------------------------------------------
# 3) Kritik dosya kontrolü
# ------------------------------------------------------------
$criticalFiles = @(
    "app.py",
    "requirements.txt",
    "projects_config.json",
    "baslat.bat",
    "static\index.html",
    "static\js\api.js",
    "static\js\main.js",
    "static\js\state.js",
    "static\js\ui.js",
    "static\js\workspace.js"
)

$criticalResults = foreach ($rel in $criticalFiles) {
    $full = Join-Path $ProjectRoot $rel
    [PSCustomObject]@{
        Dosya = $rel
        Durum = if (Test-Path -LiteralPath $full -PathType Leaf) { "VAR" } else { "YOK" }
    }
}

# ------------------------------------------------------------
# 4) Dizin ağacı
# ------------------------------------------------------------
$treeFile = Join-Path $ReportDir "DOSYA_AGACI_$Stamp.txt"

$treeLines = New-Object System.Collections.Generic.List[string]
$treeLines.Add("AI_ES6_YEREL_STUDYO - DOSYA AGACI")
$treeLines.Add("Olusturulma: $($Now.ToString('yyyy-MM-dd HH:mm:ss'))")
$treeLines.Add("Kok: $ProjectRoot")
$treeLines.Add("")

foreach ($file in ($allFiles | Sort-Object FullName)) {
    $relative = $file.FullName.Substring($ProjectRoot.Length).TrimStart('\')
    $treeLines.Add($relative)
}

$treeLines | Set-Content -LiteralPath $treeFile -Encoding UTF8

# ------------------------------------------------------------
# 5) GIT DURUM RAPORU
# ------------------------------------------------------------
$gitReportFile = Join-Path $ReportDir "GIT_DURUMU_$Stamp.txt"

$gitReport = New-Object System.Collections.Generic.List[string]
$gitReport.Add("AI_ES6_YEREL_STUDYO - GIT DURUMU")
$gitReport.Add("Olusturulma: $($Now.ToString('yyyy-MM-dd HH:mm:ss'))")
$gitReport.Add("Repo: $ProjectRoot")
$gitReport.Add("Git mevcut: $gitAvailable")
$gitReport.Add("Branch: $gitBranch")
$gitReport.Add("Son commit: $gitCommit")
$gitReport.Add("")
$gitReport.Add("git status --short:")

if ($gitStatus.Count -eq 0) {
    $gitReport.Add("TEMIZ veya değişiklik yok.")
} else {
    foreach ($line in $gitStatus) {
        $gitReport.Add($line)
    }
}

$gitReport | Set-Content -LiteralPath $gitReportFile -Encoding UTF8

# ------------------------------------------------------------
# 6) DURUM.md
# ------------------------------------------------------------
$statusFile = Join-Path $MemoryDir "DURUM.md"

@"
# AI_ES6_YEREL_STUDYO — DURUM

## Referans
- Durak: **ES6-DURAK-01**
- Tarih: $($Now.ToString("yyyy-MM-dd HH:mm:ss"))
- Proje dizini: `$ProjectRoot`
- Bu durakta uygulama koduna değişiklik yapılmadı.

## Git
- Git kullanılabilir: **$gitAvailable**
- Branch: **$gitBranch**
- Son commit: `$gitCommit`
- Envantere alınan dosya sayısı: **$fileCount**

## Ana amaç
Mevcut sistemi bozmadan, gelecekteki çalışmalar için güvenilir bir proje hafızası ve geri dönüş noktası oluşturmak.

## Kritik dosyalar
$($criticalResults | Format-Table -AutoSize | Out-String)

## Raporlar
- Dosya ağacı: `reports\$(Split-Path $treeFile -Leaf)`
- Git durumu: `reports\$(Split-Path $gitReportFile -Leaf)`

## Sonraki aşama
**ES6-DURAK-02:** Frontend ↔ Backend endpoint sağlık kontrolü.
Öncelikli kontrol:
- `/api/models` ↔ `/models`
- `/api/status` / `/status`
- `/api/gpu-status` / `/gpu-status`
- diğer frontend API çağrıları
"@ | Set-Content -LiteralPath $statusFile -Encoding UTF8

# ------------------------------------------------------------
# 7) KARARLAR.md
# ------------------------------------------------------------
$decisionsFile = Join-Path $MemoryDir "KARARLAR.md"

@"
# AI_ES6_YEREL_STUDYO — KARARLAR

## Çalışma kuralları

1. Proje baştan yazılmayacak.
2. Mevcut çalışan yapı korunacak.
3. Küçük değişiklik → test → checkpoint → Git yaklaşımı kullanılacak.
4. Uygulama kodunda gereksiz toplu değişiklik yapılmayacak.
5. Eski / `.bak` dosyaları, kullanılmadığı kanıtlanmadan silinmeyecek.
6. Yerel Windows yolu ana çalışma ortamı olarak:
   `$ProjectRoot`
7. Kritik durumlarda Git güvenli nokta olarak kullanılacak.
8. Sohbet bağlamı ile repo üzerindeki kayıtlar çelişirse, repo içindeki güncel checkpoint kayıtları esas alınacak.
9. "Sağa çek kardeş." çalışma ifadesi, bağlam tazeleme ve checkpoint kontrolü anlamına gelir.
10. Yeni özellik eklemeden önce mevcut davranış doğrulanacak.

## Bu durak
ES6-DURAK-01 yalnızca envanter ve hafıza altyapısı oluşturur.
Uygulama koduna müdahale edilmez.
"@ | Set-Content -LiteralPath $decisionsFile -Encoding UTF8

# ------------------------------------------------------------
# 8) YAPILACAKLAR.md
# ------------------------------------------------------------
$tasksFile = Join-Path $MemoryDir "YAPILACAKLAR.md"

@"
# AI_ES6_YEREL_STUDYO — YAPILACAKLAR

## Tamamlanan
- [x] Repo incelemesi
- [x] Riskli noktaların ilk tespiti
- [x] Yerel proje kökü kesinleştirildi
- [x] `_AI_STUDIO` hafıza yapısı oluşturuldu
- [x] İlk dosya envanteri oluşturuldu
- [x] Git referans bilgileri kaydedildi

## Sıradaki işler
- [ ] ES6-DURAK-02: Endpoint sağlık kontrolü
- [ ] Frontend API çağrılarının backend route'larıyla eşleştirilmesi
- [ ] Ollama bağlantısının kontrolü
- [ ] Model listesinin gerçek sistemden geldiğinin doğrulanması
- [ ] GPU status endpoint kontrolü
- [ ] Sohbet akışının temel testi
- [ ] Proje/workspace akışının temel testi

## Henüz yapılmayacaklar
- [ ] Büyük refactor
- [ ] `app.py` parçalama
- [ ] RAG/index sistemi
- [ ] Gereksiz dosya temizliği
- [ ] Yeni özellik ekleme
"@ | Set-Content -LiteralPath $tasksFile -Encoding UTF8

# ------------------------------------------------------------
# 9) DEGISIKLIKLER.md
# ------------------------------------------------------------
$changesFile = Join-Path $MemoryDir "DEGISIKLIKLER.md"

@"
# AI_ES6_YEREL_STUDYO — DEĞİŞİKLİKLER

## ES6-DURAK-01
- Tarih: $($Now.ToString("yyyy-MM-dd HH:mm:ss"))
- İşlem: Proje envanteri ve checkpoint hafızası oluşturuldu.
- Uygulama kodu değişikliği: **YOK**
- Oluşturulan klasör: `_AI_STUDIO`
- Oluşturulan kayıtlar:
  - `DURUM.md`
  - `KARARLAR.md`
  - `YAPILACAKLAR.md`
  - `DEGISIKLIKLER.md`
  - `CHECKPOINT.md`
  - `reports\DOSYA_AGACI_$Stamp.txt`
  - `reports\GIT_DURUMU_$Stamp.txt`
"@ | Set-Content -LiteralPath $changesFile -Encoding UTF8

# ------------------------------------------------------------
# 10) CHECKPOINT.md
# ------------------------------------------------------------
$checkpointFile = Join-Path $MemoryDir "CHECKPOINT.md"

@"
# CHECKPOINT

## CP-01 / ES6-DURAK-01

**Tarih:** $($Now.ToString("yyyy-MM-dd HH:mm:ss"))

### Durum
İlk güvenli başlangıç noktası oluşturuldu.

### Yapılanlar
- Repo dizini doğrulandı.
- Git bilgileri kaydedildi.
- Dosya envanteri çıkarıldı.
- Kritik dosyalar kontrol edildi.
- `_AI_STUDIO` hafıza alanı oluşturuldu.

### Teknik referans
- Proje kökü: `$ProjectRoot`
- Branch: `$gitBranch`
- Son commit: `$gitCommit`
- Dosya sayısı: `$fileCount`

### Değişmeyenler
- `app.py`
- `static\index.html`
- `static\js\*`
- `requirements.txt`
- diğer mevcut uygulama dosyaları

### Sonraki adım
**ES6-DURAK-02 — Endpoint sağlık kontrolü**

### Geri dönüş notu
Bu checkpoint uygulama kodunda değişiklik yapmaz. Amaç yalnızca güvenli başlangıç referansı oluşturmaktır.
"@ | Set-Content -LiteralPath $checkpointFile -Encoding UTF8

# ------------------------------------------------------------
# 11) .gitignore kontrolü - DEĞİŞTİRMİYORUZ
# ------------------------------------------------------------
$gitignoreExists = Test-Path -LiteralPath (Join-Path $ProjectRoot ".gitignore") -PathType Leaf

# ------------------------------------------------------------
# 12) Sonuç
# ------------------------------------------------------------
Write-Host ""
Write-Host "ES6-DURAK-01 TAMAMLANDI." -ForegroundColor Green
Write-Host ""
Write-Host "Oluşturulan hafıza alanı:" -ForegroundColor Yellow
Write-Host "  $MemoryDir"
Write-Host ""
Write-Host "Dosyalar:" -ForegroundColor Yellow
Write-Host "  DURUM.md"
Write-Host "  KARARLAR.md"
Write-Host "  YAPILACAKLAR.md"
Write-Host "  DEGISIKLIKLER.md"
Write-Host "  CHECKPOINT.md"
Write-Host "  reports\DOSYA_AGACI_$Stamp.txt"
Write-Host "  reports\GIT_DURUMU_$Stamp.txt"
Write-Host ""

if (-not $gitignoreExists) {
    Write-Host "UYARI: .gitignore bulunamadı. Şimdilik değiştirilmedi." -ForegroundColor Yellow
} else {
    Write-Host ".gitignore mevcut; değiştirilmedi." -ForegroundColor Green
}

Write-Host ""
Write-Host "ÖNEMLİ: Bu betik git commit/push yapmadı." -ForegroundColor Cyan
Write-Host "Önce oluşan raporu kontrol edeceğiz; ardından CP-01 için Git push betiği hazırlayacağız." -ForegroundColor Cyan
Write-Host ""
Read-Host "Çıkmak için Enter"
