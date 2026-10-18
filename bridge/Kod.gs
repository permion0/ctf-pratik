/**
 * CTF Pratik Takip · köprü (okul hesabında çalışır)
 * Okula kapalı ders programı tablosunu ve Düzeltmeler tablosunu 15 dakikada bir okur;
 * bir şey değiştiyse GitHub deposuna kaynak/program.json olarak gönderir.
 * Gönderilen veride öğrenci adı ya da numarası yoktur.
 *
 * Proje Ayarları → Komut dosyası özellikleri: GITHUB_TOKEN (yalnızca ctf-pratik deposuna yazma izni olan anahtar).
 */
const PROGRAM_ID = '1LahYrgkKN5aXe4nmUGCimOFnNf7MluHSqLmjdy92VM0';
const DEPO = 'permion0/ctf-pratik';
const YOL = 'kaynak/program.json';
const SEKME = /^\s*1/;  // yalnızca 1. sınıf sekmeleri (1-TR, 1- EN, 1- MT)
const PROPS = PropertiesService.getScriptProperties();

/** Bir kez çalıştır: Düzeltmeler tablosunu oluşturur, adresini günlüğe yazar. */
function kurulum() {
  let id = PROPS.getProperty('DUZELTME_ID');
  if (!id) {
    const ss = SpreadsheetApp.create('CTF Pratik Takip · Düzeltmeler');
    const sh = ss.getSheets()[0];
    sh.setName('Düzeltmeler');
    sh.getRange(1, 1, 1, 9).setValues([[
      'Tarih (gg.aa.yyyy)', 'Program (1-TR / 1-EN / hepsi)', 'Ders', 'Grup (ör. 4a, 4b, 4, hepsi)',
      'Başlangıç (ss:dd)', 'Bitiş (ss:dd)', 'Yer', 'Durum (değişti / iptal / ek)', 'Not'
    ]]).setFontWeight('bold');
    sh.setFrozenRows(1);
    sh.autoResizeColumns(1, 9);
    id = ss.getId();
    PROPS.setProperty('DUZELTME_ID', id);
  }
  Logger.log('Düzeltmeler tablosu: https://docs.google.com/spreadsheets/d/' + id + '/edit');
}

/** Bir kez çalıştır: 15 dakikalık zamanlayıcıyı kurar (eskisini siler). */
function zamanlayiciKur() {
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('gonder').timeBased().everyMinutes(15).create();
  gonder();
}

function veri() {
  const out = { program: {}, duzeltmeler: [] };
  SpreadsheetApp.openById(PROGRAM_ID).getSheets().forEach(function (s) {
    if (SEKME.test(s.getName())) out.program[s.getName().trim()] = s.getDataRange().getDisplayValues();
  });
  const id = PROPS.getProperty('DUZELTME_ID');
  if (id) out.duzeltmeler = SpreadsheetApp.openById(id).getSheets()[0].getDataRange().getDisplayValues();
  return out;
}

/** Okul sitesindeki pratik PDF'i ve ortak ders sınav görselinin özetini çıkarır. */
function izleme() {
  const UA = { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36', Referer: 'https://ctfogrenci.iuc.edu.tr/' };
  const cms = function (site, grup) {
    const r = UrlFetchApp.fetch('https://service-cms.iuc.edu.tr/api/webclient/f_getContentGroupItems?siteKey=' + site + '&Value=' + grup, { headers: UA, muteHttpExceptions: true });
    return r.getResponseCode() === 200 ? JSON.parse(r.getContentText()).Data : [];
  };
  const ozet = function (url) {
    const r = UrlFetchApp.fetch(url, { headers: UA, muteHttpExceptions: true });
    if (r.getResponseCode() !== 200) return 'hata ' + r.getResponseCode();
    return Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, r.getBlob().getBytes()));
  };
  const out = {};
  const html = cms('985BBFA20CC746A98F11C92D4E591A51', 'tip-egitimi').map(function (x) { return x.HtmlContent || ''; }).join(' ');
  const m = html.match(/href="([^"]*preklinik[^"]*pratik[^"]*\.pdf)"/i);
  if (m) { out.pdf = m[1]; out.pdfOzet = ozet(m[1]); }
  const oh = cms('E92E3756DEE540F79CD7D49E437D3AE0', 'ortak-zorunlu-dersler').map(function (x) { return x.HtmlContent || ''; }).join(' ');
  const g = oh.match(/drive\.google\.com\/file\/d\/([\w-]+)/);
  if (g) out.ortakOzet = ozet('https://drive.google.com/uc?export=download&id=' + g[1]);
  return out;
}

function gonder() {
  const token = PROPS.getProperty('GITHUB_TOKEN');
  if (!token) throw new Error('GITHUB_TOKEN yok: Proje Ayarları → Komut dosyası özellikleri');
  try { yaz_('kaynak/izleme.json', izleme(), 'IZLEME', 'Okul sitesinde değişiklik', token); } catch (e) { console.warn('izleme: ' + e); }
  try { bildir_(); } catch (e) { console.warn('bildirim: ' + e); }
  const v = veri();
  const govde = JSON.stringify(v);
  const ozet = Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, govde, Utilities.Charset.UTF_8));
  if (ozet === PROPS.getProperty('SON_OZET')) return;  // değişiklik yok
  v.alindi = new Date().toISOString();
  const api = 'https://api.github.com/repos/' + DEPO + '/contents/' + YOL;
  const bas = { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' };
  let sha = PROPS.getProperty('SON_SHA');
  if (!sha) {
    const mevcut = UrlFetchApp.fetch(api, { headers: bas, muteHttpExceptions: true });
    sha = mevcut.getResponseCode() === 200 ? JSON.parse(mevcut.getContentText()).sha : undefined;
  }
  const yanit = UrlFetchApp.fetch(api, {
    method: 'put', headers: bas, contentType: 'application/json', muteHttpExceptions: true,
    payload: JSON.stringify({
      message: 'Drive programı değişti · ' + v.alindi,
      content: Utilities.base64Encode(JSON.stringify(v), Utilities.Charset.UTF_8),
      sha: sha
    })
  });
  if (yanit.getResponseCode() >= 300) {
    PROPS.deleteProperty('SON_SHA');  // sha eskidiyse bir sonraki turda yeniden alınır
    throw new Error('GitHub: ' + yanit.getResponseCode() + ' ' + yanit.getContentText().slice(0, 300));
  }
  PROPS.setProperty('SON_SHA', JSON.parse(yanit.getContentText()).content.sha);
  PROPS.setProperty('SON_OZET', ozet);
}

/** Küçük bir dosyayı yalnızca içeriği değiştiyse GitHub'a yazar (sha ve özet Script Properties'te tutulur). */
function yaz_(yol, nesne, anahtar, mesaj, token) {
  const govde = JSON.stringify(nesne);
  const oz = Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, govde, Utilities.Charset.UTF_8));
  if (oz === PROPS.getProperty(anahtar + '_OZET')) return;
  const api = 'https://api.github.com/repos/' + DEPO + '/contents/' + yol;
  const bas = { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' };
  let sha = PROPS.getProperty(anahtar + '_SHA');
  if (!sha) {
    const r = UrlFetchApp.fetch(api, { headers: bas, muteHttpExceptions: true });
    sha = r.getResponseCode() === 200 ? JSON.parse(r.getContentText()).sha : undefined;
  }
  const y = UrlFetchApp.fetch(api, { method: 'put', headers: bas, contentType: 'application/json', muteHttpExceptions: true,
    payload: JSON.stringify({ message: mesaj + ' · ' + new Date().toISOString(), content: Utilities.base64Encode(govde, Utilities.Charset.UTF_8), sha: sha }) });
  if (y.getResponseCode() >= 300) { PROPS.deleteProperty(anahtar + '_SHA'); throw new Error('GitHub: ' + y.getResponseCode()); }
  PROPS.setProperty(anahtar + '_SHA', JSON.parse(y.getContentText()).content.sha);
  PROPS.setProperty(anahtar + '_OZET', oz);
}

/** Elle deneme: izleme sonucunu günlüğe yazar. */
function izlemeDene() { Logger.log(JSON.stringify(izleme())); }

/** Sana (bu hesabın e-postasına) mail: yeni değişiklikler, kaynaklar arası uyuşmazlık ya da durdurulan yayın. */
const SITE = 'https://cerrahpasa-turkce-tip.vercel.app';
function bildir_(deneme) {
  const ham = function (yol) {
    const r = UrlFetchApp.fetch('https://raw.githubusercontent.com/' + DEPO + '/main/' + yol + '?t=' + Date.now(), { muteHttpExceptions: true });
    return r.getResponseCode() === 200 ? JSON.parse(r.getContentText()) : null;
  };
  const saglik = ham('site/data/saglik.json') || {};
  const degis = ham('site/data/degisiklikler.json') || [];
  const ilk = !PROPS.getProperty('SON_BILDIRIM');
  const son = new Date(PROPS.getProperty('SON_BILDIRIM') || 0);
  const yeni = degis.filter(function (d) { return new Date(d.zaman) > son; });
  const saglikOzet = JSON.stringify({ d: saglik.durum, s: saglik.sorunlar, u: saglik.uyarilar, h: saglik.hatalar });
  const saglikYeni = saglikOzet !== PROPS.getProperty('SON_SAGLIK');
  PROPS.setProperty('SON_SAGLIK', saglikOzet);
  if (ilk && !deneme) { PROPS.setProperty('SON_BILDIRIM', new Date().toISOString()); return; }  // ilk çalışmada eski kayıtları yollama
  const sorunVar = saglik.durum !== 'ok' || (saglik.uyarilar || []).length || (saglik.hatalar || []).length;
  if (!deneme && !yeni.length && !(saglikYeni && sorunVar)) return;
  const satir = [];
  if (saglik.durum === 'durduruldu') satir.push('YAYIN DURDURULDU: okunan veri bozuk görünüyor, site eski veriyle kaldı.', ...(saglik.sorunlar || []).map(function (x) { return '  - ' + x; }), '');
  if ((saglik.uyarilar || []).length) satir.push('Kaynaklar birbiriyle uyuşmuyor:', ...saglik.uyarilar.map(function (x) { return '  - ' + x; }), '');
  if ((saglik.hatalar || []).length) satir.push('Okunamayan kaynaklar:', ...saglik.hatalar.map(function (x) { return '  - ' + x; }), '');
  if (yeni.length) {
    satir.push(yeni.length + ' değişiklik:');
    yeni.slice(0, 40).forEach(function (d) { satir.push('  - ' + (d.tarih ? d.tarih + ': ' : '') + d.ne + ' (' + d.kaynak + (d.program ? ', ' + d.program : '') + ')'); });
    if (yeni.length > 40) satir.push('  … ve ' + (yeni.length - 40) + ' tane daha');
    satir.push('');
  }
  if (deneme) satir.push('Bu bir deneme mailidir: bildirimler çalışıyor.', '');
  satir.push('Site: ' + SITE, 'Değişenler sekmesinde ayrıntı ve kaynak linkleri var.');
  const konu = saglik.durum === 'durduruldu' ? 'Pratik Pusulası: yayın durduruldu, kontrol et'
    : sorunVar && saglikYeni ? 'Pratik Pusulası: kaynaklarda uyuşmazlık'
    : yeni.length ? 'Pratik Pusulası: ' + yeni.length + ' değişiklik' : 'Pratik Pusulası: bildirim denemesi';
  MailApp.sendEmail({ to: Session.getEffectiveUser().getEmail(), subject: konu, body: satir.join('\n') });
  const enYeni = yeni.reduce(function (m, d) { return new Date(d.zaman) > m ? new Date(d.zaman) : m; }, son);
  PROPS.setProperty('SON_BILDIRIM', (enYeni > son ? enYeni : new Date()).toISOString());
}

/** Elle deneme: kendine bir deneme maili gönderir (ilk çalıştırmada e-posta izni ister). */
function bildirimDene() { bildir_(true); }
