# CTF Pratik Takip · durum

Site: https://permion0.github.io/ctf-pratik/  ·  Depo: github.com/permion0/ctf-pratik (açık)
Yerel: ~/projeler/pratik-takip (venv: .venv, `python scraper/guncelle.py`)

## Mimari
- **Okul portalı (ctfogrenci.iuc.edu.tr)** JS ile yükleniyor; içerik `service-cms.iuc.edu.tr/api/webclient/f_getContentGroupItems?siteKey=985BBFA20CC746A98F11C92D4E591A51&Value=tip-egitimi` JSON'unda. "Pratik Dönüşümü" linki → preklinik pratikler PDF'i (adı her güncellemede değişir). cdn.iuc.edu.tr tarayıcı User-Agent + Referer ister.
- **Ortak dersler**: siteKey E92E3756DEE540F79CD7D49E437D3AE0, "Sınav Tarihleri" → herkese açık Drive görseli (değişince günlüğe düşer, OCR yok).
- **Drive ders programı** (1LahYrgk…, okul alanına kapalı, sadece görüntüleme). Okul hesabında Apps Script "CTF Pratik Takip köprü" (n.gorgulu@ogr.iuc.edu.tr, script.google.com/u/4) 15 dk'da bir 1-TR / 1- EN / 1- MT sekmelerini + Düzeltmeler tablosunu okur, değiştiyse GitHub contents API ile `kaynak/program.json`'a yazar. Anahtar: Script Properties `GITHUB_TOKEN` (fine-grained, sadece bu depo, Contents RW, süresiz). Web uygulaması "Herkes" seçeneği okul tarafından kapalı olduğu için itme modeli seçildi.
- **Düzeltmeler tablosu** (okul Drive: "CTF Pratik Takip · Düzeltmeler", 19VG8G7RyYrMBmOmHbEsebA1m8s8yyNzdKT3E9XO7hdY): Tarih | Program | Ders | Grup | Başlangıç | Bitiş | Yer | Durum | Not. Temsilciye editör yetkisi verilecek.
- **Bölüm listeleri** (isimli Excel): `python scraper/liste_ice_aktar.py <xlsx> <kurul> <Ders>` → `kaynak/listeler/<kurul>_<Ders>.json` (numaralar tuzlu SHA-256, isim yok). Excel `manual/ham/` (git dışı). Şimdilik: 1001 Biyofizik.
- **GitHub Actions** `guncelle.yml`: */15 cron + push → `scraper/guncelle.py` → değişiklik varsa commit → Pages yayını (değişiklik varsa ya da saatte bir).
- Çıktılar `site/data/`: veri.json, liste.json, degisiklikler.json, durum.json, takvim/*.ics (grup) ve takvim/k/<özet>.ics (kişisel), kontrol.json (git dışı, yayında).
- Yerelde çalıştırınca `site/data` ve `kaynak` değişir: commit etmeden önce `git checkout origin/main -- site/data kaynak` (Actions zaten üretiyor).

## Kurallar
- Sitede/depoda öğrenci adı yok, açık numara yok (yalnızca okul PDF'indeki grup aralığı sınırları).
- Kullanıcı (Furkan) anahtar/şifre girişini kendisi yapar.

## Açık sorular / sıradakiler
- "1- MT" sekmesi kimin? (şimdilik onboarding'de EKU/MT seçimi)
- Biyokimya listesi Excel'i (elde sadece kapı fotoğrafı)
- Değişiklik bildirimi: Telegram kanalı önerildi, cevap bekleniyor
- Temsilciye Düzeltmeler tablosu yetkisi
