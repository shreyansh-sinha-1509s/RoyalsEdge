import fs from 'node:fs';
import readline from 'node:readline';
import { parse as parseSync } from 'csv-parse/sync';

const NULL_TOKENS = new Set(['', 'NaN', 'nan', 'NULL', 'null', 'Infinity', '-Infinity']);

/**
 * Normalizes a raw CSV cell while preserving literal "None" (Phase 3 cricket rule).
 */
export function cleanCell(value) {
  if (value === undefined || value === null) return null;
  const str = String(value).trim();
  if (NULL_TOKENS.has(str)) return null;
  return str;
}

export function toNullableInt(value) {
  const s = cleanCell(value);
  if (s === null) return null;
  const num = Number(s);
  if (!Number.isFinite(num)) return null;
  return Math.trunc(num);
}

export function toInt(value, fallback = 0) {
  const n = toNullableInt(value);
  return n === null ? fallback : n;
}

export function toNullableFloat(value) {
  const s = cleanCell(value);
  if (s === null) return null;
  const num = Number(s);
  if (!Number.isFinite(num)) return null;
  return num;
}

export function toFloat(value, fallback = 0) {
  const n = toNullableFloat(value);
  return n === null ? fallback : n;
}

export function toNullableBool(value) {
  const s = cleanCell(value);
  if (s === null) return null;
  const low = s.toLowerCase();
  if (low === 'true' || low === '1' || low === 'yes') return true;
  if (low === 'false' || low === '0' || low === 'no') return false;
  return null;
}

export function toBool(value, fallback = false) {
  const b = toNullableBool(value);
  return b === null ? fallback : b;
}

export function toDate(value) {
  const s = cleanCell(value);
  if (s === null) return null;
  const dt = new Date(`${s}T00:00:00.000Z`);
  if (Number.isNaN(dt.getTime())) {
    const parsed = new Date(s);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  return dt;
}

/**
 * Validates that a CSV file exists and contains all required column headers.
 */
export function validateCsvHeaders(filePath, requiredHeaders) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`Required source CSV missing: ${filePath}`);
  }
  const fd = fs.openSync(filePath, 'r');
  try {
    const buf = Buffer.alloc(65536);
    const bytesRead = fs.readSync(fd, buf, 0, buf.length, 0);
    const snippet = buf.toString('utf8', 0, bytesRead);
    const firstLineEnd = snippet.indexOf('\n');
    const headerLine = (firstLineEnd === -1 ? snippet : snippet.slice(0, firstLineEnd)).replace(/^\uFEFF/, '');
    const [headers] = parseSync(headerLine, { relax_quotes: true });
    const headerSet = new Set(headers.map((h) => h.trim()));
    const missing = requiredHeaders.filter((req) => !headerSet.has(req));
    if (missing.length > 0) {
      throw new Error(`CSV header validation failed for ${filePath}. Missing columns: ${missing.join(', ')}`);
    }
    return headers;
  } finally {
    fs.closeSync(fd);
  }
}

/**
 * Reads a standard analytical CSV (<=15k rows) into an array of keyed objects.
 */
export function readCsvRecords(filePath, requiredHeaders = []) {
  if (requiredHeaders.length > 0) {
    validateCsvHeaders(filePath, requiredHeaders);
  } else if (!fs.existsSync(filePath)) {
    throw new Error(`Required source CSV missing: ${filePath}`);
  }

  const raw = fs.readFileSync(filePath, 'utf8');
  return parseSync(raw, {
    columns: true,
    bom: true,
    skip_empty_lines: true,
    trim: false,
  });
}

/**
 * Streams a large CSV (e.g., 193,988-row pressure_deliveries.csv) using raw row arrays
 * with pre-resolved column indices. Uses fast split for unquoted lines and full RFC-4180
 * csv-parse fallback whenever a line contains quotes.
 */
export async function streamCsvIndexed(filePath, requiredHeaders, onRow) {
  validateCsvHeaders(filePath, requiredHeaders);
  let rowIndex = 0;
  let colIdx = null;

  const rl = readline.createInterface({
    input: fs.createReadStream(filePath, { encoding: 'utf8', highWaterMark: 256 * 1024 }),
    crlfDelay: Infinity,
  });

  for await (const rawLine of rl) {
    if (!rawLine) continue;
    if (colIdx === null) {
      const cleanHeader = rawLine.replace(/^\uFEFF/, '');
      const [headers] = parseSync(cleanHeader, { relax_quotes: true });
      colIdx = {};
      for (let i = 0; i < headers.length; i += 1) {
        colIdx[headers[i].trim()] = i;
      }
      continue;
    }
    const row = rawLine.includes('"') ? parseSync(rawLine, { relax_quotes: true })[0] : rawLine.split(',');
    rowIndex += 1;
    onRow(row, colIdx, rowIndex);
  }

  return rowIndex;
}

