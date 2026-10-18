"""Abone olunabilir takvim dosyaları (.ics) üretir.

- data/takvim/<program>-<grup>.ics : teorik dersler + grubun pratik günleri + sınavlar
- data/takvim/k/<numara özeti>.ics  : yukarıdakine ek olarak bölüm listesindeki kesin pratik saatleri
"""
import hashlib, os

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


def grup_olaylari(veri, program, grup, damga, kesinler=None):
    """kesinler: {(tarih, ders): oturum} bölüm listesinden; varsa saat ondan alınır."""
    out = []
    gunler = (veri.get('programlar') or {}).get(program, {}).get('gunler', {})
    for tarih, liste in gunler.items():
        for x in liste:
            if x['tur'] == 'pratik':
                continue
            out += _olay(_uid(program, tarih, x['bas'], x['ders']), tarih, x['bas'], x['bit'], x['ders'],
                         x.get('yer', ''), ', '.join(filter(None, [x.get('abd'), x.get('hoca')])), damga)
    for k in (veri.get('pratik') or {}).get('kurullar', []):
        for g in k['gunler']:
            for ders, deger in g['degerler'].items():
                v = (deger or '').replace(' ', '').lower()
                if v in ('', '-') or not (v == grup or v == grup[0]):
                    continue
                kesin = (kesinler or {}).get((g['tarih'], ders))
                slot = next((x for x in gunler.get(g['tarih'], []) if x['tur'] == 'pratik'), None)
                bas, bit = (kesin['bas'], kesin['bit']) if kesin and kesin.get('bas') else ((slot['bas'], slot['bit']) if slot else ('13:30', '16:15'))
                aciklama = f'Grup {grup}' + (f', alt grup {kesin["grup"]}-{kesin["alt"]}' if kesin else ', kesin saat duyurulur')
                out += _olay(_uid(program, grup, g['tarih'], ders), g['tarih'], bas, bit, f'{ders} pratiği', PRATIK_YER.get(ders, ''), aciklama, damga)
            if g.get('olay') and ('SINAV' in g['olay']['ad'] or 'ARASINAV' in g['olay']['ad']):
                out += _olay(_uid('olay', g['tarih'], g['olay']['ad']), g['tarih'], '09:00', '12:00', g['olay']['ad'].title(), '', 'Saati programdan kontrol et', damga)
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
            ics = _takvim(f'CTF 1. sınıf · {adlar.get(program, program)} {grup}', grup_olaylari(veri, program, grup, damga))
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
