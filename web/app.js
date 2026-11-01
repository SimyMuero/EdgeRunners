/* EdgeRunners - Phase 1 前端 */
'use strict';

// 錯誤顯示（開發用：任何未捕捉的錯誤都會顯示在左下角）
function showJsError(text) {
  let box = document.getElementById('js-error');
  if (!box) {
    box = document.createElement('div');
    box.id = 'js-error';
    box.style.cssText = 'position:fixed;left:0;bottom:0;z-index:99999;background:#fde8e8;color:#a11;'
      + 'font:12px monospace;padding:8px 12px;max-width:100%;white-space:pre-wrap';
    document.body.appendChild(box);
  }
  box.textContent += text + '\n';
}

window.addEventListener('error', (e) => {
  showJsError(`${e.message} @ ${(e.filename || '').split('/').pop()}:${e.lineno}`);
});
window.addEventListener('unhandledrejection', (e) => {
  const r = e.reason;
  showJsError('REJECT: ' + (r && r.stack ? r.stack.split('\n').slice(0, 2).join(' | ') : String(r)));
});

// ---------------------------------------------------------------- 工具

const $ = (id) => document.getElementById(id);

const R_EARTH = 6371000;

function haversine(a, b) {
  // a, b: [lng, lat]
  const lat1 = a[1] * Math.PI / 180, lat2 = b[1] * Math.PI / 180;
  const dLat = (b[1] - a[1]) * Math.PI / 180;
  const dLng = (b[0] - a[0]) * Math.PI / 180;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R_EARTH * Math.asin(Math.sqrt(Math.min(1, h)));
}

function pathLength(pts) {
  let s = 0;
  for (let i = 0; i < pts.length - 1; i++) s += haversine(pts[i], pts[i + 1]);
  return s;
}

function fmtDistance(m) {
  if (!isFinite(m) || m <= 0) return '—';
  return m >= 1000 ? (m / 1000).toFixed(2) + ' km' : Math.round(m) + ' m';
}

function fmtDuration(sec) {
  if (!isFinite(sec) || sec <= 0) return '—';
  sec = Math.round(sec);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return `${h} 小時 ${m} 分`;
  if (m > 0) return `${m} 分 ${s} 秒`;
  return `${s} 秒`;
}

function fmtPace(speedMs) {
  if (!(speedMs > 0)) return '—';
  const secPerKm = 1000 / speedMs;
  const m = Math.floor(secPerKm / 60);
  const s = Math.round(secPerKm % 60);
  return `${m}'${String(s).padStart(2, '0')}"/km`;
}

function fmtCoord(v) { return Number(v).toFixed(6); }

// ---------------- HTTP 小工具 ----------------

async function getJson(path) {
  const r = await fetch(path);
  return r.json();
}

async function postJson(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  return r.json();
}

// ---- GCJ-02 -> WGS-84（與 Python 端同一演算法）----
const GCJ_A = 6378245.0;
const GCJ_EE = 0.00669342162296594323;

function outOfChina(lat, lng) {
  return !(lng > 72.004 && lng < 137.8347 && lat > 0.8293 && lat < 55.8271);
}
function tfLat(x, y) {
  let r = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
  r += (20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2 / 3;
  r += (20 * Math.sin(y * Math.PI) + 40 * Math.sin(y / 3 * Math.PI)) * 2 / 3;
  r += (160 * Math.sin(y / 12 * Math.PI) + 320 * Math.sin(y * Math.PI / 30)) * 2 / 3;
  return r;
}
function tfLng(x, y) {
  let r = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
  r += (20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2 / 3;
  r += (20 * Math.sin(x * Math.PI) + 40 * Math.sin(x / 3 * Math.PI)) * 2 / 3;
  r += (150 * Math.sin(x / 12 * Math.PI) + 300 * Math.sin(x / 30 * Math.PI)) * 2 / 3;
  return r;
}
function wgs2gcj(lat, lng) {
  if (outOfChina(lat, lng)) return [lat, lng];
  let dLat = tfLat(lng - 105, lat - 35);
  let dLng = tfLng(lng - 105, lat - 35);
  const rad = lat / 180 * Math.PI;
  let magic = 1 - GCJ_EE * Math.sin(rad) ** 2;
  const sq = Math.sqrt(magic);
  dLat = (dLat * 180) / ((GCJ_A * (1 - GCJ_EE)) / (magic * sq) * Math.PI);
  dLng = (dLng * 180) / (GCJ_A / sq * Math.cos(rad) * Math.PI);
  return [lat + dLat, lng + dLng];
}
function gcj2wgs(lat, lng) {
  if (outOfChina(lat, lng)) return [lat, lng];
  let wLat = lat, wLng = lng;
  for (let i = 0; i < 12; i++) {
    const g = wgs2gcj(wLat, wLng);
    wLat -= g[0] - lat;
    wLng -= g[1] - lng;
  }
  return [wLat, wLng];
}

// ---------------------------------------------------------------- 對話框

let modalState = null;

function showModal(opts) {
  return new Promise((resolve) => {
    const modal = $('modal');
    $('modal-title').textContent = opts.title || '';
    $('modal-body').textContent = opts.body || '';
    const input = $('modal-input');
    if (opts.input) {
      input.hidden = false;
      input.value = opts.defaultValue || '';
      input.placeholder = opts.placeholder || '';
    } else {
      input.hidden = true;
    }
    $('modal-ok').textContent = opts.okText || '確定';
    $('modal-cancel').textContent = opts.cancelText || '取消';
    $('modal-cancel').hidden = opts.hideCancel === true;

    modal.hidden = false;
    if (opts.input) {
      setTimeout(() => { input.focus(); input.select(); }, 30);
    }

    modalState = { resolve, withInput: !!opts.input };
  });
}

function closeModal(result) {
  const st = modalState;
  modalState = null;
  $('modal').hidden = true;
  if (st) st.resolve(result);
}

function modalConfirm() {
  if (!modalState) return;
  const st = modalState;
  if (st.withInput) {
    const v = $('modal-input').value.trim();
    closeModal(v || null);
  } else {
    closeModal(true);
  }
}

// ---------------------------------------------------------------- 狀態

const state = {
  map: null,
  amapReady: false,
  mode: 'locate',
  boot: null,
  point: null,          // { gcj:[lng,lat], wgs:[lat,lng] }
  pointMarker: null,
  path: [],             // [[lng,lat], ...] GCJ
  pathLine: null,
  loopLine: null,
  draft: [],
  drawing: false,
  drawTimer: 0,
  lastSample: 0,
  previewMarker: null,
  previewLine: null,
  previewing: false,
  routeSource: 'drawn', // 'drawn' | 'saved'
  common: [],
};

// ---------------------------------------------------------------- 初始化

async function boot() {
  try {
    const res = await fetch('/api/boot');
    state.boot = await res.json();
  } catch (e) {
    showMapError('無法連線到本機服務：' + e.message);
    return;
  }

  state.common = (state.boot.locations || []).map((it) => ({
    name: it.name, wgs: it.wgs, gcj: it.gcj, custom: !!it.custom,
  }));

  const mv = state.boot.map || {};
  state.homeView = { lng: mv.lng, lat: mv.lat, zoom: mv.zoom || 16 };

  renderCommon();
  initDefaults();
  bindUI();
  renderWarnings();

  refreshDevice();
  if (deviceTimer) clearInterval(deviceTimer);
  deviceTimer = setInterval(refreshDevice, 5000);

  // 排序自我測試（不依賴地圖）
  if (new URLSearchParams(location.search).get('selftest') === 'order') {
    setTimeout(runOrderTest, 500);
  }

  const key = state.boot.amap && state.boot.amap.key;
  const jscode = state.boot.amap && state.boot.amap.jscode;
  if (!key) {
    showMapError('config.json 裡沒有高德 key。\n請在 config.json 的 amap.key 填入你的 Web端(JSAPI) key。');
    return;
  }

  try {
    await loadAMap(key, jscode);
  } catch (e) {
    showMapError('高德地圖腳本載入失敗。\n可能原因：\n  · 沒有連網\n  · key 無效或被停用\n  · 安全密鑰 jscode 不正確\n\n錯誤：' + e.message);
    return;
  }

  createMap();
}

function showMapError(msg) {
  $('map-loading').hidden = true;
  const el = $('map-error');
  el.hidden = false;
  el.textContent = msg;
}

function loadAMap(key, jscode) {
  return new Promise((resolve, reject) => {
    if (window.AMap) { resolve(); return; }
    if (jscode) {
      window._AMapSecurityConfig = { securityJsCode: jscode };
    }
    const timer = setTimeout(() => reject(new Error('載入逾時（15 秒）')), 15000);
    const s = document.createElement('script');
    s.src = 'https://webapi.amap.com/maps?v=2.0&key=' + encodeURIComponent(key);
    s.async = true;
    s.onload = () => { clearTimeout(timer); resolve(); };
    s.onerror = () => { clearTimeout(timer); reject(new Error('script onerror')); };
    document.head.appendChild(s);
  });
}

function createMap() {
  const m = state.boot.map || { lng: 120.0771, lat: 30.3074, zoom: 16 };
  state.map = new AMap.Map('map', {
    zoom: m.zoom || 16,
    center: [m.lng, m.lat],
    viewMode: '2D',
    zooms: [3, 20],
  });
  state.amapReady = true;
  $('map-loading').hidden = true;

  state.map.on('moveend', scheduleViewSave);
  state.map.on('zoomend', scheduleViewSave);

  bindGestures(state.map);

  // 自我測試：?selftest=1（僅用於開發驗證，正常啟動不會觸發）
  if (new URLSearchParams(location.search).has('selftest')) {
    setTimeout(runSelfTest, 600);
  }
}

function runOrderTest() {
  const box = $('common-list');
  const first = box.querySelector('.list-item');
  if (!first) return;
  box.appendChild(first);
  finishDragReorder();
}

async function runSelfTest() {
  const q = new URLSearchParams(location.search);

  // 排序測試：把第一筆移到最後，走與拖曳放開時同一條程式路徑
  if (q.get('selftest') === 'order') {
    const box = $('common-list');
    const first = box.querySelector('.list-item');
    if (first) {
      box.appendChild(first);
      finishDragReorder();
    }
    switchTab('locate');
    return;
  }

  // 只選點（給說明書截圖用）
  if (q.get('selftest') === 'point') {
    setPoint(120.0771, 30.3074);
    switchTab('locate');
    return;
  }

  // 設定視窗（給說明書截圖用）
  if (q.get('selftest') === 'settings') {
    $('ver-text').textContent = 'EdgeRunners ' + ((state.boot && state.boot.version) || '');
    $('settings').hidden = false;
    return;
  }

  // 模擬「沒裝 iTunes」的警告外觀（給說明書截圖用）
  if (q.get('selftest') === 'warn') {
    state.boot.warnings = [
      '未安裝 iTunes（找不到 Apple Mobile Device Service）。\n'
      + '沒有它，電腦無法辨識 iPhone，所有功能都不能用。\n'
      + '請先安裝：apple.com/itunes/download/win64，裝完重新開機再開本程式。',
    ];
    renderWarnings();
    switchTab('locate');
    return;
  }

  const ring = [];
  for (let i = 0; i < 48; i++) {
    const a = i / 48 * Math.PI * 2;
    ring.push([120.0771 + Math.cos(a) * 0.0009, 30.3074 + Math.sin(a) * 0.0006]);
  }
  setPoint(120.0771, 30.3074);
  if (state.map) state.map.setZoomAndCenter(17, [120.0771, 30.3074]);
  state.path = ring;
  state.routeSource = 'drawn';
  redrawRoute();
  updateStats();
  const q2 = new URLSearchParams(location.search);
  if (q2.get('route') === '1' && state.boot.routes && state.boot.routes[0]) {
    clearPreview();
    state.path = state.boot.routes[0].gcj.slice();
    state.routeSource = 'saved';
    redrawRoute();
    updateStats();
    if (state.map) state.map.setFitView([state.pathLine], false, [40, 40, 40, 40]);
    return;
  }
  if (q2.get('tab') !== 'locate') switchTab('sim');
  if (!q2.has('nopreview')) await doPreview();
}

// ---------------------------------------------------------------- 手勢

function containerLngLat(clientX, clientY) {
  const rect = state.map.getContainer().getBoundingClientRect();
  const px = new AMap.Pixel(clientX - rect.left, clientY - rect.top);
  const ll = state.map.containerToLngLat(px);
  return [ll.getLng(), ll.getLat()];
}

function bindGestures(map) {
  const el = map.getContainer();
  let down = null;

  el.addEventListener('contextmenu', (e) => e.preventDefault());

  el.addEventListener('mousedown', (e) => {
    if (e.button === 0) {
      down = { button: 0, x: e.clientX, y: e.clientY, t: performance.now() };
    } else if (e.button === 2) {
      if (state.mode !== 'sim') return;
      e.preventDefault();
      startDrawing(e.clientX, e.clientY, map);
      down = { button: 2, x: e.clientX, y: e.clientY, t: performance.now() };
    }
  });

  window.addEventListener('mousemove', (e) => {
    if (!down) return;
    if (down.button === 2 && state.drawing) {
      const now = performance.now();
      if (now - state.lastSample < 25) return;
      state.lastSample = now;
      const ll = containerLngLat(e.clientX, e.clientY);
      const last = state.draft[state.draft.length - 1];
      if (!last || haversine(last, ll) > 0.3) {
        state.draft.push(ll);
        updateDraftLine();
      }
    }
  });

  window.addEventListener('mouseup', (e) => {
    if (!down) return;
    const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y);
    const dt = performance.now() - down.t;

    if (down.button === 0) {
      if (moved <= 5 && dt <= 300) {
        const ll = containerLngLat(e.clientX, e.clientY);
        if (state.mode === 'locate') setPoint(ll[0], ll[1]);
      }
    } else if (down.button === 2 && state.drawing) {
      finishDrawing();
    }
    down = null;
  });
}

function startDrawing(clientX, clientY, map) {
  state.drawing = true;
  state.draft = [containerLngLat(clientX, clientY)];
  state.lastSample = performance.now();
  $('draw-badge').hidden = false;
  if (map) map.setStatus({ dragEnable: false });
  updateDraftLine();
}

function updateDraftLine() {
  if (!state.map) return;
  if (!state.pathLine) {
    state.pathLine = new AMap.Polyline({
      path: state.draft,
      strokeColor: '#2f6fed',
      strokeWeight: 5,
      strokeOpacity: 0.95,
      lineJoin: 'round',
      lineCap: 'round',
      map: state.map,
      zIndex: 60,
    });
  } else {
    state.pathLine.setPath(state.draft);
    state.pathLine.show();
  }
}

function finishDrawing() {
  state.drawing = false;
  $('draw-badge').hidden = true;
  if (state.map) state.map.setStatus({ dragEnable: true });

  const draft = state.draft;
  state.draft = [];

  if (draft.length < 2 || pathLength(draft) < 3) {
    if (state.pathLine) state.pathLine.setPath(state.path.length ? state.path : []);
    if (!state.path.length && state.pathLine) state.pathLine.hide();
    return;
  }

  state.path = draft;
  state.routeSource = 'drawn';
  state.routeSaved = false;
  clearPreview();
  redrawRoute();
  updateStats();
}

function redrawRoute() {
  if (!state.map) return;
  clearLoopLine();

  if (!state.path.length) {
    if (state.pathLine) state.pathLine.hide();
    return;
  }

  if (!state.pathLine) {
    state.pathLine = new AMap.Polyline({
      path: state.path,
      strokeColor: '#2f6fed',
      strokeWeight: 5,
      strokeOpacity: 0.95,
      lineJoin: 'round',
      lineCap: 'round',
      map: state.map,
      zIndex: 60,
    });
  } else {
    state.pathLine.setPath(state.path);
    state.pathLine.show();
  }

  if (isLoop() && state.path.length >= 2) {
    state.loopLine = new AMap.Polyline({
      path: [state.path[state.path.length - 1], state.path[0]],
      strokeColor: '#8aa4d6',
      strokeWeight: 3,
      strokeOpacity: 0.9,
      strokeStyle: 'dashed',
      strokeDasharray: [8, 6],
      lineJoin: 'round',
      map: state.map,
      zIndex: 55,
    });
  }
}

function clearLoopLine() {
  if (state.loopLine) { state.loopLine.setMap(null); state.loopLine = null; }
}

// ---------------------------------------------------------------- 選點

function setPoint(lng, lat) {
  const w = gcj2wgs(lat, lng);
  state.point = { gcj: [lng, lat], wgs: [w[0], w[1]] };

  if (state.map) {
    if (!state.pointMarker) {
      state.pointMarker = new AMap.Marker({
        position: [lng, lat],
        content: '<div class="er-pin"></div>',
        offset: new AMap.Pixel(-9, -9),
        map: state.map,
        zIndex: 90,
      });
    } else {
      state.pointMarker.setPosition([lng, lat]);
      state.pointMarker.show();
    }
  }

  $('gcj-coord').textContent = `${fmtCoord(lat)}, ${fmtCoord(lng)}`;
  $('wgs-coord').textContent = `${fmtCoord(w[0])}, ${fmtCoord(w[1])}`;
  $('btn-inject').disabled = false;
}

// ---------------------------------------------------------------- 統計

function isLoop() {
  const el = $('loop');
  return !!(el && el.checked);
}

function getTimes() {
  const n = parseInt($('times').value, 10);
  return isLoop() ? Math.max(1, Math.min(99, isNaN(n) ? 1 : n)) : 1;
}

function getSpeed() {
  const v = parseFloat($('speed').value);
  return isFinite(v) && v > 0 ? v : 5.3;
}

function getJitter() {
  const v = parseFloat($('jitter').value);
  return isFinite(v) ? v : 0;
}

function updateStats() {
  const pathLen = pathLength(state.path);
  const times = getTimes();
  const total = pathLen * times;
  const speed = getSpeed();
  const dur = speed > 0 ? total / speed : 0;

  $('route-len').textContent = fmtDistance(pathLen);
  $('total-len').textContent = fmtDistance(total);
  $('route-time').textContent = fmtDuration(dur);
  $('btn-sim').disabled = state.path.length < 2;
  $('btn-preview').disabled = state.path.length < 2;
}

function updateSpeedHint() {
  const s = getSpeed();
  const kmh = (s * 3.6).toFixed(1);
  $('speed-hint').textContent = `≈ ${kmh} km/h ／ 配速 ${fmtPace(s)}`;
}

// ---------------------------------------------------------------- 預覽

async function doPreview() {
  if (state.previewing || state.path.length < 2) return;

  const total = pathLength(state.path) * getTimes();
  const ms = total <= 15000 ? 10000 : 15000;

  // 先清掉舊的預覽（這時 previewing 還是 false，不會誤關旗標）
  clearPreview();

  state.previewing = true;
  $('btn-preview').disabled = true;
  $('btn-preview').textContent = '預覽中…';

  let data;
  try {
    const res = await fetch('/api/trajectory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: state.path,
        speed: getSpeed(),
        jitter: getJitter(),
        loop: isLoop(),
        times: getTimes(),
        simplify: state.routeSource === 'drawn',
      }),
    });
    data = await res.json();
  } catch (e) {
    data = { ok: false, error: e.message };
  }

  if (!data || !data.ok || !data.path_gcj || data.path_gcj.length < 2) {
    state.previewing = false;
    $('btn-preview').disabled = false;
    $('btn-preview').textContent = '預覽';
    await showModal({
      title: '預覽失敗',
      body: (data && data.error) || '無法產生軌跡',
      hideCancel: true,
      okText: '知道了',
    });
    return;
  }

  const pts = data.path_gcj;
  const n = pts.length;

  // 橘色軌跡：一開始只有起點，隨著動畫逐段長出來
  state.previewLine = new AMap.Polyline({
    path: [pts[0], pts[0]],
    strokeColor: '#ff8a3d',
    strokeWeight: 3,
    strokeOpacity: 0.9,
    lineJoin: 'round',
    lineCap: 'round',
    map: state.map,
    zIndex: 70,
  });

  state.previewMarker = new AMap.Marker({
    position: pts[0],
    content: '<div class="er-pin preview"></div>',
    offset: new AMap.Pixel(-7, -7),
    map: state.map,
    zIndex: 95,
  });

  // 讓視野看得到整條路線
  if (state.pathLine) {
    state.map.setFitView([state.pathLine], false, [70, 70, 70, 70]);
  }

  const t0 = performance.now();
  let lastIdx = -1;

  const step = (now) => {
    if (!state.previewing) return;
    const p = Math.min(1, (now - t0) / ms);
    const idx = Math.min(n - 1, Math.floor(p * (n - 1)));
    if (idx !== lastIdx) {
      lastIdx = idx;
      state.previewMarker.setPosition(pts[idx]);
      state.previewLine.setPath(pts.slice(0, idx + 1));
    }
    if (p < 1) {
      requestAnimationFrame(step);
    } else {
      finishPreview();
    }
  };
  requestAnimationFrame(step);
}

function finishPreview() {
  state.previewing = false;
  $('btn-preview').disabled = false;
  $('btn-preview').textContent = '預覽';
}

function clearPreview() {
  if (state.previewMarker) { state.previewMarker.setMap(null); state.previewMarker = null; }
  if (state.previewLine) { state.previewLine.setMap(null); state.previewLine = null; }
  if (state.previewing) finishPreview();
}

// ---------------------------------------------------------------- 常見定位

function renderCommon() {
  const box = $('common-list');
  box.innerHTML = '';
  if (!state.common.length) {
    const d = document.createElement('div');
    d.className = 'list-empty';
    d.textContent = '尚無資料。可在 common_location.txt 裡加入，或用上面的按鈕新增。';
    box.appendChild(d);
    return;
  }
  state.common.forEach((item, idx) => {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.dataset.name = item.name;
    row.title = '單擊＝跳到此地　長按＝拖曳排序';

    const name = document.createElement('span');
    name.textContent = item.name;
    row.appendChild(name);

    const del = document.createElement('button');
    del.className = 'del';
    del.textContent = '×';
    del.title = '刪除';
    del.addEventListener('click', (e) => {
      e.stopPropagation();
      state.common.splice(idx, 1);
      renderCommon();
      persistCommon();
    });
    row.appendChild(del);

    row.addEventListener('click', () => {
      if (dragState.justDragged) return;
      if (!state.map) return;
      state.map.setZoomAndCenter(17, item.gcj);
      setPoint(item.gcj[0], item.gcj[1]);
    });

    row.addEventListener('mousedown', (e) => listItemMouseDown(e, row));

    box.appendChild(row);
  });
}

// ---------------- 常見定位：長按拖曳排序 ----------------

const dragState = { pending: null, active: null, justDragged: false };

function listItemMouseDown(e, row) {
  if (e.button !== 0) return;
  if (e.target && e.target.classList && e.target.classList.contains('del')) return;
  dragState.pending = {
    startY: e.clientY,
    row,
    timer: setTimeout(() => {
      const p = dragState.pending;
      if (!p) return;
      dragState.active = { row: p.row };
      p.row.classList.add('dragging');
      document.body.classList.add('dragging-mode');
    }, 260),
  };
}

function listMouseMove(e) {
  if (dragState.pending && !dragState.active) {
    if (Math.abs(e.clientY - dragState.pending.startY) > 6) {
      clearTimeout(dragState.pending.timer);
      dragState.pending = null;
    }
    return;
  }
  if (!dragState.active) return;

  const box = $('common-list');
  const row = dragState.active.row;
  const others = Array.from(box.querySelectorAll('.list-item')).filter((r) => r !== row);
  let ref = null;
  for (const r of others) {
    const b = r.getBoundingClientRect();
    if (e.clientY < b.top + b.height / 2) { ref = r; break; }
  }
  if (ref) box.insertBefore(row, ref);
  else box.appendChild(row);
}

function listMouseUp() {
  if (dragState.pending) {
    clearTimeout(dragState.pending.timer);
    dragState.pending = null;
  }
  if (!dragState.active) return;

  dragState.active.row.classList.remove('dragging');
  document.body.classList.remove('dragging-mode');
  dragState.active = null;

  dragState.justDragged = true;
  setTimeout(() => { dragState.justDragged = false; }, 60);

  finishDragReorder();
}

// 依目前 DOM 的順序，重排 state.common 並存檔
function finishDragReorder() {
  const box = $('common-list');
  const names = Array.from(box.querySelectorAll('.list-item')).map((el) => el.dataset.name);
  const byName = new Map(state.common.map((c) => [c.name, c]));
  const next = names.map((n) => byName.get(n)).filter(Boolean);
  if (next.length !== state.common.length) return;
  state.common = next;
  persistCommon();
}

function persistCommon() {
  fetch('/api/common', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      items: state.common.map((c) => ({
        name: c.name, wgs: c.wgs, gcj: c.gcj, custom: !!c.custom,
      })),
    }),
  }).catch(() => {});
}

// ---------------------------------------------------------------- UI 綁定

function initDefaults() {
  const d = state.boot.defaults || {};
  $('speed').value = d.speed_ms || 5.3;
  $('jitter').value = d.jitter_level == null ? 1.2 : d.jitter_level;
  $('loop').checked = !!d.loop;
  $('times').value = d.times || 1;
  updateSpeedHint();
  updateJitterLabel();
  updateTimesDisabled();
  updateStats();
  renderRoutes();
}

function updateJitterLabel() {
  const v = getJitter();
  const label = v <= 0.05 ? '關閉' : v.toFixed(1) + ' m';
  $('jitter-val').textContent = label;
}

function updateTimesDisabled() {
  $('times').disabled = !isLoop();
}

function bindUI() {
  document.querySelectorAll('.tab').forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // 座標複製
  $('copy-coord').addEventListener('click', async () => {
    if (!state.point) return;
    const txt = `${fmtCoord(state.point.wgs[0])}, ${fmtCoord(state.point.wgs[1])}`;
    try {
      await navigator.clipboard.writeText(txt);
      $('copy-coord').textContent = '已複製';
      setTimeout(() => { $('copy-coord').textContent = '複製'; }, 1200);
    } catch (e) { /* 忽略 */ }
  });

  // 自選定位
  $('locate-go').addEventListener('click', applyLocateInput);
  $('locate-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') applyLocateInput();
  });

  // 加入常見定位
  $('save-common').addEventListener('click', async () => {
    if (!state.point) {
      await showModal({ title: '尚未選點', body: '請先在地圖上單擊一個位置。', hideCancel: true, okText: '知道了' });
      return;
    }
    const name = await showModal({
      title: '加入常見定位',
      body: '為這個位置取一個名字：',
      input: true,
      placeholder: '例如：家、公司、學校',
    });
    if (!name) return;
    if (state.common.some((c) => c.name === name)) {
      await showModal({ title: '名稱重複', body: '已經有同名的常見定位了。', hideCancel: true, okText: '知道了' });
      return;
    }
    state.common.push({
      name,
      wgs: state.point.wgs,
      gcj: state.point.gcj,
      custom: true,
    });
    renderCommon();
    persistCommon();
  });

  // 注入 / 恢復
  $('btn-inject').addEventListener('click', doInject);
  $('btn-clear').addEventListener('click', doClear);
  $('btn-sim').addEventListener('click', startSimulation);
  $('btn-stop').addEventListener('click', stopSimulation);

  // 速度
  $('speed').addEventListener('input', () => { updateSpeedHint(); updateStats(); });

  // 抖動
  $('jitter').addEventListener('input', () => { updateJitterLabel(); clearPreview(); });

  // 循環 / 次數
  $('loop').addEventListener('change', () => {
    updateTimesDisabled();
    clearPreview();
    redrawRoute();
    updateStats();
  });
  $('times').addEventListener('input', () => { clearPreview(); updateStats(); });

  // 已有路線
  $('route-select').addEventListener('change', (e) => {
    const idx = parseInt(e.target.value, 10);
    if (isNaN(idx)) return;
    const r = (state.boot.routes || [])[idx];
    if (!r) return;
    clearPreview();
    state.path = r.gcj.slice();
    state.routeSource = 'saved';
    state.routeSaved = true;
    redrawRoute();
    updateStats();
    if (state.map && state.path.length > 1 && state.pathLine) {
      state.map.setFitView([state.pathLine], false, [40, 40, 40, 40]);
    }
  });

  // 清空
  $('btn-reset').addEventListener('click', () => {
    clearPreview();
    state.path = [];
    state.routeSource = 'drawn';
    state.routeSaved = false;
    clearLoopLine();
    if (state.pathLine) { state.pathLine.setMap(null); state.pathLine = null; }
    $('route-select').value = '';
    updateStats();
  });

  // 預覽
  $('btn-preview').addEventListener('click', doPreview);

  // 地圖工具
  $('btn-map-clear').addEventListener('click', clearAll);
  $('btn-map-home').addEventListener('click', goHomeView);

  // 設定（更新 Key）
  $('btn-settings').addEventListener('click', () => {
    $('set-key').value = (state.boot && state.boot.amap && state.boot.amap.key) || '';
    $('set-jscode').value = (state.boot && state.boot.amap && state.boot.amap.jscode) || '';
    $('ver-text').textContent = 'EdgeRunners ' + ((state.boot && state.boot.version) || '');
    $('settings').hidden = false;
  });
  $('set-cancel').addEventListener('click', () => { $('settings').hidden = true; });
  $('set-diag').addEventListener('click', () => {
    $('settings').hidden = true;
    showDiagnostics();
  });
  $('set-save').addEventListener('click', async () => {
    const key = $('set-key').value.trim();
    const jscode = $('set-jscode').value.trim();
    if (!key) {
      await showModal({ title: 'Key 不能空白', body: '請貼上高德「Web端(JSAPI)」的 Key。', hideCancel: true, okText: '知道了' });
      return;
    }
    await postJson('/api/settings', { key, jscode });
    location.reload();
  });

  // 對話框
  $('modal-ok').addEventListener('click', modalConfirm);
  $('modal-cancel').addEventListener('click', () => closeModal(null));
  $('modal').addEventListener('click', (e) => {
    if (e.target === $('modal')) closeModal(null);
  });
  window.addEventListener('keydown', (e) => {
    if ($('modal').hidden) return;
    if (e.key === 'Enter') { e.preventDefault(); modalConfirm(); }
    if (e.key === 'Escape') { e.preventDefault(); closeModal(null); }
  });

  // 常見定位：長按拖曳排序
  document.addEventListener('mousemove', listMouseMove);
  document.addEventListener('mouseup', listMouseUp);
}

// ---------------------------------------------------------------- 啟動警告

function renderWarnings() {
  const box = $('warn-bar');
  const list = (state.boot && state.boot.warnings) || [];
  if (!list.length) {
    box.hidden = true;
    return;
  }
  box.innerHTML = '';
  const title = document.createElement('b');
  title.textContent = '⚠ 啟動檢查發現問題：';
  box.appendChild(title);
  const ul = document.createElement('div');
  list.forEach((w) => {
    const li = document.createElement('div');
    li.textContent = '· ' + w;
    ul.appendChild(li);
  });
  box.appendChild(ul);

  const bar = document.createElement('div');
  bar.style.cssText = 'display:flex;gap:8px;margin-top:8px';

  const retry = document.createElement('button');
  retry.textContent = '重新檢查';
  retry.className = 'mini';
  retry.addEventListener('click', () => location.reload());
  bar.appendChild(retry);

  const diag = document.createElement('button');
  diag.textContent = '複製診斷資訊';
  diag.className = 'mini';
  diag.addEventListener('click', showDiagnostics);
  bar.appendChild(diag);

  box.appendChild(bar);
  box.hidden = false;
}

// 收集環境證據並複製到剪貼簿（讓使用者能直接貼給開發者）
async function showDiagnostics() {
  let text = '';
  try {
    const r = await getJson('/api/diagnose');
    text = (r && r.text) || '（沒有取得診斷資料）';
  } catch (e) {
    text = '診斷失敗：' + e;
  }

  let copied = false;
  try {
    await navigator.clipboard.writeText(text);
    copied = true;
  } catch (e) { /* 忽略，改用下面的文字框手動複製 */ }

  await showModal({
    title: copied ? '診斷資訊已複製' : '診斷資訊',
    body: (copied ? '已複製到剪貼簿，直接貼給開發者即可。\n\n' : '請手動選取下面文字複製：\n\n') + text,
    hideCancel: true,
    okText: '知道了',
  });
}

// ---------------------------------------------------------------- 裝置狀態

let deviceTimer = null;

async function refreshDevice() {
  try {
    const d = await getJson('/api/device');
    renderDevice(d);
  } catch (e) { /* 忽略 */ }
}

function renderDevice(d) {
  const dot = document.querySelector('#status-bar .dot');
  const txt = $('status-text');
  if (!d || !d.connected) {
    dot.className = 'dot err';
    txt.textContent = '未連接 iPhone（需已安裝 iTunes、插上 USB、解鎖並按「信任」）';
    return;
  }
  const bits = [`已連接 ${d.name || 'iPhone'}${d.ios ? ' · iOS ' + d.ios : ''}`];
  bits.push(d.ddi ? 'DDI 已掛載' : 'DDI 未掛載');
  if (d.injecting) bits.push('定位已注入');
  dot.className = 'dot ' + (d.ddi ? 'ok' : 'warn');
  txt.textContent = bits.join(' · ');
}

// ---------------------------------------------------------------- 注入 / 恢復

async function doInject() {
  if (!state.point) {
    await showModal({ title: '尚未選點', body: '請先在地圖上單擊一個位置。', hideCancel: true, okText: '知道了' });
    return;
  }
  const btn = $('btn-inject');
  btn.disabled = true;
  btn.textContent = '準備中…（首次需掛載映像檔，可能要 1 分鐘）';

  let r;
  try {
    const w = state.point.wgs;   // [lat, lon]
    r = await postJson('/api/inject', { lat: w[0], lon: w[1] });
  } catch (e) {
    r = { ok: false, error: String(e) };
  }

  if (r.ok) {
    btn.textContent = '已注入 ✓';
    $('btn-clear').disabled = false;
    setTimeout(() => { btn.textContent = '注入該座標'; btn.disabled = false; }, 1500);
    refreshDevice();
  } else {
    btn.textContent = '注入該座標';
    btn.disabled = false;
    await showModal({ title: '注入失敗', body: r.error || '未知錯誤', hideCancel: true, okText: '知道了' });
  }
}

async function doClear() {
  const btn = $('btn-clear');
  btn.disabled = true;
  btn.textContent = '恢復中…';

  let r;
  try {
    r = await postJson('/api/clear', {});
  } catch (e) {
    r = { ok: false, error: String(e) };
  }

  btn.textContent = '恢復真實定位';
  btn.disabled = false;

  if (!r.ok) {
    await showModal({ title: '恢復失敗', body: r.error || '未知錯誤', hideCancel: true, okText: '知道了' });
  }
  refreshDevice();
}

// ---------------------------------------------------------------- 模擬

let simTimer = null;

function stopSimPolling() {
  if (simTimer) { clearInterval(simTimer); simTimer = null; }
}

async function startSimulation() {
  if (state.path.length < 2) return;

  // 自繪路線 → 詢問是否保留（呼叫已有路線則不問）
  if (state.routeSource === 'drawn' && !state.routeSaved) {
    const keep = await showModal({
      title: '保留這條路線？',
      body: '這是你剛畫的路線。\n要存進「已有路線」方便下次直接用嗎？',
      okText: '保留', cancelText: '不用',
    });
    if (keep) {
      const d = new Date();
      const def = '路線 ' + d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0');
      const name = await showModal({
        title: '路線名稱', body: '幫這條路線取個名字：', input: true, defaultValue: def,
      });
      if (name) {
        const r = await postJson('/api/routes', { name, points: state.path });
        if (r.ok) {
          state.routeSaved = true;
          await reloadRoutes();
        } else {
          await showModal({ title: '儲存失敗', body: r.error || '', hideCancel: true, okText: '知道了' });
        }
      }
    } else {
      state.routeSaved = true;
    }
  }

  const btn = $('btn-sim');
  btn.disabled = true;
  btn.textContent = '啟動中…（首次需掛載映像檔，可能要 1 分鐘）';

  let r;
  try {
    r = await postJson('/api/simulate', {
      path: state.path,
      speed: getSpeed(),
      jitter: getJitter(),
      loop: isLoop(),
      times: getTimes(),
      simplify: state.routeSource === 'drawn',
    });
  } catch (e) {
    r = { ok: false, error: String(e) };
  }

  if (!r.ok) {
    btn.disabled = false;
    btn.textContent = '開始模擬';
    await showModal({ title: '無法開始模擬', body: r.error || '未知錯誤', hideCancel: true, okText: '知道了' });
    return;
  }

  btn.textContent = '模擬進行中…';
  $('progress-card').hidden = false;
  $('bar-fill').style.width = '0%';
  $('prog-pct').textContent = '0%';
  $('prog-text').textContent = '已送出，開始移動…';
  stopSimPolling();
  simTimer = setInterval(pollSim, 1000);
  pollSim();
}

async function pollSim() {
  let s;
  try {
    s = await getJson('/api/sim');
  } catch (e) {
    return;
  }
  if (!s) return;

  if (s.running) {
    const pct = Math.max(0, Math.min(100, s.percent || 0));
    $('bar-fill').style.width = pct + '%';
    $('prog-pct').textContent = Math.round(pct) + '%';
    const left = Math.max(0, (s.duration || 0) - (s.elapsed || 0));
    $('prog-text').textContent = `已跑 ${fmtDuration(s.elapsed)} ／ 共 ${fmtDuration(s.duration)}　剩 ${fmtDuration(left)}`;
    return;
  }

  stopSimPolling();
  $('btn-sim').disabled = false;
  $('btn-sim').textContent = '開始模擬';

  if (s.error) {
    $('progress-card').hidden = true;
    await showModal({ title: '模擬中止', body: s.error, hideCancel: true, okText: '知道了' });
    await askRestore();
    return;
  }

  $('bar-fill').style.width = '100%';
  $('prog-pct').textContent = '100%';
  $('prog-text').textContent = '已完成';
  await askRestore();
}

async function stopSimulation() {
  try { await postJson('/api/sim/stop', {}); } catch (e) { /* 忽略 */ }
  stopSimPolling();
  $('btn-sim').disabled = false;
  $('btn-sim').textContent = '開始模擬';
  $('progress-card').hidden = true;
  await askRestore();
}

async function askRestore() {
  const yes = await showModal({
    title: '已停止',
    body: '要恢復手機的真實定位嗎？',
    okText: '恢復', cancelText: '先不用',
  });
  if (yes) await doClear();
  $('progress-card').hidden = true;
}

// ---------------------------------------------------------------- 路線清單

function renderRoutes() {
  const sel = $('route-select');
  sel.innerHTML = '<option value="">— 選擇已保存的路線 —</option>';
  (state.boot.routes || []).forEach((r, i) => {
    const o = document.createElement('option');
    o.value = String(i);
    o.textContent = `${r.name}（${fmtDistance(r.distance)}）`;
    sel.appendChild(o);
  });
}

async function reloadRoutes() {
  const b = await getJson('/api/boot');
  state.boot.routes = (b && b.routes) || [];
  renderRoutes();
}

function notYet(what) {
  showModal({
    title: what,
    body: 'Phase 1 只做介面與地圖互動。\n這個按鈕會在 Phase 2 接通 iPhone 之後生效。',
    hideCancel: true,
    okText: '知道了',
  });
}

// 清圖：清掉路線、預覽、選點
function clearAll() {
  clearPreview();
  state.path = [];
  state.routeSource = 'drawn';
  state.routeSaved = false;
  clearLoopLine();
  if (state.pathLine) { state.pathLine.setMap(null); state.pathLine = null; }
  if (state.pointMarker) { state.pointMarker.setMap(null); state.pointMarker = null; }
  state.point = null;
  $('gcj-coord').textContent = '—';
  $('wgs-coord').textContent = '—';
  const sel = $('route-select');
  if (sel) sel.value = '';
  updateStats();
}

// 回原位：有路線→縮放到路線；沒路線→回到開啟時的視野
function goHomeView() {
  if (!state.map) return;
  if (state.path.length > 1 && state.pathLine) {
    state.map.setFitView([state.pathLine], false, [60, 60, 60, 60]);
    return;
  }
  const h = state.homeView;
  if (h && h.lng != null) {
    state.map.setZoomAndCenter(h.zoom, [h.lng, h.lat]);
  }
}

function switchTab(tab) {
  state.mode = tab;
  document.querySelectorAll('.tab').forEach((b) => {
    b.classList.toggle('active', b.dataset.tab === tab);
  });
  $('pane-locate').hidden = tab !== 'locate';
  $('pane-sim').hidden = tab !== 'sim';
  if (tab !== 'sim') {
    clearPreview();
  }
}

function applyLocateInput() {
  const raw = $('locate-input').value.trim();
  if (!raw) return;
  const parts = raw.replace(/[，、]/g, ',').split(/[\s,]+/).filter(Boolean);
  if (parts.length < 2) {
    showModal({ title: '格式錯誤', body: '請輸入「緯度, 經度」，例如 25.0339, 121.5654', hideCancel: true, okText: '知道了' });
    return;
  }
  const lat = parseFloat(parts[0]);
  const lng = parseFloat(parts[1]);
  if (!isFinite(lat) || !isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) {
    showModal({ title: '座標無效', body: '緯度需在 -90~90、經度需在 -180~180 之間。', hideCancel: true, okText: '知道了' });
    return;
  }
  const crs = $('input-crs').value;
  const gcj = crs === 'gcj' ? [lat, lng] : (() => { const g = wgs2gcj(lat, lng); return [g[0], g[1]]; })();

  if (state.map) state.map.setZoomAndCenter(17, [gcj[1], gcj[0]]);
  setPoint(gcj[1], gcj[0]);
}

// ---------------------------------------------------------------- 儲存視野

let viewTimer = 0;
function scheduleViewSave() {
  clearTimeout(viewTimer);
  viewTimer = setTimeout(() => {
    if (!state.map) return;
    const c = state.map.getCenter();
    fetch('/api/view', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lng: c.getLng(), lat: c.getLat(), zoom: state.map.getZoom() }),
    }).catch(() => {});
  }, 900);
}

// ---------------------------------------------------------------- 啟動

window.addEventListener('DOMContentLoaded', boot);
