# -*- coding: utf-8 -*-
"""解析 common_location.txt

支援兩種寫法（可混用）：

  1) 筆記式（目前使用者的檔案就是這種）
         台北 101
         pymobiledevice3 developer dvt simulate-location set 25.0339 121.5654 --userspace

  2) 精簡式
         名稱,緯度,經度

檔案第一行可加 `#coord=gcj02` 切換座標系，預設為 wgs84
（因為 set 指令吃的就是 GPS 座標）。
"""

import os
import re

_NUM = re.compile(r'^-?\d+(\.\d+)?$')


def _read_text(path):
    for enc in ('utf-8-sig', 'utf-8', 'cp950', 'gbk'):
        try:
            with open(path, 'r', encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError:
            return None
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except OSError:
        return None


def _parse_set_line(line):
    """從 `pymobiledevice3 ... simulate-location set ... lat lon` 取出 (lat, lon)"""
    if 'simulate-location' not in line or ' set' not in line:
        return None
    tokens = line.split()
    try:
        idx = tokens.index('set')
    except ValueError:
        return None
    rest = [t for t in tokens[idx + 1:] if not t.startswith('--')]
    if len(rest) < 2:
        return None
    a, b = rest[-2], rest[-1]
    if not (_NUM.match(a) and _NUM.match(b)):
        return None
    return float(a), float(b)


def load_common_locations(path):
    """回傳 [{name, lat, lon, source}]，lat/lon 為檔案中標示的座標系"""
    if not path or not os.path.exists(path):
        return []

    text = _read_text(path)
    if text is None:
        return []

    crs = 'wgs84'
    out = []
    seen = set()
    last_name = None

    for raw in text.splitlines():
        line = raw.strip()

        if not line:
            continue

        if line.startswith('#'):
            m = re.match(r'^#\s*coord\s*=\s*(\w+)', line, re.IGNORECASE)
            if m:
                crs = m.group(1).lower()
            continue

        # 寫法 2：名稱,緯度,經度
        if ',' in line and not line.lower().startswith('pymobiledevice3'):
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 3 and _NUM.match(parts[1]) and _NUM.match(parts[2]):
                name = parts[0]
                lat, lon = float(parts[1]), float(parts[2])
                if name and name not in seen:
                    seen.add(name)
                    out.append({'name': name, 'lat': lat, 'lon': lon, 'source': 'csv'})
                continue

        # 寫法 1：指令行 + 上一行名稱
        coords = _parse_set_line(line)
        if coords is not None:
            name = last_name
            if name and name not in seen:
                seen.add(name)
                out.append({'name': name, 'lat': coords[0], 'lon': coords[1], 'source': 'note'})
            last_name = None
            continue

        # 更新「候選名稱」
        lowered = line.lower()
        if ('pymobiledevice3' in lowered
                or lowered.startswith('python')
                or line.endswith(':')
                or line.endswith('：')
                or '\\' in line):
            continue
        last_name = line

    for item in out:
        item['crs'] = crs
    return out
