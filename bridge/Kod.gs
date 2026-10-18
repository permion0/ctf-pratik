/**
 * CTF Pratik Takip · köprü (okul hesabında çalışır)
 * Okula kapalı ders programı tablosunu ve Düzeltmeler tablosunu 10 dakikada bir okur;
 * bir şey değiştiyse GitHub deposuna kaynak/program.json olarak gönderir.
 * Gönderilen veride öğrenci adı ya da numarası yoktur.
 *
 * Proje Ayarları → Komut dosyası özellikleri: GITHUB_TOKEN (yalnızca ctf-pratik deposuna yazma izni olan anahtar).
 */
const PROGRAM_ID = '1LahYrgkKN5aXe4nmUGCimOFnNf7MluHSqLmjdy92VM0';
const DEPO = 'permion0/ctf-pratik';
const YOL = 'kaynak/program.json';
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

/** Bir kez çalıştır: 10 dakikalık zamanlayıcıyı kurar (eskisini siler). */
function zamanlayiciKur() {
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('gonder').timeBased().everyMinutes(10).create();
  gonder();
}

function veri() {
  const out = { program: {}, duzeltmeler: [] };
  SpreadsheetApp.openById(PROGRAM_ID).getSheets().forEach(function (s) {
    out.program[s.getName()] = s.getDataRange().getDisplayValues();
  });
  const id = PROPS.getProperty('DUZELTME_ID');
  if (id) out.duzeltmeler = SpreadsheetApp.openById(id).getSheets()[0].getDataRange().getDisplayValues();
  return out;
}

function gonder() {
  const token = PROPS.getProperty('GITHUB_TOKEN');
  if (!token) throw new Error('GITHUB_TOKEN yok: Proje Ayarları → Komut dosyası özellikleri');
  const v = veri();
  const govde = JSON.stringify(v);
  const ozet = Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, govde, Utilities.Charset.UTF_8));
  if (ozet === PROPS.getProperty('SON_OZET')) return;  // değişiklik yok
  v.alindi = new Date().toISOString();
  const api = 'https://api.github.com/repos/' + DEPO + '/contents/' + YOL;
  const bas = { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' };
  const mevcut = UrlFetchApp.fetch(api, { headers: bas, muteHttpExceptions: true });
  const sha = mevcut.getResponseCode() === 200 ? JSON.parse(mevcut.getContentText()).sha : undefined;
  const yanit = UrlFetchApp.fetch(api, {
    method: 'put', headers: bas, contentType: 'application/json', muteHttpExceptions: true,
    payload: JSON.stringify({
      message: 'Drive programı değişti · ' + v.alindi,
      content: Utilities.base64Encode(JSON.stringify(v, null, 1), Utilities.Charset.UTF_8),
      sha: sha
    })
  });
  if (yanit.getResponseCode() >= 300) throw new Error('GitHub: ' + yanit.getResponseCode() + ' ' + yanit.getContentText().slice(0, 300));
  PROPS.setProperty('SON_OZET', ozet);
}
