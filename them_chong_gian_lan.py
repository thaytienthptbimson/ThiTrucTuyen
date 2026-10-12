#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vá tính năng CHỐNG GIAN LẬN vào index.html (Hệ thống Thi & Ôn luyện Trắc nghiệm).
Dùng:  python them_chong_gian_lan.py index.html   ->  tạo index_chong_gian_lan.html
(Mỗi vị trí vá được kiểm tra đúng 1 lần; sai file thì dừng, không ghi gì.)"""
import io, sys

CSS = r'''
#pg-cam-box{position:fixed;right:12px;bottom:calc(12px + env(safe-area-inset-bottom));z-index:60;width:132px;background:#0f172a;color:#fff;border-radius:10px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.35);font-size:11px;text-align:center}
#pg-cam{display:block;width:100%;height:auto;transform:scaleX(-1);background:#000}
#pg-st{padding:3px 4px}
'''

HTML_OVERLAY = r'''<div id="pg" class="overlay hide" style="z-index:200;background:rgba(15,23,42,.96)">
  <div class="box">
    <div class="ic">⚠️</div>
    <h2 id="pg-title" style="margin:0 0 8px"></h2>
    <p id="pg-msg"></p>
    <button class="btn" id="pg-btn" type="button">Quay lại làm bài</button>
  </div>
</div>
<div id="pg-cam-box" class="hide"><video id="pg-cam" muted playsinline autoplay></video><div id="pg-st">📷 Camera đang bật</div></div>
<div id="toast" class="toast hide" role="status"></div>'''

HTML_TEACHER = r'''<div class="sch-box" style="margin:15px 0 0">
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer;margin:0;font-weight:600"><input type="checkbox" id="chk-proctor"> 🛡 Chống gian lận: bắt buộc toàn màn hình + camera, ghi nhận khi rời màn hình</label>
          <div><label for="max-viol">Vi phạm tối đa trước khi tự nộp (0 = chỉ ghi nhận)</label><input type="number" id="max-viol" min="0" style="width:120px;margin:0"></div>
        </div>
        <div class="sch-box">'''

NOTE = r'''<div id="s-pg-note" class="sch-state wait hide">📷 Bài thi có giám sát: em cần cho phép camera và làm bài ở chế độ toàn màn hình. Rời màn hình, chuyển tab hoặc ra khỏi khung camera sẽ bị ghi nhận và có thể bị tự động nộp bài.</div>'''

PG_JS = r'''

// ===================== CHỐNG GIAN LẬN: toàn màn hình + camera + rời màn hình =====================
const pgMax = () => exam.maxViol == null ? 3 : exam.maxViol;
const pgFsOk = () => !!(document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen);
const pgIsFs = () => !!(document.fullscreenElement || document.webkitFullscreenElement);
const pgCamOk = () => !!PG.stream && PG.stream.getVideoTracks().some(t => t.readyState === 'live');
const pgOk = () => (!pgFsOk() || pgIsFs()) && pgCamOk() && !document.hidden;
const pgFsReq = () => {
  const d = document.documentElement, f = d.requestFullscreen || d.webkitRequestFullscreen;
  return f ? Promise.resolve(f.call(d)).catch(() => {}) : Promise.resolve();
};

async function pgCam() {
  if (pgCamOk()) return true;
  try {
    PG.stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240, facingMode: 'user' }, audio: false });
    const v = $('pg-cam'); v.srcObject = PG.stream;
    $('pg-cam-box').classList.remove('hide');
    PG.stream.getVideoTracks()[0].onended = () => pgViol('Camera bị tắt hoặc mất kết nối');
    try { await v.play(); } catch (e) {}
    return true;
  } catch (e) { return false; }
}

// Gọi ngay khi học sinh bấm "Bắt đầu làm bài" (phải có thao tác bấm thì trình duyệt mới cho toàn màn hình)
async function pgStart() {
  if (PG.busy) return false;
  PG.busy = 1;
  const fs = pgFsReq();
  const cam = await pgCam();
  await fs;
  PG.busy = 0;
  if (cam && (!pgFsOk() || pgIsFs())) return true;
  showToast(cam ? 'Không bật được chế độ toàn màn hình. Hãy thử lại.' : 'Không bật được camera. Hãy cho phép camera cho trang này (phải mở bằng https) rồi bấm lại.', 8000);
  pgStop(true);
  return false;
}

function pgStop(force) {
  const was = PG.on;
  PG.on = 0; clearInterval(PG.tm);
  if (PG.stream) { PG.stream.getTracks().forEach(t => { t.onended = null; t.stop(); }); PG.stream = null; }
  $('pg-cam-box').classList.add('hide'); $('pg').classList.add('hide');
  if ((was || force) && pgIsFs()) { try { (document.exitFullscreen || document.webkitExitFullscreen).call(document); } catch (e) {} }
}

function pgBegin(sv) {
  PG.on = 1; PG.last = 0; PG.none = PG.many = PG.lostF = PG.manyF = 0;
  PG.viol = (sv && sv.viol) || [];
  pgDetectInit();
  clearInterval(PG.tm); PG.tm = setInterval(pgTick, 1000);
  // Tải lại trang: tính 1 lần vi phạm, bắt buộc bấm tiếp tục để bật lại camera + toàn màn hình
  if (sv) pgViol('Tải lại trang hoặc mở lại bài thi');
}

async function pgDetectInit() {
  if (PG.det) return;
  try {
    const V = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14';
    const M = await import(V + '/vision_bundle.mjs');
    const fs = await M.FilesetResolver.forVisionTasks(V + '/wasm');
    PG.det = await M.FaceDetector.createFromOptions(fs, {
      baseOptions: { modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite' },
      runningMode: 'VIDEO', minDetectionConfidence: 0.5
    });
  } catch (e) { PG.det = null; } // không tải được thư viện: chỉ giám sát camera bật/tắt, không phạt oan
}

function pgTick() {
  const v = $('pg-cam');
  if (!PG.on || submitted || !PG.det || document.hidden || !v.videoWidth) return;
  let n;
  try { n = PG.det.detectForVideo(v, performance.now()).detections.length; } catch (e) { return; }
  $('pg-st').textContent = n === 0 ? '⚠ Không thấy mặt' : n > 1 ? '⚠ Có nhiều người' : '✔ Bình thường';
  if (n === 0) { if (++PG.none >= 5 && !PG.lostF) { PG.lostF = 1; pgViol('Không thấy thí sinh trong khung camera'); } } else { PG.none = 0; PG.lostF = 0; }
  if (n > 1) { if (++PG.many >= 3 && !PG.manyF) { PG.manyF = 1; pgViol('Phát hiện nhiều hơn 1 người trong khung camera'); } } else { PG.many = 0; PG.manyF = 0; }
}

function pgShow(reason) {
  const max = pgMax(), n = PG.viol.length, fin = max && n > max;
  $('pg-title').textContent = fin ? '⛔ Vượt quá số lần vi phạm' : '⚠️ Cảnh báo vi phạm ' + n + (max ? '/' + max : '');
  $('pg-msg').textContent = fin
    ? reason + '. Hệ thống đang tự động nộp bài của em.'
    : reason + '. Mọi vi phạm đều được ghi lại và gửi cho giáo viên. Bấm nút bên dưới để tiếp tục làm bài.';
  $('pg-btn').classList.toggle('hide', !!fin);
  $('pg').classList.remove('hide');
}

function pgViol(reason) {
  if (!PG.on || PG.mute || submitted || !examRunning) return;
  const now = Date.now();
  if (now - PG.last < 2000) return; // 1 sự cố có thể bắn nhiều sự kiện (blur + đổi tab + thoát toàn màn hình)
  PG.last = now;
  PG.viol.push({ t: now, r: reason });
  saveProg();
  pgShow(reason);
  if (pgMax() && PG.viol.length > pgMax()) { clearInterval(timerInterval); processSubmission(); }
}

document.addEventListener('visibilitychange', () => { if (document.hidden) pgViol('Chuyển tab hoặc thu nhỏ cửa sổ'); });
window.addEventListener('blur', () => pgViol('Rời khỏi cửa sổ làm bài'));
['fullscreenchange', 'webkitfullscreenchange'].forEach(ev => document.addEventListener(ev, () => {
  if (pgFsOk() && !pgIsFs()) pgViol('Thoát chế độ toàn màn hình');
}));
$('pg-btn').onclick = async () => {
  PG.mute = 1;
  await pgFsReq(); await pgCam();
  PG.mute = 0; PG.last = Date.now();
  if (pgOk()) $('pg').classList.add('hide');
  else $('pg-msg').textContent = pgCamOk() ? 'Chưa vào được toàn màn hình. Hãy bấm lại nút bên dưới.' : 'Camera chưa hoạt động. Hãy cho phép camera cho trang này rồi bấm lại.';
};
'''

P = []
def add(old, new): P.append((old, new))

# --- giao diện ---
add('</style>', CSS + '</style>')
add('<div id="toast" class="toast hide" role="status"></div>', HTML_OVERLAY)
add('<div class="sch-box">', HTML_TEACHER)
add('<div id="s-schedule" class="sch-state hide"></div>', '<div id="s-schedule" class="sch-state hide"></div>\n    ' + NOTE)
# --- trạng thái + lưu cài đặt đề ---
add("let examEndAt = Infinity, examRunning = false;",
    "let examEndAt = Infinity, examRunning = false;\nconst PG = { on: 0, mute: 0, busy: 0, viol: [], stream: null, det: null, tm: null, last: 0, none: 0, many: 0, lostF: 0, manyF: 0 };")
add("shufGrp: !!x.shufGrp, shufQ: x.shufQ !== false, shufOpt: x.shufOpt !== false",
    "shufGrp: !!x.shufGrp, shufQ: x.shufQ !== false, shufOpt: x.shufOpt !== false, proctor: !!x.proctor, maxViol: x.maxViol == null ? 3 : Math.max(0, parseInt(x.maxViol) || 0)")
add("$('chk-shuf-opt').checked = exam.shufOpt !== false;",
    "$('chk-shuf-opt').checked = exam.shufOpt !== false;\n    $('chk-proctor').checked = !!exam.proctor; $('max-viol').value = exam.maxViol == null ? 3 : exam.maxViol;")
add("exam.shufOpt = $('chk-shuf-opt').checked;",
    "exam.shufOpt = $('chk-shuf-opt').checked;\n        exam.proctor = $('chk-proctor').checked; exam.maxViol = Math.max(0, parseInt($('max-viol').value) || 0);")
add("ex.shufOpt=old.shufOpt!==false; }", "ex.shufOpt=old.shufOpt!==false; ex.proctor=!!old.proctor; ex.maxViol=old.maxViol; }")
# --- luồng học sinh ---
add("$('sf').onsubmit = (e) => {", "$('sf').onsubmit = async (e) => {")
add("studentData.class = $('s-class').value.trim();",
    "studentData.class = $('s-class').value.trim();\n        if(exam.proctor && !(await pgStart())) return;")
add("$('s-exam-name').textContent = exam.name;",
    "$('s-exam-name').textContent = exam.name;\n    $('s-pg-note').classList.toggle('hide', !exam.proctor);")
add("examRunning = true;", "examRunning = true;\n    if(exam.proctor) pgBegin(sv);")
add("endAt: isFinite(examEndAt) ? examEndAt : 0 }", "endAt: isFinite(examEndAt) ? examEndAt : 0, viol: PG.viol }")
add("if(confirm(un ?", "PG.mute = 1; const okc = confirm(un ?")
add("'Bạn có chắc chắn muốn nộp bài?')) {", "'Bạn có chắc chắn muốn nộp bài?'); PG.mute = 0;\n    if(okc) {")
add("alert('Đã hết thời gian làm bài (hoặc đã đến giờ đóng đề)! Hệ thống tự động nộp bài.');",
    "PG.mute = 1; alert('Đã hết thời gian làm bài (hoặc đã đến giờ đóng đề)! Hệ thống tự động nộp bài.');")
add("$('list-student').style.pointerEvents = 'none';", "pgStop(); $('list-student').style.pointerEvents = 'none';")
add("tf_qs: tfQuestions,",
    "tf_qs: tfQuestions, violations: PG.viol.length, viol_log: PG.viol.map(v => new Date(v.t).toLocaleTimeString('vi-VN') + ' ' + v.r).join(' | '),")
add("if(isFinite(examEndAt) && examEndAt - nowMs() > 0) runTimer();",
    "PG.mute = 0; if(isFinite(examEndAt) && examEndAt - nowMs() > 0) runTimer();")
add("try { if (document.fullscreenElement) await document.exitFullscreen(); } catch (e) {}",
    "try { if (document.fullscreenElement && !PG.on) await document.exitFullscreen(); } catch (e) {}")


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 1
    src = sys.argv[1]
    s = io.open(src, encoding='utf-8-sig').read()
    if 'pgStart' in s:
        print('File này đã được vá chống gian lận rồi.'); return 1
    bad = [(i, o) for i, (o, _) in enumerate(P, 1) if s.count(o) != 1]
    if bad:
        for i, o in bad:
            print('Không vá được mục %d (tìm thấy %d vị trí): %s' % (i, s.count(o), o[:70]))
        print('Có vẻ đây không phải đúng bản index.html đã gửi. Chưa ghi gì cả.'); return 1
    for o, n in P:
        s = s.replace(o, n, 1)
    k = s.rfind('</script>')
    if k < 0:
        print('Không tìm thấy thẻ </script> cuối file.'); return 1
    s = s[:k] + PG_JS + s[k:]
    out = (src.rsplit('.', 1)[0] if '.' in src else src) + '_chong_gian_lan.html'
    io.open(out, 'w', encoding='utf-8', newline='\n').write(s)
    print('Xong! Đã tạo:', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
