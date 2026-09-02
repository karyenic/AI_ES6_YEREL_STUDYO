# push_fresh.ps1
Set-Location "C:\AI_YEREL\AI_ES6_YEREL_STUDYO"

if (Test-Path ".git") {
    Remove-Item -Recurse -Force ".git"
}

git init
git remote add origin https://github.com/karyenic/AI_ES6_YEREL_STUDYO.git
git add .
git commit -m "GK AI Studyo taze baslangic ve guncel durum"
git branch -M main
git push -u origin main --force

Write-Host "İşlem başarıyla tamamlandı!" -ForegroundColor Green
Read-Host "Çıkış için bir tuşa basın..."