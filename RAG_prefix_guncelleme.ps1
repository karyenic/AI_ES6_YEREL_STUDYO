Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "      RAG NOMIC EMBEDDING ÖNEK GÜNCELLEME BETİĞİ    " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$DizinYolu = "C:\AI_YEREL\AI_ES6_YEREL_STUDYO"
$AppPyYolu = Join-Path $DizinYolu "app.py"
$YedekYolu = Join-Path $DizinYolu "app.py.bak2"

# 1. Dosya Kontrolü ve Yedekleme
if (-not (Test-Path $AppPyYolu)) {
    Write-Host "❌ Hata: $AppPyYolu dosyası bulunamadı!" -ForegroundColor Red
    Read-Host "Kapatmak için Enter'a basın..."
    exit
}

Write-Host "[1/3] Mevcut app.py dosyası yedekleniyor..." -ForegroundColor Yellow
Copy-Item -Path $AppPyYolu -Destination $YedekYolu -Force
Write-Host "✓ Yedek oluşturuldu: app.py.bak2" -ForegroundColor Green

# 2. Dosya İçeriğini Oku
Write-Host "[2/3] Dosya içeriği analiz ediliyor ve güncelleniyor..." -ForegroundColor Yellow
$Icerik = Get-Content -Path $AppPyYolu -Raw -Encoding utf8

# --- 2a. _get_embedding fonksiyonunu güncelle ---
$EskiEmbeddingFonksiyonu = @'
def _get_embedding(text):
    """Ollama'nin embedding uc noktasini kullanir - tamamen yerel, buluta
    hic cikmaz. nomic-embed-text kurulu degilse acik bir hata firlatir
    (cagiran yer bunu kullaniciya bildirir - 'ollama pull nomic-embed-text'
    calistirmasi gerekir)."""
    r = requests.post(
        "http://127.0.0",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=30
    )
'@

$YeniEmbeddingFonksiyonu = @'
def _get_embedding(text, is_query=False):
    """Ollama'nin embedding uc noktasini kullanir - tamamen yerel, buluta
    hic cikmaz. nomic-embed-text kurulu degilse acik bir hata firlatir."""
    prefix = "search_query: " if is_query else "search_document: "
    full_text = f"{prefix}{text}"
    r = requests.post(
        "http://127.0.0",
        json={"model": EMBED_MODEL, "prompt": full_text},
        timeout=30
    )
'@

# --- 2b. _rag_query içindeki çağrıyı güncelle ---
$EskiRagCagrisi = "query_emb = _get_embedding(query)"
$YeniRagCagrisi = "query_emb = _get_embedding(query, is_query=True)"

# --- 2c. api_index_project içindeki çağrıyı güncelle ---
$EskiIndexCagrisi = "emb = _get_embedding(chunk)"
$YeniIndexCagrisi = "emb = _get_embedding(chunk, is_query=False)"

# Değişiklikleri Uygula
if ($Icerik -contains "_get_embedding(text, is_query=False)") {
    Write-Host "⚠ Bu değişiklik zaten daha önce uygulanmış görünüyor!" -ForegroundColor Magenta
} else {
    $Icerik = $Icerik.Replace($EskiEmbeddingFonksiyonu, $YeniEmbeddingFonksiyonu)
    $Icerik = $Icerik.Replace($EskiRagCagrisi, $YeniRagCagrisi)
    $Icerik = $Icerik.Replace($EskiIndexCagrisi, $YeniIndexCagrisi)

    # 3. Dosyayı Kaydet
    Write-Host "[3/3] Değişiklikler app.py dosyasına güvenli şekilde yazılıyor..." -ForegroundColor Yellow
    [System.IO.File]::WriteAllText($AppPyYolu, $Icerik, [System.Text.Encoding]::UTF8)
    Write-Host "✓ Güncelleme başarıyla tamamlandı!" -ForegroundColor Green
}

Write-Host ""
Write-Host "Artık baslat.bat dosyasını çalıştırıp projeyi test edebilirsiniz." -ForegroundColor Cyan
Read-Host "Kapatmak için Enter tuşuna basın..."
