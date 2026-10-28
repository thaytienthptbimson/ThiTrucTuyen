#!/usr/bin/env node
/*
 * prepare.js - chạy trong GitHub Actions (hoặc trên máy bạn) trước khi đóng gói.
 *
 *   node prepare.js                 Giải nén app-data.zip -> www/ (mã nguồn web) và assets/ (biểu tượng)
 *   node prepare.js android-version Ghi versionName / versionCode vào dự án Android
 *
 * Không cần thư viện ngoài: tự đọc tệp zip bằng zlib có sẵn của Node.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const ROOT = __dirname;
const mode = process.argv[2] || 'extract';

function fail(message) {
  console.error('LỖI: ' + message);
  process.exit(1);
}

/* ---------- đọc zip ---------- */

function readEntries(buf) {
  let eocd = -1;
  const lowest = Math.max(0, buf.length - 22 - 65535);
  for (let i = buf.length - 22; i >= lowest; i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) {
      eocd = i;
      break;
    }
  }
  if (eocd < 0) fail('app-data.zip không phải là tệp zip hợp lệ (có thể tệp bị tải lên chưa đủ).');

  const total = buf.readUInt16LE(eocd + 10);
  let offset = buf.readUInt32LE(eocd + 16);
  const entries = [];

  for (let n = 0; n < total; n++) {
    if (buf.readUInt32LE(offset) !== 0x02014b50) fail('Danh mục của app-data.zip bị lỗi.');
    const method = buf.readUInt16LE(offset + 10);
    const compressedSize = buf.readUInt32LE(offset + 20);
    const nameLength = buf.readUInt16LE(offset + 28);
    const extraLength = buf.readUInt16LE(offset + 30);
    const commentLength = buf.readUInt16LE(offset + 32);
    const localOffset = buf.readUInt32LE(offset + 42);
    const name = buf.toString('utf8', offset + 46, offset + 46 + nameLength);
    entries.push({ name, method, compressedSize, localOffset });
    offset += 46 + nameLength + extraLength + commentLength;
  }
  return entries;
}

function entryData(buf, entry) {
  const o = entry.localOffset;
  if (buf.readUInt32LE(o) !== 0x04034b50) fail('Tệp zip bị lỗi tại: ' + entry.name);
  const nameLength = buf.readUInt16LE(o + 26);
  const extraLength = buf.readUInt16LE(o + 28);
  const start = o + 30 + nameLength + extraLength;
  const raw = buf.subarray(start, start + entry.compressedSize);
  if (entry.method === 0) return raw;
  if (entry.method === 8) return zlib.inflateRawSync(raw);
  fail('Kiểu nén chưa hỗ trợ (' + entry.method + ') tại: ' + entry.name);
}

/* ---------- giải nén ---------- */

function extract() {
  const zipPath = path.join(ROOT, 'app-data.zip');
  if (!fs.existsSync(zipPath)) {
    fail('Không thấy app-data.zip. Hãy tải tệp này lên cùng thư mục với package.json.');
  }

  fs.rmSync(path.join(ROOT, 'www'), { recursive: true, force: true });
  fs.rmSync(path.join(ROOT, 'assets'), { recursive: true, force: true });

  const buf = fs.readFileSync(zipPath);
  let files = 0;

  for (const entry of readEntries(buf)) {
    const rel = entry.name.replace(/\\/g, '/');
    // Chỉ nhận thư mục www/ và assets/ để tránh ghi đè tệp cấu hình.
    if (!rel.startsWith('www/') && !rel.startsWith('assets/')) continue;

    const target = path.resolve(ROOT, rel);
    if (!target.startsWith(ROOT + path.sep)) fail('Đường dẫn không an toàn trong zip: ' + entry.name);

    if (rel.endsWith('/')) {
      fs.mkdirSync(target, { recursive: true });
      continue;
    }
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, entryData(buf, entry));
    files++;
  }

  flattenIfNeeded();

  const indexFile = path.join(ROOT, 'www', 'index.html');
  if (!fs.existsSync(indexFile)) {
    fail('Không thấy www/index.html. Trang chính của ứng dụng phải tên là index.html.');
  }

  // Biểu tượng cho bản Windows (electron-builder tự chuyển PNG thành ICO).
  const icon = path.join(ROOT, 'assets', 'icon-only.png');
  if (fs.existsSync(icon)) {
    fs.mkdirSync(path.join(ROOT, 'build'), { recursive: true });
    fs.copyFileSync(icon, path.join(ROOT, 'build', 'icon.png'));
  } else {
    console.warn('Cảnh báo: không có biểu tượng, sẽ dùng biểu tượng mặc định.');
  }

  console.log('Đã giải nén ' + files + ' tệp. Trang khởi động: www/index.html');
}

// Nếu cả ứng dụng nằm trong đúng một thư mục con của www/ thì đưa lên cấp trên.
function flattenIfNeeded() {
  const www = path.join(ROOT, 'www');
  if (fs.existsSync(path.join(www, 'index.html'))) return;
  const items = fs.readdirSync(www);
  if (items.length !== 1) return;
  const inner = path.join(www, items[0]);
  if (!fs.statSync(inner).isDirectory()) return;
  if (!fs.existsSync(path.join(inner, 'index.html'))) return;
  for (const name of fs.readdirSync(inner)) {
    fs.renameSync(path.join(inner, name), path.join(www, name));
  }
  fs.rmdirSync(inner);
}

/* ---------- phiên bản Android ---------- */

function androidVersion() {
  const gradle = path.join(ROOT, 'android', 'app', 'build.gradle');
  if (!fs.existsSync(gradle)) fail('Chưa có android/app/build.gradle (chạy "npx cap add android" trước).');

  const pkg = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8'));
  const code = parseInt(process.env.GITHUB_RUN_NUMBER || '1', 10) || 1;

  const original = fs.readFileSync(gradle, 'utf8');
  let text = original.replace(/(versionCode\s*=?\s*)\d+/, (m, head) => head + code);
  text = text.replace(/(versionName\s*=?\s*)"[^"]*"/, (m, head) => head + '"' + pkg.version + '"');

  if (text === original) {
    console.warn('Cảnh báo: không sửa được versionName/versionCode, giữ nguyên giá trị mặc định.');
    return;
  }
  fs.writeFileSync(gradle, text);
  console.log('Android: versionName ' + pkg.version + ', versionCode ' + code);
}

/* ---------- chạy ---------- */

if (mode === 'extract') extract();
else if (mode === 'android-version') androidVersion();
else fail('Lệnh không hợp lệ: ' + mode);
