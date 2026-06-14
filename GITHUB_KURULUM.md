# GitHub'a Yükleme Adımları

Bu depo push edilmeye hazırdır. Aşağıdaki adımları kendi GitHub hesabınızla
çalıştırın (kimlik doğrulama gerektiği için bu adımı sizin yapmanız gerekir).

## 1. GitHub'da boş bir depo oluşturun
github.com → New repository → ör. `jfreechart-qmood-analiz`
(README/lisans EKLEMEYİN; bu depoda zaten var.)


## 2. Yerelde başlatın ve push edin

```bash
cd qmood-jfreechart
git init
git add .
git commit -m "JFreeChart QMOOD kalite evrimi + LLM analizi (dönem projesi)"
git branch -M main
git remote add origin https://github.com/<KULLANICI_ADI>/jfreechart-qmood-analiz.git
git push -u origin main
```

## 3. Rapor ve sunumdaki bağlantıyı güncelleyin
Depo bağlantısını aldıktan sonra:
- `rapor/build_report.js` içindeki "[depo bağlantısı buraya]" yerine linki yazıp
  `node scripts/build_report.js` ile raporu yeniden üretin (veya .docx başlık
  sayfasını elle düzenleyin).
- Sunumun başlık slaytındaki "[depo bağlantısı]" ifadesini güncelleyin.

## Notlar
- `data/` klasörü (her sürümün CSV'leri) repoya dahildir; analizi yeniden
  çalıştırmadan sonuçların görülebilmesi için faydalıdır. İstemezseniz
  `.gitignore`'a `data/` ekleyip commit'ten çıkarabilirsiniz.
- `.gitignore`, `node_modules/`, `__pycache__/` ve geçici PDF/slide görüntülerini
  hariç tutar.
