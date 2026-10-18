"""Bölüm listesi Excel'ini isimsiz hale getirip depoya koyar.

Kullanım: python scraper/liste_ice_aktar.py <dosya.xlsx> <kurul> <Ders>
Çıktı: kaynak/listeler/<kurul>_<Ders>.json — oturumlar + numaraların tuzlu özetleri. İsim ve açık numara yoktur.
Excel'in kendisi depoya girmez (manual/ham/ git dışında).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import liste_xlsx
from guncelle import numara_ozeti, KAYNAK

yol, kurul, ders = sys.argv[1:4]
oturumlar = liste_xlsx.oku(yol, ders, kurul)
for o in oturumlar:
    o['numaralar'] = sorted(numara_ozeti(n) for n in o['numaralar'])
hedef = os.path.join(KAYNAK, 'listeler', f'{kurul}_{ders}.json')
os.makedirs(os.path.dirname(hedef), exist_ok=True)
json.dump({'kurul': kurul, 'ders': ders, 'oturumlar': oturumlar}, open(hedef, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(hedef, len(oturumlar), 'oturum', sum(len(o['numaralar']) for o in oturumlar), 'numara')
