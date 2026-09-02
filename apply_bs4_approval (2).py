Set-Content -Path "C:\AI_YEREL\AI_ES6_YEREL_STUDYO\apply_bs4_approval.py" -Value @'
path = r"C:\AI_YEREL\AI_ES6_YEREL_STUDYO\app.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# app.py içindeki arama bloğunu BeautifulSoup tabanlı canlı site kazıma motoruyla güncelliyoruz
start_anchor = '    web_context = ""'
end_anchor = '    if web_context:'

start_idx = content.find(start_anchor)
end_idx = content.find(end_anchor, start_idx)

new_snippet = """    web_context = ""
    if use_web_search:
        try:
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin
            url_match = re.search(r'https?://[^\\s]+|www\\.[^\\s]+|[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}', prompt)
            if url_match:
                target_url = url_match.group(0)
                if not target_url.startswith('http'):
                    target_url = 'https://' + target_url
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                r_scrape = requests.get(target_url, timeout=15, headers=headers)
                if r_scrape.status_code == 200:
                    soup = BeautifulSoup(r_scrape.text, 'html.parser')
                    links = []
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        full_url = urljoin(target_url, href)
                        text_l = a.get_text(strip=True) or href
                        links.append(f"- [{text_l}]({full_url})")
                    if links:
                        web_context = f"[CANLI WEB KAZIMA SONUÇLARI ({target_url})]:\\n" + "\\n".join(links[:50])
                    else:
                        web_context = f"[UYARI: {target_url} tarandı ancak sayfada hiç bağlantı bulunamadı.]"
                else:
                    web_context = f"[UYARI: {target_url} adresi {r_scrape.status_code} durum koduyla yanıt verdi.]"
        except Exception as e:
            web_context = f"[UYARI: Web tarama hatası: {e}]" """

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_snippet + "\n" + content[end_idx:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("BAŞARILI: app.py canlı BeautifulSoup kazıma motoruyla güncellendi.")
else:
    print("HATA: Çapa noktaları bulunamadı.")
'@ -Encoding UTF8