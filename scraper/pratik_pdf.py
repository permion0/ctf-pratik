"""Okulun 'preklinik dönem pratikler tablosu' PDF'ini okur (yalnızca 1. sınıf sayfaları).

Çıktı:
  gruplar: numara aralığından grup (1a … 4b)
  kurullar: her kurul için gün gün hangi derste hangi grup pratiğe girer
Değer anlamı: "1" = 1a ve 1b birlikte, "2a" = yalnızca 2a, "-" = pratik yok.
"""
import re
import pdfplumber

AYLAR = {'ocak': 1, 'şubat': 2, 'mart': 3, 'nisan': 4, 'mayıs': 5, 'haziran': 6, 'temmuz': 7,
         'ağustos': 8, 'eylül': 9, 'ekim': 10, 'kasım': 11, 'aralık': 12}
TARIH = re.compile(r'^(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})')
GRUP = re.compile(r'^(\d)\s?([abc])?$')
ARALIK = re.compile(r'^(\d[ab])\s*[-–]\s*(\d{10})(?:-(\d{10}))?\s*(.*?)\s*(İngilizce|Türkçe)\s+Tıp', re.I)


def tr_lower(s):
    return s.replace('I', 'ı').replace('İ', 'i').lower()


def tarih(metin):
    m = TARIH.match(metin.strip())
    if not m:
        return None
    ay = AYLAR.get(tr_lower(m.group(2)))
    if not ay:
        return None
    yil = int(m.group(3))
    if ay == 1 and yil == 2026:  # PDF'te "1 Ocak 2026" yazım hatası var; akademik yılın ocağı 2027
        yil = 2027
    return f'{yil:04d}-{ay:02d}-{int(m.group(1)):02d}'


def gruplar(sayfa):
    out = []
    for satir in (sayfa.extract_text() or '').splitlines():
        m = ARALIK.match(satir.strip())
        if m:
            out.append({'grup': m.group(1).lower(), 'bas': m.group(2), 'bit': m.group(3),
                        'program': 'EN' if m.group(5).lower().startswith('i') else 'TR'})
    return out


def oku(yol, son_sayfa=None):
    """1. sınıf sayfalarını okur; '2. SINIF' başlığını görünce durur."""
    sonuc = {'gruplar': [], 'kurullar': []}
    with pdfplumber.open(yol) as pdf:
        kurul = None
        basliklar = None  # [(ders, x_merkez)]
        for no, sayfa in enumerate(pdf.pages):
            metin = sayfa.extract_text() or ''
            if no > 0 and re.search(r'^\s*2\.\s*SINIF', metin, re.M):
                break
            if son_sayfa and no >= son_sayfa:
                break
            if not sonuc['gruplar']:
                sonuc['gruplar'] = gruplar(sayfa)
            kelimeler = sayfa.extract_words()
            for tablo in sayfa.find_tables():
                for satir in tablo.rows:
                    hucreler = [c for c in satir.cells if c]
                    if not hucreler:
                        continue
                    x0 = min(c[0] for c in hucreler); x1 = max(c[2] for c in hucreler)
                    top = min(c[1] for c in hucreler); bot = max(c[3] for c in hucreler)
                    icerik = [w for w in kelimeler if top - 1 <= (w['top'] + w['bottom']) / 2 <= bot + 1 and x0 - 1 <= w['x0'] <= x1 + 1]
                    yazi = ' '.join(w['text'] for w in icerik)
                    km = re.fullmatch(r'\s*(100\d)\s*', yazi)
                    if km:  # kurul başlığı
                        kurul = {'kurul': km.group(1), 'dersler': [], 'gunler': []}
                        sonuc['kurullar'].append(kurul)
                        basliklar = None
                        continue
                    t = tarih(yazi)
                    if not t:
                        # ders başlık satırı: harfli kelimeler, tarih yok
                        if kurul is not None and icerik and all(re.search(r'[A-Za-zÇĞİÖŞÜçğıöşü]', w['text']) for w in icerik):
                            basliklar = []
                            for w in icerik:
                                if basliklar and w['x0'] - basliklar[-1][2] < 6:  # "Tıbbi Biyoloji" gibi iki kelimeli başlık
                                    ad, a, b = basliklar[-1]; basliklar[-1] = (ad + ' ' + w['text'], a, w['x1'])
                                else:
                                    basliklar.append((w['text'], w['x0'], w['x1']))
                            kurul['dersler'] = [b[0] for b in basliklar]
                        continue
                    if kurul is None or not basliklar:
                        continue
                    # tarih kelimelerini at (gün adı dahil ilk 4 kelime civarı): tarih sütununun sağındakiler
                    tarih_sag = max(w['x1'] for w in icerik[:4]) if icerik else 0
                    degerler, olay, notlar = {}, [], {}
                    for w in icerik:
                        if w['x0'] <= tarih_sag + 2:
                            continue
                        merkez = (w['x0'] + w['x1']) / 2
                        en_yakin = min(basliklar, key=lambda b: abs((b[1] + b[2]) / 2 - merkez))
                        txt = w['text'].strip()
                        if txt in '-–':
                            degerler[en_yakin[0]] = '-'
                        elif GRUP.match(txt) or (re.fullmatch(r'\d', txt)):
                            degerler[en_yakin[0]] = degerler.get(en_yakin[0], '') + txt
                        elif re.fullmatch(r'[abc]', txt) and en_yakin[0] in degerler:
                            degerler[en_yakin[0]] += txt  # "3 a" gibi ayrık yazım
                        elif re.fullmatch(r'\(?sın|av\)|\(sınav\)', txt):
                            notlar[en_yakin[0]] = 'sınav'  # o günkü pratik sınavı
                        else:
                            olay.append((txt, w['x0'], w['x1']))
                    for k in list(degerler):
                        degerler[k] = degerler[k].replace(' ', '').lower()
                    gun = {'tarih': t, 'degerler': degerler}
                    if notlar:
                        gun['notlar'] = notlar
                    if olay:
                        ad = re.sub(r'\s+', ' ', ' '.join(o[0] for o in olay))
                        ad = re.sub(r'ARASIN ?A ?V(I)?', 'ARASINAVI', ad)
                        # olay, o satırda değeri olmayan derslerin hepsini kapsar (birleşik hücre)
                        gun['olay'] = {'ad': ad, 'dersler': [bb[0] for bb in basliklar if bb[0] not in degerler]}
                    # aynı tarih iki kez gelirse (sayfa geçişi) birleştir
                    if kurul['gunler'] and kurul['gunler'][-1]['tarih'] == t:
                        kurul['gunler'][-1]['degerler'].update(degerler)
                        if 'olay' in gun:
                            kurul['gunler'][-1]['olay'] = gun['olay']
                    else:
                        kurul['gunler'].append(gun)
    return sonuc


if __name__ == '__main__':
    import json, sys
    print(json.dumps(oku(sys.argv[1]), ensure_ascii=False, indent=1))
