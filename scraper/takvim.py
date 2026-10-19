"""Abone olunabilir takvim dosyaları (.ics) üretir.

- data/takvim/<program>-<grup>.ics : teorik dersler + grubun pratik günleri + sınavlar
- data/takvim/k/<numara özeti>.ics  : yukarıdakine ek olarak bölüm listesindeki kesin pratik saatleri
"""
import hashlib, os, re

PRATIK_YER = {'Anatomi': 'Temel Bilimler B Blok, 2. kat', 'Biyofizik': 'Temel Bilimler B Blok, 2. kat',
              'Biyokimya': 'Temel Bilimler B Blok, 1. kat', 'Biyoistatistik': 'Dahiliye binası, Hakkı Ogan amfisi'}


def _kac(s):
    return s.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def _olay(uid, tarih, bas, bit, baslik, yer='', aciklama='', damga=''):
    d = tarih.replace('-', '')
    satirlar = ['BEGIN:VEVENT', f'UID:{uid}@ctf-pratik', 'DTSTAMP:20260901T000000Z',
                f'DTSTART;TZID=Europe/Istanbul:{d}T{bas.replace(":", "")}00',
                f'DTEND;TZID=Europe/Istanbul:{d}T{bit.replace(":", "")}00', f'SUMMARY:{_kac(baslik)}']
    if yer:
        satirlar.append(f'LOCATION:{_kac(yer)}')
    if aciklama:
        satirlar.append(f'DESCRIPTION:{_kac(aciklama)}')
    satirlar.append('END:VEVENT')
    return satirlar


def _takvim(ad, olaylar):
    bas = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//ctf-pratik//TR', 'CALSCALE:GREGORIAN', f'X-WR-CALNAME:{_kac(ad)}',
           'X-WR-TIMEZONE:Europe/Istanbul', 'REFRESH-INTERVAL;VALUE=DURATION:PT1H', 'X-PUBLISHED-TTL:PT1H',
           'BEGIN:VTIMEZONE', 'TZID:Europe/Istanbul', 'BEGIN:STANDARD', 'DTSTART:19700101T000000',
           'TZOFFSETFROM:+0300', 'TZOFFSETTO:+0300', 'TZNAME:+03', 'END:STANDARD', 'END:VTIMEZONE']
    return '\r\n'.join(bas + olaylar + ['END:VCALENDAR']) + '\r\n'


def _uid(*p):
    return hashlib.sha1('|'.join(p).encode()).hexdigest()[:16]


def _ekle(s, n):
    t = int(s[:2]) * 60 + int(s[3:]) + n
    return f'{t // 60:02d}:{t % 60:02d}'


def kural_saati(veri, ders, kurul, grup, tarih):
    """Sitedeki siraKimde/yapilanlar ile aynı mantık. (bas, bit, not) ya da None."""
    k = {**(veri.get('kural_varsayilan') or {}), **((veri.get('kurallar') or {}).get(ders) or {})}
    if tarih in k.get('iptal', []):
        return 'iptal'
    deger = next((g['degerler'].get(ders) for kk in (veri.get('pratik') or {}).get('kurullar', []) if kk['kurul'] == kurul
                  for g in kk['gunler'] if g['tarih'] == tarih), '') or ''
    if k.get('sira') == 'ab_donusumlu' and re.fullmatch(r'\d', deger):
        yap = []
        for kk in (veri.get('pratik') or {}).get('kurullar', []):
            if kk['kurul'] != kurul:
                continue
            for g in kk['gunler']:
                v = (g['degerler'].get(ders) or '').lower()
                if not v.startswith(grup[0]) or g['tarih'] in k.get('iptal', []) or (g.get('olay') and ders in g['olay']['dersler']):
                    continue
                yap.append(g['tarih'])
        if tarih not in yap:
            return None
        i = sorted(yap).index(tarih)
        if k.get('ilk') == 'birlikte':
            once = 'birlikte' if i == 0 else ('b' if i % 2 else 'a')
        else:
            ilk = k.get('ilk', 'a'); once = ilk if i % 2 == 0 else ('b' if ilk == 'a' else 'a')
        bas = k['saatler'][0] if once == 'birlikte' or grup[1:] == once else k['saatler'][1]
        return bas, _ekle(bas, k.get('sure', 60)), ('İki grup birlikte girer' if once == 'birlikte' else f'Bu sefer önce {grup[0]}{once} girer') + ' (tahmini)'
    if k.get('sira') == 'liste':
        return None
    if k.get('bas') or k.get('saatler'):
        bas = k.get('bas') or k['saatler'][0]
        return bas, _ekle(bas, k.get('sure', 60)), 'Tahmini saat'
    return None


def _kucuk(s):
    return (s or '').replace('I', 'ı').replace('İ', 'i').lower().strip()


def _duzeltmeler(veri, program, tur):
    return [d for d in veri.get('duzeltmeler') or [] if d.get('tur') == tur and d['program'] in ('hepsi', program)]


def teorik_dersler(veri, program):
    """{tarih: [ders]} temsilci düzeltmeleri uygulanmış (sitedeki dersler() ile aynı mantık)."""
    gunler = {t: [dict(x) for x in l if x['tur'] not in ('pratik', 'olay')]
              for t, l in (veri.get('programlar') or {}).get(program, {}).get('gunler', {}).items()}
    for d in _duzeltmeler(veri, program, 'teorik'):
        liste = gunler.setdefault(d['tarih'], [])
        x = next((y for y in liste if _kucuk(y['ders']) == _kucuk(d['ders'])), None)
        if not x and d['durum'] == 'ek' and d.get('bas'):
            x = {'ders': d['ders'], 'tur': 'teorik'}; liste.append(x)
        if not x:
            continue
        if d.get('bas'):
            x['bas'], x['bit'] = d['bas'], d.get('bit') or ''
        for k in ('yer', 'abd', 'hoca', 'not'):
            if d.get(k):
                x[k] = d[k]
        if d['durum'] == 'iptal':
            x['iptal'] = True
    return gunler


def grup_olaylari(veri, program, grup, damga, kesinler=None, bolum=None):
    """kesinler: {(tarih, ders): oturum} bölüm listesinden; varsa saat ondan alınır."""
    out = []
    gunler = (veri.get('programlar') or {}).get(program, {}).get('gunler', {})
    for tarih, liste in teorik_dersler(veri, program).items():
        for x in liste:
            bit = x.get('bit') or _ekle(x['bas'], 40)
            aciklama = ', '.join(filter(None, [x.get('abd'), x.get('hoca')]))
            if x.get('not'):
                aciklama += ('. ' if aciklama else '') + x['not']
            if not x.get('bit'):
                aciklama += ('. ' if aciklama else '') + 'Bitiş saati belli değil'
            out += _olay(_uid(program, tarih, x['bas'], x['ders']), tarih, x['bas'], bit, ('İptal: ' if x.get('iptal') else '') + x['ders'],
                         x.get('yer', ''), aciklama, damga)
    pdz = _duzeltmeler(veri, program, 'pratik')
    for k in (veri.get('pratik') or {}).get('kurullar', []):
        for g in k['gunler']:
            for ders, deger in g['degerler'].items():
                v = (deger or '').replace(' ', '').lower()
                if v in ('', '-') or not (v == grup or v == grup[0]):
                    continue
                kesin = (kesinler or {}).get((g['tarih'], ders))
                dg = (kesinler or {}).get(('grup', ders)) or grup
                slot = next((x for x in gunler.get(g['tarih'], []) if x['tur'] == 'pratik'), None)
                kural = kural_saati(veri, ders, k['kurul'], dg, g['tarih'])
                if kural == 'iptal':
                    continue
                # bölüm listesi bu grubu başka güne koyduysa tablo satırını atla; aynı günse alt grup saat aralığını kullan
                lo = [o for o in (bolum or {}).get('oturumlar', []) if o['ders'] == ders and o['kurul'] == k['kurul'] and o['grup'] == dg]
                if lo and not kesin:
                    bugunku = [o for o in lo if o['tarih'] == g['tarih'] and o.get('bas')]
                    if not bugunku:
                        continue
                    kural = (min(o['bas'] for o in bugunku), max(o['bit'] for o in bugunku), 'Alt grubuna göre yarım saat; kesin saatin için siteye bak')
                if kesin and kesin.get('bas'):
                    bas, bit, aciklama = kesin['bas'], kesin['bit'], f'Alt grup {kesin["grup"]}-{kesin["alt"]}'
                elif kural:
                    bas, bit, aciklama = kural[0], kural[1], f'Grup {dg}. {kural[2]}'
                else:
                    bas, bit = (slot['bas'], slot['bit']) if slot else ('13:30', '16:15')
                    aciklama = f'Grup {dg}. ' + (((veri.get('kurallar') or {}).get(ders) or {}).get('not') or 'Saat belli değil')
                yer = ((veri.get('kurallar') or {}).get(ders) or {}).get('yer') or PRATIK_YER.get(ders, '')
                dz = [d for d in pdz if d['tarih'] == g['tarih'] and _kucuk(d['ders']) == _kucuk(ders) and d['grup'] in ('hepsi', dg, dg[0])]
                if any(d['durum'] == 'iptal' for d in dz):
                    continue
                for d in dz:
                    if d.get('bas'):
                        bas, bit = d['bas'], d.get('bit') or _ekle(d['bas'], 60)
                        aciklama = f'Grup {dg}. Temsilci duyurusu' + ('' if d.get('bit') else '; bitiş saati belli değil')
                    yer = d.get('yer') or yer
                    if d.get('not'):
                        aciklama += f". {d['not']}"
                out += _olay(_uid(program, grup, g['tarih'], ders), g['tarih'], bas, bit, f'{ders} pratiği', yer, aciklama, damga)
    out += sinav_olaylari(veri, program, damga)
    return out


TUR_AD = {'ara': 'ara sınavı', 'final': 'final sınavı', 'butunleme': 'bütünleme sınavı', 'sinav': 'sınavı'}


def _tumgun(uid, tarih, baslik, aciklama, damga):
    d = tarih.replace('-', '')
    import datetime as _dt
    ertesi = (_dt.date.fromisoformat(tarih) + _dt.timedelta(days=1)).strftime('%Y%m%d')
    return ['BEGIN:VEVENT', f'UID:{uid}@ctf-pratik', 'DTSTAMP:20260901T000000Z', f'DTSTART;VALUE=DATE:{d}', f'DTEND;VALUE=DATE:{ertesi}',
            f'SUMMARY:{_kac(baslik)}', f'DESCRIPTION:{_kac(aciklama)}', 'END:VEVENT']


def sinav_olaylari(veri, program, damga):
    """Kurul sınavları, törenler ve tatiller (Drive programı) + ortak ders sınavları. Saat bilinmiyorsa tüm gün."""
    out = []
    for o in ((veri.get('programlar') or {}).get(program) or {}).get('onemli', []):
        if o['tur'] in ('tatil', 'toren'):
            ad = 'Beyaz Önlük Töreni' if o['tur'] == 'toren' else (re.search(r'\(([^)]+)\)', o['metin']) or [None, o['metin']])[1]
            out += _tumgun(_uid('onemli', o['tarih'], o['tur']), o['tarih'], ad, 'Ders programından', damga)
            continue
        baslik = f"{o['kurul'] + ' kurulu ' if o.get('kurul') else ''}{TUR_AD.get(o['tur'], 'sınavı')}"
        if o.get('saat'):
            out += _olay(_uid('sinav', o['tarih'], o['tur']), o['tarih'], o['saat'], _ekle(o['saat'], 120), baslik, '',
                         'Programdaki saat; son hafta kesinleşir. Bitiş saati tahmini.', damga)
        else:
            out += _tumgun(_uid('sinav', o['tarih'], o['tur']), o['tarih'], baslik, 'Saat henüz duyurulmadı', damga)
    for o in veri.get('ortak_sinavlar') or []:
        baslik = f"{o['ders']} {TUR_AD.get(o['tur'], 'sınavı')}"
        out += _olay(_uid('ortak', o['tarih'], o['ders'], o['tur']), o['tarih'], o['saat'], _ekle(o['saat'], 60), baslik, '',
                     'Ortak Dersler Bölümü sınav tarihleri. Bitiş saati tahmini.', damga)
    return out


def yaz(veri, liste, data_klasoru, damga):
    hedef = os.path.join(data_klasoru, 'takvim')
    os.makedirs(os.path.join(hedef, 'k'), exist_ok=True)
    adlar = {'TR': 'Türkçe Tıp', 'MT': 'Türkçe Tıp MT', 'EN': 'İngilizce Tıp'}
    gruplar = [g['grup'] for g in veri.get('gruplar', [])]
    for program in (veri.get('programlar') or {'TR': {}, 'EN': {}}).keys() | {'TR', 'EN'}:
        for grup in gruplar:
            if (program == 'EN') != grup.startswith('1'):
                continue
            ics = _takvim(f'CTF 1. sınıf · {adlar.get(program, program)} {grup}', grup_olaylari(veri, program, grup, damga, bolum=liste))
            open(os.path.join(hedef, f'{program}-{grup}.ics'), 'w', encoding='utf-8').write(ics)
    # kişisel: listedeki numaralar için kesin saatli takvim (programı TR/EN numaradan bilinmez; ikisini de üret)
    for h, idx in liste.get('numara', {}).items():
        oturumlar = [liste['oturumlar'][i] for i in idx]
        grup = oturumlar[0]['grup']
        program = 'EN' if grup.startswith('1') else 'TR'
        kesinler = {(o['tarih'], o['ders']): o for o in oturumlar}
        olaylar = grup_olaylari(veri, program, grup, damga, kesinler)
        # tabloda olmayan ama listede olan oturumlar
        for o in oturumlar:
            if not any(f'{o["ders"]} pratiği' in s for s in olaylar) and o.get('bas'):
                olaylar += _olay(_uid(h, o['tarih'], o['ders']), o['tarih'], o['bas'], o['bit'], f'{o["ders"]} pratiği', PRATIK_YER.get(o['ders'], ''), f'Alt grup {o["grup"]}-{o["alt"]}', damga)
        open(os.path.join(hedef, 'k', f'{h}.ics'), 'w', encoding='utf-8').write(_takvim(f'CTF 1. sınıf · pratiklerim ({grup})', olaylar))
