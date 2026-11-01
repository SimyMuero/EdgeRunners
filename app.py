# -*- coding: utf-8 -*-
"""EdgeRunners - Phase 1 原型

本機 HTTP 服務 + WebView2 視窗。
Phase 1 只做：地圖、手勢、UI、路線與軌跡預覽（完全不碰手機）。
"""

import json
import os
import sys
import tempfile
import threading
import time
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core import coords, device, gpx, locations, settings, track

IS_WIN = sys.platform == 'win32'
IS_MAC = sys.platform == 'darwin'

if IS_WIN:
    from core import winsvc
else:
    winsvc = None          # macOS 內建 usbmuxd，不需要 Windows 服務檢查

ROOT = os.path.dirname(os.path.abspath(__file__))
FROZEN = bool(getattr(sys, 'frozen', False))
APP_DIR = os.path.dirname(sys.executable) if FROZEN else ROOT
BUNDLE_DIR = getattr(sys, '_MEIPASS', APP_DIR)

if IS_MAC and FROZEN:
    # macOS：設定檔放 ~/Library/Application Support，不寫進 .app 內部
    APP_DIR = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'EdgeRunners')
    os.makedirs(APP_DIR, exist_ok=True)

WEB_DIR = os.path.join(BUNDLE_DIR, 'web')
CONFIG_PATH = os.path.join(APP_DIR, 'config.json')
ROUTES_PATH = os.path.join(APP_DIR, 'routes.json')
DEFAULT_GPX = r'C:\iPhoneGPS\zju_track_12km_v2.gpx' if IS_WIN else ''
TMP_DIR = os.path.join(tempfile.gettempdir(), 'EdgeRunners')

VERSION = '0.5.2'

dev = device.DeviceManager()

# 裝置狀態快取：由背景執行緒定期更新，讓 /api/device 能瞬間回應
DEV_STATE = {'connected': False, 'devices': [], 'ddi': False, 'checked': 0}
DEV_LOCK = threading.Lock()
DEV_POLL_SEC = 6


def device_monitor():
    while True:
        try:
            info = dev.device_summary()
            if info.get('connected'):
                info['ddi'] = dev.ddi_mounted()
            else:
                info['ddi'] = False
            info['injecting'] = dev.injecting()
            info['checked'] = int(time.time())
            with DEV_LOCK:
                DEV_STATE.clear()
                DEV_STATE.update(info)
        except Exception:
            pass
        time.sleep(DEV_POLL_SEC)

CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
}

cfg = settings.Settings(CONFIG_PATH)


# ---------------------------------------------------------------- routes

def load_routes():
    """讀 routes.json；不存在就從預設 GPX 匯入一次"""
    if os.path.exists(ROUTES_PATH):
        try:
            with open(ROUTES_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (OSError, ValueError):
            pass

    routes = []
    if os.path.exists(DEFAULT_GPX):
        try:
            pts = gpx.read_gpx_points(DEFAULT_GPX)
            if len(pts) >= 2:
                routes.append({
                    'name': '浙大紫金港西操 12km',
                    'points': [[round(p[0], 6), round(p[1], 6)] for p in pts],
                    'distance': round(coords.polyline_length_m(pts), 1),
                    'created': 'imported',
                })
                save_routes(routes)
        except OSError:
            pass
    return routes


def save_routes(routes):
    tmp = ROUTES_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(routes, f, ensure_ascii=False)
    os.replace(tmp, ROUTES_PATH)


# ---------------------------------------------------------------- payload

def health_checks():
    """啟動自我檢查：把沉默故障變成看得見的警告

    關於 Apple 手機通訊服務（usbmuxd）：這裡做的是**功能檢查**，不是名稱檢查。
    先看能不能真的跟 usbmuxd 通話，不通才去猜原因。
    因為有些電腦沒裝 iTunes 卻有第三方工具裝好了服務，
    也有些電腦裝了 iTunes 但服務元件沒註冊成功 —— 只看服務名稱會誤判。
    """
    warns = []

    if winsvc is not None:      # 只有 Windows 需要檢查 Apple 服務（macOS 內建 usbmuxd）
        with DEV_LOCK:
            usbmux_ok = DEV_STATE.get('usbmux_ok')
        if usbmux_ok is None:                       # 監控執行緒還沒跑過第一次
            try:
                usbmux_ok = dev.device_summary().get('usbmux_ok', True)
            except Exception:
                usbmux_ok = True
        if not usbmux_ok:
            warns.append(winsvc.diagnose())

    index_html = os.path.join(WEB_DIR, 'index.html')
    if not os.path.exists(index_html):
        warns.append('找不到介面檔案 web/index.html，視窗會是空白。')

    if FROZEN:
        required = [
            (os.path.join(BUNDLE_DIR, 'pykdebugparser', 'trace.codes'),
             '缺少 pykdebugparser/trace.codes，定位與模擬指令會失敗'),
        ]
        if IS_WIN:
            required.append(
                (os.path.join(BUNDLE_DIR, 'pytun_pmd3', 'wintun', 'bin', 'amd64', 'wintun.dll'),
                 '缺少 wintun.dll，無法與手機建立連線'))
        for path, msg in required:
            if not os.path.exists(path):
                warns.append(msg)

    try:
        probe = CONFIG_PATH + '.probe'
        with open(probe, 'w', encoding='utf-8') as f:
            f.write('x')
        os.remove(probe)
    except OSError:
        warns.append('程式資料夾無法寫入，設定與路線不會被保存。請把程式移到有寫入權限的位置。')

    if not cfg.get('amap', 'key', default=''):
        warns.append('尚未設定高德地圖 Key，地圖不會顯示。請按右上角 ⚙ 填入。')

    return warns


def build_locations():
    """檔案裡的地點 + 介面上保存的順序／自訂地點

    規則：
      · config.common_list 有內容 → 以它為準（保留使用者的排序、刪除、新增）
      · txt 裡新出現的名稱 → 自動附加到最後
      · config.common_list 為空 → 直接用 txt 的內容
    """
    file_items = []
    for item in locations.load_common_locations(cfg.get('common_location_file')):
        lat, lon = item['lat'], item['lon']
        if item.get('crs', 'wgs84') == 'wgs84':
            glat, glon = coords.wgs2gcj(lat, lon)
        else:
            glat, glon = lat, lon
            lat, lon = coords.gcj2wgs(lat, lon)
        file_items.append({
            'name': item['name'],
            'wgs': [round(lat, 6), round(lon, 6)],
            'gcj': [round(glon, 6), round(glat, 6)],
            'custom': False,
        })

    saved = cfg.get('common_list', default=[]) or []
    if not saved:
        return file_items

    result = []
    seen = set()
    for it in saved:
        name = it.get('name')
        if not name or name in seen:
            continue
        seen.add(name)
        result.append({
            'name': name,
            'wgs': it.get('wgs'),
            'gcj': it.get('gcj'),
            'custom': bool(it.get('custom')),
        })

    for it in file_items:
        if it['name'] not in seen:
            result.append(it)
    return result


def build_boot():
    locs = build_locations()

    routes = []
    for r in load_routes():
        pts_gcj = []
        for p in r.get('points', []):
            glat, glon = coords.wgs2gcj(p[0], p[1])
            pts_gcj.append([round(glon, 6), round(glat, 6)])
        routes.append({
            'name': r.get('name', '未命名'),
            'distance': r.get('distance', 0),
            'gcj': pts_gcj,
        })

    return {
        'version': VERSION,
        'phase': 3,
        'warnings': health_checks(),
        'amap': {
            'key': cfg.get('amap', 'key', default=''),
            'jscode': cfg.get('amap', 'jscode', default=''),
        },
        'map': cfg.get('map'),
        'defaults': cfg.get('defaults'),
        'locations': locs,
        'routes': routes,
    }


# ---------------------------------------------------------------- handler

class Handler(BaseHTTPRequestHandler):
    server_version = 'EdgeRunners/0.1'

    def log_message(self, fmt, *args):
        if os.environ.get('EDGERUNNERS_VERBOSE'):
            sys.stderr.write('[http] ' + (fmt % args) + '\n')

    # --- helpers ---
    def _send(self, code, body, ctype='application/json; charset=utf-8'):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _read_json(self):
        try:
            n = int(self.headers.get('Content-Length') or 0)
            if n <= 0:
                return {}
            return json.loads(self.rfile.read(n).decode('utf-8'))
        except (ValueError, OSError):
            return {}

    def _static(self, path):
        if path in ('', '/'):
            path = '/index.html'
        rel = path.lstrip('/')
        full = os.path.normpath(os.path.join(WEB_DIR, rel))
        if not full.startswith(WEB_DIR):
            self._send(403, 'forbidden', 'text/plain; charset=utf-8')
            return
        if not os.path.isfile(full):
            self._send(404, 'not found', 'text/plain; charset=utf-8')
            return
        ext = os.path.splitext(full)[1].lower()
        ctype = CONTENT_TYPES.get(ext, 'application/octet-stream')
        try:
            with open(full, 'rb') as f:
                data = f.read()
        except OSError:
            self._send(500, 'read error', 'text/plain; charset=utf-8')
            return
        self._send(200, data, ctype)

    # --- routes ---
    def do_GET(self):
        try:
            if self.path.startswith('/api/boot'):
                self._json(build_boot())
                return
            if self.path.startswith('/api/status'):
                self._json({'phase': 3, 'version': VERSION})
                return
            if self.path.startswith('/api/diagnose'):
                try:
                    if winsvc is not None:
                        text = winsvc.format_report()
                    else:
                        text = ('--- EdgeRunners 環境診斷 ---\n'
                                '平台：macOS（內建 usbmuxd，不需要檢查 Apple 服務）\n'
                                '版本：%s\n'
                                '設定檔：%s\n'
                                '裝置：%s' % (
                                    VERSION, APP_DIR,
                                    '已連接' if DEV_STATE.get('connected') else '未連接'))
                except Exception as exc:
                    text = '診斷失敗：%s' % exc
                self._json({'ok': True, 'text': text})
                return
            if self.path.startswith('/api/device'):
                with DEV_LOCK:
                    self._json(dict(DEV_STATE))
                return
            if self.path.startswith('/api/sim'):
                self._json(dev.sim_status())
                return
            self._static(self.path.split('?')[0])
        except Exception:
            traceback.print_exc()
            self._json({'ok': False, 'error': 'internal error'}, 500)

    def do_POST(self):
        try:
            route = self.path.split('?')[0]

            if route == '/api/trajectory':
                self._api_trajectory()
                return

            if route == '/api/view':
                body = self._read_json()
                try:
                    cfg.set(float(body['lng']), 'map', 'lng')
                    cfg.set(float(body['lat']), 'map', 'lat')
                    cfg.set(int(body['zoom']), 'map', 'zoom')
                    cfg.save()
                    self._json({'ok': True})
                except (KeyError, TypeError, ValueError):
                    self._json({'ok': False, 'error': 'bad payload'}, 400)
                return

            if route == '/api/common':
                body = self._read_json()
                items = []
                for it in (body.get('items') or []):
                    try:
                        name = str(it.get('name') or '').strip()
                        wgs = it.get('wgs')
                        gcj = it.get('gcj')
                        if not name or not wgs or not gcj:
                            continue
                        items.append({
                            'name': name,
                            'wgs': [float(wgs[0]), float(wgs[1])],
                            'gcj': [float(gcj[0]), float(gcj[1])],
                            'custom': bool(it.get('custom')),
                        })
                    except (TypeError, ValueError, IndexError):
                        continue
                cfg.set(items, 'common_list')
                self._json({'ok': cfg.save(), 'count': len(items)})
                return

            if route == '/api/settings':
                body = self._read_json()
                key = str(body.get('key') or '').strip()
                jscode = str(body.get('jscode') or '').strip()
                if key:
                    cfg.set(key, 'amap', 'key')
                cfg.set(jscode, 'amap', 'jscode')
                self._json({'ok': cfg.save()})
                return

            if route == '/api/inject':
                body = self._read_json()
                try:
                    lat = float(body['lat'])
                    lon = float(body['lon'])
                except (KeyError, TypeError, ValueError):
                    self._json({'ok': False, 'error': '座標格式錯誤'}, 400)
                    return
                dev.invalidate_cache()
                chk = dev.ensure_ddi()
                if not chk.get('ok'):
                    self._json(chk)
                    return
                res = dev.inject(lat, lon)
                if res.get('ok'):
                    with DEV_LOCK:
                        DEV_STATE['injecting'] = True
                        DEV_STATE['ddi'] = True
                self._json(res)
                return

            if route == '/api/clear':
                dev.invalidate_cache()
                res = dev.clear_location()
                if res.get('ok'):
                    with DEV_LOCK:
                        DEV_STATE['injecting'] = False
                self._json(res)
                return

            if route == '/api/devmode':
                status = dev.developer_mode_status()
                if status is True:
                    self._json({'ok': True, 'already': True, 'status': True})
                    return
                res = dev.reveal_developer_mode()
                if res.get('ok'):
                    res['status'] = dev.developer_mode_status()
                self._json(res)
                return

            if route == '/api/simulate':
                self._api_simulate()
                return

            if route == '/api/sim/stop':
                self._json(dev.stop_play())
                return

            if route == '/api/routes':
                self._api_save_route()
                return

            self._json({'ok': False, 'error': 'unknown endpoint'}, 404)
        except Exception:
            traceback.print_exc()
            self._json({'ok': False, 'error': 'internal error'}, 500)

    # --- api ---
    def _api_simulate(self):
        body = self._read_json()
        path = body.get('path') or []
        if len(path) < 2:
            self._json({'ok': False, 'error': '路線太短'}, 400)
            return

        speed = float(body.get('speed', 5.3))
        jitter = float(body.get('jitter', 0.0))
        loop = bool(body.get('loop', False))
        times = int(body.get('times', 1))

        path_wgs = [coords.gcj2wgs(p[1], p[0]) for p in path]
        if body.get('simplify'):
            path_wgs = track.simplify_rdp(path_wgs, 1.0)

        result = track.generate_trajectory(
            path_wgs, speed_ms=speed, jitter_m=jitter, loop=loop, times=times)
        if not result['points']:
            self._json({'ok': False, 'error': '無法產生軌跡'}, 400)
            return

        try:
            os.makedirs(TMP_DIR, exist_ok=True)
            gpx_path = os.path.join(TMP_DIR, 'run_%s.gpx' % uuid.uuid4().hex[:8])
            track.write_gpx(result['points'], gpx_path, dt=1.0)
        except OSError as exc:
            self._json({'ok': False, 'error': '無法寫入暫存檔：%s' % exc}, 500)
            return

        dev.invalidate_cache()
        chk = dev.ensure_ddi()
        if not chk.get('ok'):
            self._json(chk)
            return

        res = dev.play(gpx_path, result['duration'])
        if res.get('ok'):
            with DEV_LOCK:
                DEV_STATE['ddi'] = True
            res.update({
                'distance': result['distance'],
                'duration': result['duration'],
                'steps': result['steps'],
            })
        else:
            try:
                os.remove(gpx_path)
            except OSError:
                pass
        self._json(res)

    def _api_save_route(self):
        body = self._read_json()
        name = str(body.get('name') or '').strip()
        pts = body.get('points') or []
        if not name:
            self._json({'ok': False, 'error': '沒有名稱'}, 400)
            return
        if len(pts) < 2:
            self._json({'ok': False, 'error': '路線太短'}, 400)
            return

        wgs = [coords.gcj2wgs(p[1], p[0]) for p in pts]
        routes = load_routes()
        routes = [r for r in routes if r.get('name') != name]
        routes.append({
            'name': name,
            'points': [[round(p[0], 6), round(p[1], 6)] for p in wgs],
            'distance': round(coords.polyline_length_m(wgs), 1),
            'created': int(time.time()),
        })
        try:
            save_routes(routes)
        except OSError as exc:
            self._json({'ok': False, 'error': '存檔失敗：%s' % exc}, 500)
            return
        self._json({'ok': True, 'count': len(routes)})

    def _api_trajectory(self):
        body = self._read_json()
        path = body.get('path') or []
        if len(path) < 2:
            self._json({'ok': False, 'error': '路線太短'}, 400)
            return

        speed = float(body.get('speed', 5.3))
        jitter = float(body.get('jitter', 0.0))
        loop = bool(body.get('loop', False))
        times = int(body.get('times', 1))

        # 地圖座標是 GCJ-02，轉成 WGS-84 再算
        path_wgs = [coords.gcj2wgs(p[1], p[0]) for p in path]

        # 只有「手畫的線」才簡化（滑鼠取樣很密）；已保存的路線保持原樣
        if body.get('simplify'):
            path_wgs = track.simplify_rdp(path_wgs, 1.0)

        result = track.generate_trajectory(
            path_wgs, speed_ms=speed, jitter_m=jitter, loop=loop, times=times)

        pts_gcj = []
        for lat, lon in result['points']:
            glat, glon = coords.wgs2gcj(lat, lon)
            pts_gcj.append([round(glon, 6), round(glat, 6)])

        self._json({
            'ok': True,
            'path_gcj': pts_gcj,
            'distance': result['distance'],
            'path_len': result['path_len'],
            'duration': result['duration'],
            'steps': result['steps'],
        })


# ---------------------------------------------------------------- app

def serve(port=0):
    httpd = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    m = threading.Thread(target=device_monitor, daemon=True)
    m.start()
    return httpd, httpd.server_address[1]


def _screen_size():
    """螢幕邏輯尺寸；判斷不出來時用 1920x1080 當保守值"""
    if IS_WIN:
        try:
            import ctypes
            return (ctypes.windll.user32.GetSystemMetrics(0),
                    ctypes.windll.user32.GetSystemMetrics(1))
        except Exception:
            pass
    if IS_MAC:
        try:
            from AppKit import NSScreen
            f = NSScreen.mainScreen().frame()
            return (int(f.size.width), int(f.size.height))
        except Exception:
            pass
    return (1920, 1080)


def sanitize_window(w):
    """驗證記住的視窗幾何

    程式關閉時會記住視窗位置。但如果關閉當下視窗是最小化的，
    存下來的座標會是 -32000 這類離譜數值，下次啟動就會開出一個
    螢幕外、只有一百多像素的隱形視窗 —— 使用者會以為程式根本沒開。

    所以讀取時一律驗證：尺寸太小或位置離開畫面，就回到預設置中。
    """
    w = w or {}

    def _int(v, default=None):
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    width = _int(w.get('width'), 1280)
    height = _int(w.get('height'), 800)
    if width < 900 or height < 600:
        width, height = 1280, 800

    x = _int(w.get('x'))
    y = _int(w.get('y'))
    if x is None or y is None:
        return {'width': width, 'height': height, 'x': None, 'y': None}

    sw, sh = _screen_size()
    # 至少要有一部分（左上角算起 120x80）落在畫面內
    if x < 0 or y < 0 or x > sw - 120 or y > sh - 80:
        return {'width': width, 'height': height, 'x': None, 'y': None}

    return {'width': width, 'height': height, 'x': x, 'y': y}


def main():
    # 被當成 pymobiledevice3 CLI 使用（打包後的 exe 會用這個模式跑子行程）
    if '--pmd' in sys.argv:
        idx = sys.argv.index('--pmd')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
        for stream in (sys.stdout, sys.stderr):
            if stream is None:
                continue
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
        if sys.stdout is None:
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        if sys.stderr is None:
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')
        from pymobiledevice3.__main__ import main as pmd_main
        sys.exit(pmd_main())

    browser_mode = '--browser' in sys.argv
    try:
        fixed_port = int(os.environ.get('ER_PORT') or 0)
    except ValueError:
        fixed_port = 0
    httpd, port = serve(fixed_port)
    qs = os.environ.get('ER_QS', '')          # 開發用：可附加 ?selftest=1 之類的參數
    url = 'http://127.0.0.1:%d/%s' % (port, qs)
    print('EdgeRunners %s' % VERSION, flush=True)
    print('serving: %s' % url, flush=True)

    if browser_mode:
        import webbrowser
        webbrowser.open(url)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        return

    try:
        import webview
    except ImportError:
        print('未安裝 pywebview，改用瀏覽器模式。')
        import webbrowser
        webbrowser.open(url)
        threading.Event().wait()
        return

    # 驗證上次記住的視窗位置：最小化時存下的 -32000 這類座標會讓視窗開在螢幕外
    w = sanitize_window(cfg.get('window'))
    win_w = w['width']
    win_h = w['height']
    win_x = w['x']
    win_y = w['y']

    if win_x is None or win_y is None:
        try:
            sw, sh = _screen_size()
            win_x = max(0, (sw - win_w) // 2)
            win_y = max(0, (sh - win_h) // 2 - 20)
        except Exception:
            win_x = win_y = None

    window = webview.create_window(
        'EdgeRunners',
        url,
        width=win_w,
        height=win_h,
        x=win_x,
        y=win_y,
        min_size=(900, 600),
        text_select=False,
    )

    def on_closing():
        try:
            ww = int(window.width or 0)
            wh = int(window.height or 0)
            # 最小化時回報的尺寸極小，不要存（否則下次會開成隱形視窗）
            if ww >= 900 and wh >= 600:
                cfg.set(ww, 'window', 'width')
                cfg.set(wh, 'window', 'height')
                wx, wy = window.x, window.y
                try:
                    wx, wy = int(wx), int(wy)
                except (TypeError, ValueError):
                    wx = wy = None
                if wx is not None and wy is not None and wx >= 0 and wy >= 0:
                    cfg.set(wx, 'window', 'x')
                    cfg.set(wy, 'window', 'y')
            cfg.save()
        except Exception:
            pass
        return True

    try:
        window.events.closing += on_closing
    except Exception:
        pass

    debug = '--debug' in sys.argv
    if IS_WIN:
        try:
            webview.start(gui='edgechromium', debug=debug)
        except Exception as exc:
            print('edgechromium 後端啟動失敗（%s），改用預設後端。' % exc, flush=True)
            webview.start(debug=debug)
    else:
        # macOS 用 pywebview 預設的 Cocoa/WebKit 後端
        webview.start(debug=debug)
    httpd.shutdown()


if __name__ == '__main__':
    main()








