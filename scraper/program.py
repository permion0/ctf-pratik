"""Drive ders programı sekmelerini (1-TR, 1- EN, 1- MT) gün gün ders listesine çevirir.

Sekme düzeni: her hafta bir tarih satırı ("14 EYLÜL 2026 PAZARTESİ" / "14 SEPTEMBER 2026 MONDAY"),
altında saat satırları. Her gün 4 sütun: ders, anabilim dalı, öğretim üyesi, derslik.
Saat hücresi boşsa önceki saat aralığına aittir (birleşik hücre).
"""
import re

AY = {'ocak': 1, 'şubat': 2, 'mart': 3, 'nisan': 4, 'mayıs': 5, 'haziran': 6, 'temmuz': 7, 'ağustos': 8,
      'eylül': 9, 'ekim': 10, 'kasım': 11, 'aralık': 12,
      'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6, 'july': 7, 'august': 8,
      'september': 9, 'october': 10, 'november': 11, 'december': 12}
TARIH = re.compile(r'^\s*(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})')
SAAT = re.compile(r'(\d{1,2})[.:](\d{2})\s*-\s*(\d{1,2})[.:](\d{2})')
KURUL = re.compile(r'(\d\.\d)\s*(?:DERS KURULU|:)|COURSE\s+(\d\.\d)', re.I)
PROGRAMLAR = {'1-TR': 'TR', '1- EN': 'EN', '1-EN': 'EN', '1- MT': 'MT', '1-MT': 'MT'}


def kucuk(s):
    return s.replace('I', 'ı').replace('İ', 'i').lower()


def tarih(s):
    m = TARIH.match(s or '')
    if not m:
        return None
    ay = AY.get(kucuk(m.group(2)))
    return f'{int(m.group(3)):04d}-{ay:02d}-{int(m.group(1)):02d}' if ay else None


def tur(ders, abd):
    d = kucuk(ders)
    if d.startswith('pratik') or d.startswith('practical'):
        return 'pratik'
    if 'ortak dersler' in kucuk(abd) or 'common' in kucuk(abd):
        return 'ortak'
    if re.search(r'sınav|exam', d):
        return 'sinav'
    return 'teorik'


def sekme(satirlar):
    gunler = {}      # tarih → [ders]
    kurullar = []    # [{kod, ad, bas}]
    gun_sutun = []   # [(tarih, sütun)]
    saat = None
    for satir in satirlar:
        satir = [c.strip() if isinstance(c, str) else '' for c in satir]
        ilk = satir[0] if satir else ''
        km = KURUL.search(ilk)
        if km and not SAAT.search(ilk):
            kurullar.append({'kod': km.group(1) or km.group(2), 'ad': re.sub(r'\s+', ' ', ilk)})
            continue
        tarihler = [(tarih(c), i) for i, c in enumerate(satir) if i > 0 and tarih(c)]
        if tarihler:
            gun_sutun, saat = tarihler, None
            if kurullar and 'bas' not in kurullar[-1]:
                kurullar[-1]['bas'] = tarihler[0][0]
            continue
        if not gun_sutun or kucuk(ilk) in ('saat', 'hour'):
            continue
        sm = SAAT.search(ilk)
        if sm:
            saat = (f'{int(sm.group(1)):02d}:{sm.group(2)}', f'{int(sm.group(3)):02d}:{sm.group(4)}')
        if not saat:
            continue
        for t, s in gun_sutun:
            ders = satir[s] if s < len(satir) else ''
            if not ders:
                continue
            abd, hoca, yer = (satir[s + k] if s + k < len(satir) else '' for k in (1, 2, 3))
            kayit = {'bas': saat[0], 'bit': saat[1], 'ders': re.sub(r'\s+', ' ', ders), 'abd': abd, 'hoca': hoca,
                     'yer': yer, 'tur': tur(ders, abd)}
            liste = gunler.setdefault(t, [])
            # birleşik pratik hücresi aynı saatte birkaç satır tekrar eder: bir kez yaz
            if not any(x['bas'] == kayit['bas'] and x['ders'] == kayit['ders'] for x in liste):
                liste.append(kayit)
    for t in gunler:
        gunler[t].sort(key=lambda x: x['bas'])
    return {'gunler': gunler, 'kurullar': kurullar}


def oku(program):
    out = {}
    for ad, satirlar in program.items():
        kod = PROGRAMLAR.get(ad.strip()) or PROGRAMLAR.get(re.sub(r'\s+', '', ad))
        if kod:
            out[kod] = sekme(satirlar)
    return out


def duzeltmeler(satirlar):
    """Düzeltmeler tablosu: Tarih | Program | Ders | Grup | Başlangıç | Bitiş | Yer | Durum | Not"""
    out = []
    for s in satirlar[1:]:
        s = [str(c).strip() for c in s] + [''] * 9
        t = re.match(r'(\d{1,2})[./](\d{1,2})[./](\d{4})', s[0])
        if not t or not s[2]:
            continue
        out.append({'tarih': f'{t.group(3)}-{int(t.group(2)):02d}-{int(t.group(1)):02d}',
                    'program': (s[1] or 'hepsi').upper().replace('1-', '').replace('HEPSİ', 'hepsi').replace('HEPSI', 'hepsi'),
                    'ders': s[2], 'grup': (s[3] or 'hepsi').lower().replace(' ', ''), 'bas': s[4], 'bit': s[5],
                    'yer': s[6], 'durum': kucuk(s[7]) or 'değişti', 'not': s[8]})
    return out
