import os
import re

path = r"C:\AI_YEREL\AI_ES6_YEREL_STUDYO\app.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Eski BeautifulSoup ve url_match bloğunu hedef alıp temizliyoruz
# app.py içerisindeki ilgili arama bloğunu Gemini Cloud Search ile değiştiriyoruz
pattern = r'    web_context = ""\s+url_match = re\.search\(.+?web_context = f"\[UYARI: Web arama sırasında beklenmeyen bir hata oluştu: \{e\}\. Bunu kullanıcıya belirt\.\]"'

new_block = """    web_context = ""
    if use_web_search and GEMINI_API_KEY:
        try:
            search_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + GEMINI_API_KEY
            search_payload = {
                "contents": [{"parts": [{"text": "Hedef Sorgu: " + prompt + "\\n\\nGörev: Bu sorgu için web üzerinde nokta atışı arama yap. Gürültülü içerikleri ve gereksiz metinleri ele. Doğrudan resmi kaynakları, site yapılarını, dosya ve katalog indirme linklerini net bir Markdown listesi olarak derle."}]}],
                "tools": [{"googleSearch": {}}]
            }
            s_res = requests.post(search_url, json=search_payload, timeout=30)
            if s_res.status_code == 200:
                s_parts = s_res.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
                web_context = "".join([p.get("text", "") for p in s_parts])
            else:
                web_context = f"[UYARI: Bulut web araması başarısız oldu ({s_res.status_code}): {s_res.text[:200]}]"
        except Exception as e:
            web_context = f"[UYARI: Bulut arama hatası: {e}]\""""

# Alternatif olarak esnek arama ile değiştirelim
if "from bs4 import BeautifulSoup" in content:
    # BeautifulSoup bloğunun tamamını güvenli bir şekilde değiştir
    start_pos = content.find("    web_context = \"\"")
    end_pos = content.find("    if web_context:", start_pos)
    if end_pos == -1:
        end_pos = content.find("    if role and role != \"default\":", start_pos)
    
    if start_pos != -1 and end_pos != -1:
        target_snippet = content[start_pos:end_pos]
        content = content.replace(target_snippet, new_block + "\n\n")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("BAŞARILI: app.py web arama motoru Gemini Cloud Search'e geçirildi.")
    else:
        print("HATA: Blok sınırları bulunamadı.")
else:
    print("BİLGİ: Dosya yapısı zaten güncel.")
