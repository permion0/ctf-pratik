# CTF 1. sınıf ders programı sitesi

Site: https://cerrahpasa-turkce-tip.vercel.app (her push'ta Vercel yayınlar). Depo herkese açık.

- `scraper/guncelle.py` bütün kaynakları okuyup `site/data/` altına yazar; GitHub Actions (`guncelle.yml`) her push'ta ve 15 dakikada bir çalıştırır. Yerelde çalıştırırsan commit'ten önce `git checkout origin/main -- site/data kaynak` (yalnızca kendi değiştirdiğin kaynak dosyalarını tut).
- Drive programını okul hesabındaki Apps Script köprüsü (`bridge/Kod.gs`) `kaynak/program.json`'a yazar; bu dosyayı elle değiştirme.
- Temsilci duyurusu geldiyse (iptal, telafi, saat/derslik değişikliği): `duzeltme` becerisini kullan, kayıt `kaynak/duzeltmeler.json`'a girer.
- T6 Sirkeci–Kazlıçeşme sefer çizelgesi: `kaynak/tren.json`.

Kurallar: öğrenci adı, telefon ya da açık öğrenci numarası hiçbir dosyaya yazılmaz. Emin olunmayan bilgi yayınlanmaz; sorulur. Arayüz dili Türkçe, kısa ve net.
