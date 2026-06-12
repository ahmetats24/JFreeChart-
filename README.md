# JFreeChart QMOOD Kalite Evrimi Analizi

**Yazılım Mimarileri ve Tasarım Yöntemleri — Dönem Projesi**

Bu depo, açık kaynak **JFreeChart** kütüphanesinin 2007–2025 yılları arasındaki
**12 sürümünü**, Bansiya & Davis'in (2002) **QMOOD** (Quality Model for
Object-Oriented Design) modeliyle analiz eden uçtan uca bir Python pipeline'ı
içerir. Kaynak koddan nesne yönelimli metrikler statik analizle çıkarılır, QMOOD
tasarım özelliklerine ve oradan 6 kalite niteliğine eşlenir; sürümler arası
kalite değişimi, mimari bozulma ve teknik borç yorumlanır.

> Tüm metrikler **kaynak koddan kendi yazdığımız çıkarıcı** ile hesaplanmıştır;
> hazır analiz çıktısı veya üçüncü parti metrik aracı kullanılmamıştır (yönerge
> gereği). Tek bağımlılık, ayrıştırma (parsing) için `javalang`'dır.

---

## 1. Analiz edilen sürümler

Repo geçmişi GitHub'da 2007-06-29'da `1.0.x` dalının başlangıcıyla (1.0.6)
başladığı için daha eski sürümler erişilebilir değildir. 1.0.x ailesinde resmi
git etiketi bulunmayan sürümler için, projenin `NEWS` dosyasındaki **yayın
tarihine** denk gelen commit anlık görüntüsü (snapshot) kullanılmıştır.

| Sürüm | Tarih | Referans türü |
|---|---|---|
| 1.0.6 | 2007-06 | commit (1.0.x dalı başlangıcı) |
| 1.0.9 | 2008-01 | commit (yayın tarihi) |
| 1.0.11 | 2008-09 | commit (yayın tarihi) |
| 1.0.13 | 2009-04 | commit (yayın tarihi) |
| 1.0.14 | 2011-11 | commit (yayın tarihi) |
| 1.0.16 | 2013-09 | commit (yayın tarihi) |
| 1.0.19 | 2014-07 | resmi etiket `v1.0.19` |
| 1.5.0 | 2017-11 | resmi etiket `v1.5.0` |
| 1.5.2 | 2020-12 | resmi etiket `v1.5.2` |
| 1.5.4 | 2023-01 | resmi etiket `v1.5.4` |
| 1.5.5 | 2024-06 | resmi etiket `v1.5.5` |
| 1.5.6 | 2025-05 | resmi etiket `v1.5.6` |

Tam commit SHA'ları `versions.json` dosyasındadır.

---

## 2. Metodoloji ve metrik → özellik eşlemesi

QMOOD üç katmanlıdır: **(metrikler) → (tasarım özellikleri) → (kalite
nitelikleri)**. Sınıf başına çıkarılan metrikler, sistem düzeyinde aşağıdaki 11
tasarım özelliğine toplanır (sınıflar üzerinde ortalama; aksi belirtilmedikçe
arayüzler ortalamalara dahil **değildir**):

| QMOOD Tasarım Özelliği | Kullanılan metrik | Toplama |
|---|---|---|
| Design Size (Tasarım Boyutu) | DSC | sınıf sayısı |
| Hierarchies (Hiyerarşiler) | NOH | kök hiyerarşi sayısı |
| Abstraction (Soyutlama) | ANA | ort. atalar sayısı |
| Encapsulation (Kapsülleme) | DAM | ort. private/protected alan oranı |
| Coupling (Bağlılık) | DCC | ort. doğrudan sınıf bağlantısı |
| Cohesion (Uyum) | CAM | ort. metot-parametre tipi tutarlılığı |
| Composition (Bileşim) | MOA | ort. veri-üyesi (kullanıcı tipi alan) sayısı |
| Inheritance (Kalıtım) | MFA | ort. miras alınan metot oranı |
| Polymorphism (Çok biçimlilik) | NOP | ort. polimorfik metot sayısı |
| Messaging (Mesajlaşma) | CIS | ort. public metot sayısı |
| Complexity (Karmaşıklık) | NOM | ort. metot sayısı |

### Kalite niteliği formülleri (Bansiya & Davis 2002 ağırlıkları)

```
Reusability       = -0.25·Coupling + 0.25·Cohesion + 0.50·Messaging + 0.50·DesignSize
Flexibility       =  0.25·Encapsulation - 0.25·Coupling + 0.50·Composition + 0.50·Polymorphism
Understandability = -0.33·Abstraction + 0.33·Encapsulation - 0.33·Coupling + 0.33·Cohesion
                    - 0.33·Polymorphism - 0.33·Complexity - 0.33·DesignSize
Functionality     =  0.12·Cohesion + 0.22·Polymorphism + 0.22·Messaging
                    + 0.22·DesignSize + 0.22·Hierarchies
Extendibility     =  0.50·Abstraction - 0.50·Coupling + 0.50·Inheritance + 0.50·Polymorphism
Effectiveness     =  0.20·Abstraction + 0.20·Encapsulation + 0.20·Composition
                    + 0.20·Inheritance + 0.20·Polymorphism
```

**Normalizasyon:** Her tasarım özelliği, ilk analiz edilen sürüm (1.0.6 = 1.00)
taban alınarak oranlanır; kalite formülleri bu normalize değerler üzerinden
hesaplanır. Böylece skorlar sürümler arası **göreli** değişimi gösterir (QMOOD'un
önerdiği yaklaşım).

---

## 3. Hesaplama yaklaşımları ve geçerlilik tehditleri

Rapordaki "Tartışma / Geçerlilik Tehditleri" bölümünde bunlara değinilmelidir:

1. **Statik ayrıştırma, derleme yok.** Metrikler `javalang` ile sözdizimi
   ağacından çıkarılır; tip çözümlemesi isim tabanlı sezgisel (heuristic)
   yöntemledir. Tam bir tip denetleyicisi değildir.

2. **Yalnızca proje-içi bağlılık.** Coupling (DCC/CBO/MPC), yalnızca JFreeChart'ın
   kendi sınıfları arasındaki bağlantıları sayar; JDK/dış kütüphane bağımlılıkları
   hariçtir. Bu, Bansiya & Davis'in sistemin kendisini analiz eden aracıyla
   tutarlıdır ve sürümler arası karşılaştırmayı adil tutar.

3. **NOP (Polymorphism) ölçüm artefaktı — ÖNEMLİ.** İlk yaklaşımda polimorfik
   metotlar `@Override` anotasyonuna göre de sayılıyordu. JFreeChart'ta `@Override`
   kullanımı 1.0.16 → 1.0.19 arasında **167'den 2469'a** fırlamıştır (2014'teki
   toplu anotasyon temizliği). Bu, gerçek bir tasarım değişikliği değil, **stil
   değişikliğidir**. Bu nedenle `NOP_strict` tanımlandı: anotasyondan bağımsız
   olarak yalnızca *abstract metotlar* + *proje-içi bir atanın metot imzasını
   (ad + arite) gerçekten ezen metotlar* sayılır. Polymorphism özelliği
   `NOP_strict` ile hesaplanır; her iki varyant da `classes.csv` içinde mevcuttur.
   Bu vaka, "metrik tanımının ölçüm sonucunu nasıl bozabileceğine" dair raporda
   güçlü bir örnektir.

4. **1.0.6 anlık görüntüsü.** 1.0.6 için tam yayın etiketi olmadığından 1.0.x
   dalının ilk commit'i kullanılmıştır; bu, yayımlanan 1.0.6'ya çok yakındır ancak
   birebir aynı olmayabilir. Taban çizgisi olduğu için tüm normalize değerleri
   etkiler (sistematik, yön değiştirmeyen bir etki).

5. **Test/deneysel kod hariç.** Yalnızca ana kaynak kökü analiz edilir
   (`src/main/java` veya eski düzende `source`); test, deneysel ve SWT modülleri
   dışarıda bırakılır.

---

## 4. Temel bulgular (özet)

- **Tasarım boyutu** istikrarlı büyüdü: 446 → 564 sınıf (+ 86 → 111 arayüz).
- **1.0.x dönemi (2007–2014):** Kademeli büyüme; Reusability ve Functionality
  yavaşça artarken **Understandability sürekli kötüleşti** (büyüklük ve
  karmaşıklık arttıkça beklenen davranış).
- **1.5.0 (2017) — gerçek mimari olay:** Bu sürümde, ayrı bir bağımlılık olan
  **JCommon** kütüphanesi büyük ölçüde projeye gömüldü. Sonuç metriklerde net
  görülür: **Composition +%33.8**, Coupling +%7.2, **Abstraction −%8.8**,
  Inheritance −%7.8. Buna bağlı olarak **Extendibility 1.0.19'daki ~1.01
  düzeyinden 1.5.0'da ~0.87'ye düştü** — projenin genişletilebilirliğinde gerçek
  bir gerileme.
- **1.5.x dönemi (2017–2025):** Görece durağanlaşma ve kısmi toparlanma;
  Flexibility ve Effectiveness en yüksek değerlerine ulaştı.
- **Kalıcı teknik borç hotspot'ları:** `XYPlot` (WMC≈658, LCOM≈24500) ve
  `CategoryPlot` her sürümde en karmaşık ve en düşük uyumlu sınıflar — klasik
  "god class" belirtileri; refactoring için birincil adaylar.

Tam tablolar `results/` altındaki CSV'lerde, görseller `charts/` altındadır.

---

## 5. Klasör yapısı

```
qmood-jfreechart/
├── versions.json              # 12 sürüm: etiket/commit + tarih
├── README.md
├── LICENSE                    # MIT
├── GITHUB_KURULUM.md          # depoyu push etmek için adımlar (kullanıcı çalıştırır)
├── scripts/
│   ├── extract_metrics.py     # javalang tabanlı metrik çıkarıcı (çekirdek)
│   ├── run_all.py             # her sürümü indirir + analiz eder
│   ├── qmood.py               # normalizasyon + 6 kalite formülü + grafikler
│   ├── make_llm_inputs.py     # Faz 2 için LLM girdi paketleri üretir
│   ├── compare_llms.py        # LLM çıktılarını karşılaştırır (korelasyon + grafik)
│   ├── build_report.js        # 7 bölümlük akademik raporu (.docx) üretir
│   └── build_deck.js          # sunumu (.pptx) üretir
├── data/<sürüm>/
│   ├── classes.csv            # sınıf başına tüm ham metrikler
│   └── summary.json           # sürüm özeti + tasarım özellikleri
├── results/
│   ├── design_properties.csv             # ham tasarım özellikleri
│   ├── design_properties_normalized.csv  # normalize (1.0.6=1.00)
│   ├── qmood_quality_scores.csv          # 6 kalite niteliği skoru
│   ├── raw_metric_means.csv              # sınıf başına ort. metrikler
│   └── llm_karsilastirma_sonuc.json      # LLM karşılaştırma çıktısı
├── charts/
│   ├── 01_qmood_kalite_evrimi.png        # kalite niteliklerinin evrimi
│   ├── 02_tasarim_ozellikleri.png        # 11 tasarım özelliği (normalize)
│   ├── 03_tasarim_boyutu.png             # sınıf/arayüz büyümesi
│   ├── 04_ham_metrikler.png              # ortalama OO metrikleri
│   └── 05_llm_puan_karsilastirma.png     # LLM puan karşılaştırması
├── llm_inputs/
│   ├── 00_prompt_sablonu.md   # tüm LLM'lere verilecek ortak prompt
│   └── <sürüm>.md             # sürüm başına metrik paketi
├── llm_outputs/
│   ├── 00_karsilastirma_metodolojisi.md      # prompt mühendisliği + karşılaştırma yöntemi
│   ├── LLM_PROMPTLARI_yapistir.md            # 12 sürüm için hazır promptlar
│   ├── claude_degerlendirme.md               # Claude'un 12 sürüm değerlendirmesi
│   ├── chatgpt_degerlendirme.md              # ChatGPT'nin 12 sürüm değerlendirmesi
│   ├── gemini_degerlendirme.md               # Gemini'nin 12 sürüm değerlendirmesi
│   ├── _responses/                           # her sürüm için ayrı ham LLM çıktıları
│   └── llm_puan_karsilastirma.csv            # 3 modelin puan tablosu (dolu)
├── rapor/
│   └── JFreeChart_QMOOD_Rapor.docx           # 7 bölümlük akademik rapor
└── sunum/
    └── JFreeChart_QMOOD_Sunum.pptx           # 12 slaytlık sunum
```

---

## 6. Çalıştırma

```bash
# Bağımlılıklar
pip install javalang pandas matplotlib

# 1) Tüm sürümleri indir + analiz et (data/ üretilir)
cd scripts && python3 run_all.py            # veya: python3 run_all.py 1.5.6

# 2) QMOOD skorlarını ve grafikleri üret (results/ + charts/)
python3 qmood.py

# 3) LLM girdi paketlerini üret (llm_inputs/)
python3 make_llm_inputs.py

# 4) (Faz 2 sonrası) LLM puanlarını karşılaştır (results/ + charts/05)
python3 compare_llms.py

# 5) Raporu (.docx) ve sunumu (.pptx) üret  (Node.js + 'npm install docx pptxgenjs')
node build_report.js
node build_deck.js
```

İnternet erişimi `codeload.github.com` üzerinden sürüm tarball'larını indirmek
için gereklidir.

## Teslimler (hazır)

- **Akademik rapor:** `rapor/JFreeChart_QMOOD_Rapor.docx` — 7 bölüm (Giriş,
  Literatür, Yöntem, Analiz, Sonuçlar, Tartışma, Gelecek) + özet + kaynakça,
  başlık sayfası, içindekiler, gömülü grafikler ve tablolar.
- **Sunum:** `sunum/JFreeChart_QMOOD_Sunum.pptx` — 12 slayt, native grafikler.
- **Analiz kodları:** `scripts/` altındaki 7 betik.
- **Promptlar ve LLM materyalleri:** `llm_inputs/`, `llm_outputs/`.
- **Grafikler:** `charts/` (5 adet).
- **Ham sonuçlar:** `results/`, `data/`.

---

## 7. Faz 2 — LLM tabanlı değerlendirme (TAMAMLANDI)

Üç büyük dil modeli (Claude, ChatGPT, Gemini), 12 sürümün her biri için aynı promptla
(`llm_inputs/00_prompt_sablonu.md`) değerlendirildi. Tam çıktılar `llm_outputs/` altındadır:
`claude_degerlendirme.md`, `chatgpt_degerlendirme.md`, `gemini_degerlendirme.md`.
Puanlar `llm_puan_karsilastirma.csv`'de; karşılaştırma sonuçları `results/llm_karsilastirma_sonuc.json`
ve grafiği `charts/05_llm_puan_karsilastirma.png`'dedir.

### Sürüm bazlı puanlar (0–100)

| Sürüm | 1.0.6 | 1.0.9 | 1.0.11 | 1.0.13 | 1.0.14 | 1.0.16 | 1.0.19 | 1.5.0 | 1.5.2 | 1.5.4 | 1.5.5 | 1.5.6 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Claude | 68 | 67 | 66 | 65 | 65 | 64 | 66 | 64 | 64 | 66 | 67 | 67 |
| ChatGPT | 68 | 65 | 62 | 61 | 59 | 58 | 60 | 57 | 57 | 58 | 59 | 58 |
| Gemini | 55 | 50 | 45 | 35 | 30 | 28 | 32 | 48 | 48 | 46 | 46 | 45 |

### Temel karşılaştırma bulguları
- **Ortak teşhis:** Üç model de aynı god-class'ları (XYPlot, CategoryPlot) ve aşırı bağlı
  ChartFactory'yi yakaladı; sınıf düzeyinde somut refactoring önerdi; hiçbiri halüsinasyon yapmadı.
- **Eğilim uyumu:** 1.0.x boyunca üçü de monoton düşüş gösterdi (QMOOD Anlaşılabilirlik erozyonuyla
  örtüşür). İkili Pearson: Claude–ChatGPT 0.68, Claude–Gemini 0.50, ChatGPT–Gemini 0.39.
- **1.5.0'da ayrışma:** Gemini bu sürümü iyileşme (32→48) olarak gördü; Claude/ChatGPT hafif gerileme
  (66→64, 60→57). Aynı veriyi farklı ağırlıklandırdılar.
- **Mutlak puan farkı:** Gemini sistematik olarak çok daha sert (ortalama ~41 vs Claude 66, ChatGPT 60);
  ortalama mutlak farklar (MAD) 5.6 / 23.4 / 17.8 puan. LLM skorları mutlak ölçü değil, sıralama sinyali
  olarak güvenilir.

`compare_llms.py` yeniden çalıştırıldığında bu sonuçlar (korelasyon + grafik) otomatik üretilir.


## 8. Rapor için ipuçları

- **Yöntem bölümü:** Bölüm 2'deki eşleme tablosu ve formüller doğrudan kullanılabilir.
- **Geçerlilik tehditleri:** Bölüm 3, özellikle NOP artefaktı (madde 3) güçlü bir tartışma örneğidir.
- **Analiz bölümü:** 1.5.0'daki JCommon birleşmesi, mimari kararın metriklere yansıması için somut bir vakadır.
- **LLM karşılaştırması:** Bölüm 7'deki tablo ve bulgular, raporun karşılaştırma bölümünü (rapor 6.3) destekler.
