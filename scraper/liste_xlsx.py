"""Bölümlerin pratik listesi Excel'lerini okur (ör. '1001 BİYOFİZİK PRATİK LİSTELERİ').

Biçim: her sayfada "<n> A GRUBU" başlıkları, her alt grupta "Sıra | … | Numara" başlıklı bir blok
ve bloğun yanında tarih ("5 Ekim 2026 Pazartesi") ile saat ("13.30-14.00").
İsim sütunları hiç okunmaz; çıktı yalnızca numara → oturum eşleşmesidir.
"""
import re
import openpyxl

from pratik_pdf import tarih as tarih_coz

GRUP = re.compile(r'^\s*(\d)\s*([AB])\s*GRUBU', re.I)
SAAT = re.compile(r'(\d{1,2})[.:](\d{2})\s*[-–]\s*(\d{1,2})[.:](\d{2})')
NUMARA = re.compile(r'^\d{10}$')


def oku(yol, ders, kurul):
    wb = openpyxl.load_workbook(yol, data_only=True)
    oturumlar = []  # {grup, alt, tarih, bas, bit, numaralar}
    for ws in wb.worksheets:
        grup, blok = None, None
        alt = 0
        for satir in ws.iter_rows():
            hucre = {c.column: c.value for c in satir if c.value is not None}
            if not hucre:
                continue
            for v in hucre.values():
                m = GRUP.match(str(v))
                if m:
                    grup, alt = (m.group(1) + m.group(2)).lower(), 0
            if any(str(v).strip().lower() == 'sıra' for v in hucre.values()):
                alt += 1
                blok = {'grup': grup, 'alt': alt, 'tarih': None, 'bas': None, 'bit': None, 'numaralar': []}
                oturumlar.append(blok)
                continue
            if blok is None:
                continue
            for kol, v in hucre.items():
                s = str(v).strip()
                if NUMARA.match(s):
                    blok['numaralar'].append(s)
                elif kol >= 5:
                    t = tarih_coz(s)
                    if t:
                        blok['tarih'] = t
                    sm = SAAT.search(s)
                    if sm:
                        blok['bas'] = f'{int(sm.group(1)):02d}:{sm.group(2)}'
                        blok['bit'] = f'{int(sm.group(3)):02d}:{sm.group(4)}'
    oturumlar = [o for o in oturumlar if o['numaralar']]
    for o in oturumlar:
        o.update(ders=ders, kurul=kurul)
    return oturumlar


if __name__ == '__main__':
    import json, sys
    r = oku(sys.argv[1], sys.argv[2], sys.argv[3])
    for o in r:
        print(o['grup'], o['alt'], o['tarih'], o['bas'], o['bit'], len(o['numaralar']))
