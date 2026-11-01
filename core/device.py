# -*- coding: utf-8 -*-
"""iPhone 裝置控制：包裝 pymobiledevice3 命令列

三個關鍵設計（都是踩過坑才定下來的）：

  1. 全域 CLI 鎖
     每個 pymobiledevice3 指令都會建立一條 userspace tunnel（wintun 介面）。
     兩個指令同時跑會互搶，導致其中一個卡死或失敗。所以所有指令一律排隊。

  2. 忙碌旗標（_busy）
     注入或模擬期間會有一個長駐子行程持有 tunnel。這段時間**絕對不能**
     再跑任何其他 CLI（尤其是背景監控），否則會把長駐行程踢掉。

  3. 輸出即時排空 + 錯誤偵測
     子行程的 stdout 用獨立執行緒持續讀取。不讀的話 pipe 緩衝區（64KB）
     寫滿後子行程會阻塞，模擬就會「跑到一半不動」。
     同時可以從輸出裡即時發現 Traceback，避免行程沒死但其實失敗了。
"""

import atexit
import collections
import json
import os
import subprocess
import sys
import threading
import time

_FATAL_MARKERS = ('Traceback', 'FileNotFoundError', 'ModuleNotFoundError',
                  'ImportError', ' ERROR ', 'Error:')


def _python_exe():
    exe = sys.executable
    if os.path.basename(exe).lower().startswith('pythonw'):
        cand = os.path.join(os.path.dirname(exe), 'python.exe')
        if os.path.exists(cand):
            return cand
    return exe


def _cmd(*args):
    # 打包成 exe 之後沒有 python 可呼叫，改用自己（--pmd 模式）當 CLI
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--pmd'] + list(args)
    return [_python_exe(), '-m', 'pymobiledevice3'] + list(args)


def _env():
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    env['PYTHONUNBUFFERED'] = '1'
    return env


CREATION_FLAGS = 0
if os.name == 'nt':
    CREATION_FLAGS = 0x08000000  # CREATE_NO_WINDOW


def _extract_json(text):
    s = text.find('[')
    e = text.rfind(']')
    if s < 0 or e <= s:
        s = text.find('{')
        e = text.rfind('}')
    if s < 0 or e <= s:
        return None
    try:
        return json.loads(text[s:e + 1])
    except ValueError:
        return None


class DeviceManager:
    def __init__(self):
        self.lock = threading.RLock()
        self._cli_lock = threading.Lock()      # 一次只跑一個 CLI
        self._busy = threading.Event()         # 有長駐行程（set / play）時為 True
        self._inject_proc = None
        self._play_proc = None
        self._out = collections.deque(maxlen=400)
        self._sim = None
        self._ddi_cache = (0.0, False)
        atexit.register(self.shutdown)

    # ---------------- 內部工具 ----------------

    def busy(self):
        return self._busy.is_set()

    def _output_text(self):
        return ''.join(self._out)

    def _clear_output(self):
        self._out.clear()

    def _start_reader(self, proc):
        """持續排空子行程輸出，避免 pipe 寫滿造成阻塞"""
        out = self._out

        def _reader():
            try:
                while True:
                    chunk = proc.stdout.readline()
                    if not chunk:
                        break
                    out.append(chunk.decode('utf-8', 'replace'))
            except Exception:
                pass

        t = threading.Thread(target=_reader, daemon=True)
        t.start()
        return t

    def run(self, args, timeout=90):
        """執行一次性命令（會排隊，避免與長駐行程搶 tunnel）"""
        if not self._cli_lock.acquire(timeout=timeout + 10):
            return 124, '', '裝置忙碌中（另一個指令尚未結束）'
        try:
            p = subprocess.run(args, capture_output=True, timeout=timeout,
                               env=_env(), creationflags=CREATION_FLAGS)
            return (p.returncode,
                    (p.stdout or b'').decode('utf-8', 'replace'),
                    (p.stderr or b'').decode('utf-8', 'replace'))
        except subprocess.TimeoutExpired:
            return 124, '', 'timeout'
        except FileNotFoundError as exc:
            return 127, '', str(exc)
        finally:
            self._cli_lock.release()

    def _spawn_long(self, args, wait=5.0):
        """啟動長駐子行程並確認它沒有立刻失敗

        回傳 (proc, error)
        """
        self._clear_output()
        try:
            proc = subprocess.Popen(
                args, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                env=_env(), creationflags=CREATION_FLAGS,
            )
        except OSError as exc:
            return None, '無法啟動 pymobiledevice3：%s' % exc

        self._start_reader(proc)
        self._busy.set()

        time.sleep(wait)
        text = self._output_text()
        fatal = any(m in text for m in _FATAL_MARKERS)

        if proc.poll() is not None or fatal:
            self._kill(proc)
            self._busy.clear()
            return None, _friendly_error(text) or '指令失敗（無輸出）'

        return proc, None

    def _kill(self, proc):
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except Exception:
            pass
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass

    # ---------------- 查詢 ----------------

    def list_devices(self):
        code, out, err = self.run(_cmd('usbmux', 'list'), timeout=30)
        data = _extract_json(out)
        return data if isinstance(data, list) else []

    def device_summary(self):
        """回傳裝置資訊，並附帶 usbmuxd 是否通（usbmux_ok）

        usbmux_ok 才是「這台電腦能不能跟 iPhone 溝通」的唯一真相：
        有些電腦沒裝 iTunes 卻有第三方工具（愛思助手等）裝好了服務，
        有些電腦裝了 iTunes 但服務沒註冊成功 —— 只看服務名稱會誤判。
        """
        code, out, err = self.run(_cmd('usbmux', 'list'), timeout=30)
        text = (out or '') + (err or '')
        ok = (code == 0) and ('Failed to connect to usbmuxd' not in text)

        data = _extract_json(out) if ok else None
        devs = data if isinstance(data, list) else []

        if not devs:
            return {'connected': False, 'devices': [], 'usbmux_ok': ok}

        d = devs[0]
        return {
            'connected': True,
            'usbmux_ok': True,
            'name': d.get('DeviceName') or 'iPhone',
            'ios': d.get('ProductVersion') or '',
            'model': d.get('ProductType') or '',
            'udid': d.get('UniqueDeviceID') or d.get('Identifier') or '',
            'connection': d.get('ConnectionType') or '',
            'count': len(devs),
        }

    def ddi_mounted(self, use_cache=True, ttl=300):
        """檢查開發者映像檔是否已掛載

        ⚠️ 這個查詢會建立 tunnel，所以：
           · 有長駐行程在跑時直接回傳上次結果（絕不打擾）
           · 快取時間拉長到 5 分鐘
        """
        if self.busy():
            return self._ddi_cache[1]
        now = time.time()
        if use_cache and now - self._ddi_cache[0] < ttl:
            return self._ddi_cache[1]

        code, out, err = self.run(_cmd('mounter', 'list', '--userspace'), timeout=60)
        mounted = False
        data = _extract_json(out)
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                if item.get('PersonalizedImageType') == 'DeveloperDiskImage':
                    mounted = True
                elif item.get('MountPath') == '/System/Developer':
                    mounted = True
                elif item.get('ImageType') == 'Developer':
                    mounted = True
        self._ddi_cache = (now, mounted)
        return mounted

    def invalidate_cache(self):
        self._ddi_cache = (0.0, False)

    # ---------------- 前置檢查 ----------------

    def ensure_ddi(self):
        """確認映像檔已掛載，沒有就自動掛（首次 30~90 秒）"""
        if self.busy():
            return {'ok': True, 'mounted': True}
        if self.ddi_mounted(use_cache=False):
            return {'ok': True, 'mounted': True}

        code, out, err = self.run(_cmd('mounter', 'auto-mount', '--userspace'), timeout=200)
        text = (out or '') + (err or '')
        self.invalidate_cache()

        if code == 0 and 'Traceback' not in text:
            self._ddi_cache = (time.time(), True)
            return {'ok': True, 'mounted': True}
        if 'DeviceLocked' in text:
            return {'ok': False, 'error': '手機鎖住了。請解鎖並保持螢幕亮著，再試一次。'}
        if 'developer mode' in text.lower():
            return {'ok': False, 'error': '手機沒開啟「開發者模式」。\n設定 → 隱私權與安全性 → 開發者模式。'}
        return {'ok': False, 'error': _friendly_error(text)}

    # ---------------- 定位 ----------------

    def inject(self, lat, lon):
        with self.lock:
            self._kill_play()      # 模擬進行中就停掉，避免兩個 tunnel 打架
            self._kill_inject()
            self._sim = None

            args = _cmd('developer', 'dvt', 'simulate-location', 'set',
                        '--userspace', '--', '%.6f' % lat, '%.6f' % lon)
            proc, err = self._spawn_long(args, wait=6.0)
            if err:
                return {'ok': False, 'error': err}

            self._inject_proc = proc
            return {'ok': True, 'lat': lat, 'lon': lon}

    def clear_location(self):
        with self.lock:
            self._kill_inject()
            code, out, err = self.run(
                _cmd('developer', 'dvt', 'simulate-location', 'clear', '--userspace'),
                timeout=60)
            text = (out or '') + (err or '')
            if code != 0 or 'Traceback' in text:
                if 'DeviceLocked' in text:
                    return {'ok': False, 'error': '手機鎖住了，請解鎖後再試'}
                return {'ok': False, 'error': _friendly_error(text)}
            return {'ok': True}

    def injecting(self):
        with self.lock:
            return self._inject_proc is not None and self._inject_proc.poll() is None

    def _kill_inject(self):
        p = self._inject_proc
        self._inject_proc = None
        self._kill(p)
        if p is not None:
            self._busy.clear()

    # ---------------- 模擬 ----------------

    def play(self, gpx_path, duration):
        with self.lock:
            self._kill_play()
            self._kill_inject()    # 先收掉定點注入，兩者不能並存
            self._sim = None

            args = _cmd('developer', 'dvt', 'simulate-location', 'play',
                        gpx_path, '--userspace')
            proc, err = self._spawn_long(args, wait=6.0)
            if err:
                return {'ok': False, 'error': err}

            self._play_proc = proc
            self._sim = {'start': time.time(), 'duration': float(duration), 'gpx': gpx_path}
            return {'ok': True, 'duration': float(duration)}

    def sim_status(self):
        with self.lock:
            if not self._sim:
                return {'running': False}

            proc = self._play_proc
            elapsed = time.time() - self._sim['start']
            total = self._sim['duration']

            text = self._output_text()
            fatal = any(m in text for m in _FATAL_MARKERS)

            if proc is not None and proc.poll() is None and fatal:
                self._kill_play()
                return {'running': False, 'elapsed': round(elapsed, 1),
                        'duration': round(total, 1),
                        'percent': round(min(100.0, elapsed / total * 100) if total else 0, 1),
                        'error': _friendly_error(text) or '模擬異常中止'}

            running = proc is not None and proc.poll() is None

            # 播完後 CLI 會停在「Press ENTER to exit>」，主動收掉
            if running and total > 0 and elapsed > total + 1.5:
                self._kill_play()
                return {'running': False, 'elapsed': round(total, 1),
                        'duration': round(total, 1), 'percent': 100.0, 'error': None}

            err = None
            if proc is not None and proc.poll() is not None:
                if proc.returncode not in (0, None):
                    err = _friendly_error(text) or '模擬中斷'
                running = False
                self._play_proc = None
                self._busy.clear()

            return {
                'running': running,
                'elapsed': round(min(elapsed, total), 1),
                'duration': round(total, 1),
                'percent': round(min(100.0, elapsed / total * 100.0), 1) if total > 0 else 0,
                'error': err,
            }

    def stop_play(self):
        with self.lock:
            self._kill_play()
            self._sim = None
            return {'ok': True}

    def _kill_play(self):
        p = self._play_proc
        self._play_proc = None
        self._kill(p)
        if p is not None:
            self._busy.clear()

    # ---------------- 收尾 ----------------

    def shutdown(self):
        with self.lock:
            self._kill_play()
            self._kill_inject()


def _friendly_error(text):
    t = text or ''
    low = t.lower()
    if 'devicelocked' in low:
        return '手機鎖住了（DeviceLocked）。請解鎖並保持螢幕亮著，再試一次。'
    if 'developer mode' in low or 'developermode' in low:
        return '手機沒開啟「開發者模式」。請到 設定 → 隱私權與安全性 → 開發者模式。'
    if 'no device' in low or 'not found' in low or 'usbmux has no device' in low:
        return '找不到裝置。請確認 USB 已連接、手機已解鎖並按過「信任」。'
    if 'not connected' in low:
        return '找不到裝置。請確認 USB 已連接、手機已解鎖並按過「信任」。'
    if 'filenotfounderror' in low or 'modulenotfounderror' in low:
        return '程式檔案不完整（可能是打包缺漏）。請重新解壓或回報這個錯誤：\n' + t.strip()[-300:]
    if 'tunneld' in low or 'unable to connect' in low:
        return '無法建立 tunnel。請重新啟動程式再試。'
    if 'timeout' in low:
        return '指令逾時，請確認手機連線後重試。'
    lines = [ln.strip() for ln in t.strip().splitlines() if ln.strip()]
    tail = lines[-4:] if lines else ['未知錯誤']
    return '\n'.join(tail)
