# 🏗️ CE 4011: Yapısal Analiz Yazılımı (v2.0)

Selam! Bu repo, **METU CE 4011** dersi kapsamında geliştirdiğim 2D yapısal analiz yazılımının en güncel halini içeriyor. İlk başta temel bir çerçeve çözücü olarak başlayan bu proje, Assignment #4 ile birlikte gerçek dünya mühendislik problemlerine kafa tutan profesyonel bir simülasyon aracına dönüştü.

## ✨ Neler Yeni? (Assignment #4 Güncellemeleri)

Sadece dış yükleri hesaplamak yetmezdi; yapıyı içten zorlayan etkileri de koda öğrettik:

* **Sıcaklık Yükleri:** Elemanlardaki üniform genleşme ve kesit içindeki sıcaklık gradyanı (alt-üst farkı) etkileri artık sistemin bir parçası.
* **Mesnet Çökmeleri:** "Zemin her zaman sağlamdır" demedik; mesnetlerdeki beklenmedik çökmeleri (Support Settlements) hesaba katan Penalty Method entegrasyonunu tamamladık.
* **Gelişmiş OOP Tasarımı:** Kodun çekirdeğini bozmadan yeni fiziksel özellikleri enjekte edebileceğimiz, esnek ve genişletilebilir bir sınıf yapısına geçtik.

## 🧪 Analiz Senaryoları

Bu sürümle birlikte şu iki kritik vakayı çözüyoruz:

1.  **Senaryo A:** ABCD-BE betonarme çerçevesi ve FC çelik kafes elemanından oluşan sistemde, E mesnetinde meydana gelen **2 mm'lik çökmenin** yapıda oluşturduğu ek moment ve gerilmeleri analiz ediyoruz.
2.  **Senaryo B:** ABC kirişi ve çelik kafes elemanlar (BD, BE) üzerindeki **+50°C'lik** termal gradyan etkisini çözerek, ısıl genleşmenin yapıyı nasıl "büktüğünü" görüyoruz.

## 🛠️ Teknik Detaylar

* **Motor:** Python (NumPy & SciPy)
* **Beton Özellikleri:** $E = 30000$ MPa, $\alpha = 8 \times 10^{-6} / ^\circ\text{C}$
* **Çelik Özellikleri:** $E = 200$ GPa, $\alpha = 1.2 \times 10^{-5} / ^\circ\text{C}$
* **Doğrulama:** Tüm sonuçlar el hesapları ve ticari yazılımlar ile çapraz kontrolden geçirilmiştir.

## 📁 Proje Yapısı
* `src/`: Analiz motoru (Solver) ve yapısal modeller.
* `tests/`: Sistemin doğruluğunu kanıtlayan birim ve entegrasyon testleri.
* `data/`: Analiz edilecek yapıların tanımları.

---
**Hazırlayan:** Hasancan Doğan  
**Medeniyet Mühendisi Adayı | METU CE**
