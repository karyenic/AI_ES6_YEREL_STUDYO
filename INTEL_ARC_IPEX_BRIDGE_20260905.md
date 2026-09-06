# GK AI STUDIO — Intel Arc 140V + IPEX-LLM Bridge

## 2026-09-06 durum

Bu branch, Intel Arc 140V üzerinde doğrudan çalışan IPEX `ollama-lib.exe runner` ile GK AI STUDIO arasındaki uyumluluk katmanını ve tek konsollu başlatma düzenini içerir.

## Kanıtlanmış GPU zinciri

- Intel Arc 140V GPU 16 GB
- Level Zero / SYCL cihazı görüldü
- Qwen 2.5 Coder 7B Q4_K_M modeli yüklendi
- `offloaded 29/29 layers to GPU`
- Runner: `127.0.0.1:59584`
- `/health` başarılı
- `/completion` gerçek token üretimi başarılı
- Bridge: `127.0.0.1:11434`
- GK AI STUDIO: `127.0.0.1:5000`

## Mimari

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

`app.py` IPEX/SYCL ayrıntılarını taşımaz; Ollama uyumlu API'ye `127.0.0.1:11434` üzerinden bağlanır.

## Tek konsol düzeni

`baslat_ipex_bridge.bat` artık runner, bridge ve Flask için ayrı CMD pencereleri açmak yerine servisleri arka planda başlatmayı hedefler.

Loglar:

- `ipex_runner.log`
- `ai_bridge.log`
- `studio.log`

Launcher kapanırken yalnızca **bu oturumda başlatılan** süreçleri durdurmayı hedefler. Daha önce çalışan runner/bridge süreçlerine dokunulmaz.

## Model mimarisi

Şu an gerçek IPEX runner tek model için yapılandırılmıştır:

```text
qwen2.5-coder:7b → IPEX runner → Intel Arc 140V
```

GK AI STUDIO içinde görünen diğer Ollama modellerinin otomatik olarak IPEX GPU'da çalıştığı varsayılmamalıdır.

Hedeflenen sonraki mimari:

```text
                 ┌→ Qwen Coder 7B → IPEX → Arc
GK AI STUDIO ────┼→ Qwen 2.5 7B  → IPEX → Arc
                 ├→ DeepSeek R1   → IPEX → Arc
                 └→ diğer modeller → uygun runner → Arc/CPU
```

Bu çoklu-model yapı henüz uygulanmış değildir. VRAM, runner yaşam döngüsü, model değiştirme ve eşzamanlılık ayrıca test edilmelidir.

## RAG / Embedding

`/api/embeddings` mevcut bridge sürümünde henüz gerçek embedding backend'ine bağlı değildir ve `501` döndürür.

RAG embedding, sohbet modelinden ayrı bir katmandır. Önce embedding modelinin IPEX/SYCL üzerinde çalışması doğrulanacak; daha sonra bridge'e bağlanacaktır.

## Context notu

GK AI STUDIO mevcut `app.py` içinde chat isteklerinde `num_ctx=16384` göndermektedir. Mevcut IPEX runner başlangıçta `--ctx-size 4096` ile çalıştırılmıştır. Bu değerler sonraki performans/uyumluluk testinde birlikte ele alınmalıdır.

## Çalıştırma

1. Normal Ollama'nın 11434 portunu kullanmadığından emin olun.
2. `baslat_ipex_bridge.bat` çalıştırın.
3. Launcher tek konsolda durum bilgisini gösterir.
4. Tarayıcı `http://127.0.0.1:5000` adresine açılır.
5. Gerekirse loglar Studio klasöründeki `.log` dosyalarından incelenir.

## Güvenlik / stabilite ilkesi

- `app.py` gereksiz yere değiştirilmez.
- Çalışan Qwen + IPEX zinciri bozulmaz.
- Yeni model desteği gerçek GPU doğrulaması olmadan aktif kabul edilmez.
- RAG embedding, chat'ten ayrı ve kontrollü aşamada eklenir.
