/* Pratik Pusulası · istemci
 * Veri: data/veri.json (program, pratik tablosu, düzeltmeler), data/liste.json (bölüm listeleri, numaralar özetli),
 * data/degisiklikler.json. Öğrenci numarası yalnızca bu cihazda saklanır.
 */
'use strict';

const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const depo = {
  al(k, d) { try { const v = localStorage.getItem('pp:' + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  koy(k, v) { try { localStorage.setItem('pp:' + k, JSON.stringify(v)); } catch { } }
};

const GUN_ADI = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi'];
const GUN_KISA = ['Paz', 'Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt'];
const AY_ADI = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
const PROGRAM_AD = { TR: 'Türkçe Tıp · EKU amfisi', MT: 'Türkçe Tıp · MT amfisi', EN: 'İngilizce Tıp' };

/* Pratik yerleri: okulun öğrenci portalındaki "1001 Pratikleri" bilgisi */
const YER = {
  'Anatomi': 'Temel Bilimler B Blok, 2. kat (Temel Genetik laboratuvarı)',
  'Biyofizik': 'Temel Bilimler B Blok, 2. kat',
  'Biyokimya': 'Temel Bilimler B Blok, 1. kat',
  'Biyoistatistik': 'Dahiliye binası, Hakkı Ogan amfisi'
};

function hat(ad) {
  const s = (ad || '').toLocaleLowerCase('tr');
  if (s.includes('anatomi') || s.includes('anatomy')) return 'var(--anatomi)';
  if (s.includes('biyokimya') || s.includes('biochem')) return 'var(--biyokimya)';
  if (s.includes('biyofizik') || s.includes('biophys')) return 'var(--biyofizik)';
  if (s.includes('biyoistatistik') || s.includes('biostat')) return 'var(--biyoistatistik)';
  if (s.includes('tıp tarihi') || s.includes('history')) return 'var(--tiptarihi)';
  if (s.includes('ortak ders') || s.includes('common')) return 'var(--ortak)';
  return 'var(--diger)';
}
const kisaDers = ad => ({ 'Tıbbi Biyokimya': 'Biyokimya', 'Biyoistatistik ve Tıp Bilişimi': 'Biyoistatistik', 'Tıp Tarihi ve Etik': 'Tıp Tarihi' }[ad] || ad);

/* tarih yardımcıları (yerel saat, Türkiye) */
const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const tarihten = s => { const [y, m, g] = s.split('-').map(Number); return new Date(y, m - 1, g); };
const ekle = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const pazartesi = d => ekle(d, -((d.getDay() + 6) % 7));
const dk = s => { const [h, m] = (s || '0:0').split(':').map(Number); return h * 60 + m; };
const insanTarih = s => { const d = tarihten(s); return `${d.getDate()} ${AY_ADI[d.getMonth()]} ${GUN_ADI[d.getDay()]}`; };

let VERI = null, LISTE = null, DEGISIM = [], KONTROL = {};
let durum = {
  sekme: 'bugun',
  gun: null,                       // seçili gün (ISO)
  numara: depo.al('numara', ''),
  program: depo.al('program', ''),
  grup: depo.al('grup', ''),
  gitmedim: depo.al('gitmedim', {}),
  benim: []                        // numaranın listelerdeki oturumları
};

/* ---------- grup ve oturumlar ---------- */
function gruptan(no) {
  if (!VERI) return '';
  const n = Number(no);
  for (const g of VERI.gruplar) {
    const bas = Number(g.bas), bit = g.bit ? Number(g.bit) : null;
    if (bit != null && n >= bas && n <= bit) return g.grup;
  }
  // "ve diğer öğrenciler": programın son grubu
  const ing = no.startsWith('0902');
  const acik = VERI.gruplar.filter(g => !g.bit && (g.program === 'EN') === ing);
  return acik.length ? acik[acik.length - 1].grup : '';
}
async function ozetle(no) {
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(LISTE.tuz + no));
  return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('').slice(0, 12);
}
async function benimOturumlar() {
  if (!LISTE || !durum.numara || !crypto.subtle) return [];
  const h = await ozetle(durum.numara);
  return (LISTE.numara[h] || []).map(i => LISTE.oturumlar[i]);
}

/* bir gün için öğrencinin pratikleri: tablo + liste + temsilci düzeltmesi */
function grupUyar(deger, grup) {
  if (!deger || deger === '-') return false;
  const v = deger.replace(/\s/g, '').toLowerCase();
  return v === grup || v === grup[0];
}
function pratikler(gun) {
  const out = [];
  const g = durum.grup;
  for (const k of VERI.pratik?.kurullar || []) {
    for (const satir of k.gunler) {
      if (satir.tarih !== gun) continue;
      for (const [ders, deger] of Object.entries(satir.degerler)) {
        if (!grupUyar(deger, g)) continue;
        out.push({ ders, kurul: k.kurul, deger, kaynak: 'Pratik dönüşüm tablosu', sinav: satir.notlar?.[ders] === 'sınav' });
      }
    }
  }
  // listede bu güne oturum varsa (grup tablosundan farklı da olabilir) onu esas al
  for (const o of durum.benim) {
    if (o.tarih !== gun) continue;
    let p = out.find(x => x.ders === o.ders);
    if (!p) { p = { ders: o.ders, kurul: o.kurul, kaynak: 'Bölüm listesi' }; out.push(p); }
    Object.assign(p, { bas: o.bas, bit: o.bit, altgrup: `${o.grup}-${o.alt}`, saatKaynak: `${o.ders} bölümünün listesi` });
  }
  // bölüm listesi o derste başka bir günü gösteriyorsa tablo satırını düşür
  for (let i = out.length - 1; i >= 0; i--) {
    const p = out[i];
    if (p.kaynak === 'Pratik dönüşüm tablosu' && durum.benim.some(o => o.ders === p.ders && o.kurul === p.kurul) && !durum.benim.some(o => o.ders === p.ders && o.tarih === gun)) out.splice(i, 1);
  }
  // temsilci düzeltmeleri
  for (const d of VERI.duzeltmeler || []) {
    if (d.tarih !== gun) continue;
    if (d.program !== 'hepsi' && d.program !== durum.program) continue;
    if (d.grup !== 'hepsi' && d.grup !== g && d.grup !== g[0]) continue;
    let p = out.find(x => x.ders.toLocaleLowerCase('tr') === d.ders.toLocaleLowerCase('tr'));
    if (!p && (d.durum === 'ek' || d.durum === 'değişti')) { p = { ders: d.ders, kaynak: 'Temsilci' }; out.push(p); }
    if (!p) continue;
    if (d.bas) { p.bas = d.bas; p.bit = d.bit; p.saatKaynak = 'Temsilci'; }
    if (d.yer) p.yer = d.yer;
    if (d.durum === 'iptal') p.iptal = true;
    if (d.not) p.not = d.not;
    p.duzeltildi = true;
  }
  return out;
}
function olaylar(gun) {
  const out = [];
  for (const k of VERI.pratik?.kurullar || []) for (const s of k.gunler) if (s.tarih === gun && s.olay) out.push(s.olay);
  return out;
}
function dersler(gun) {
  const p = VERI.programlar?.[durum.program];
  return (p?.gunler?.[gun] || []).filter(x => x.tur !== 'pratik');
}
function pratikSaati(gun) {
  const p = VERI.programlar?.[durum.program]?.gunler?.[gun] || [];
  const s = p.find(x => x.tur === 'pratik');
  return s ? [s.bas, s.bit] : ['13:30', '16:15'];
}

/* ---------- görünümler ---------- */
function ustBugun() {
  const d = tarihten(durum.gun), bugun = iso(new Date());
  const pzt = pazartesi(d);
  let gunler = '';
  for (let i = 0; i < 5; i++) {
    const x = ekle(pzt, i), s = iso(x);
    const im = pratikler(s).filter(p => !p.iptal).map(p => `<i style="background:${hat(p.ders)}"></i>`).join('');
    gunler += `<button class="gun ${s === bugun ? 'bugun' : ''}" aria-pressed="${s === durum.gun}" data-gun="${s}" aria-label="${insanTarih(s)}"><span class="ad">${GUN_KISA[x.getDay()]}</span><span class="no">${x.getDate()}</span><span class="imler">${im}</span></button>`;
  }
  const baslik = durum.gun === bugun ? 'Bugün' : durum.gun === iso(ekle(new Date(), 1)) ? 'Yarın' : GUN_ADI[d.getDay()];
  return `<div class="basrow"><div><h1 class="gunbas">${baslik}</h1><div class="gunalt">${d.getDate()} ${AY_ADI[d.getMonth()]}${baslik === GUN_ADI[d.getDay()] ? '' : ', ' + GUN_ADI[d.getDay()]}</div></div>${grupRozet()}</div>
  <div class="hafta"><button class="ok" data-hafta="-7" aria-label="Önceki hafta">‹</button>${gunler}<button class="ok" data-hafta="7" aria-label="Sonraki hafta">›</button></div>`;
}
function grupRozet() {
  return durum.grup ? `<button class="grupbadge" data-git="ben" aria-label="Grubun ${durum.grup}, değiştir"><span>Grup</span><b>${esc(durum.grup)}</b></button>` : '';
}

function durakPratik(p, gun) {
  const [vb, ve] = pratikSaati(gun);
  const kesin = !!p.bas;
  const bas = p.bas || vb, bit = p.bit || (p.bas ? String(Math.min(dk(p.bas) + 45, dk(ve)) / 60 | 0).padStart(2, '0') + ':' + String(Math.min(dk(p.bas) + 45, dk(ve)) % 60).padStart(2, '0') : ve);
  const yer = p.yer || YER[p.ders] || '';
  const etiket = [
    `<span class="etiket hat">${p.altgrup ? 'Alt grup ' + esc(p.altgrup) : 'Grup ' + esc(durum.grup)}</span>`,
    kesin ? `<span class="etiket kesin">Saat kesin</span>` : `<span class="etiket belirsiz">Kesin saat henüz duyurulmadı</span>`,
    p.sinav ? `<span class="etiket dikkat">Pratik sınavı</span>` : ''
  ].join('');
  return { bas, bit, html: `<li class="durak pratik ${p.iptal ? 'iptal' : ''}" style="--hat:${hat(p.ders)}" data-bas="${bas}" data-bit="${bit}">
    <div class="saat">${kesin ? bas : vb}<small>${kesin ? (p.bit || 'başlar') : 've sonrası'}</small></div><div class="nokta"></div>
    <div class="icerik"><div class="ders">${esc(p.ders)} pratiği${p.iptal ? ' · iptal' : ''}</div>
    ${yer ? `<div class="alt">${esc(yer)}</div>` : ''}${p.not ? `<div class="alt">${esc(p.not)}</div>` : ''}
    <div class="etiketler">${etiket}</div>
    <div class="kaynak">Kaynak: ${esc([p.kaynak, p.saatKaynak && p.saatKaynak !== p.kaynak ? 'saat: ' + p.saatKaynak : ''].filter(Boolean).join(', '))}</div></div></li>` };
}

function gorBugun() {
  const gun = durum.gun;
  const ol = olaylar(gun);
  const pr = pratikler(gun);
  const ds = dersler(gun);
  const duraklar = [];
  for (const x of ds) duraklar.push({ bas: x.bas, bit: x.bit, html: `<li class="durak ${x.tur === 'ortak' ? 'ara' : ''}" style="--hat:${hat(x.abd || x.ders)}" data-bas="${x.bas}" data-bit="${x.bit}"><div class="saat">${x.bas}<small>${x.bit}</small></div><div class="nokta"></div><div class="icerik"><div class="ders">${esc(x.ders)}</div><div class="alt">${esc([kisaDers(x.abd), x.hoca, x.yer].filter(Boolean).join(', '))}</div></div></li>` });
  for (const p of pr) duraklar.push(durakPratik(p, gun));
  duraklar.sort((a, b) => dk(a.bas) - dk(b.bas));

  let h = '';
  for (const o of ol) h += `<div class="serit" role="status">${esc(olayAdi(o.ad))}${o.dersler?.length && o.dersler.length < 4 ? ': ' + esc(o.dersler.join(', ')) : ''}</div>`;
  if (gun === iso(new Date())) h += siradaki(duraklar);
  if (!VERI.programlar?.[durum.program]) h += `<div class="serit bilgi">Teorik ders programı henüz yüklenmedi; şimdilik sadece pratikler görünüyor.</div>`;
  if (duraklar.length) h += `<ol class="guzergah">${duraklar.map(d => d.html).join('')}</ol>`;
  else if (!ol.length) h += `<div class="bos"><b>${[0, 6].includes(tarihten(gun).getDay()) ? 'Hafta sonu' : 'Bu gün boş'}</b>Programda ders ya da pratik yok.</div>`;
  h += `<p class="guncel">Kaynaklar son kontrol: ${zamanFark(KONTROL.zaman || VERI.guncelleme)}</p>`;
  return h;
}
function olayAdi(a) {
  return a.replace(/ARASINAVI/, 'ara sınavı').replace(/BİTİRME SINAVI/, 'bitirme sınavı').replace(/DOĞAL AFET/, 'Pratik yok: doğal afet (yağmur) nedeniyle iptal').replace(/BAYRAMI/, 'Bayramı');
}
function siradaki(duraklar) {
  const simdi = new Date(), m = simdi.getHours() * 60 + simdi.getMinutes();
  const su = duraklar.find(d => dk(d.bas) <= m && m < dk(d.bit)) || duraklar.find(d => dk(d.bas) > m);
  if (!su) return '';
  const el = document.createElement('div'); el.innerHTML = su.html;
  const ders = el.querySelector('.ders')?.textContent || '', alt = el.querySelector('.alt')?.textContent || '';
  const hatRenk = el.firstElementChild.style.getPropertyValue('--hat');
  const fark = dk(su.bas) - m;
  const ne = fark > 0 ? (fark < 60 ? `${fark} dakika sonra` : `${Math.floor(fark / 60)} saat ${fark % 60 ? (fark % 60) + ' dakika ' : ''}sonra`) : 'Şu an';
  return `<section class="siradaki" style="--hat:${hatRenk}" aria-label="Sıradaki"><div class="ne">${ne}, ${su.bas}</div><div class="baslik">${esc(ders)}</div>${alt ? `<div class="ayrinti"><span>${esc(alt)}</span></div>` : ''}</section>`;
}
function zamanFark(isoz) {
  if (!isoz) return 'bilinmiyor';
  const f = Math.round((Date.now() - new Date(isoz)) / 60000);
  if (f < 2) return 'az önce';
  if (f < 60) return `${f} dakika önce`;
  if (f < 1440) return `${Math.round(f / 60)} saat önce`;
  return new Date(isoz).toLocaleString('tr-TR', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' });
}

/* Pratiklerim: ders ders bütün oturumlar + devamsızlık hakkı */
function hakHesap(toplam) {
  if (toplam <= 1) return 0;
  if (toplam < 5) return 1;
  return Math.floor(toplam * 0.2);
}
function gorPratik() {
  const bugun = iso(new Date());
  const gruplu = {};
  const tum = new Set();
  for (const k of VERI.pratik?.kurullar || []) for (const s of k.gunler) tum.add(s.tarih);
  for (const o of durum.benim) tum.add(o.tarih);
  for (const t of [...tum].sort()) for (const p of pratikler(t)) {
    const a = `${p.kurul || ''}|${p.ders}`;
    (gruplu[a] = gruplu[a] || []).push({ ...p, tarih: t });
  }
  const kurullar = [...new Set(Object.keys(gruplu).map(k => k.split('|')[0]))];
  const aktif = kurullar.find(k => Object.entries(gruplu).some(([a, l]) => a.startsWith(k + '|') && l.some(p => p.tarih >= bugun))) || kurullar[kurullar.length - 1];
  let h = `<p class="ipucu" style="margin:0">Okulun tablosundan ve bölüm listelerinden. Gitmediğin pratiği işaretle, kalan hakkını görürsün.</p>`;
  for (const kurul of kurullar.sort((a, b) => (a === aktif ? -1 : b === aktif ? 1 : a.localeCompare(b)))) {
    const satirlar = Object.entries(gruplu).filter(([a]) => a.startsWith(kurul + '|'));
    h += `<section class="bolum"><h2>${esc(kurul)} kurulu${kurul === aktif ? '' : ''}</h2>`;
    for (const [a, l] of satirlar) {
      const ders = a.split('|')[1];
      const gecerli = l.filter(p => !p.iptal);
      const hak = hakHesap(gecerli.length);
      const kullanilan = gecerli.filter(p => durum.gitmedim[`${p.tarih}|${p.ders}`]).length;
      const kalan = hak - kullanilan;
      h += `<div class="kart" style="--hat:${hat(ders)}"><div class="hak"><div class="say">${Math.max(kalan, 0)}<small>hak</small></div><div><b>${esc(ders)}</b><div class="ipucu">${gecerli.length} pratik, ${hak ? hak + ' devamsızlık hakkı' : 'devamsızlık hakkı yok'}${kalan < 0 ? '. Hakkını aştın, temsilciye sor' : ''}</div></div></div>
      <div class="cubuk">${gecerli.map(p => `<i class="${durum.gitmedim[`${p.tarih}|${p.ders}`] ? 'gitmedi' : p.tarih < bugun ? 'gitti' : p.tarih === bugun ? 'bugun' : ''}"></i>`).join('')}</div>
      <div style="margin-top:6px">${l.map(p => { const anahtar = `${p.tarih}|${p.ders}`; const [vb] = pratikSaati(p.tarih); return `<div class="satir"><div class="tarih">${tarihten(p.tarih).getDate()} ${AY_ADI[tarihten(p.tarih).getMonth()].slice(0, 3)}<small>${GUN_KISA[tarihten(p.tarih).getDay()]}</small></div><div class="ne"><b>${p.iptal ? 'İptal' : (p.bas ? (p.bit ? p.bas + '–' + p.bit : 'Başlangıç ' + p.bas) : vb + ' ve sonrası')}</b><span>${p.altgrup ? 'Alt grup ' + esc(p.altgrup) : 'Grup ' + esc(durum.grup)}${p.sinav ? ', pratik sınavı' : ''}</span></div>${p.tarih <= bugun && !p.iptal ? `<button class="secim" data-gitmedim="${esc(anahtar)}" aria-pressed="${!!durum.gitmedim[anahtar]}">${durum.gitmedim[anahtar] ? 'Gitmedim' : 'Gittim'}</button>` : '<span></span>'}</div>`; }).join('')}</div></div>`;
    }
    h += `</section>`;
  }
  h += `<section class="bolum"><div class="kart ipucu">Kural (temsilcinin 8 Ekim duyurusu): bir derste 5 ya da daha fazla pratik varsa %80 devam zorunlu, 5'ten azsa 1 devamsızlık hakkı var, tek pratiği olan derse gitmek zorunlu. Ayrıca kuruldaki bütün pratiklerin %80'ine katılmalısın. Rapor devamsızlıktan sayılmaz; pratiğin asistanına iletilir.</div></section>`;
  return h;
}

function gorDegisen() {
  const liste = DEGISIM.filter(d => !d.program || d.program === durum.program);
  let h = `<p class="ipucu" style="margin:0">Okulun tablolarında ve temsilcinin düzeltmelerinde yakalanan her değişiklik, en yenisi üstte.</p>`;
  if (!liste.length) h += `<div class="kart bos"><b>Henüz değişiklik yok</b>Kaynaklar 15 dakikada bir kontrol ediliyor. Bir şey değişince burada görünür.</div>`;
  else h += `<div class="kart">${liste.slice(0, 80).map(d => `<div class="degisim" style="--hat:${hat(d.ders || '')}"><i></i><div><div>${d.tarih ? '<b>' + esc(insanTarih(d.tarih)) + '</b>, ' : ''}${esc(d.ne)}</div><div class="zaman">${esc(zamanFark(d.zaman))} · ${esc(d.kaynak)}</div></div></div>`).join('')}</div>`;
  h += `<section class="bolum"><h2>İzlenen kaynaklar</h2><div class="kart">${(VERI.kaynaklar || []).map(k => `<div class="satir iki"><div class="ne"><b>${esc(k.ad)}</b><span>Son değişiklik: ${esc(zamanFark(k.degisti))}</span></div>${k.url ? `<a href="${esc(k.url)}" target="_blank" rel="noopener">Kaynağı aç</a>` : '<span></span>'}</div>`).join('')}</div></section>`;
  return h;
}

function gorBen() {
  const takvim = durum.grup ? new URL(`data/takvim/${durum.program}-${durum.grup}.ics`, location.href).href : '';
  return `<section class="bolum"><h2>Numaran ve grubun</h2>
  <div class="kart" style="display:grid;gap:14px">${formNumara()}</div></section>
  ${takvim ? `<section class="bolum"><h2>Telefonunun takvimine ekle</h2><p>Bir kez abone ol; program değişince takvimin de kendiliğinden güncellenir.</p><div class="kart" style="display:grid;gap:10px">
  <a class="dugme" style="text-align:center;text-decoration:none" href="${esc(takvim.replace(/^https?:/, 'webcal:'))}">Takvime abone ol</a>
  <div class="kopya"><input readonly value="${esc(takvim)}" aria-label="Takvim adresi"><button class="dugme ikincil" data-kopyala="${esc(takvim)}">Kopyala</button></div>
  <div class="ipucu">Android'de Google Takvim: Ayarlar → Takvim ekle → URL ile, adresi yapıştır.</div></div></section>` : ''}
  <section class="bolum"><h2>Bu site ne yapıyor?</h2><div class="kart ipucu">Okulun öğrenci portalındaki pratik dönüşüm tablosunu, Drive'daki ders programını, bölümlerin pratik listelerini ve temsilcinin düzeltmelerini 15 dakikada bir okur. Numaran bu telefonda kalır; sunucuya gönderilmez. Sitede öğrenci adı yoktur.</div></section>`;
}
function formNumara(ilk) {
  const ing = durum.numara.startsWith('0902');
  return `<form id="numform" class="alan" novalidate>
    <label for="no">Öğrenci numaran</label>
    <input id="no" inputmode="numeric" autocomplete="off" maxlength="10" placeholder="0901260…" value="${esc(durum.numara)}">
    <div class="ipucu">Grubun numarandan bulunur. Numara bu telefonda kalır.</div>
    <div class="hata" id="nohata" hidden></div>
    ${!ing ? `<div class="alan" style="margin-top:8px"><label>Teorik dersler hangi amfide?</label><div class="ikili">
      <button type="button" data-program="TR" aria-pressed="${durum.program !== 'MT'}"><b>EKU</b><span>Türkçe tıp programı</span></button>
      <button type="button" data-program="MT" aria-pressed="${durum.program === 'MT'}"><b>MT</b><span>Türkçe tıp, MT amfisi</span></button></div></div>` : ''}
    ${durum.grup && !ilk ? `<div class="ipucu">Grubun: <b>${esc(durum.grup)}</b>. Bölüm listesinde başka bir alt gruptaysan Pratiklerim'de o görünür.</div>` : ''}
    <button class="dugme" type="submit">${ilk ? 'Programımı göster' : 'Kaydet'}</button></form>`;
}
function gorKarsilama() {
  return `<div class="karsilama"><div><h1>Bugün nerede olman gerektiğini söyleyen sayfa</h1></div>
  <p>Cerrahpaşa Tıp 1. sınıf: teorik dersler, pratik grubun, saatin ve yerin. Okulun tabloları değişince kendiliğinden güncellenir.</p>
  <div class="kart" style="display:grid;gap:14px">${formNumara(true)}</div></div>`;
}

/* ---------- çizim ve olaylar ---------- */
function ciz() {
  const ust = $('#ust'), ana = $('#ana'), alt = $('#alt');
  if (!durum.grup) { ust.innerHTML = ''; alt.hidden = true; ana.innerHTML = gorKarsilama(); bagla(); return; }
  alt.hidden = false;
  alt.querySelectorAll('button').forEach(b => b.dataset.sekme === durum.sekme ? b.setAttribute('aria-current', 'page') : b.removeAttribute('aria-current'));
  ust.innerHTML = durum.sekme === 'bugun' ? ustBugun() : `<div class="basrow"><div><h1 class="gunbas">${{ pratik: 'Pratikler', degisen: 'Değişenler', ben: 'Ben' }[durum.sekme]}</h1><div class="gunalt">${esc(PROGRAM_AD[durum.program] || '')}</div></div>${grupRozet()}</div>`;
  ana.innerHTML = { bugun: gorBugun, pratik: gorPratik, degisen: gorDegisen, ben: gorBen }[durum.sekme]();
  isaretleSimdi();
  bagla();
}
function isaretleSimdi() {
  if (durum.gun !== iso(new Date())) return;
  const m = new Date().getHours() * 60 + new Date().getMinutes();
  document.querySelectorAll('.durak').forEach(d => {
    const b = dk(d.dataset.bas), e = dk(d.dataset.bit);
    d.classList.toggle('gecti', e <= m);
    d.classList.toggle('simdi', b <= m && m < e);
  });
}
function bagla() {
  document.querySelectorAll('[data-gun]').forEach(b => b.onclick = () => { durum.gun = b.dataset.gun; ciz(); });
  document.querySelectorAll('[data-hafta]').forEach(b => b.onclick = () => { durum.gun = iso(ekle(tarihten(durum.gun), +b.dataset.hafta)); ciz(); });
  document.querySelectorAll('[data-git]').forEach(b => b.onclick = () => sekmeyeGit(b.dataset.git));
  document.querySelectorAll('[data-gitmedim]').forEach(b => b.onclick = () => {
    const k = b.dataset.gitmedim; if (durum.gitmedim[k]) delete durum.gitmedim[k]; else durum.gitmedim[k] = 1;
    depo.koy('gitmedim', durum.gitmedim); ciz();
  });
  document.querySelectorAll('[data-program]').forEach(b => b.onclick = () => {
    durum.program = b.dataset.program; b.parentElement.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
  });
  document.querySelectorAll('[data-kopyala]').forEach(b => b.onclick = async () => {
    try { await navigator.clipboard.writeText(b.dataset.kopyala); b.textContent = 'Kopyalandı'; } catch { b.previousElementSibling.select(); }
  });
  const f = $('#numform');
  if (f) f.onsubmit = async e => {
    e.preventDefault();
    const no = $('#no').value.replace(/\D/g, '');
    const hata = $('#nohata');
    if (no.length !== 10) { hata.hidden = false; hata.textContent = 'Numara 10 haneli olmalı.'; return; }
    const g = gruptan(no);
    if (!g) { hata.hidden = false; hata.textContent = 'Bu numara 1. sınıf gruplarının hiçbirinde yok. Numarayı kontrol et.'; return; }
    durum.numara = no; durum.grup = g;
    durum.program = no.startsWith('0902') ? 'EN' : (durum.program === 'MT' ? 'MT' : 'TR');
    depo.koy('numara', no); depo.koy('grup', g); depo.koy('program', durum.program);
    durum.benim = await benimOturumlar();
    durum.sekme = 'bugun'; ciz(); window.scrollTo({ top: 0 });
  };
}
function sekmeyeGit(s) { durum.sekme = s; ciz(); window.scrollTo({ top: 0 }); }
$('#alt').addEventListener('click', e => { const b = e.target.closest('[data-sekme]'); if (b) sekmeyeGit(b.dataset.sekme); });

async function yukle() {
  const al = async (y, d) => { try { const r = await fetch(y, { cache: 'no-cache' }); return r.ok ? r.json() : d; } catch { return d; } };
  [VERI, LISTE, DEGISIM, KONTROL] = await Promise.all([al('data/veri.json', {}), al('data/liste.json', { numara: {}, oturumlar: [] }), al('data/degisiklikler.json', []), al('data/kontrol.json', {})]);
  const bugun = new Date();
  const gun = [0, 6].includes(bugun.getDay()) ? ekle(pazartesi(bugun), 7) : bugun; // hafta sonu: gelecek pazartesi
  durum.gun = durum.gun || iso(gun);
  if (durum.numara) durum.benim = await benimOturumlar();
  ciz();
}
yukle();
setInterval(() => { if (durum.sekme === 'bugun') isaretleSimdi(); }, 60000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) yukle(); });
