# Intel Arc 140V + IPEX-LLM + Ollama Bridge

## 2026-09-05 doğrulama

Bu sürüm, Intel Arc 140V üzerinde doğrudan çalışan IPEX `ollama-lib.exe runner` ile GK AI STUDIO arasına uyumluluk katmanı ekler.

### Kanıtlanmış GPU zinciri

- Intel Arc 140V GPU 16 GB
- Level Zero / SYCL cihazı görüldü
- Qwen 2.5 Coder 7B Q4_K_M modeli yüklendi
- `offloaded 29/29 layers to GPU`
- Runner: `127.0.0.1:59584`
- `/health` → `{"status":0,"progress":1}`
- `/completion` gerçek token üretti

### Mimari

```text
GK AI STUDIO
     |
     v
   app.py
     |
     v
11434  ai_bridge.py
     |
     v
59584  IPEX ollama-lib runner
     |
     v
ggml-sycl / Level Zero
     |
     v
Intel Arc 140V
```

`app.py` bu sürümde IPEX/SYCL bilgisi taşımaz. Mevcut `app.py`, Ollama API'sine `127.0.0.1:11434` üzerinden istek göndermeye devam eder.

## Dosyalar

- `ai_bridge.py` — temel `/api/chat`, `/api/generate`, `/api/tags`, `/api/ps`, `/api/version` uyumluluğu.
- `baslat.bat` — IPEX runner + bridge + Flask başlatma orkestrasyonu.

## Önemli sınırlar

- Runner `--parallel 1` olduğundan bridge inference isteklerini seri hale getirir.
- `/api/embeddings` bu sürümde bilinçli olarak `501` döndürür. RAG/embedding, ayrı test ve tasarım aşamasıdır.
- Vision/multimodal istekleri henüz bridge'e taşınmamıştır.
- Çoklu model desteği henüz yoktur; varsayılan model `qwen2.5-coder:7b`.
- `app.py` değiştirilmemiştir.

## Çalıştırma

1. IPEX runner'ın 59584 üzerinde çalıştığından emin olun veya `baslat.bat` ile başlatın.
2. `baslat.bat` bridge'i 11434'te açar.
3. Flask uygulaması 5000'de başlar.
4. Test: `curl http://127.0.0.1:11434/api/version`
5. Chat testi için GK AI STUDIO arayüzü kullanılabilir.

> Not: Sistemde normal Ollama da 11434 kullanıyorsa önce kapatılmalıdır. Bu mimaride 11434 bridge'e ayrılmıştır.
