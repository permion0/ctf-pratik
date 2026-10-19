"""Temsilci duyurularından gelen düzeltmeler.

İki kaynak birleşir:
  1. Düzeltmeler tablosu (okul Drive'ı, köprü kaynak/program.json'a yazar)
  2. kaynak/duzeltmeler.json (depodan; telefondan Claude ile ya da elle eklenir)

Her düzeltme: tarih (yyyy-aa-gg), program (TR/EN/MT/hepsi), ders, durum (değişti/iptal/ek),
grup (hepsi, 4, 4a...), bas, bit, yer, not; isteğe bağlı abd, hoca, duyuru (nereden geldiği).
tur: pratik / teorik / sinav (verilmezse dersin adından çıkarılır).

Önizleme ve denetim: python scraper/duzeltme.py
"""
import datetime as dt, json, os, re, sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSYA = os.path.join(KOK, 'kaynak', 'duzeltmeler.json')
DURUMLAR = ('değişti', 'iptal', 'ek')
GUN = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
AY = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']


def kucuk(s):
    return (s or '').replace('I', 'ı').replace('İ', 'i').lower().strip()


def pratik_dersleri(veri):
    return {kucuk(d) for k in (veri.get('pratik') or {}).get('kurullar', []) for d in k.get('dersler', [])} | \
           {kucuk(d) for d in (veri.get('kurallar') or {})}


def tur_bul(d, pratikler):
    if d.get('tur') in ('pratik', 'teorik', 'sinav'):
        return d['tur']
    if re.search(r's[ıi]nav', d['ders'], re.I):
        return 'sinav'
    return 'pratik' if kucuk(re.sub(r'\s*pratiği?$', '', d['ders'], flags=re.I)) in pratikler else 'teorik'


def dosya_oku():
    try:
        satirlar = json.load(open(DOSYA, encoding='utf-8'))
    except FileNotFoundError:
        return []
    out = []
    for d in satirlar:
        x = {'tarih': d.get('tarih', ''), 'program': (d.get('program') or 'hepsi').replace('1-', ''), 'ders': d.get('ders', '').strip(),
             'grup': (d.get('grup') or 'hepsi').lower().replace(' ', ''), 'bas': d.get('bas', ''), 'bit': d.get('bit', ''),
             'yer': d.get('yer', ''), 'durum': d.get('durum') or 'değişti', 'not': d.get('not', ''), 'kaynak': 'depo'}
        if x['program'].lower() == 'hepsi':
            x['program'] = 'hepsi'
        for k in ('abd', 'hoca', 'tur', 'duyuru'):
            if d.get(k):
                x[k] = d[k]
        out.append(x)
    return out


def birlestir(tablo, veri):
    """Tablodaki ve depodaki düzeltmeleri birleştirir, türlerini işaretler."""
    pr = pratik_dersleri(veri)
    out = []
    for d in [x for x in tablo if x.get('kaynak') != 'depo'] + dosya_oku():
        d = dict(d)
        d['tur'] = tur_bul(d, pr)
        out.append(d)
    return out


def _ad_uyar(a, b):
    return kucuk(a) == kucuk(b)


def kontrol(veri):
    """Uygulanamayan ya da hatalı düzeltmeler (her biri bir cümle)."""
    sorun = []
    programlar = veri.get('programlar') or {}
    for d in veri.get('duzeltmeler') or []:
        ad = f"{d.get('tarih')} {d.get('ders')}"
        try:
            dt.date.fromisoformat(d.get('tarih', ''))
        except ValueError:
            sorun.append(f'Düzeltme tarihi okunamadı: {ad}')
            continue
        if d['program'] != 'hepsi' and d['program'] not in programlar:
            sorun.append(f"Düzeltmede program tanınmadı ({d['program']}): {ad}")
        if d['durum'] not in DURUMLAR:
            sorun.append(f"Düzeltmede durum tanınmadı ({d['durum']}), değişti / iptal / ek olmalı: {ad}")
        for k in ('bas', 'bit'):
            if d.get(k) and not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', d[k]):
                sorun.append(f'Düzeltmede saat ss:dd biçiminde değil ({d[k]}): {ad}')
        if d.get('tur') == 'teorik':
            if d['durum'] == 'ek' and not d.get('bas'):
                sorun.append(f'Eklenen derste başlangıç saati yok: {ad}')
            if d['durum'] in ('iptal', 'değişti'):
                kodlar = list(programlar) if d['program'] == 'hepsi' else [d['program']]
                if not any(_ad_uyar(x['ders'], d['ders']) for k in kodlar for x in (programlar.get(k) or {}).get('gunler', {}).get(d['tarih'], [])):
                    sorun.append(f"Düzeltmedeki ders o gün programda yok, uygulanamadı: {ad} ({d['program']})")
    return sorun


def ozet(d):
    try:
        t = dt.date.fromisoformat(d['tarih'])
    except ValueError:
        return f"{d['tarih']} (tarih okunamadı) {d['ders']}"
    ne = {'iptal': 'İPTAL', 'ek': 'EKLENDİ', 'değişti': 'DEĞİŞTİ'}.get(d['durum'], d['durum'])
    saat = d['bas'] + ('–' + d['bit'] if d.get('bit') else '') if d.get('bas') else ''
    parca = [saat, d['ders'] + (' pratiği' if d.get('tur') == 'pratik' else ''),
             ', '.join(filter(None, [d.get('abd'), d.get('hoca'), d.get('yer')])), d.get('not')]
    hedef = f"{d['program']}" + (f", grup {d['grup']}" if d['grup'] != 'hepsi' else '')
    return f"{t.day} {AY[t.month]} {GUN[t.weekday()]} [{hedef}] {ne} ({d.get('tur')}): " + ' | '.join(p for p in parca if p)


def gun_dok(veri, tarih, program):
    """Bir günün programdaki dersleri ve pratik tablosu (düzeltme yazmadan önce bakmak için)."""
    t = dt.date.fromisoformat(tarih)
    print(f"{t.day} {AY[t.month]} {GUN[t.weekday()]}, program {program}:")
    for x in ((veri.get('programlar') or {}).get(program) or {}).get('gunler', {}).get(tarih, []):
        print(f"  {x['bas']}-{x['bit']}  [{x['tur']}] {x['ders']}  ({', '.join(filter(None, [x.get('abd'), x.get('hoca'), x.get('yer')]))})")
    for k in (veri.get('pratik') or {}).get('kurullar', []):
        for g in k['gunler']:
            if g['tarih'] == tarih:
                print(f"  pratik tablosu ({k['kurul']}): " + ', '.join(f'{d}={v}' for d, v in g['degerler'].items()) + (f"  olay: {g['olay']['ad']}" if g.get('olay') else ''))
    for o in ((veri.get('programlar') or {}).get(program) or {}).get('onemli', []):
        if o['tarih'] == tarih:
            print(f"  önemli: {o['tur']} {o.get('kurul') or ''} {o.get('saat') or ''} {o['metin'][:80]}")


if __name__ == '__main__':
    veri = json.load(open(os.path.join(KOK, 'site', 'data', 'veri.json'), encoding='utf-8'))
    if len(sys.argv) >= 3 and sys.argv[1] == '--gun':
        for tarih in sys.argv[2].split(','):
            gun_dok(veri, tarih, sys.argv[3] if len(sys.argv) > 3 else 'TR')
        sys.exit(0)
    try:
        dosya_oku()
    except (json.JSONDecodeError, AttributeError) as e:
        print('kaynak/duzeltmeler.json okunamadı:', e)
        sys.exit(1)
    veri['duzeltmeler'] = birlestir(veri.get('duzeltmeler') or [], veri)
    for d in veri['duzeltmeler']:
        print(('[depo]  ' if d.get('kaynak') == 'depo' else '[tablo] ') + ozet(d))
    s = kontrol(veri)
    print('\nSorun yok.' if not s else '\nSORUNLAR:\n- ' + '\n- '.join(s))
    sys.exit(1 if s else 0)
