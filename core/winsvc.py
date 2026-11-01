# -*- coding: utf-8 -*-
"""Windows 環境檢查

EdgeRunners 在 Windows 上要靠 Apple 的「Apple Mobile Device Service」才看得到 iPhone，
這個服務是安裝 iTunes 時一起裝的。沒有它就完全連不上，所以開機就要檢查。

用 ctypes 直接問 Windows 服務管理員，不呼叫 sc.exe（避免中文系統的輸出格式問題）。
"""

import ctypes
import sys
from ctypes import wintypes

APPLE_SERVICE = 'Apple Mobile Device Service'

_SC_MANAGER_CONNECT = 0x0001
_SERVICE_QUERY_STATUS = 0x0004
_ERROR_SERVICE_DOES_NOT_EXIST = 1060

_SERVICE_STOPPED = 0x00000001
_SERVICE_RUNNING = 0x00000004


class _SERVICE_STATUS(ctypes.Structure):
    _fields_ = [
        ('dwServiceType', wintypes.DWORD),
        ('dwCurrentState', wintypes.DWORD),
        ('dwControlsAccepted', wintypes.DWORD),
        ('dwWin32ExitCode', wintypes.DWORD),
        ('dwServiceSpecificExitCode', wintypes.DWORD),
        ('dwCheckPoint', wintypes.DWORD),
        ('dwWaitHint', wintypes.DWORD),
    ]


def _probe(service_name):
    """回傳 ('running'|'stopped'|'missing'|'unknown', 原始狀態碼)"""
    if sys.platform != 'win32':
        return 'running', 0

    try:
        advapi = ctypes.WinDLL('advapi32', use_last_error=True)
        advapi.OpenSCManagerW.restype = wintypes.HANDLE
        advapi.OpenSCManagerW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
        advapi.OpenServiceW.restype = wintypes.HANDLE
        advapi.OpenServiceW.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR, wintypes.DWORD]
        advapi.QueryServiceStatus.restype = wintypes.BOOL
        advapi.QueryServiceStatus.argtypes = [wintypes.HANDLE,
                                             ctypes.POINTER(_SERVICE_STATUS)]
        advapi.CloseServiceHandle.restype = wintypes.BOOL
        advapi.CloseServiceHandle.argtypes = [wintypes.HANDLE]

        scm = advapi.OpenSCManagerW(None, None, _SC_MANAGER_CONNECT)
        if not scm:
            return 'unknown', ctypes.get_last_error()
        try:
            handle = advapi.OpenServiceW(scm, service_name, _SERVICE_QUERY_STATUS)
            if not handle:
                code = ctypes.get_last_error()
                if code == _ERROR_SERVICE_DOES_NOT_EXIST:
                    return 'missing', code
                return 'unknown', code
            try:
                status = _SERVICE_STATUS()
                if not advapi.QueryServiceStatus(handle, ctypes.byref(status)):
                    return 'unknown', ctypes.get_last_error()
                if status.dwCurrentState == _SERVICE_RUNNING:
                    return 'running', status.dwCurrentState
                if status.dwCurrentState == _SERVICE_STOPPED:
                    return 'stopped', status.dwCurrentState
                return 'stopped', status.dwCurrentState
            finally:
                advapi.CloseServiceHandle(handle)
        finally:
            advapi.CloseServiceHandle(scm)
    except Exception:
        return 'unknown', 0


def apple_mobile_service():
    """檢查 Apple Mobile Device Service

    回傳 {'installed': bool, 'running': bool, 'state': str}
    """
    state, code = _probe(APPLE_SERVICE)
    return {
        'installed': state in ('running', 'stopped'),
        'running': state == 'running',
        'state': state,
        'code': code,
    }


def apple_software_present():
    """電腦上是否有任何 Apple 行動裝置軟體的痕跡

    iTunes 不是唯一會安裝 Apple Mobile Device Service 的軟體：
      · Microsoft Store 的「Apple Devices」
      · 愛思助手、iTools 等第三方 iOS 工具
      · 筆電預裝的舊版 iTunes
    所以「找不到服務」不能直接等於「沒裝 iTunes」。
    """
    if sys.platform != 'win32':
        return False

    import os
    import winreg

    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Apple Inc.'),
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Apple Inc.'),
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\iTunes'),
    ]
    for root, path in keys:
        try:
            winreg.CloseKey(winreg.OpenKey(root, path))
            return True
        except OSError:
            continue

    paths = [
        os.path.join(os.environ.get('ProgramFiles', r'C:\Program Files'),
                     r'Common Files\Apple\Mobile Device Support'),
        os.path.join(os.environ.get('ProgramFiles', r'C:\Program Files'), r'iTunes'),
        os.path.join(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
                     r'Common Files\Apple\Mobile Device Support'),
    ]
    for p in paths:
        try:
            if os.path.isdir(p):
                return True
        except OSError:
            continue
    return False


def collect_report():
    """收集完整的環境證據，讓使用者可以複製回報

    為什麼需要：朋友 A 從官網裝了 iTunes 卻找不到服務，這種情況光靠
    「有沒有某個服務」猜不出原因，必須看實際證據（服務清單、檔案、
    已安裝產品、鎖定服務的埠號）。
    """
    import os
    import socket
    import winreg

    report = {}
    report['service'] = apple_mobile_service()
    report['apple_software_present'] = apple_software_present()

    # 1) 系統裡所有名字含 Apple / iPod 的服務
    found_services = []
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services')
        i = 0
        while True:
            try:
                name = winreg.EnumKey(key, i)
            except OSError:
                break
            i += 1
            low = name.lower()
            if 'apple' in low or 'ipod' in low:
                found_services.append(name)
        winreg.CloseKey(key)
    except OSError:
        pass
    report['apple_services'] = found_services

    # 2) 服務執行檔是否存在
    import glob
    exe_paths = []
    for base in (os.environ.get('ProgramFiles', r'C:\Program Files'),
                 os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')):
        pat = os.path.join(base, r'Common Files\Apple\Mobile Device Support\*.exe')
        try:
            exe_paths.extend(glob.glob(pat))
        except OSError:
            pass
    report['mobile_device_files'] = exe_paths

    # 3) 已安裝的 Apple 相關產品
    products = []
    uninstall_roots = [
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
        (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
    ]
    for root, path in uninstall_roots:
        try:
            key = winreg.OpenKey(root, path)
        except OSError:
            continue
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(key, i)
            except OSError:
                break
            i += 1
            try:
                sk = winreg.OpenKey(key, sub)
                display, _ = winreg.QueryValueEx(sk, 'DisplayName')
                winreg.CloseKey(sk)
            except OSError:
                continue
            low = str(display).lower()
            if 'itunes' in low or 'apple' in low or 'bonjour' in low or 'ipod' in low:
                products.append(str(display))
        try:
            winreg.CloseKey(key)
        except OSError:
            pass
    report['apple_products'] = sorted(set(products))

    # 4) usbmuxd 的埠（27015）有沒有在聽
    listening = False
    try:
        s = socket.socket()
        s.settimeout(1.0)
        s.connect(('127.0.0.1', 27015))
        listening = True
        s.close()
    except OSError:
        listening = False
    report['usbmuxd_port_27015'] = listening

    return report


def format_report(report=None):
    """把報告排成可貼上回報的純文字"""
    r = report or collect_report()
    lines = ['--- EdgeRunners 環境診斷 ---']

    svc = r.get('service') or {}
    names = {'running': '執行中', 'stopped': '已停止',
             'missing': '不存在', 'unknown': '無法判斷'}
    lines.append('Apple Mobile Device Service：%s%s'
                 % (names.get(svc.get('state'), svc.get('state')),
                    '' if svc.get('state') != 'missing' else '（錯誤碼 %s）' % svc.get('code')))

    lines.append('usbmuxd 埠 27015：%s' % ('有在聽' if r.get('usbmuxd_port_27015') else '沒有回應'))
    lines.append('Apple 軟體痕跡：%s' % ('有' if r.get('apple_software_present') else '無'))

    services = r.get('apple_services') or []
    lines.append('系統中 Apple 相關服務：%s' % (', '.join(services) if services else '（無）'))

    files = r.get('mobile_device_files') or []
    lines.append('Mobile Device Support 執行檔：%s'
                 % (', '.join(files) if files else '（找不到）'))

    products = r.get('apple_products') or []
    lines.append('已安裝的 Apple 產品：')
    if products:
        for p in products:
            lines.append('  · ' + p)
    else:
        lines.append('  （無）')

    return '\n'.join(lines)


def diagnose():
    """連不上 usbmuxd 時，給出最貼近實情的說明"""
    info = apple_mobile_service()

    if info['state'] == 'running':
        return ('Apple Mobile Device Service 正在執行，但仍連不上手機通訊服務（usbmuxd）。\n'
                '請先重新開機；若還是不行，按 Win+R 輸入 services.msc，'
                '對「Apple Mobile Device Service」按右鍵 → 重新啟動。')

    if info['state'] == 'stopped':
        return ('Apple Mobile Device Service 存在但沒有在執行。\n'
                '按 Win+R 輸入 services.msc → 找到「Apple Mobile Device Service」→ 右鍵啟動，'
                '或直接重新開機。')

    if apple_software_present():
        return ('找不到 Apple Mobile Device Service，但電腦上確實裝了 Apple 的軟體。\n'
                '這通常是這個服務沒有安裝成功，或被清理軟體停用 / 移除了（iTunes 本體仍可正常使用）。\n'
                '建議依序試：\n'
                '  1. 控制台 → 程式和功能 → iTunes → 變更 → 修復\n'
                '  2. 仍不行就完整移除後重裝「官網版」iTunes\n'
                '  3. 重開機後再開本程式\n'
                '若想回報問題，請按下方「複製診斷資訊」，把內容貼給開發者。')

    return ('找不到 Apple 手機通訊服務（usbmuxd）。\n'
            '通常是這台電腦沒有安裝任何 Apple 行動裝置軟體。請安裝：\n'
            '  · iTunes 官網版：apple.com/itunes/download/win64\n'
            '  · 或 Microsoft Store 的「Apple Devices」\n'
            '裝完務必重新開機。\n'
            '（若你確定裝過了，請把「服務」視窗裡 Apple 開頭的項目截圖回報）')

