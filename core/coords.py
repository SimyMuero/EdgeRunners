# -*- coding: utf-8 -*-
"""座標轉換：WGS-84 <-> GCJ-02 <-> BD-09

與 C:\\iPhoneGPS\\coord_convert.py 使用同一套演算法（已驗證往返誤差 0.00 m）。
所有函數的參數順序一律是 (lat, lon)，回傳也是 (lat, lon)。
"""

import math

_A = 6378245.0
_EE = 0.00669342162296594323
_X_PI = math.pi * 3000.0 / 180.0

R_EARTH = 6371000.0


def out_of_china(lat, lon):
    return not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271)


def _tf_lat(x, y):
    r = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    r += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    r += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    r += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return r


def _tf_lon(x, y):
    r = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    r += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    r += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    r += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return r


def wgs2gcj(lat, lon):
    if out_of_china(lat, lon):
        return lat, lon
    dlat = _tf_lat(lon - 105.0, lat - 35.0)
    dlon = _tf_lon(lon - 105.0, lat - 35.0)
    rad = lat / 180.0 * math.pi
    magic = 1 - _EE * math.sin(rad) ** 2
    sq = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (magic * sq) * math.pi)
    dlon = (dlon * 180.0) / (_A / sq * math.cos(rad) * math.pi)
    return lat + dlat, lon + dlon


def gcj2wgs(lat, lon, iterations=30):
    if out_of_china(lat, lon):
        return lat, lon
    wlat, wlon = lat, lon
    for _ in range(iterations):
        glat, glon = wgs2gcj(wlat, wlon)
        wlat -= glat - lat
        wlon -= glon - lon
    return wlat, wlon


def gcj2bd(lat, lon):
    z = math.sqrt(lon * lon + lat * lat) + 0.00002 * math.sin(lat * _X_PI)
    theta = math.atan2(lat, lon) + 0.000003 * math.cos(lon * _X_PI)
    return z * math.sin(theta) + 0.006, z * math.cos(theta) + 0.0065


def bd2gcj(lat, lon):
    x, y = lon - 0.0065, lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * _X_PI)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * _X_PI)
    return z * math.sin(theta), z * math.cos(theta)


def wgs2bd(lat, lon):
    return gcj2bd(*wgs2gcj(lat, lon))


def bd2wgs(lat, lon):
    return gcj2wgs(*bd2gcj(lat, lon), iterations=30)


def distance_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH * math.asin(math.sqrt(max(0.0, h)))


def polyline_length_m(pts):
    """pts: [(lat, lon), ...]"""
    total = 0.0
    for i in range(len(pts) - 1):
        total += distance_m(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
    return total


def to_local_xy(pts, lat0):
    """經緯度 -> 局部平面公尺（以 lat0 為基準緯度）"""
    k = math.pi * R_EARTH / 180.0
    cx = k * math.cos(math.radians(lat0))
    return [(p[1] * cx, p[0] * k) for p in pts]


def from_local_xy(xy, lat0):
    k = math.pi * R_EARTH / 180.0
    cx = k * math.cos(math.radians(lat0))
    return [(y / k, x / cx) for x, y in xy]
