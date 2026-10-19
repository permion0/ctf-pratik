---
name: duzeltme
description: Temsilcinin WhatsApp duyurusunu (metin ya da ekran görüntüsü) siteye düzeltme olarak işler. Ders iptali, telafi, saat/derslik değişikliği, pratik sırası, sınav saati gibi duyurular gelince kullan.
---

# Temsilci duyurusunu siteye işleme

Kullanıcı (Furkan) temsilcinin mesajını yapıştırır ya da ekran görüntüsünü atar. Görev: duyuruyu `kaynak/duzeltmeler.json`'a doğru bir kayıt olarak eklemek ve yayına almak. Bu site bütün 1. sınıfın kullandığı program; **yanlış bilgi yayınlamaktansa sormak her zaman daha iyidir.**

## 1. Duyuruyu oku, programla karşılaştır

- Tarih: mesajdaki gün adı + tarih birbirini tutmalı (akademik yıl Eylül 2026 – Haziran 2027). Tutmuyorsa sor.
- Program: varsayılan `TR` (Türkçe Tıp temsilcisi). Mesaj İngilizce Tıp ya da MT için olabilir gibi duruyorsa sor.
- O günün dersine bak, ders adını programdaki haliyle birebir yaz:

```bash
python3 scraper/duzeltme.py --gun 2026-10-21 TR          # birden çok gün: 2026-10-15,2026-10-21
```

Mesajda adı geçen ders, hoca ya da saat programla uyuşmuyorsa ya da hangi derse ait olduğu belli değilse **tek, kısa bir soru sor**, tahmin etme.

## 2. Kaydı yaz

`kaynak/duzeltmeler.json` bir liste. Her kayıt:

| alan | değer |
|---|---|
| `tarih` | `yyyy-aa-gg` |
| `program` | `TR` / `EN` / `MT` / `hepsi` |
| `ders` | teorik derste programdaki ders adı (birebir); pratikte ders adı (`Anatomi`, `Biyokimya`…); sınavda adında "sınav" geçen bir ad |
| `durum` | `iptal` / `değişti` / `ek` |
| `grup` | pratikte `4a`, `4`, `hepsi`; teorikte `hepsi` |
| `bas`, `bit` | `ss:dd`. Duyuruda yoksa boş bırak; **bitiş saati uydurma** |
| `yer` | derslik, `Zoom` vb. Yoksa boş |
| `abd`, `hoca` | eklenen derste (telafi) programdaki gibi |
| `not` | sitede görünen kısa açıklama: `Telafi dersi`, `Hoca gelemiyor` gibi. Duyurudaki ifadeyi koru, yorum katma |
| `duyuru` | nereden geldiği: `Temsilci, WhatsApp 19 Ekim 10:40` (sitede görünmez) |

Durumlar:
- **Teorik ders iptal:** `iptal`, ders adı programdaki gibi, tarih dersin olduğu gün.
- **Aynı gün saat/derslik değişti:** `değişti` + yeni `bas`/`bit`/`yer`.
- **Başka güne taşındı:** eski güne `iptal`, yeni güne `ek` (abd, hoca, yer ile).
- **Telafi / ek ders:** `ek`, `bas` zorunlu.
- **Pratik saati ya da sırası:** `değişti`, `ders` pratik dersinin adı, `grup` hangi gruba diyorsa.
- **Sınav saati/yeri:** `ders` örn. `1001 kurulu ara sınavı`, `değişti`, `bas`, `yer`.
- Temsilci daha önceki bir duyuruyu değiştirdiyse yeni kayıt ekleme, **eski kaydı güncelle**.

Kesinlikle yazılmaz: öğrenci adı, telefon numarası, öğrenci numarası (depo herkese açık). Hoca adları programda zaten var, yazılabilir.

## 3. Denetle

```bash
python3 scraper/duzeltme.py
```

Çıktı `Sorun yok.` ile bitmeli. Her kaydın tek satırlık özetini kullanıcıya göster (tarih, gün, ne değişti); kullanıcı açıkça onay vermeden önce emin olmadığın bir şey varsa sor.

## 4. Yayına al

```bash
git add kaynak/duzeltmeler.json
git commit -m "Düzeltme: <kısa açıklama>"
git push
```

- `main` dalındaysan doğrudan `git pull --rebase && git push`.
- Başka bir daldaysan (örn. telefondan açılan bulut oturumu) sadece o dalı it: `duzeltme-birlestir` akışı, dal **yalnızca** `kaynak/duzeltmeler.json`'ı değiştiriyorsa denetleyip `main`'e alır ve siteyi günceller. Başka dosya değiştiyse birleştirmez.
- Site 2-3 dakika içinde güncellenir: https://cerrahpasa-turkce-tip.vercel.app (Değişenler sekmesinde "Temsilci" kaynaklı satır olarak da görünür).

Kullanıcıya en sonda tek iki satır yaz: ne eklendi, ne zaman sitede olur.
