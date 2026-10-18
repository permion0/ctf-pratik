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
    ay = AY.get(kucuk(m.group(2))) or AY.get(m.group(2).lower())  # İngilizce adlarda Türkçe küçük harf "aprıl" yapar
    return f'{int(m.group(3)):04d}-{ay:02d}-{int(m.group(1)):02d}' if ay else None


def tur(ders, abd):
    d = kucuk(ders)
    if d.startswith('pratik') or d.startswith('practical'):
        return 'pratik'
    if 'ortak dersler' in kucuk(abd) or 'common' in kucuk(abd):
        return 'ortak'
    if HAZIRLIK.search(ders):
        return 'serbest'   # serbest çalışma / sınava hazırlık
    if SINAV.search(ders) or TOREN.search(ders) or (TATIL.search(ders) and not re.match(r'^Bayram\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+', ders)):
        return 'olay'      # sınav, tören, tatil: Sınavlar sekmesinde ve günün şeridinde gösterilir
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
        # hafta başlığı: saat sütunu boş ya da en az iki gün tarihi (ders hücresindeki "28 OCTOBER 2025 …" başlık sayılmaz)
        if tarihler and (len(tarihler) >= 2 or not SAAT.search(ilk)):
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
            out[kod]['onemli'] = onemli_tarihler(satirlar)
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


# ---------- önemli tarihler (sınavlar, törenler, tatiller) ----------
AY_TUM = dict(AY)
SINAV = re.compile(r'ARA\s*SINAV|F[İI]NAL\s*SINAV|B[İI]T[İI]RME\s*SINAV|B[ÜU]T[ÜU]NLEME|MIDTERM\s*EXAM|FINAL\s*EXAM|KURULU\s*SINAV', re.I)
HAZIRLIK = re.compile(r'SERBEST|SELF STUDY|Haz[ıi]rl[ıi]k|Preparation|^SINAV\s*/|^EXAM\s*/', re.I)
TOREN = re.compile(r'T[ÖO]REN[İI]|CEREMONY', re.I)
TATIL = re.compile(r'BAYRAM[İI]?\b|Bayram[ıi]|TAT[İI]L[İI]|Holiday|HOLIDAY|Republic Day|REPUBLIC DAY|Children\'s Day|E[İI]D AL|Eid al', re.U)
SAAT_TEK = re.compile(r'(?:SAAT|Saat)\s*:?\s*:?\s*(\d{1,2})[.:](\d{2})|(\d{1,2})[.:](\d{2})\s*am', re.I)
TARIH_ICINDE = re.compile(r'(\d{1,2})\s*([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(20\d\d)')


def _metin_tarih(s):
    m = TARIH_ICINDE.search(s)
    if not m:
        return None
    ay = AY_TUM.get(kucuk(m.group(2))) or AY_TUM.get(m.group(2).lower())
    return f'{int(m.group(3)):04d}-{ay:02d}-{int(m.group(1)):02d}' if ay else None


def _tur(s):
    k = kucuk(s) + ' ' + s.lower()
    if re.search(r'bütünleme|butunleme', k): return 'butunleme'
    if re.search(r'ara\s*s[ıi]nav|midterm', k): return 'ara'
    if re.search(r'final|bitirme', k): return 'final'
    return 'sinav'


def onemli_tarihler(satirlar):
    """Program sekmesinden sınav, tören ve tatil günlerini çıkarır. Saat yazıyorsa alır."""
    out = {}
    gun_sutun = []
    for satir in satirlar:
        satir = [c.strip() if isinstance(c, str) else '' for c in satir]
        tarihler = [(tarih(c), i) for i, c in enumerate(satir) if i > 0 and tarih(c)]
        if tarihler and (len(tarihler) >= 2 or not SAAT.search(satir[0] if satir else '')):
            gun_sutun = tarihler
        for j, c in enumerate(satir):
            if not c or j == 0 and not SINAV.search(c):
                continue
            metin = re.sub(r'\s+', ' ', c)
            sinav = SINAV.search(metin) and not HAZIRLIK.search(metin)
            toren = TOREN.search(metin)
            tatil = TATIL.search(metin) and not re.match(r'^Bayram\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s', metin)  # "Bayram Mert …" kişi adı
            if not (sinav or toren or tatil):
                continue
            onceki = [g for g in gun_sutun if g[1] <= j]
            sutun_t = onceki[-1][0] if onceki else None
            t = _metin_tarih(metin)
            # okul bazen yılı yanlış yazıyor ("28 OCTOBER 2025"): sütunun tarihinden çok uzaksa sütunu esas al
            if t and sutun_t:
                import datetime as _dt
                if abs((_dt.date.fromisoformat(t) - _dt.date.fromisoformat(sutun_t)).days) > 200:
                    t = sutun_t
            t = t or sutun_t
            if not t:
                continue
            sm = SAAT_TEK.search(metin)
            saat = None
            if sm:
                h, d = (sm.group(1), sm.group(2)) if sm.group(1) else (sm.group(3), sm.group(4))
                saat = f'{int(h):02d}:{d}'
            km = re.search(r'(1\.\d)\s*(?:DERS\s*)?(?:KURUL|COURSE)|(10\d\d)\s*(?:DERS\s*)?KURUL', metin, re.I)
            if not km:
                km = re.search(r'\b(1\.\d)\b()', metin)
            kurul = (km.group(1) or km.group(2)) if km else None
            if kurul and '.' in kurul:
                kurul = '10' + kurul.replace('1.', '0')  # 1.1 → 1001
            tur = _tur(metin) if sinav else ('toren' if toren else 'tatil')
            anahtar = (t, tur if tur not in ('tatil',) else 'tatil')
            onceki_kayit = out.get(anahtar)
            kayit = {'tarih': t, 'tur': tur, 'kurul': kurul, 'saat': saat, 'metin': metin[:140]}
            if onceki_kayit:  # aynı gün birden çok hücre: bilgisi fazla olanı tut
                for k in ('kurul', 'saat'):
                    if not onceki_kayit.get(k) and kayit.get(k):
                        onceki_kayit[k] = kayit[k]
                continue
            out[anahtar] = kayit
    return sorted(out.values(), key=lambda x: x['tarih'])
