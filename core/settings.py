# -*- coding: utf-8 -*-
"""設定檔讀寫（config.json），並提供安全的預設值合併"""

import copy
import json
import os

DEFAULTS = {
    'amap': {'key': '', 'jscode': ''},
    'window': {'width': 1280, 'height': 800, 'x': None, 'y': None, 'maximized': False},
    'map': {'lng': 120.0771, 'lat': 30.3074, 'zoom': 16},
    'common_location_file': r'C:\iPhoneGPS\common_location.txt',
    'common_list': [],
    'defaults': {'speed_ms': 5.3, 'jitter_level': 1.2, 'loop': False, 'times': 1},
}


def _deep_merge(base, override):
    out = copy.deepcopy(base)
    if not isinstance(override, dict):
        return out
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Settings:
    def __init__(self, path):
        self.path = path
        self.data = copy.deepcopy(DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            self.data = _deep_merge(DEFAULTS, raw)
        except (OSError, ValueError):
            self.data = copy.deepcopy(DEFAULTS)

    def save(self):
        tmp = self.path + '.tmp'
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False

    def get(self, *keys, default=None):
        cur = self.data
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    def set(self, value, *keys):
        cur = self.data
        for k in keys[:-1]:
            if not isinstance(cur.get(k), dict):
                cur[k] = {}
            cur = cur[k]
        cur[keys[-1]] = value
