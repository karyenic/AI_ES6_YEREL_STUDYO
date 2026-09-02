import os, sys, json, time, subprocess, requests, signal, threading, re, csv
from flask import Flask, request, jsonify, send_from_directory, send_file, Response, stream_with_context, make_response
import io
import psutil

print("\n[BAŞLANGIÇ SAĞLIK KONTROLÜ]")
try:
    import pandas as pd
    print("  ✓ pandas [Yüklü]")
except ImportError:
    print("  ❌ pandas [EKSİK]")

try:
    import pdfplumber
    print("  ✓ pdfplumber [Yüklü]")
except ImportError:
    print("  ❌ pdfplumber [EKSİK]")

try:
    import openpyxl
    print("  ✓ openpyxl [Yüklü]")
except ImportError:
    print("  ❌ openpyxl [EKSİK]")

try:
    import psutil
    print("  ✓ psutil [Yüklü]")
except ImportError:
    print("  ❌ psutil [EKSİK]")

try:
    from bs4 import BeautifulSoup
    print("  ✓ BeautifulSoup [Yüklü] (web taraması için gerekli)")
except ImportError:
    print("  ❌ BeautifulSoup [EKSİK - web taraması çalışmayacak, 'pip install beautifulsoup4']")
print("--------------------------------------------------\n")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
GEMINI_API_KEY = ""

if os.path.exists(ENV_FILE):
    try:
        with open(ENV_FILE, "r", encoding="utf-8-sig") as ef:
            for line in ef:
                if "GEMINI_API_KEY" in line and not line.strip().startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) > 1:
                        GEMINI_API_KEY = parts[1].strip().strip('"').strip("'").split("#")[0].strip()
    except Exception:
        pass

app = Flask(__name__, static_folder="static", template_folder="static")

@app.after_request
def add_no_cache_headers(response):
    # ONEMLI: index.html icin onbellekleme kapatilmisti ama static/js/*.js
    # ve static/css/*.css dosyalari icin HICBIR SEY yoktu - tarayicilar JS
    # dosyalarini agresif sekilde onbellekliyor. Bu, "dosyayi degistirdim
    # ama hala eski davranis var" seklindeki tekrarlayan sorunlarin
    # muhtemel bir kaynagiydi - kod diskte guncellenmis olsa bile tarayici
    # sekmeyi normal yeniledigimizde hala ESKI ui.js'i bellekten
    # kullanabiliyordu. Artik TUM yanitlar icin onbellekleme kapali.
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

CONV_DIR = os.path.join(BASE_DIR, "conversations")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
CHAT_DIR = os.path.join(BASE_DIR, "chat_history")
EXCELS_DIR = os.path.join(BASE_DIR, "excel")
PROJECTS_FILE = os.path.join(BASE_DIR, "projects_config.json")

os.makedirs(CONV_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(CHAT_DIR, exist_ok=True)
os.makedirs(EXCELS_DIR, exist_ok=True)

ROLE_PROMPTS = {
    "default": "Sen nazik, net ve çözüm odaklı genel bir yapay zeka asistanısın.",
    "coder": "Sen kıdemli bir yazılım mimarısın. Kod yanıtlarını eksiksiz, temiz ve Markdown formatında ver.",
    "writer": "Sen teknik ve idari işlerde uzmanlaşmış kıdemli bir teknik yazarsın.",
    "analyst": "Sen veri ve iş analistisin. Yanıtları maddeler ve tablolar halinde sun.",
    "engineer": "Sen otomotiv ve imalat mühendisliği uzmanısın. Toleranslar ve malzeme bilgisine odaklan."
}

SYSTEM_PROFILE = """[MASTER SİSTEM PROFİLİ & LOKAL HİBRİT MİMARİ SÖZLEŞMESİ]
- Kullanıcı / Sahip: Güven (İzmir, Türkiye - Otomotiv yan sanayi, yazılım geliştirici).
- Donanım Altyapısı: Dell 16250 Plus, 32 GB RAM, Intel Arc GPU, Windows 11 (64-bit).
- Çalışma İlkeleri: Asla varsayım yapma. Tüm yanıtlarını istisnasız ve SADECE TÜRKÇE dilinde ver.
- KESİN DOSYA / KLASÖR ANALİZ TALİMATI: Sana iletilen [PAKETLENMİŞ DOSYA İÇERİĞİ] bloğundaki tüm dosya yollarını, kod satırlarını ve yapıları eksiksiz olarak okur, hafızana alır ve gerçek veriler üzerinden incelersin."""

FALLBACK_LOCAL = [
    "qwen2.5:7b", "deepseek-r1:7b", "gemma4:latest", "qwen2.5-coder:7b", 
    "llama3.2:3b", "gemma2:2b", "deepseek-r1-64k:latest"
]
CLOUD_MODELS = ["gemini-2.5-flash"]

def get_installed_ollama_models():
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
        if r.status_code == 200:
            return [m.get("name") for m in r.json().get("models", [])]
    except:
        pass
    return []

def load_projects_config():
    if os.path.exists(PROJECTS_FILE):
        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_projects_config(config):
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

@app.route('/api/projects/list', methods=['GET'])
def api_list_projects():
    config = load_projects_config()
    return jsonify({"status": "success", "projects": config})

@app.route('/api/projects/add', methods=['POST'])
def api_add_project():
    try:
        data = request.get_json(silent=True) or {}
        proj_name = data.get("name", "").strip()
        proj_path = data.get("path", "").strip().strip('"').strip("'")
        default_model = data.get("default_model", "auto").strip()
        
        if not proj_name or not proj_path:
            return jsonify({"status": "error", "message": "Proje adı ve dizin yolu zorunludur."}), 400
            
        mtime = 0
        if os.path.exists(proj_path):
            try: mtime = os.path.getmtime(proj_path)
            except: pass
        else:
            return jsonify({"status": "error", "message": f"Dizin bulunamadı: {proj_path}"}), 400
                
        config = load_projects_config()
        existing_memory = config.get(proj_name, {}).get("memory", [])
        existing_conv_id = config.get(proj_name, {}).get("conversationId")

        config[proj_name] = {
            "path": proj_path,
            "default_model": default_model,
            "created_at": mtime,
            "memory": existing_memory,
            "conversationId": existing_conv_id
        }
        save_projects_config(config)
        return jsonify({"status": "success", "message": f"'{proj_name}' projesi kaydedildi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def _scan_project_folder(proj_path):
    package_text = f"[PROJE ÇALIŞMA ALANI DİZİNİ: {proj_path}]\n"
    count = 0
    for root, dirs, files in os.walk(proj_path):
        dirs[:] = [d for d in dirs if d not in ['.git', 'venv', '__pycache__', 'node_modules', 'chat_history', 'conversations', 'exports', 'excel', 'uploads', 'GK_Studyo_Exports']]
        for file in files:
            lower_f = file.lower()
            if lower_f.endswith(('.png', '.jpg', '.jpeg', '.zip', '.exe', '.pyc', '.xlsx', '.pdf', '.ico', '.db')):
                continue
            file_full_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_full_path, proj_path)
            try:
                with open(file_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    package_text += f"\n--- DOSYA: {rel_path} ---\n{content}\n"
                    count += 1
            except: pass
    return package_text, count

@app.route('/api/projects/activate', methods=['POST'])
def api_activate_project():
    try:
        data = request.get_json(silent=True) or {}
        proj_name = data.get("name", "").strip()
        config = load_projects_config()
        proj = config.get(proj_name)
        if not proj:
            return jsonify({"status": "error", "message": "Proje bulunamadı."}), 404
        if not os.path.exists(proj["path"]):
            return jsonify({"status": "error", "message": f"Dizin mevcut değil: {proj['path']}"}), 400

        if not proj.get("conversationId"):
            proj["conversationId"] = f"proj_{proj_name}_{int(time.time())}"
            config[proj_name] = proj
            save_projects_config(config)

        package_text, count = _scan_project_folder(proj["path"])
        return jsonify({
            "status": "success",
            "project": {
                "name": proj_name,
                "path": proj["path"],
                "default_model": proj.get("default_model", "auto"),
                "conversationId": proj["conversationId"]
            },
            "package_content": package_text,
            "file_count": count
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def index():
    response = make_response(send_from_directory('static', 'index.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/models', methods=['GET'])
def get_models():
    local_models = get_installed_ollama_models()
    if not local_models: local_models = FALLBACK_LOCAL
    if "auto" not in local_models: local_models.append("auto")
    
    vision_models = [m for m in local_models if any(k in m.lower() for k in ["vision", "moondream", "granite"]) and "qwen3-vl" not in m.lower()]
    coder_models = [m for m in local_models if "coder" in m.lower()]
    reasoning_models = [m for m in local_models if any(k in m.lower() for k in ["r1", "deepseek"])]
    
    assigned = set(vision_models + coder_models + reasoning_models + ["auto"])
    pure_local = [m for m in local_models if m not in assigned]

    return jsonify({"local": pure_local, "coder": coder_models, "reasoning": reasoning_models, "vision": vision_models, "cloud": CLOUD_MODELS})

@app.route('/api/parse_file', methods=['POST'])
def parse_file():
    if 'file' not in request.files: return jsonify({"error": "Dosya bulunamadı"}), 400
    file = request.files['file']
    filename = file.filename.lower()
    content = ""
    try:
        if filename.endswith('.pdf'):
            import pdfplumber
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text: content += text + "\n"
        elif filename.endswith(('.xlsx', '.xls')):
            import pandas as pd
            df = pd.read_excel(file)
            content = df.to_string(index=False)
        elif filename.endswith('.csv'):
            import pandas as pd
            df = pd.read_csv(file)
            content = df.to_string(index=False)
        else:
            content = file.read().decode('utf-8', errors='ignore')
        return jsonify({"status": "ok", "filename": file.filename, "content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/markdown-to-excel', methods=['POST'])
def markdown_to_excel():
    data = request.json or {}
    md_text = data.get('markdown_text', '')
    if not md_text: return jsonify({"error": "Metin bulunamadı"}), 400
    lines = md_text.splitlines()
    table_lines = [l for l in lines if '|' in l and not re.match(r'^\s*\|?\s*[:\-\|\s]+\s*\|?\s*$', l)]
    if not table_lines: return jsonify({"error": "Tablo bulunamadı"}), 400
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Stüdyo Tablo"
    for line in table_lines:
        parts = [p.strip() for p in line.split('|')]
        if parts and parts[0] == '': parts = parts[1:]
        if parts and parts[-1] == '': parts = parts[:-1]
        if parts: ws.append(parts)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"tablo_markdown_{timestamp}.xlsx"
    filepath = os.path.join(EXCELS_DIR, filename)
    wb.save(filepath)
    return send_file(filepath, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/image-to-excel', methods=['POST'])
def image_to_excel():
    data = request.json or {}
    image_b64 = data.get('image')
    use_cloud = data.get('use_cloud', False)
    if not image_b64: return jsonify({"error": "Görsel gerekli"}), 400
    clean_b64 = re.sub(r'^data:image/.+;base64,', '', image_b64)
    prompt = "Bu görseldeki tabloyu hücreleri '|' ile ayırarak satırlar halinde yaz. Sadece Markdown tablo verisini döndür."
    text = ""
    try:
        model_tag = "gemini_cloud_flash"
        cloud_failed_reason = None
        if use_cloud and GEMINI_API_KEY:
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + GEMINI_API_KEY
            payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": clean_b64}}]}]}
            try:
                r = requests.post(url, json=payload, timeout=60)
                if r.status_code == 200:
                    res_json = r.json()
                    parts = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    text = "".join([p.get("text", "") for p in parts])
                else:
                    cloud_failed_reason = f"Gemini Cloud Vizyon Hatası ({r.status_code})"
            except requests.exceptions.RequestException as e:
                cloud_failed_reason = f"Gemini Cloud bağlantı hatası: {e}"

        if not text and (not use_cloud or not GEMINI_API_KEY or cloud_failed_reason):
            installed = get_installed_ollama_models()
            if not installed: installed = FALLBACK_LOCAL
            vision_candidates = [m for m in installed if any(k in m.lower() for k in ["granite", "moondream", "vision"]) and "qwen3-vl" not in m.lower()]
            if not vision_candidates:
                if cloud_failed_reason:
                    return jsonify({"error": f"{cloud_failed_reason} — yerel vizyon modeli de yok."}), 500
                return jsonify({"error": "Aktif yerel Vizyon modeli yok."}), 500
            model_to_use = vision_candidates[0]
            model_tag = model_to_use.replace(":", "_").replace("/", "_")
            ollama_payload = {"model": model_to_use, "messages": [{"role": "user", "content": prompt, "images": [clean_b64]}], "stream": False, "options": {"temperature": 0}}
            r = requests.post("http://127.0.0.1:11434/api/chat", json=ollama_payload, timeout=1.500)
            if r.status_code != 200:
                return jsonify({"error": f"Ollama hata: {r.text}"}), 500
            text = r.json().get("message", {}).get("content", "")
        if not text: return jsonify({"error": "Metin çıkarılamadı."}), 500
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Görsel Tablo"
        for line in text.strip().splitlines():
            if line.strip() and '|' in line:
                parts = [c.strip() for c in line.strip('|').split('|')]
                if parts: ws.append(parts)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"tablo_{model_tag}_{timestamp}.xlsx"
        filepath = os.path.join(EXCELS_DIR, filename)
        wb.save(filepath)
        return send_file(filepath, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e: return jsonify({"error": str(e)}), 500

def get_num_ctx(model_name, extra_chars=0, is_project=False):
    """KULLANICI GERI BILDIRIMI: daha once model kategorisine gore 16K
    tavanla iyi yanitlar aliniyordu. Sonra "64k" etiketli modeller icin
    32768/65536'ya cikan bir tavan eklendi - bu, Arc/IPEX donaniminda
    pratikte DAHA YAVAS ve sorunlu sonuc verdi (uzun prefill sureleri,
    2+ dakikaya varan bekleme). Tavan tekrar 16384'e sabitlendi - model
    adinin '64k' icermesi ARTIK tavani yukseltmiyor, sadece kategoriye
    gore hangi kademenin secilecegini etkiliyor (kucuk mesajlar hala
    kucuk/hizli kademede kalir)."""
    tiers = [4096, 8192, 16384]
    hard_cap = 16384
    needed = 2048 + int(extra_chars / 3)
    if is_project:
        needed = max(needed, 16384)
    for t in tiers:
        if t >= needed:
            return min(t, hard_cap)
    return hard_cap

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    model = data.get("model", "qwen2.5:7b")
    prompt = data.get("prompt", "")
    role = data.get("role", "default")
    history = data.get("history", [])
    image_base64 = data.get("image", None)
    images_list = data.get("images", None)
    file_package = data.get("filePackage", None)
    use_web_search = data.get("web_search", False) or data.get("force_web", False)
    is_project = bool(data.get("is_project", False))

    installed = get_installed_ollama_models()
    if not installed: installed = FALLBACK_LOCAL

    route_label = ""
    if not model or model == "auto":
        p_lower = prompt.lower()
        if any(k in p_lower for k in ["kod", "python", "javascript", "fonksiyon", "class", "def ", "script", "hata", "bug", "sql", "html"]):
            coder_match = [m for m in installed if "coder" in m.lower()]
            model = coder_match[0] if coder_match else "qwen2.5:7b"
        elif any(k in p_lower for k in ["neden", "nasıl", "mantık", "analiz", "çözümle", "derin"]):
            r1_match = [m for m in installed if "r1" in m.lower() or "deepseek" in m.lower()]
            model = r1_match[0] if r1_match else "qwen2.5:7b"
        else:
            qwen_default = [m for m in installed if "qwen2.5:7b" in m.lower()]
            model = qwen_default[0] if qwen_default else installed[0]
        route_label = "AU"

    if role and role != "default":
        route_label = (route_label + "+RO") if route_label else "RO"

    web_context = ""
    if use_web_search and GEMINI_API_KEY:
        try:
            search_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + GEMINI_API_KEY
            search_payload = {
                "contents": [{"parts": [{"text": "Hedef Sorgu: " + prompt + "\n\nGörev: Bu sorgu için web üzerinde nokta atışı arama yap. Gürültülü içerikleri ve gereksiz metinleri ele. Doğrudan resmi kaynakları, site yapılarını, dosya ve katalog indirme linklerini net bir Markdown listesi olarak derle."}]}],
                "tools": [{"googleSearch": {}}]
            }
            s_res = requests.post(search_url, json=search_payload, timeout=30)
            if s_res.status_code == 200:
                s_parts = s_res.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
                web_context = "".join([p.get("text", "") for p in s_parts])
            else:
                web_context = f"[UYARI: Bulut web araması başarısız oldu ({s_res.status_code}): {s_res.text[:200]}]"
        except Exception as e:
            web_context = f"[UYARI: Bulut arama hatası: {e}]" 
    if web_context:
        prompt = f"[WEB VERİLERİ]:\n{web_context}\n\n[İSTEK]:\n{prompt}"

    if file_package:
        m_lower = (model or "").lower()
        hard_cap_chars = 16384 * 3
        if len(file_package) > hard_cap_chars:
            kept = file_package[:hard_cap_chars]
            file_package = kept + f"\n\n[!! UYARI: Dosya paketi çok büyüktü, ilk {hard_cap_chars} karakter gösteriliyor. !!]"
        prompt = f"[PAKETLENMİŞ DOSYA İÇERİĞİ]:\n{file_package}\n\n[İSTEK]:\n{prompt}"

    role_instruction = ROLE_PROMPTS.get(role, "")
    system_msg = SYSTEM_PROFILE + ("\n[SİSTEM ROLÜ]: " + role_instruction if role_instruction else "")

    def generate_stream():
        yield "data: " + json.dumps({"type": "meta", "model": model, "route": route_label}) + "\n\n"
        if not model.startswith("gemini"):
            ollama_messages = [{"role": "system", "content": system_msg}]
            for h in history[-8:]: ollama_messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
            user_msg_obj = {"role": "user", "content": prompt}
            all_images = []
            if images_list:
                for img in images_list:
                    all_images.append(re.sub(r'^data:image/.+;base64,', '', img))
            if image_base64:
                all_images.append(re.sub(r'^data:image/.+;base64,', '', image_base64))
            if all_images:
                user_msg_obj["images"] = all_images
            ollama_messages.append(user_msg_obj)
            try:
                total_chars = sum(len(m.get("content", "")) for m in ollama_messages)
                effective_ctx = get_num_ctx(model, extra_chars=total_chars, is_project=is_project)
                dynamic_timeout = 180 if effective_ctx <= 8192 else min(900, 180 + int((effective_ctx - 8192) / 20))
                payload = {"model": model, "messages": ollama_messages, "stream": True, "options": {"temperature": 0.2, "num_ctx": effective_ctx, "num_gpu": int(os.environ.get("OLLAMA_NUM_GPU", "999"))}}
                res = requests.post("http://127.0.0.1:11434/api/chat", json=payload, stream=True, timeout=dynamic_timeout)
                if res.status_code != 200:
                    fallback_model = "qwen2.5:7b"
                    yield "data: " + json.dumps({"type": "meta", "model": fallback_model, "route": "FB"}) + "\n\n"
                    payload["model"] = fallback_model
                    res = requests.post("http://127.0.0.1:11434/api/chat", json=payload, stream=True, timeout=dynamic_timeout)
                for line in res.iter_lines():
                    if line:
                        chunk = json.loads(line.decode('utf-8'))
                        if "error" in chunk:
                            yield "data: " + json.dumps({"type": "error", "message": f"Ollama: {chunk['error']}"}) + "\n\n"
                            break
                        content = chunk.get("message", {}).get("content", "")
                        if content: yield "data: " + json.dumps({"type": "chunk", "text": content}) + "\n\n"
            except Exception as e: yield "data: " + json.dumps({"type": "error", "message": str(e)}) + "\n\n"
        else:
            try:
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + GEMINI_API_KEY
                parts = [{"text": system_msg + "\n\n" + prompt}]
                gemini_images = (images_list or ([image_base64] if image_base64 else []))
                for img in gemini_images:
                    parts.append({"inline_data": {"mime_type": "image/jpeg", "data": re.sub(r'^data:image/.+;base64,', '', img)}})
                payload = {"contents": [{"parts": parts}]}
                res = requests.post(url, json=payload, timeout=60)
                if res.status_code == 200:
                    ans = "".join([p.get("text", "") for p in res.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])])
                    if not ans:
                        ans = f"[UYARI: Gemini 200 döndü ama yanıt metni boş geldi. Ham yanıt: {res.text[:400]}]"
                    yield "data: " + json.dumps({"type": "chunk", "text": ans}) + "\n\n"
                else:
                    # ONEMLI: "Gemini Hatasi" gibi genel bir mesaj yerine
                    # gercek durum kodu + Google'in kendi hata metnini
                    # gosteriyoruz - "bulut calismiyor" sikayetini artik
                    # tahmin etmek yerine dogrudan teshis edebiliriz
                    # (gecersiz/degismis model adi, anahtar sorunu, kota
                    # asimi vb. hepsi burada gorunur).
                    yield "data: " + json.dumps({"type": "error", "message": f"Gemini API Hatası ({res.status_code}): {res.text[:500]}"}) + "\n\n"
            except Exception as e: yield "data: " + json.dumps({"type": "error", "message": str(e)}) + "\n\n"
    return Response(stream_with_context(generate_stream()), mimetype='text/event-stream')

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    def kill_server():
        time.sleep(1)
        subprocess.run("taskkill /F /IM ollama.exe /T", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.kill(os.getpid(), signal.SIGINT)
    threading.Thread(target=kill_server, daemon=True).start()
    return jsonify({"status": "closed"})

@app.route('/models', methods=['GET'])
def grk_models(): return get_models()
@app.route('/chat', methods=['POST'])
def grk_chat(): return chat()
@app.route('/chat-multi-image', methods=['POST'])
def grk_chat_multi_image(): return chat()
@app.route('/upload-pdf', methods=['POST'])
def grk_upload_pdf(): return parse_file()
@app.route('/shutdown', methods=['POST'])
def grk_shutdown(): return shutdown()

@app.route('/gpu-status', methods=['GET'])
def gpu_status():
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        gpu_val = 0
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-Counter '\\GPU Engine(*)\\Utilization Percentage' -ErrorAction SilentlyContinue)."
                 "CounterSamples | Measure-Object -Property CookedValue -Sum | Select-Object -ExpandProperty Sum"],
                capture_output=True, text=True, timeout=1.5
            )
            gpu_val = float(result.stdout.strip() or 0)
        except:
            gpu_val = 0
        return jsonify({'status': 'ok', 'info': f"CPU: %{int(cpu)} | RAM: %{int(ram)}% | GPU: %{int(gpu_val)}"})
    except: return jsonify({'status': 'error', 'info': 'Okunamadı'})

_gpu_cache = {"value": False, "ts": 0}

def _check_windows_gpu_usage():
    now = time.time()
    if now - _gpu_cache["ts"] < 5:
        return _gpu_cache["value"]
    active = False
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Counter '\\GPU Engine(*)\\Utilization Percentage' -ErrorAction SilentlyContinue)."
             "CounterSamples | Measure-Object -Property CookedValue -Sum | Select-Object -ExpandProperty Sum"],
            capture_output=True, text=True, timeout=8
        )
        total = float(result.stdout.strip() or 0)
        if total > 0.5:
            active = True
    except:
        pass
    
    if not active:
        try:
            for p in psutil.process_iter(['name']):
                if p.info.get('name') and 'ollama' in p.info['name'].lower():
                    active = True
                    break
        except:
            pass

    _gpu_cache["value"] = active
    _gpu_cache["ts"] = now
    return active

@app.route('/status', methods=['GET'])
def grk_status():
    ollama_ok = False
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
        ollama_ok = r.status_code == 200
    except Exception:
        pass

    gpu_active = _check_windows_gpu_usage()

    # ONEMLI: sadece "anahtar yeterince uzun mu" diye bakmak da bir ara
    # geri gelmisti - bu, anahtar bicimsel olarak dogru ama GECERSIZ,
    # SUresi dolmus veya kota asilmis olsa bile yesil gosterirdi. Kisa
    # timeout'lu GERCEK bir baglanti denemesi yapiyoruz.
    gemini_ok = False
    if GEMINI_API_KEY:
        try:
            gr = requests.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}",
                timeout=2.5
            )
            gemini_ok = gr.status_code == 200
            if not gemini_ok:
                print(f"[GEMINI-STATUS HATASI] status={gr.status_code} body={gr.text[:300]}")
        except Exception as e:
            print(f"[GEMINI-STATUS İSTİSNASI] {type(e).__name__}: {e}")
            gemini_ok = False
    else:
        print("[GEMINI-STATUS] GEMINI_API_KEY boş/okunamadı - .env dosyasını ve BASE_DIR yolunu kontrol et.")

    return jsonify({"ollama": ollama_ok, "gpu": gpu_active, "gemini": gemini_ok})

@app.route('/api/conversations/delete', methods=['POST'])
def delete_conversation():
    try:
        data = request.get_json(silent=True) or {}
        conv_id = str(data.get('id', '')).strip()
        if not conv_id:
            return jsonify({"status": "error", "message": "id gerekli"}), 400
        removed_from = []
        if os.path.exists(CHAT_DIR):
            for fn in os.listdir(CHAT_DIR):
                if not fn.endswith('.json'):
                    continue
                fpath = os.path.join(CHAT_DIR, fn)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        fdata = json.load(f)
                    convs = fdata.get('conversations', {})
                    if conv_id in convs:
                        del convs[conv_id]
                        fdata['conversations'] = convs
                        if fdata.get('currentConvId') == conv_id:
                            fdata['currentConvId'] = None
                        with open(fpath, 'w', encoding='utf-8') as f:
                            json.dump(fdata, f, ensure_ascii=False, indent=4)
                        removed_from.append(fn)
                except Exception:
                    continue
        return jsonify({"status": "success", "removed_from": removed_from})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/load-conversations', methods=['GET'])
def load_conversations():
    all_convs = {}
    latest_id = None
    max_id = 1
    if os.path.exists(CHAT_DIR):
        for fn in os.listdir(CHAT_DIR):
            if fn.endswith('.json'):
                try:
                    with open(os.path.join(CHAT_DIR, fn), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for cid, c in data.get('conversations', {}).items(): all_convs[cid] = c
                        if data.get('currentConvId'): latest_id = data.get('currentConvId')
                        if data.get('nextId', 1) > max_id: max_id = data.get('nextId', 1)
                except: pass
    return jsonify({'found': bool(all_convs), 'data': {'conversations': all_convs, 'currentConvId': latest_id, 'nextId': max_id}})

@app.route('/save-conversations', methods=['POST'])
def save_conversations():
    data = request.get_json() or {}
    convs = data.get('conversations', {})
    cur_id = data.get('currentConvId')
    next_id = data.get('nextId', 1)
    groups = {}
    for cid, c in convs.items():
        m = (c.get('model') or 'default_model').replace(":", "_").replace("\\", "_").replace("/", "_")
        if m not in groups: groups[m] = {}
        groups[m][cid] = c
    for m, g in groups.items():
        try:
            with open(os.path.join(CHAT_DIR, f"{m}.json"), 'w', encoding='utf-8') as f:
                json.dump({"conversations": g, "currentConvId": cur_id if cur_id in g else None, "nextId": next_id}, f, ensure_ascii=False, indent=4)
        except: pass
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)


@app.route('/api/projects/delete', methods=['POST'])
def api_delete_project():
    try:
        data = request.get_json(silent=True) or {}
        proj_name = data.get("name", "").strip()
        if not proj_name:
            return jsonify({"status": "error", "message": "Proje adÄ± zorunludur."}), 400
        config = load_projects_config()
        if proj_name in config:
            del config[proj_name]
            save_projects_config(config)
            return jsonify({"status": "success", "message": f"'{proj_name}' projesi silindi."})
        return jsonify({"status": "error", "message": "Proje bulunamadÄ±."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500








