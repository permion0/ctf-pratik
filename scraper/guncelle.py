"""Bütün kaynakları okur, site/data/ altına sitenin kullandığı JSON'ları yazar, değişiklikleri günlüğe ekler.

Kaynaklar:
  1. Okulun öğrenci portalı (CMS API): Ders Programları sayfasındaki linkler → pratik dönüşüm PDF'i
  2. Drive ders programı + Düzeltmeler tablosu: okul hesabındaki köprü betiği kaynak/program.json'a yazar
  3. Bölüm listeleri (Excel): kaynak/listeler/<kurul>_<Ders>.xlsx
  4. Ortak dersler sınav tarihleri görseli (Drive, herkese açık)
Çalıştırma: python scraper/guncelle.py  (GitHub Actions 15 dakikada bir çalıştırır)
"""
import hashlib, html, json, os, re, sys, datetime as dt
import requests

sys.path.insert(0, os.path.dirname(__file__))
import pratik_pdf, program as programcoz, takvim

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK = os.path.join(KOK, 'kaynak')
DATA = os.path.join(KOK, 'site', 'data')
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36',
      'Referer': 'https://ctfogrenci.iuc.edu.tr/'}
CMS = 'https://service-cms.iuc.edu.tr/api/webclient/f_getContentGroupItems'
PORTAL_KEY = '985BBFA20CC746A98F11C92D4E591A51'
ORTAK_KEY = 'E92E3756DEE540F79CD7D49E437D3AE0'
TUZ = 'ctf-pratik-2026'  # numaralar sitede açık yazılmaz, bu tuzla özetlenir
SIMDI = dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).replace(microsecond=0)


def oku_json(yol, varsayilan):
    try:
        with open(yol, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return varsayilan


def yaz_json(yol, veri):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, 'w', encoding='utf-8') as f:
        json.dump(veri, f, ensure_ascii=False, separators=(',', ':'))


def ozet(b):
    return hashlib.sha256(b).hexdigest()[:16]


def numara_ozeti(no):
    return hashlib.sha256((TUZ + no).encode()).hexdigest()[:12]


def cms_linkler(site, grup):
    r = requests.get(CMS, params={'siteKey': site, 'Value': grup}, headers=UA, timeout=30)
    r.raise_for_status()
    out = []
    for it in r.json()['Data']:
        h = it.get('HtmlContent') or ''
        for m in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', h, re.S):
            etiket = re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', html.unescape(m.group(2)))).strip()
            out.append({'baslik': it['Header'], 'etiket': etiket, 'url': html.unescape(m.group(1)).strip()})
    return out


def indir(url):
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    return r.content


def kaydet_kaynak(ad, icerik):
    yol = os.path.join(KAYNAK, ad)
    eski = open(yol, 'rb').read() if os.path.exists(yol) else None
    if eski != icerik:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, 'wb') as f:
            f.write(icerik)
        return True
    return False


def main():
    durum = oku_json(os.path.join(DATA, 'durum.json'), {'kaynaklar': {}})
    eski_veri = oku_json(os.path.join(DATA, 'veri.json'), {})
    gunluk = oku_json(os.path.join(DATA, 'degisiklikler.json'), [])
    yeni_kayit = []
    hatalar = []

    def kaynak_durumu(anahtar, ad, url, icerik_ozeti):
        k = durum['kaynaklar'].get(anahtar)
        if not k or k['ozet'] != icerik_ozeti:
            if k:
                yeni_kayit.append({'zaman': SIMDI.isoformat(), 'kaynak': ad, 'ne': f'{ad} güncellendi', 'url': url})
            durum['kaynaklar'][anahtar] = {'ad': ad, 'url': url, 'ozet': icerik_ozeti, 'degisti': SIMDI.isoformat()}
        durum['kaynaklar'][anahtar]['url'] = url

    # 1) Okul portalı → pratik dönüşüm PDF'i
    pratik = eski_veri.get('pratik')
    try:
        linkler = cms_linkler(PORTAL_KEY, 'tip-egitimi')
        pdf_url = next(l['url'] for l in linkler if 'pratik' in l['etiket'].lower() and 'dönüşüm' in l['etiket'].lower()
                       and 'preklinik' in l['url'].lower())
        pdf = indir(pdf_url)
        kaynak_durumu('pratik_pdf', 'Pratik dönüşüm tablosu (okul sitesi)', pdf_url, ozet(pdf))
        if kaydet_kaynak('pratik.pdf', pdf) or not pratik:
            pratik = pratik_pdf.oku(os.path.join(KAYNAK, 'pratik.pdf'))
        program_url = next((l['url'] for l in linkler if l['etiket'] == 'Program' and 'spreadsheets' in l['url']), None)
        if program_url:
            durum['program_url'] = program_url
    except Exception as e:  # kaynak geçici olarak erişilemezse eski veriyle devam
        hatalar.append(f'Okul sitesi: {e}')

    # 2) Ortak dersler sınav tarihleri (görsel)
    try:
        ol = cms_linkler(ORTAK_KEY, 'ortak-zorunlu-dersler')
        gorsel = next(l['url'] for l in ol if 'sınav tarihleri' in l['baslik'].lower() and 'drive.google' in l['url'])
        fid = re.search(r'/d/([^/]+)', gorsel).group(1)
        resim = indir(f'https://drive.google.com/uc?export=download&id={fid}')
        kaynak_durumu('ortak_sinav', 'Ortak dersler sınav tarihleri', gorsel, ozet(resim))
        kaydet_kaynak('ortak_sinav.jpg', resim)
    except Exception as e:
        hatalar.append(f'Ortak dersler: {e}')

    # 3) Drive programı + Düzeltmeler (köprünün yazdığı dosya)
    kopru = oku_json(os.path.join(KAYNAK, 'program.json'), {})
    programlar, duzeltmeler = eski_veri.get('programlar', {}), eski_veri.get('duzeltmeler', [])
    if kopru.get('program'):
        kaynak_durumu('drive_program', 'Ders programı (Drive)', durum.get('program_url', ''),
                      ozet(json.dumps(kopru['program'], sort_keys=True).encode()))
        programlar = programcoz.oku(kopru['program'])
        kaynak_durumu('duzeltmeler', 'Düzeltmeler (temsilci)', '', ozet(json.dumps(kopru.get('duzeltmeler', [])).encode()))
        duzeltmeler = programcoz.duzeltmeler(kopru.get('duzeltmeler', []))
        durum['kopru_alindi'] = kopru.get('alindi')

    # 4) Bölüm listeleri (liste_ice_aktar.py ile isimsizleştirilmiş JSON'lar)
    oturumlar, numara = [], {}
    liste_klasoru = os.path.join(KAYNAK, 'listeler')
    for ad in sorted(os.listdir(liste_klasoru)) if os.path.isdir(liste_klasoru) else []:
        if not ad.endswith('.json'):
            continue
        yol = os.path.join(liste_klasoru, ad)
        l = oku_json(yol, {})
        kaynak_durumu('liste_' + ad, f"{l.get('ders')} pratik listesi ({l.get('kurul')})", '', ozet(open(yol, 'rb').read()))
        for o in l.get('oturumlar', []):
            i = len(oturumlar)
            for h in o.pop('numaralar'):
                numara.setdefault(h, []).append(i)
            oturumlar.append(o)

    veri = {
        'guncelleme': None,  # aşağıda: içerik değiştiyse şimdi, değişmediyse eskisi
        'gruplar': (pratik or {}).get('gruplar', []),
        'pratik': pratik,
        'programlar': programlar,
        'duzeltmeler': duzeltmeler,
        'kaynaklar': list(durum['kaynaklar'].values()),
        'kopru_alindi': durum.get('kopru_alindi'),
        'hatalar': hatalar,
    }

    # içerik farklarını insan diliyle yaz
    yeni_kayit += farklar(eski_veri, veri)
    karsilastir = lambda v: json.dumps({k: x for k, x in v.items() if k not in ('guncelleme', 'kaynaklar')}, sort_keys=True, ensure_ascii=False)
    veri['guncelleme'] = SIMDI.isoformat() if karsilastir(veri) != karsilastir(eski_veri) or not eski_veri.get('guncelleme') else eski_veri['guncelleme']
    yaz_json(os.path.join(DATA, 'kontrol.json'), {'zaman': SIMDI.isoformat(), 'hatalar': hatalar})
    if yeni_kayit:
        gunluk = yeni_kayit + gunluk
    yaz_json(os.path.join(DATA, 'veri.json'), veri)
    yaz_json(os.path.join(DATA, 'liste.json'), {'tuz': TUZ, 'oturumlar': oturumlar, 'numara': numara})
    yaz_json(os.path.join(DATA, 'degisiklikler.json'), gunluk[:300])
    yaz_json(os.path.join(DATA, 'durum.json'), durum)
    takvim.yaz(veri, {'oturumlar': oturumlar, 'numara': numara}, DATA, SIMDI.astimezone(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    print(f'tamam · {len(yeni_kayit)} yeni değişiklik · hatalar: {hatalar or "yok"}')


def farklar(eski, yeni):
    """Pratik tablosundaki gün/ders/grup değişikliklerini tek tek yazar."""
    out = []
    if not eski.get('pratik') or not yeni.get('pratik'):
        return out
    def harita(p):
        h = {}
        for k in p['kurullar']:
            for g in k['gunler']:
                for d, v in g['degerler'].items():
                    h[(g['tarih'], d)] = v
                if g.get('olay'):
                    for d in g['olay']['dersler']:
                        h[(g['tarih'], d)] = g['olay']['ad']
        return h
    a, b = harita(eski['pratik']), harita(yeni['pratik'])
    for anahtar in sorted(set(a) | set(b)):
        if a.get(anahtar) != b.get(anahtar) and anahtar[0] >= SIMDI.date().isoformat():
            out.append({'zaman': SIMDI.isoformat(), 'kaynak': 'Pratik dönüşüm tablosu', 'tarih': anahtar[0], 'ders': anahtar[1],
                        'ne': f'{anahtar[1]}: {a.get(anahtar) or "—"} → {b.get(anahtar) or "—"}'})
    return out


if __name__ == '__main__':
    main()
