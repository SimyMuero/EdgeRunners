# -*- coding: utf-8 -*-
"""軌跡生成：把「畫出來的折線」變成「每秒一個點的運動軌跡」

與先前驗證過的 GPX 生成器同一套邏輯：
  - 按速度做等弧長重採樣（每秒一個點）
  - 疊加慢速漂移 + 高頻抖動
  - 支援閉環與重複圈數
"""

import math
import random

from . import coords


def write_gpx(points_wgs, path, dt=1.0, start=None):
    """把 [[lat, lon], ...] 寫成每秒一點的 GPX 檔

    pymobiledevice3 的 play 會依 <time> 的間隔決定節奏，所以時間戳一定要寫。
    """
    import datetime as _dt

    if start is None:
        start = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<gpx version="1.1" creator="EdgeRunners" xmlns="http://www.topografix.com/GPX/1/1">',
             '  <trk>', '    <name>EdgeRunners</name>', '    <trkseg>']
    for i, p in enumerate(points_wgs):
        t = start + _dt.timedelta(seconds=i * dt)
        lines.append('      <trkpt lat="%.6f" lon="%.6f"><time>%sZ</time></trkpt>'
                     % (p[0], p[1], t.strftime('%Y-%m-%dT%H:%M:%S')))
    lines += ['    </trkseg>', '  </trk>', '</gpx>']

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    return path


def simplify_rdp(pts, tolerance_m):
    """Douglas-Peucker 簡化（pts: [(lat, lon)]）"""
    if len(pts) < 3:
        return list(pts)

    lat0 = sum(p[0] for p in pts) / len(pts)
    xy = coords.to_local_xy(pts, lat0)
    keep = [False] * len(xy)
    keep[0] = keep[-1] = True
    stack = [(0, len(xy) - 1)]

    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        ax, ay = xy[i]
        bx, by = xy[j]
        dx, dy = bx - ax, by - ay
        seg = math.hypot(dx, dy)
        best_d, best_k = -1.0, -1
        for k in range(i + 1, j):
            px, py = xy[k]
            if seg < 1e-9:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs((px - ax) * dy - (py - ay) * dx) / seg
            if d > best_d:
                best_d, best_k = d, k
        if best_d > tolerance_m:
            keep[best_k] = True
            stack.append((i, best_k))
            stack.append((best_k, j))

    return [pts[i] for i in range(len(pts)) if keep[i]]


class _Path:
    """局部平面上的折線，可按弧長取點與法向量"""

    def __init__(self, xy):
        self.xy = xy
        self.cum = [0.0]
        for i in range(len(xy) - 1):
            dx = xy[i + 1][0] - xy[i][0]
            dy = xy[i + 1][1] - xy[i][1]
            self.cum.append(self.cum[-1] + math.hypot(dx, dy))
        self.length = self.cum[-1]

    def at(self, s, closed):
        if self.length <= 1e-9:
            x, y = self.xy[0]
            return x, y, 0.0, 1.0
        if closed:
            s = s % self.length
        else:
            s = min(max(s, 0.0), self.length)

        lo, hi = 0, len(self.cum) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if self.cum[mid] <= s:
                lo = mid + 1
            else:
                hi = mid
        i = max(0, min(len(self.xy) - 2, lo - 1))

        a = self.xy[i]
        b = self.xy[i + 1]
        seg = self.cum[i + 1] - self.cum[i]
        t = 0.0 if seg <= 0 else (s - self.cum[i]) / seg
        x = a[0] + (b[0] - a[0]) * t
        y = a[1] + (b[1] - a[1]) * t
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1.0
        return x, y, -dy / d, dx / d


def generate_trajectory(path_wgs, speed_ms, jitter_m=0.0, loop=False, times=1,
                        dt=1.0, seed=None):
    """path_wgs: [(lat, lon)] WGS-84 -> 軌跡資料

    回傳 dict:
        points     [[lat, lon], ...]  每秒一點（WGS-84）
        distance   實際路徑總長（含閉環與圈數，公尺）
        path_len   單趟長度（公尺）
        duration   秒數
        steps      點數
    """
    pts = [p for p in path_wgs if p and len(p) >= 2]
    if len(pts) < 2:
        return {'points': [], 'distance': 0.0, 'path_len': 0.0,
                'duration': 0.0, 'steps': 0}

    closed_path = list(pts)
    if loop and closed_path[0] != closed_path[-1]:
        closed_path.append(closed_path[0])

    lat0 = sum(p[0] for p in closed_path) / len(closed_path)
    xy = coords.to_local_xy(closed_path, lat0)
    path = _Path(xy)
    path_len = path.length

    if path_len <= 1e-6:
        return {'points': [], 'distance': 0.0, 'path_len': 0.0,
                'duration': 0.0, 'steps': 0}

    times = max(1, int(times)) if loop else 1
    total = path_len * times

    speed_ms = max(0.1, float(speed_ms))
    steps = int(round(total / (speed_ms * dt)))
    steps = max(2, steps)

    rng = random.Random(seed)
    jitter_m = max(0.0, float(jitter_m))

    # 慢速漂移：週期約總長的 1/8，最少 80 公尺
    wander_period = max(80.0, total / 8.0)
    wander_phase = rng.uniform(0, 2 * math.pi)
    wander_amp = jitter_m

    lat_ou = 0.0
    ou_sigma = jitter_m * 0.32
    ou_clip = jitter_m * 1.5

    out_xy = []
    for i in range(steps):
        s = i * speed_ms * dt
        x, y, nx, ny = path.at(s, closed=loop)
        travelled = s

        if jitter_m > 0:
            wander = wander_amp * math.sin(wander_phase + travelled / wander_period * 2 * math.pi)
            lat_ou = lat_ou * 0.88 + rng.gauss(0, ou_sigma * 0.35)
            lat_ou = max(-ou_clip, min(ou_clip, lat_ou))
            lateral = wander + lat_ou
            x += nx * lateral
            y += ny * lateral

        out_xy.append((x, y))

    out_pts = coords.from_local_xy(out_xy, lat0)

    return {
        'points': [[round(p[0], 6), round(p[1], 6)] for p in out_pts],
        'distance': round(total, 1),
        'path_len': round(path_len, 1),
        'duration': round(steps * dt, 1),
        'steps': steps,
        'times': times,
        'loop': bool(loop),
    }
