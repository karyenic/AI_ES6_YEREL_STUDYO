# C:\AI_YEREL\AI_ES6_YEREL_STUDYO dizininde olduğunuzdan emin olun
Set-Location "C:\AI_YEREL\AI_ES6_YEREL_STUDYO"

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# 1. app.py Güncellemesi ve Yedeklenmesi
$AppPath = "app.py"
if (Test-Path $AppPath) {
    $BackupApp = "app_yedek_$Timestamp.py"
    Copy-Item $AppPath $BackupApp
    Write-Host "✓ app.py yedeği alındı: $BackupApp" -ForegroundColor Green

    $AppContent = Get-Content $AppPath -Raw -Encoding UTF8

    # Gelişmiş Dosya İndir Endpoint'i (Kod bloklarını uzantısına göre akıllı kaydeder)
    $NewExportEndpoint = @'

@app.route('/api/projects/export-file', methods=['POST'])
def api_export_file():
    try:
        data = request.get_json(silent=True) or {}
        filename = data.get("filename", "").strip()
        content = data.get("content", "")
        
        if not content:
            return jsonify({"status": "error", "message": "İçerik boş olamaz."}), 400
            
        if not filename:
            filename = f"export_{time.strftime('%Y%m%d_%H%M%S')}.txt"
            
        # Güvenli dosya adı temizliği
        filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
        filepath = os.path.join(EXPORTS_DIR, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            
        return jsonify({"status": "success", "message": f"'{filename}' başarıyla kaydedildi.", "path": filepath})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
'@

    if ($AppContent -match "def api_export_file\(\):") {
        # Eski endpoint'i yenisiyle değiştir
        $AppContent = $AppContent -replace '(?s)@app\.route\(\'/api/projects/export-file\'[^}]*?return jsonify\(\{"status": "error"[^}]*?\}.*?\n\s*except[^\n]*\n\s*return[^\n]*\n', $NewExportEndpoint.Trim()
    } else {
        # Yoksa sona ekle
        $AppContent += $NewExportEndpoint
    }

    Set-Content -Path $AppPath -Value $AppContent -Encoding UTF8
    Write-Host "✓ app.py başarıyla güncellendi (Gelişmiş Dosya İndir API aktif)." -ForegroundColor Green
} else {
    Write-Host "HATA: app.py bulunamadı!" -ForegroundColor Red
}

# 2. Arayüz (static/index.html veya UI dosyası) Yedeklenmesi
$StaticHtmlPath = "static/index.html"
if (Test-Path $StaticHtmlPath) {
    $BackupHtml = "static_index_yedek_$Timestamp.html"
    Copy-Item $StaticHtmlPath $BackupHtml
    Write-Host "✓ static/index.html yedeği alındı: $BackupHtml" -ForegroundColor Green
    Write-Host "BİLGİ: Arayüzdeki mesaj balonlarına 4'lü buton setinin (Kopyala, İndir, Dosya İndir, Sil) ve Silme mantığının işleneceği JS/HTML yapılandırması arayüz kodunuza entegre edilmeye hazırdır." -ForegroundColor Cyan
} else {
    Write-Host "BİLGİ: static/index.html doğrudan bulunamadı, arayüz farklı bir yapıda olabilir." -ForegroundColor Yellow
}