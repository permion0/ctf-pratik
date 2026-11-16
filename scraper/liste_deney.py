"""Bölüm listesi biçimi 2 (Biyofizik 1002): her sayfa bir grup, içinde "1 A GRUBU" … "1D GRUBU" alt grupları;
her alt grubun altında numaralar ve sağda "DENEY | TARİH | SAAT" tablosu (1.DENEY H1 2026-11-17 13.30-14.30).

Alt grup harfi sayfadaki sıraya göre verilir (A, B, C, D): tabloda aynı etiket iki kez yazılmışsa ("1 B" iki kez) yine doğru çıkar.
"""
import datetime as dt, re
import openpyxl

ETIKET = re.compile(r'^\s*(\d)\s*([A-Za-zÇĞİÖŞÜ])\s*GRUBU', re.I)
SAAT = re.compile(r'(\d{1,2})[.:](\d{2})\s*-\s*(\d{1,2})[.:](\d{2})')


def uygun(yol):
    wb = openpyxl.load_workbook(yol, data_only=True, read_only=True)
    return any(str(c).strip().upper() == 'DENEY' for ws in wb.worksheets for r in ws.iter_rows(values_only=True) for c in r if c)


def _numara(v):
    if v is None:
        return None
    s = str(v).strip()
    if re.fullmatch(r'\d+\.0', s):
        s = s[:-2]
    return s.zfill(10) if re.fullmatch(r'\d{9,10}', s) else None


def _tarih(v):
    if isinstance(v, (dt.datetime, dt.date)):
        return v.strftime('%Y-%m-%d')
    m = re.match(r'(\d{1,2})[./](\d{1,2})[./](\d{4})', str(v or ''))
    return f'{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}' if m else None


def oku(yol, ders, kurul):
    wb = openpyxl.load_workbook(yol, data_only=True)
    out, uyari = [], []
    for ws in wb.worksheets:
        bloklar = []  # [{grup, alt, numaralar, deneyler}]
        for row in ws.iter_rows(values_only=True):
            hucre = [c for c in row]
            etiket = next((ETIKET.match(str(c)) for c in hucre[:3] if c and ETIKET.match(str(c))), None)
            if etiket:
                harf = 'ABCD'[len([b for b in bloklar if b['grup'] == etiket.group(1)])] if len(bloklar) < 4 else etiket.group(2).upper()
                if harf != etiket.group(2).upper():
                    uyari.append(f'{ws.title}: "{etiket.group(0).strip()}" sırasına göre {etiket.group(1)}{harf} sayıldı')
                bloklar.append({'grup': etiket.group(1), 'alt': harf, 'numaralar': set(), 'deneyler': []})
                continue
            if not bloklar:
                continue
            b = bloklar[-1]
            n = _numara(hucre[3] if len(hucre) > 3 else None)
            if n:
                b['numaralar'].add(n)
            # deney satırı: "1.DENEY", kod, tarih, saat (sağ taraftaki sütunlarda)
            sag = [c for c in hucre[4:] if c not in (None, '')]
            if sag and re.match(r'^\d\.\s*DENEY', str(sag[0]).upper()):
                t = next((_tarih(c) for c in sag if _tarih(c)), None)
                s = next((SAAT.search(str(c)) for c in sag if SAAT.search(str(c))), None)
                kod = str(sag[1]).strip() if len(sag) > 1 and not _tarih(sag[1]) else ''
                if t and s:
                    b['deneyler'].append({'tarih': t, 'bas': f'{int(s.group(1)):02d}:{s.group(2)}', 'bit': f'{int(s.group(3)):02d}:{s.group(4)}',
                                          'deney': f'{str(sag[0]).strip()[0]}. deney' + (f' ({kod})' if kod else '')})
        for b in bloklar:
            if not b['deneyler'] or not b['numaralar']:
                uyari.append(f'{ws.title} {b["grup"]}{b["alt"]}: deney ya da numara bulunamadı')
            for d in b['deneyler']:
                out.append({'grup': b['grup'], 'alt': b['alt'], **d, 'numaralar': sorted(b['numaralar']), 'ders': ders, 'kurul': kurul})
    return out, uyari
