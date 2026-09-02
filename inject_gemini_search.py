path = r"C:\AI_YEREL\AI_ES6_YEREL_STUDYO\app.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

start_anchor = '    web_context = ""'
end_anchor = '    if web_context:'

start_idx = content.find(start_anchor)
end_idx = content.find(end_anchor, start_idx)

new_snippet = """    web_context = ""
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
            web_context = f"[UYARI: Bulut arama hatası: {e}]" """

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_snippet + "\n" + content[end_idx:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("BAŞARILI: Gemini Cloud Search mantığı .env anahtarıyla app.py dosyasına entegre edildi.")
else:
    print("HATA: Çapa noktaları bulunamadı.")
