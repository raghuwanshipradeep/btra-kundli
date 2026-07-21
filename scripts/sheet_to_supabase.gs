/**
 * Smart Kundli — Google Sheet → Supabase hourly sync.
 *
 * Paste this into the orders sheet: Extensions → Apps Script → replace Code.gs.
 * Companion schema: sheet_orders_schema.sql (run it in the Supabase SQL Editor first).
 *
 * SETUP
 *   1. Project Settings → Script Properties → add:
 *        SUPABASE_URL          https://<ref>.supabase.co
 *        SUPABASE_SERVICE_KEY  the LEGACY service_role key, from Supabase → Project
 *                              Settings → API Keys → Legacy. Take the one labelled
 *                              "service_role", NOT "anon" — both are JWTs starting with
 *                              "eyJ" and are indistinguishable by eye. _config_ decodes
 *                              the role claim and rejects the wrong one.
 *      Never hardcode the key here. service_role bypasses Row Level Security, so
 *      anyone with it has full read/write on the database. Script Properties keep it
 *      out of the source and out of git.
 *
 *      It must be the legacy JWT, NOT one of the newer "sb_secret_..." keys. Secret
 *      keys refuse any request whose User-Agent looks like a browser, and UrlFetchApp
 *      always sends "Mozilla/5.0 (compatible; Google-Apps-Script; ...)" — which matches.
 *      Apps Script strips any User-Agent you try to set, so this is unfixable from here:
 *      an sb_secret key can never work in this script. It fails as
 *        401 {"message":"Forbidden use of secret API key in browser"}
 *      whose hint tells you to delete the key. Ignore that — nothing leaked, the request
 *      just came from Google's servers. Swap in the legacy JWT instead.
 *      If Supabase ever retires legacy keys, the way out is an Edge Function holding the
 *      secret key, called from here with a publishable key.
 *   2. Run syncToSupabase() once by hand and accept the OAuth prompt. With no cursor
 *      set yet this backfills every existing row.
 *   3. Run setupHourlyTrigger() once. From then on it syncs new rows every hour.
 *
 * DEDUP
 *   Two independent mechanisms, on purpose:
 *     - A row cursor in Script Properties, so an hourly run only reads new rows.
 *     - row_hash (SHA-256 of the row's displayed cells) with a UNIQUE constraint,
 *       POSTed with Prefer: resolution=ignore-duplicates.
 *   The cursor makes it fast; the hash makes it safe. A lost cursor, a retried batch,
 *   or a manual re-run can't duplicate anything.
 *   Caveat: editing an already-synced row changes its hash, so it lands as a NEW row.
 *
 * OTHER FUNCTIONS
 *   resetCursor()        — forces a full re-scan on the next sync (safe; hash dedups).
 *   setupHourlyTrigger() — idempotent; re-running won't stack duplicate triggers.
 */

var SHEET_GID = 0;
var HEADER_ROW = 1;
var BATCH_SIZE = 500;
var TABLE = 'sheet_orders';
var CURSOR_KEY = 'LAST_SYNCED_ROW';

// Pinned rather than Session.getScriptTimeZone() so order_at can't silently shift
// if someone changes the script's timezone setting.
var TZ = 'Asia/Kolkata';
var TZ_OFFSET = '+05:30';

/**
 * Sheet header (normalized: lowercased, non-alphanumerics stripped) → target column.
 * Normalizing is what lets the sheet's inconsistent casing/spacing ("Utm Medium",
 * "utm content", "UTM Term") map cleanly, and survives later header re-spacing.
 *
 * type drives parsing: 'date' and 'time' and 'number' columns also get a *_raw text
 * column holding the sheet's original display string, so a parse miss loses nothing.
 */
var COLUMN_MAP = {
  orderid:          { col: 'order_id',           type: 'text' },  // Razorpay id; joins kundli_orders.order_id
  orderdate:        { col: 'order_date',         type: 'date' },
  ordertime:        { col: 'order_time',         type: 'time' },
  name:             { col: 'name',               type: 'text' },
  phone:            { col: 'phone',              type: 'text' },
  email:            { col: 'email',              type: 'text' },
  placeofbirth:     { col: 'place_of_birth',     type: 'text' },
  longitude:        { col: 'longitude',          type: 'number' },
  latitude:         { col: 'latitude',           type: 'number' },
  dateofbirth:      { col: 'date_of_birth',      type: 'date' },
  timeofbirth:      { col: 'time_of_birth',      type: 'time' },
  gender:           { col: 'gender',             type: 'text' },
  state:            { col: 'state',              type: 'text' },
  pincode:          { col: 'pin_code',           type: 'text' },
  reportlanguage:   { col: 'report_language',    type: 'text' },
  reportname:       { col: 'report_name',        type: 'text' },
  ordertotalamount: { col: 'order_total_amount', type: 'number' },
  addonsname:       { col: 'addons_name',        type: 'text' },
  paymentstatus:    { col: 'payment_status',     type: 'text' },
  utmid:            { col: 'utm_id',             type: 'text' },
  utmsource:        { col: 'utm_source',         type: 'text' },
  utmcampaign:      { col: 'utm_campaign',       type: 'text' },
  utmmedium:        { col: 'utm_medium',         type: 'text' },
  utmcontent:       { col: 'utm_content',        type: 'text' },
  utmterm:          { col: 'utm_term',           type: 'text' }
};

var MONTHS = {
  jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6,
  jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12
};

// ---------------------------------------------------------------------------
// Entry points
// ---------------------------------------------------------------------------

/** Trigger target. Pushes every sheet row after the cursor to Supabase. */
function syncToSupabase() {
  // An hourly tick must never overlap a still-running backfill, or both would read
  // the same cursor and POST the same rows (harmless thanks to row_hash, but wasteful).
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) {
    Logger.log('Another sync is already running; skipping this run.');
    return;
  }

  try {
    var cfg = _config_();
    var sheet = _getSheetByGid_(SHEET_GID);
    var lastRow = sheet.getLastRow();
    var lastCol = sheet.getLastColumn();

    var props = PropertiesService.getScriptProperties();
    var cursor = Number(props.getProperty(CURSOR_KEY) || HEADER_ROW);
    // A cursor past the end means rows were deleted; re-scan rather than sit stuck.
    if (cursor > lastRow) {
      Logger.log('Cursor %s is past last row %s (rows deleted?); rescanning from the top.', cursor, lastRow);
      cursor = HEADER_ROW;
    }

    var startRow = Math.max(cursor + 1, HEADER_ROW + 1);
    if (startRow > lastRow) {
      Logger.log('No new rows (cursor=%s, lastRow=%s).', cursor, lastRow);
      return;
    }

    var fields = _mapHeaders_(sheet, lastCol);
    var numRows = lastRow - startRow + 1;
    var range = sheet.getRange(startRow, 1, numRows, lastCol);
    // Typed values parse cleanly (Sheets hands back real Date objects and numbers);
    // display values are exactly what a human sees, which is what we hash and keep
    // in the *_raw columns.
    var values = range.getValues();
    var display = range.getDisplayValues();

    var rows = [];
    for (var i = 0; i < values.length; i++) {
      var row = _buildRow_(values[i], display[i], fields, startRow + i);
      if (row) rows.push(row);
    }

    if (!rows.length) {
      Logger.log('Rows %s-%s are all blank; advancing cursor.', startRow, lastRow);
      props.setProperty(CURSOR_KEY, String(lastRow));
      return;
    }

    for (var start = 0; start < rows.length; start += BATCH_SIZE) {
      _postBatch_(cfg, rows.slice(start, start + BATCH_SIZE));
    }

    // Only advance after every batch lands. A throw above leaves the cursor alone so
    // the next hourly run retries the same rows.
    props.setProperty(CURSOR_KEY, String(lastRow));
    Logger.log('Synced %s row(s) (sheet rows %s-%s).', rows.length, startRow, lastRow);
  } finally {
    lock.releaseLock();
  }
}

/** Run once. Installs the hourly trigger, replacing any it already made. */
function setupHourlyTrigger() {
  var existing = ScriptApp.getProjectTriggers();
  for (var i = 0; i < existing.length; i++) {
    if (existing[i].getHandlerFunction() === 'syncToSupabase') {
      ScriptApp.deleteTrigger(existing[i]);
    }
  }
  ScriptApp.newTrigger('syncToSupabase').timeBased().everyHours(1).create();
  Logger.log('Hourly trigger installed for syncToSupabase.');
}

/** Clears the cursor so the next sync re-scans every row. row_hash prevents duplicates. */
function resetCursor() {
  PropertiesService.getScriptProperties().deleteProperty(CURSOR_KEY);
  Logger.log('Cursor cleared. The next syncToSupabase() will re-scan the whole sheet.');
}

// ---------------------------------------------------------------------------
// Internals
// ---------------------------------------------------------------------------

function _config_() {
  var props = PropertiesService.getScriptProperties();
  var url = props.getProperty('SUPABASE_URL');
  var key = props.getProperty('SUPABASE_SERVICE_KEY');
  if (!url || !key) {
    throw new Error(
      'Missing Script Properties. Add SUPABASE_URL and SUPABASE_SERVICE_KEY under ' +
      'Project Settings → Script Properties.'
    );
  }
  _assertServiceRoleKey_(key);
  return { url: url.replace(/\/+$/, ''), key: key };
}

/**
 * Reject the two wrong keys up front, while the error can still name the cause.
 *
 * Both legacy keys are JWTs beginning with "eyJ", so anon looks exactly like service_role
 * until PostgREST reads its role claim. Without this check the anon key fails 400 rows later
 * as 42501 "permission denied for table sheet_orders", and Postgres helpfully suggests
 * GRANT SELECT, INSERT ON public.sheet_orders TO anon — which would hand the table to anyone
 * holding the publishable key. An error that talks you into a security hole is worth
 * pre-empting.
 */
function _assertServiceRoleKey_(key) {
  if (key.indexOf('sb_secret_') === 0) {
    throw new Error(
      'SUPABASE_SERVICE_KEY is an "sb_secret_..." key, which can never work from Apps Script: ' +
      'secret keys reject browser-looking User-Agents and UrlFetchApp\'s cannot be changed. ' +
      'Use the LEGACY service_role JWT (Supabase → Project Settings → API Keys → Legacy).'
    );
  }
  var role = _jwtRole_(key);
  if (role && role !== 'service_role') {
    throw new Error(
      'SUPABASE_SERVICE_KEY is the "' + role + '" key, not service_role. Writing needs ' +
      'service_role (Supabase → Project Settings → API Keys → Legacy). Do NOT grant ' +
      'privileges to ' + role + ' instead — that key is public.'
    );
  }
}

/** JWT payload role claim, or null if the key isn't a decodable JWT (then let the API answer). */
function _jwtRole_(key) {
  var parts = String(key).split('.');
  if (parts.length !== 3) return null;
  try {
    var json = Utilities.newBlob(Utilities.base64DecodeWebSafe(parts[1])).getDataAsString();
    return JSON.parse(json).role || null;
  } catch (e) {
    return null;
  }
}

/** Resolve the tab by gid, not name, so renaming the tab doesn't break the sync. */
function _getSheetByGid_(gid) {
  var sheets = SpreadsheetApp.getActive().getSheets();
  for (var i = 0; i < sheets.length; i++) {
    if (sheets[i].getSheetId() === gid) return sheets[i];
  }
  throw new Error('No sheet with gid ' + gid + ' in this spreadsheet.');
}

function _normalizeHeader_(header) {
  return String(header || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

/** Column index → field spec. Logs anything unrecognized or missing. */
function _mapHeaders_(sheet, lastCol) {
  var headers = sheet.getRange(HEADER_ROW, 1, 1, lastCol).getDisplayValues()[0];
  var fields = {};
  var seen = {};

  for (var i = 0; i < headers.length; i++) {
    var key = _normalizeHeader_(headers[i]);
    if (!key) continue;
    if (COLUMN_MAP[key]) {
      fields[i] = COLUMN_MAP[key];
      seen[key] = true;
    } else {
      Logger.log('Ignoring unmapped column "%s".', headers[i]);
    }
  }

  var missing = Object.keys(COLUMN_MAP).filter(function (k) { return !seen[k]; });
  if (missing.length) {
    Logger.log('WARNING: expected columns not found in the header row: %s', missing.join(', '));
  }
  if (!Object.keys(fields).length) {
    throw new Error('No known columns found in row ' + HEADER_ROW + '. Is HEADER_ROW correct?');
  }
  return fields;
}

/** One sheet row → one Supabase row object. Returns null for blank rows. */
function _buildRow_(values, display, fields, sheetRow) {
  var isBlank = display.every(function (cell) { return _asText_(cell) === null; });
  if (isBlank) return null;

  var row = {
    row_hash: _rowHash_(display),
    sheet_row: sheetRow
  };

  for (var idx in fields) {
    var field = fields[idx];
    var typed = values[idx];
    var shown = display[idx];
    var raw = _asText_(shown);

    if (field.type === 'text') {
      row[field.col] = _asText_(typed);
    } else if (field.type === 'date') {
      row[field.col] = _parseDate_(typed, raw);
      row[field.col + '_raw'] = raw;
    } else if (field.type === 'time') {
      row[field.col] = _parseTime_(typed, raw);
      row[field.col + '_raw'] = raw;
    } else if (field.type === 'number') {
      row[field.col] = _parseNumber_(typed, raw);
      row[field.col + '_raw'] = raw;
    }
  }

  row.order_at = _combineDateTime_(row.order_date, row.order_time);
  return row;
}

/** SHA-256 over the row's displayed cells — stable, and matches what a human sees. */
function _rowHash_(display) {
  // Joined with an explicit unit separator so field boundaries cannot collide:
  // ['ab','c'] and ['a','bc'] must hash differently. Written as the \u001F escape,
  // never a literal control character — an editor that strips those would silently
  // change every hash and re-insert the whole sheet as duplicates.
  var joined = display.map(function (cell) { return String(cell == null ? '' : cell); }).join('\u001F');
  var bytes = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, joined, Utilities.Charset.UTF_8);
  var hex = '';
  for (var i = 0; i < bytes.length; i++) {
    // Apps Script bytes are signed; mask back to 0-255 before hexing.
    var b = (bytes[i] + 256) % 256;
    hex += (b < 16 ? '0' : '') + b.toString(16);
  }
  return hex;
}

/**
 * Cell → trimmed string, or null when empty. Guards the two ways Sheets mangles an
 * identifier typed as a number: scientific notation on big values, and Date objects.
 */
function _asText_(value) {
  if (value === null || value === undefined) return null;
  if (value instanceof Date) {
    if (isNaN(value.getTime())) return null;
    return Utilities.formatDate(value, TZ, 'yyyy-MM-dd HH:mm:ss');
  }
  var text;
  if (typeof value === 'number') {
    if (!isFinite(value)) return null;
    // toFixed(0) keeps an id-like integer (phone, pin) out of the exponent notation
    // String() produces. Values >= 1e21 exponentiate anyway, but no phone or pin is
    // remotely near that.
    text = Number.isInteger(value) && Math.abs(value) < 1e21 ? value.toFixed(0) : String(value);
  } else {
    text = String(value);
  }
  text = text.trim();
  return text === '' ? null : text;
}

/**
 * → 'yyyy-MM-dd' or null.
 * Bare numeric dates are read as DAY-first (15/08/1990), the Indian convention. An
 * ambiguous value like 05/08/1990 is therefore 5 August, not 8 May — check
 * date_of_birth_raw if a row ever looks wrong.
 */
function _parseDate_(typed, raw) {
  if (typed instanceof Date && !isNaN(typed.getTime())) {
    return Utilities.formatDate(typed, TZ, 'yyyy-MM-dd');
  }
  if (!raw) return null;

  var m = raw.match(/^(\d{4})[-\/.](\d{1,2})[-\/.](\d{1,2})/);
  if (m) return _ymd_(Number(m[1]), Number(m[2]), Number(m[3]));

  m = raw.match(/^(\d{1,2})[-\/.](\d{1,2})[-\/.](\d{2,4})/);
  if (m) {
    var year = Number(m[3]);
    if (year < 100) year += year < 50 ? 2000 : 1900;
    return _ymd_(year, Number(m[2]), Number(m[1]));
  }

  // "15 Aug 1990" / "15 August 1990"
  m = raw.match(/^(\d{1,2})[\s-]+([A-Za-z]{3,})[\s,-]+(\d{4})/);
  if (m) {
    var month = MONTHS[m[2].slice(0, 3).toLowerCase()];
    if (month) return _ymd_(Number(m[3]), month, Number(m[1]));
  }

  // "Aug 15, 1990"
  m = raw.match(/^([A-Za-z]{3,})[\s-]+(\d{1,2})[\s,-]+(\d{4})/);
  if (m) {
    var mon = MONTHS[m[1].slice(0, 3).toLowerCase()];
    if (mon) return _ymd_(Number(m[3]), mon, Number(m[2]));
  }

  Logger.log('Unparseable date: "%s" (kept in the _raw column).', raw);
  return null;
}

function _ymd_(year, month, day) {
  if (!year || !month || !day || month > 12 || day > 31) return null;
  return year + '-' + _pad2_(month) + '-' + _pad2_(day);
}

/** → 'HH:mm:ss' or null. Handles 24h, 12h with am/pm, and real Date cells. */
function _parseTime_(typed, raw) {
  if (typed instanceof Date && !isNaN(typed.getTime())) {
    return Utilities.formatDate(typed, TZ, 'HH:mm:ss');
  }
  if (!raw) return null;

  var m = raw.match(/(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp])?\.?\s*[Mm]?\.?/);
  if (!m) {
    Logger.log('Unparseable time: "%s" (kept in the _raw column).', raw);
    return null;
  }

  var hour = Number(m[1]);
  var minute = Number(m[2]);
  var second = m[3] ? Number(m[3]) : 0;
  var meridiem = m[4] ? m[4].toLowerCase() : null;

  if (meridiem === 'p' && hour < 12) hour += 12;
  if (meridiem === 'a' && hour === 12) hour = 0;
  if (hour > 23 || minute > 59 || second > 59) return null;

  return _pad2_(hour) + ':' + _pad2_(minute) + ':' + _pad2_(second);
}

/** → number or null. Tolerates currency symbols, thousands separators, stray text. */
function _parseNumber_(typed, raw) {
  if (typeof typed === 'number' && !isNaN(typed)) return typed;
  if (!raw) return null;

  // Match the number rather than stripping the non-digits out. Stripping turns
  // "Rs. 999" into ".999" — the abbreviation's dot survives — which parses to 0.999.
  var m = raw.match(/-?(?:\d[\d,]*(?:\.\d+)?|\.\d+)/);
  if (!m) {
    Logger.log('Unparseable number: "%s" (kept in the _raw column).', raw);
    return null;
  }

  var num = parseFloat(m[0].replace(/,/g, ''));
  if (isNaN(num)) {
    Logger.log('Unparseable number: "%s" (kept in the _raw column).', raw);
    return null;
  }
  return num;
}

/** 'yyyy-MM-dd' + 'HH:mm:ss' → IST timestamptz. Missing time means midnight. */
function _combineDateTime_(date, time) {
  if (!date) return null;
  return date + 'T' + (time || '00:00:00') + TZ_OFFSET;
}

function _pad2_(n) {
  return (n < 10 ? '0' : '') + n;
}

function _postBatch_(cfg, rows) {
  // ignore-duplicates + the unique row_hash is what makes a retry or a manual re-run
  // a no-op instead of a pile of duplicate rows.
  var url = cfg.url + '/rest/v1/' + TABLE + '?on_conflict=row_hash';
  var response = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    headers: {
      apikey: cfg.key,
      Authorization: 'Bearer ' + cfg.key,
      Prefer: 'return=minimal,resolution=ignore-duplicates'
    },
    payload: JSON.stringify(rows),
    muteHttpExceptions: true
  });

  var code = response.getResponseCode();
  if (code < 200 || code >= 300) {
    // Throwing leaves the cursor unmoved, so the next run retries these rows.
    throw new Error('Supabase POST failed (' + code + '): ' + response.getContentText());
  }
}
