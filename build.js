const fs = require('fs');
const path = require('path');

const srcPath = path.join(__dirname, 'index.html');
const outDir = path.join(__dirname, 'dist');
const outPath = path.join(outDir, 'index.html');

fs.mkdirSync(outDir, { recursive: true });
const html = fs.readFileSync(srcPath, 'utf8');

let JavaScriptObfuscator = null;
try {
  JavaScriptObfuscator = require('javascript-obfuscator');
} catch (e) {
  console.warn('! Không tìm thấy javascript-obfuscator, sao chép nguyên bản index.html');
}

if (JavaScriptObfuscator) {
  const obfuscatedHtml = html.replace(/<script>([\s\S]*?)<\/script>/, (match, jsCode) => {
    const obfuscationResult = JavaScriptObfuscator.obfuscate(jsCode, {
      compact: true,
      controlFlowFlattening: false,
      deadCodeInjection: false,
      stringArray: true,
      stringArrayEncoding: ['base64'],
      stringArrayThreshold: 0.75,
      splitStrings: true,
      splitStringsChunkLength: 12,
      unicodeEscapeSequence: false
    });
    return '<script>' + obfuscationResult.getObfuscatedCode() + '</script>';
  });
  fs.writeFileSync(outPath, obfuscatedHtml, 'utf8');
  console.log('✓ Đã làm rối (obfuscate) mã nguồn JavaScript và xuất ra dist/index.html');
} else {
  fs.writeFileSync(outPath, html, 'utf8');
}
