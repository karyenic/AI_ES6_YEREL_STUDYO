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

Hedef çalışma biçimi: kullanıcı açısından tek konsol. Runner, bridge ve Flask ayrı süreçler olarak çalışabilir ancak kullanıcıya gereksiz ayrı CMD pencereleri açılmamalıdır.

Hedef log yapısı:

- `ipex_runner.log`
- `ai_bridge.log`
- `studio.log`

Launcher kapanırken yalnızca bu oturumda başlatılan süreçleri durdurmalıdır. Daha önce çalışan bağımsız runner/bridge süreçlerine dokunulmamalıdır.

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

Bu çoklu-model yapı henüz uygulanmış değildir. VRAM, runner yaşam döngüsü, model değiştirme, model başlatma maliyeti ve eşzamanlılık ayrıca test edilmelidir.

## RAG / Embedding

`/api/embeddings` mevcut bridge sürümünde henüz gerçek embedding backend'ine bağlı değildir ve `501` döndürür.

RAG embedding, sohbet modelinden ayrı bir katmandır. Önce embedding modelinin IPEX/SYCL üzerinde çalışması doğrulanacak; daha sonra bridge'e bağlanacaktır.

## Context notu

GK AI STUDIO'nun mevcut `app.py` sürümünde chat payload'ı `num_ctx=16384` göndermektedir. Mevcut IPEX runner ise `--ctx-size 4096` ile başlatılmaktadır. Bu iki değer sonraki performans ve uyumluluk testinin açık maddesidir. `app.py` değiştirilmeden bridge/runner tarafında güvenli bir çözüm tercih edilmelidir.

## GERİ KAZANILACAK WEB SEARCH DAVRANIŞI

Önceki çalışma sürümlerinde web arama daha gelişmiş bir akışa sahipti. Git geçmişindeki 3 Eylül 2026 yedeğinde Gemini + Google Search için şu yaklaşım görülüyor:

- Kullanıcı sorgusunu "Hedef Sorgu" olarak modele aktarma
- Web üzerinde nokta atışı arama istemi
- Gürültülü içerikleri ve gereksiz metinleri eleme
- Resmi kaynakları önceliklendirme
- Site yapısını çıkarma
- Dosya / katalog / indirme bağlantılarını belirgin şekilde filtreleme
- Sonuçları temiz Markdown listesi olarak derleme

Bu davranış mevcut sadeleştirilmiş sürümde kaybolmuştur. Önceki yedekten geri kazanılacak ve daha sonra yeni mimariye uyarlanacaktır. fileciteturn24file1L34-L45

## İYİLEŞTİRME / BUG LİSTESİ

### 1. Web Search yeniden kurulacak

Hedef davranış:

```text
Kullanıcı sorgusu
      ↓
Gemini / akıllı web arama
      ↓
sonuçları filtrele
      ↓
resmi / güvenilir kaynakları önceliklendir
      ↓
gereksiz/gürültülü sonuçları ele
      ↓
özetlenmiş ve kaynaklı sonuç
```

BeautifulSoup doğrudan model aramasının yerine geçmeyecek; gerektiğinde sayfa içeriği/bağlantı çıkarımı için yardımcı katman olacak. Eski Gemini tabanlı nokta-atışı arama davranışı korunacaktır.

### 2. Yanıt sırasında yeni soru gönderme problemi

Model cevap üretirken kullanıcı hazır tuttuğu bir sonraki sorunun gönder tuşuna bastığında bazı aksamalar oluşuyor.

Araştırılacak konular:

- aktif request kilidi
- aynı anda ikinci `/chat` çağrısı
- streaming bağlantısının yarım bırakılması
- UI gönder butonunun disable/enable durumu
- ikinci sorunun kuyruğa alınması veya güvenli şekilde reddedilmesi
- eski stream tamamlanmadan yeni cevabın UI'ı ezmesi

Hedef davranış:

```text
Model cevaplıyor
      |
      +--> Gönder'e basılırsa
              |
              +--> güvenli kuyruk
              veya
              +--> "önceki yanıt sürüyor" uyarısı
```

### 3. IPEX multi-model desteği

Her seçilen model için gerçekten GPU kullanımı doğrulanmadan UI'da "GPU" kabul edilmemeli.

Testler:

- Qwen Coder 7B
- Qwen 2.5 7B
- DeepSeek R1
- Gemma
- model değiştirme sonrası eski runner'ın temizlenmesi
- VRAM kullanımının ölçülmesi
- aynı anda kaç modelin 16 GB Arc belleğe sığdığı

### 4. RAG / Embedding

`/api/embeddings` gerçek backend'e bağlanacak.

Önce:

```text
embedding modeli
      ↓
Intel Arc / IPEX-SYCL test
```

Sonra:

```text
ChromaDB
   ↓
embedding
   ↓
RAG sorgusu
   ↓
chat modeli
```

### 5. Context / performans

4096, 8192 ve 16384 context seviyeleri gerçek Arc 140V üzerinde karşılaştırılacak.

Ölçülecekler:

- ilk token süresi
- token/saniye
- VRAM
- RAM
- uzun prompt davranışı
- model yeniden yükleme süresi

### 6. Streaming kararlılığı

Ollama uyumlu NDJSON ile IPEX runner'ın `/completion` akışı arasındaki dönüşüm daha kapsamlı test edilecek.

### 7. Vision / multimodal

`app.py` görsel isteklerde de `11434/api/chat` kullanmaktadır. Bridge'in görselleri gerçek bir vision runner'a aktarabilmesi ayrıca tasarlanmalıdır. Vision modelinin otomatik olarak Qwen Coder runner'a yönlendirilmemesi gerekir.

### 8. Model listesi / durum bilgisi

`/api/tags` ve `/api/ps` şu anda bridge tarafından uyumluluk amaçlı üretilmektedir. Gelecekte gerçek runner/model durumunu yansıtacak şekilde geliştirilmelidir.

### 9. Temiz kapatma

Tek konsollu launcher kapanırken:

- Flask
- bridge
- sadece launcher'ın başlattığı runner

kontrollü biçimde kapatılmalı; başka Ollama süreçleri yanlışlıkla öldürülmemelidir.

## DENEME / DOĞRULAMA LİSTESİ

Her değişiklikten sonra minimum test sırası:

1. Runner `/health`
2. Runner `/completion`
3. Bridge `/api/version`
4. Bridge `/api/tags`
5. Bridge `/api/chat` non-stream
6. Bridge `/api/chat` stream
7. GK AI STUDIO normal sohbet
8. Uzun Türkçe prompt
9. Kod üretimi
10. Model değişimi
11. RAG/embedding
12. Yanıt devam ederken yeni soru gönderme
13. Studio kapatma / yeniden başlatma

## Çalıştırma

1. Normal Ollama'nın 11434 portunu kullanmadığından emin olun.
2. `baslat_ipex_bridge.bat` çalıştırın.
3. Launcher tek konsolda durum bilgisini göstermelidir.
4. Tarayıcı `http://127.0.0.1:5000` adresine açılır.
5. Loglar gerekirse `.log` dosyalarından incelenir.

## Güvenlik / stabilite ilkesi

- `app.py` gereksiz yere değiştirilmez.
- Çalışan Qwen + IPEX zinciri bozulmaz.
- Yeni model desteği gerçek GPU doğrulaması olmadan aktif kabul edilmez.
- RAG embedding, chat'ten ayrı ve kontrollü aşamada eklenir.
- Normal Ollama ile IPEX portable Ollama birbirine karıştırılmaz.
- Her önemli değişiklik ayrı Git branch/commit ile geri alınabilir halde tutulur.
