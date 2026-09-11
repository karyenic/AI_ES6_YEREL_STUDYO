# git_guncelle.ps1
git add .
$mesaj = Read-Host "Commit mesajını girin"
git commit -m "$mesaj"
git push
Write-Host "GitHub senkronizasyonu başarıyla tamamlandı!" -ForegroundColor Green