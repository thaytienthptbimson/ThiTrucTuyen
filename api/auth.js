const crypto = require('crypto');

const SALT = 'egp_bimson_2026_salt:';
// Mã băm SHA-256 mặc định (không lưu mật khẩu văn bản thuần trong mã nguồn)
const DEFAULT_HASH = '879cbc72fee92d5b3b1d60fbb00c7155dbd8aa8cac8f18adc02b4eee73d5e932';

module.exports = (req, res) => {
  res.setHeader('Cache-Control', 'no-store, max-age=0');
  if (req.method !== 'POST') {
    return res.status(405).json({ ok: false, error: 'Method Not Allowed' });
  }

  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
    const inputPw = String(body.password || '').trim();
    if (!inputPw) {
      return res.status(400).json({ ok: false, error: 'Missing password' });
    }

    // Ưu tiên 1: So khớp với biến môi trường APP_PASSWORD (bật chế độ Sensitive trên Vercel Dashboard)
    const envPassword = process.env.APP_PASSWORD;
    if (envPassword && envPassword.length > 0) {
      const a = Buffer.from(inputPw, 'utf8');
      const b = Buffer.from(String(envPassword).trim(), 'utf8');
      const match = a.length === b.length && crypto.timingSafeEqual(a, b);
      return res.status(match ? 200 : 401).json({ ok: match });
    }

    // Ưu tiên 2: So khớp với mã băm SHA-256 (APP_PASSWORD_HASH hoặc DEFAULT_HASH)
    const targetHash = (process.env.APP_PASSWORD_HASH || DEFAULT_HASH).trim().toLowerCase();
    const inputHash = crypto.createHash('sha256').update(SALT + inputPw, 'utf8').digest('hex');
    const isValid = inputHash === targetHash;

    return res.status(isValid ? 200 : 401).json({ ok: isValid });
  } catch (err) {
    return res.status(500).json({ ok: false, error: 'Server error' });
  }
};
