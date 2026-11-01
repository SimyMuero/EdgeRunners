# -*- coding: utf-8 -*-
"""GPX 讀取（只取 trkpt 的經緯度）"""

import re

_ATTR = re.compile(r'lat="(-?[\d.]+)"\s+lon="(-?[\d.]+)"')


def read_gpx_points(path):
    """回傳 [(lat, lon), ...]（WGS-84）"""
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()
    pts = []
    for m in _ATTR.finditer(text):
        try:
            pts.append((float(m.group(1)), float(m.group(2))))
        except ValueError:
            continue
    return pts
