"""Bir dersin pratik listesinde standart gruptan farklı olan numaraları isimsizleştirip kaydeder.

Kullanım: python scraper/grup_istisna.py <kurul> <Ders> <dosya.txt>
dosya.txt satırları: "<numara> <grup>" ya da "<başlangıç>-<bitiş> <grup>". Çıktı: kaynak/listeler/<kurul>_<Ders>_gruplar.json
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from guncelle import numara_ozeti, KAYNAK

kurul, ders, yol = sys.argv[1:4]
gruplar = {}
for satir in open(yol, encoding='utf-8'):
    satir = satir.split('#')[0].strip()
    if not satir:
        continue
    no, grup = satir.split()
    if '-' in no:
        a, b = no.split('-')
        for n in range(int(a), int(b) + 1):
            gruplar[numara_ozeti(f'{n:010d}')] = grup
    else:
        gruplar[numara_ozeti(no)] = grup
hedef = os.path.join(KAYNAK, 'listeler', f'{kurul}_{ders}_gruplar.json')
json.dump({'kurul': kurul, 'ders': ders, 'gruplar': dict(sorted(gruplar.items()))}, open(hedef, 'w', encoding='utf-8'), indent=1)
print(hedef, len(gruplar))
