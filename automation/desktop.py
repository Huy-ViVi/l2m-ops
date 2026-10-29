"""Phần Windows của agent chạy ngầm: biểu tượng ở khay hệ thống, khoá chạy một bản, tự bật cùng Windows, cửa sổ log.

Chỉ dùng Win32 qua ctypes (không cần cài thêm thư viện). Tiến trình khác (agent.bat) gửi lệnh cho agent đang chạy
bằng PostMessage tới cửa sổ ẩn của khay, tìm theo tên lớp cửa sổ (mỗi thư mục dữ liệu một tên).
"""
from __future__ import annotations

import ctypes
import math
import os
import struct
import subprocess
import threading
import winreg
from ctypes import wintypes
from pathlib import Path
from typing import Callable

user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

WM_NULL, WM_DESTROY, WM_CLOSE, WM_COMMAND = 0x0000, 0x0002, 0x0010, 0x0111
WM_LBUTTONUP, WM_RBUTTONUP, WM_CONTEXTMENU = 0x0202, 0x0205, 0x007B
WM_USER, WM_APP = 0x0400, 0x8000
WM_TRAY, WM_REFRESH, WM_BALLOON = WM_APP + 1, WM_APP + 2, WM_APP + 3
NIN_BALLOONUSERCLICK = WM_USER + 5
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_INFO = 0x1, 0x2, 0x4, 0x10
NIIF_INFO, NIIF_WARNING = 0x1, 0x2
MF_STRING, MF_GRAYED, MF_CHECKED, MF_SEPARATOR = 0x0, 0x1, 0x8, 0x800
TPM_RIGHTBUTTON, TPM_NONOTIFY, TPM_RETURNCMD = 0x2, 0x80, 0x100
MB_YESNO, MB_ICONWARNING, MB_SETFOREGROUND, IDYES = 0x4, 0x30, 0x10000, 6
SM_CXSMICON = 49
ERROR_ALREADY_EXISTS, ERROR_CLASS_ALREADY_EXISTS = 183, 1410
SYNCHRONIZE = 0x00100000
CSIDL_STARTUP = 7

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
COLORS = {"idle": (46, 160, 67), "busy": (31, 111, 235), "warn": (227, 139, 26)}  # xanh lá / xanh dương / cam


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND), ("uID", wintypes.UINT), ("uFlags", wintypes.UINT),
                ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON), ("szTip", wintypes.WCHAR * 128),
                ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD), ("szInfo", wintypes.WCHAR * 256),
                ("uVersion", wintypes.UINT), ("szInfoTitle", wintypes.WCHAR * 64), ("dwInfoFlags", wintypes.DWORD),
                ("guidItem", GUID), ("hBalloonIcon", wintypes.HICON)]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON), ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH), ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


def _fn(dll, name: str, restype, *argtypes):
    f = getattr(dll, name)
    f.restype, f.argtypes = restype, argtypes
    return f


HWND, UINT, WPARAM, LPARAM = wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
DefWindowProcW = _fn(user32, "DefWindowProcW", LRESULT, HWND, UINT, WPARAM, LPARAM)
RegisterClassW = _fn(user32, "RegisterClassW", wintypes.ATOM, ctypes.POINTER(WNDCLASSW))
CreateWindowExW = _fn(user32, "CreateWindowExW", HWND, wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                      ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID)
DestroyWindow = _fn(user32, "DestroyWindow", wintypes.BOOL, HWND)
GetMessageW = _fn(user32, "GetMessageW", wintypes.BOOL, ctypes.POINTER(wintypes.MSG), HWND, UINT, UINT)
TranslateMessage = _fn(user32, "TranslateMessage", wintypes.BOOL, ctypes.POINTER(wintypes.MSG))
DispatchMessageW = _fn(user32, "DispatchMessageW", LRESULT, ctypes.POINTER(wintypes.MSG))
PostMessageW = _fn(user32, "PostMessageW", wintypes.BOOL, HWND, UINT, WPARAM, LPARAM)
PostQuitMessage = _fn(user32, "PostQuitMessage", None, ctypes.c_int)
FindWindowW = _fn(user32, "FindWindowW", HWND, wintypes.LPCWSTR, wintypes.LPCWSTR)
RegisterWindowMessageW = _fn(user32, "RegisterWindowMessageW", UINT, wintypes.LPCWSTR)
CreatePopupMenu = _fn(user32, "CreatePopupMenu", wintypes.HMENU)
AppendMenuW = _fn(user32, "AppendMenuW", wintypes.BOOL, wintypes.HMENU, UINT, ctypes.c_size_t, wintypes.LPCWSTR)
SetMenuDefaultItem = _fn(user32, "SetMenuDefaultItem", wintypes.BOOL, wintypes.HMENU, UINT, UINT)
TrackPopupMenu = _fn(user32, "TrackPopupMenu", ctypes.c_int, wintypes.HMENU, UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                     HWND, wintypes.LPVOID)
DestroyMenu = _fn(user32, "DestroyMenu", wintypes.BOOL, wintypes.HMENU)
GetCursorPos = _fn(user32, "GetCursorPos", wintypes.BOOL, ctypes.POINTER(wintypes.POINT))
SetForegroundWindow = _fn(user32, "SetForegroundWindow", wintypes.BOOL, HWND)
AllowSetForegroundWindow = _fn(user32, "AllowSetForegroundWindow", wintypes.BOOL, wintypes.DWORD)
MessageBoxW = _fn(user32, "MessageBoxW", ctypes.c_int, HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, UINT)
GetSystemMetrics = _fn(user32, "GetSystemMetrics", ctypes.c_int, ctypes.c_int)
CreateIconFromResourceEx = _fn(user32, "CreateIconFromResourceEx", wintypes.HICON, ctypes.c_char_p, wintypes.DWORD, wintypes.BOOL,
                               wintypes.DWORD, ctypes.c_int, ctypes.c_int, UINT)
DestroyIcon = _fn(user32, "DestroyIcon", wintypes.BOOL, wintypes.HICON)
Shell_NotifyIconW = _fn(shell32, "Shell_NotifyIconW", wintypes.BOOL, wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW))
SHGetFolderPathW = _fn(shell32, "SHGetFolderPathW", ctypes.c_long, HWND, ctypes.c_int, wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR)
GetModuleHandleW = _fn(kernel32, "GetModuleHandleW", wintypes.HMODULE, wintypes.LPCWSTR)
CreateMutexW = _fn(kernel32, "CreateMutexW", wintypes.HANDLE, wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
OpenMutexW = _fn(kernel32, "OpenMutexW", wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)
CloseHandle = _fn(kernel32, "CloseHandle", wintypes.BOOL, wintypes.HANDLE)


# ---- chạy một bản --------------------------------------------------------------------
class SingleInstance:
    """Mutex có tên: agent giữ suốt lúc chạy; agent.bat mở lại thì biết agent đã chạy."""

    def __init__(self, name: str):
        self.name, self.handle = name, None

    def acquire(self) -> bool:
        ctypes.set_last_error(0)
        handle = CreateMutexW(None, False, self.name)
        if not handle:
            return False
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            CloseHandle(handle)
            return False
        self.handle = handle
        return True

    def release(self) -> None:
        if self.handle:
            CloseHandle(self.handle)
            self.handle = None


def instance_running(name: str) -> bool:
    handle = OpenMutexW(SYNCHRONIZE, False, name)
    if handle:
        CloseHandle(handle)
        return True
    return False


def post_command(class_name: str, command: int) -> bool:
    """Gửi lệnh menu (vd tắt agent) tới khay của agent đang chạy. False nếu không thấy."""
    hwnd = FindWindowW(class_name, None)
    return bool(hwnd) and bool(PostMessageW(hwnd, WM_COMMAND, command, 0))


# ---- tự bật cùng Windows (HKCU\...\Run: của riêng người dùng, không cần quyền admin) ------------
def _run_key() -> str:
    return os.environ.get("L2M_AUTOSTART_KEY") or RUN_KEY  # test đặt khoá tạm, không đụng khoá thật


def autostart_get(name: str) -> str | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _run_key()) as key:
            return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def autostart_set(name: str, command: str | None) -> None:
    """command=None: gỡ."""
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _run_key()) as key:
        if command:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass


CLASSES_KEY = r"Software\Classes"


def protocol_get(scheme: str) -> str | None:
    """Lệnh đang đăng ký cho link scheme:// (None nếu chưa có)."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"{CLASSES_KEY}\{scheme}\shell\open\command") as key:
            return winreg.QueryValueEx(key, "")[0]
    except OSError:
        return None


def protocol_set(scheme: str, command: str, app_name: str) -> None:
    """Link scheme://… (vd website bấm) chạy command. Đăng ký cho riêng người dùng (HKCU), không cần quyền admin.
    app_name: tên trình duyệt hiện khi hỏi "Mở ứng dụng?" (FriendlyAppName — thiếu thì Windows lấy tên pythonw)."""
    base = rf"{CLASSES_KEY}\{scheme}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f"URL:{app_name}")
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\shell\open") as key:
        winreg.SetValueEx(key, "FriendlyAppName", 0, winreg.REG_SZ, app_name)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\shell\open\command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)


def protocol_remove(scheme: str) -> None:
    base = rf"{CLASSES_KEY}\{scheme}"
    for sub in (r"\shell\open\command", r"\shell\open", r"\shell", ""):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, base + sub)
        except OSError:
            pass


def edge_installed() -> bool:
    """Microsoft Edge (Playwright dùng kênh msedge) — cùng các chỗ tools/setup.ps1 kiểm tra."""
    roots = [os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")]
    return any(r and (Path(r) / "Microsoft" / "Edge" / "Application" / "msedge.exe").is_file() for r in roots)


def chrome_installed() -> bool:
    roots = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")]
    return any(r and (Path(r) / "Google" / "Chrome" / "Application" / "chrome.exe").is_file() for r in roots)


def chromium_installed() -> bool:
    """Chromium riêng của Playwright (tải bằng "playwright install chromium" — agent không tự tải)."""
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or str(Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright")
    return any(Path(root).glob("chromium-*/chrome-win*/chrome.exe"))


def browser_installed(channel: str) -> bool:
    return {"msedge": edge_installed, "chrome": chrome_installed, "chromium": chromium_installed}.get(channel, edge_installed)()


def startup_folder() -> Path:
    buf = ctypes.create_unicode_buffer(260)
    SHGetFolderPathW(None, CSIDL_STARTUP, None, 0, buf)
    return Path(buf.value)


# ---- cửa sổ log ------------------------------------------------------------------------
def open_console(args: list[str], cwd: Path, env: dict) -> subprocess.Popen:
    """Mở cửa sổ console cổ điển (conhost) — Windows 11 mặc định mở bằng Windows Terminal, đóng tab ở đó
    không chắc tắt được tiến trình. Gọi được từ tiến trình không có console (pythonw)."""
    AllowSetForegroundWindow(0xFFFFFFFF)  # cho cửa sổ mới nổi lên trên (người dùng vừa bấm vào khay)
    return subprocess.Popen(["conhost.exe", *args], cwd=cwd, env=env)


def ask_yes_no(title: str, text: str) -> bool:
    return MessageBoxW(None, text, title, MB_YESNO | MB_ICONWARNING | MB_SETFOREGROUND) == IDYES


# ---- biểu tượng khay ---------------------------------------------------------------------
def _dot_icon(rgb: tuple[int, int, int]):
    """Chấm tròn màu trạng thái (vẽ bằng tay — không cần file .ico)."""
    size = GetSystemMetrics(SM_CXSMICON) or 16
    c, radius = (size - 1) / 2, size * 0.44
    dark = tuple(int(v * 0.6) for v in rgb)
    pixels = bytearray()
    for y in range(size - 1, -1, -1):  # bitmap của icon lưu từ dưới lên
        for x in range(size):
            d = math.hypot(x - c, y - c)
            alpha = max(0.0, min(1.0, radius + 0.5 - d))
            r, g, b = dark if d > radius - 1.5 else rgb  # viền đậm cho dễ thấy trên nền sáng
            pixels += bytes((b, g, r, int(alpha * 255)))
    mask = bytes(((size + 31) // 32 * 4) * size)
    header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, len(pixels) + len(mask), 0, 0, 0, 0)
    data = header + bytes(pixels) + mask
    return CreateIconFromResourceEx(data, len(data), True, 0x00030000, size, size, 0)


_windows: dict[int, "Tray"] = {}


@WNDPROC
def _dispatch(hwnd, msg, wparam, lparam):
    tray = _windows.get(hwnd)
    if tray is not None:
        handled = tray._on_message(hwnd, msg, wparam, lparam)
        if handled is not None:
            return handled
    return DefWindowProcW(hwnd, msg, wparam, lparam)


class Tray(threading.Thread):
    """Biểu tượng khay + menu chuột phải. Callback chạy trên luồng của khay — giữ ngắn.

    items(): danh sách (mã lệnh | None = vạch ngăn, chữ, đánh dấu, bấm được) dựng lại mỗi lần mở menu.
    on_click(): bấm chuột trái vào biểu tượng hoặc vào thông báo. on_command(mã): chọn mục menu / tiến trình khác gửi tới.
    """

    def __init__(self, class_name: str, tip: str, items: Callable[[], list], on_command: Callable[[int], None],
                 on_click: Callable[[], None], default_command: int | None = None, log: Callable[[str], None] = print):
        super().__init__(daemon=True, name="tray")
        self.class_name, self.items, self.on_command, self.on_click = class_name, items, on_command, on_click
        self.default_command, self.log = default_command, log
        self.tip, self.state = tip, "idle"
        self.hwnd = None
        self.shown = False
        self.ready = threading.Event()
        self._icons: dict[str, int] = {}
        self._balloon: tuple[str, str, bool] | None = None
        self._taskbar_created = RegisterWindowMessageW("TaskbarCreated")

    # -- gọi từ luồng khác --
    def set_status(self, state: str, tip: str) -> None:
        if (state, tip) != (self.state, self.tip):
            self.state, self.tip = state, tip
            if self.hwnd:
                PostMessageW(self.hwnd, WM_REFRESH, 0, 0)

    def notify(self, title: str, text: str, warning: bool = False) -> None:
        self._balloon = (title, text, warning)
        if self.hwnd:
            PostMessageW(self.hwnd, WM_BALLOON, 0, 0)

    def stop(self) -> None:
        if self.hwnd:
            PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
        self.join(5)

    # -- luồng khay --
    def run(self) -> None:
        try:
            hinst = GetModuleHandleW(None)
            wc = WNDCLASSW(lpfnWndProc=_dispatch, hInstance=hinst, lpszClassName=self.class_name)
            if not RegisterClassW(ctypes.byref(wc)) and ctypes.get_last_error() != ERROR_CLASS_ALREADY_EXISTS:
                raise ctypes.WinError(ctypes.get_last_error())
            hwnd = CreateWindowExW(0, self.class_name, self.class_name, 0, 0, 0, 0, 0, None, None, hinst, None)
            if not hwnd:
                raise ctypes.WinError(ctypes.get_last_error())
            _windows[hwnd] = self
            self.hwnd = hwnd
            self.shown = self._shell(NIM_ADD)
            self.ready.set()
            msg = wintypes.MSG()
            while GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                TranslateMessage(ctypes.byref(msg))
                DispatchMessageW(ctypes.byref(msg))
        except Exception as e:  # noqa: BLE001 — không có khay (vd phiên không có màn hình): agent vẫn chạy
            self.log(f"tray: {type(e).__name__}: {e}")
        finally:
            _windows.pop(self.hwnd, None)
            for icon in self._icons.values():
                DestroyIcon(icon)
            self.ready.set()

    def _icon(self) -> int:
        if self.state not in self._icons:
            self._icons[self.state] = _dot_icon(COLORS.get(self.state, COLORS["idle"]))
        return self._icons[self.state]

    def _data(self, flags: int) -> NOTIFYICONDATAW:
        nid = NOTIFYICONDATAW()
        nid.cbSize, nid.hWnd, nid.uID = ctypes.sizeof(NOTIFYICONDATAW), self.hwnd, 1
        nid.uFlags, nid.uCallbackMessage = flags, WM_TRAY
        nid.hIcon, nid.szTip = self._icon(), self.tip[:127]
        return nid

    def _shell(self, action: int) -> bool:
        return bool(Shell_NotifyIconW(action, ctypes.byref(self._data(NIF_MESSAGE | NIF_ICON | NIF_TIP))))

    def _safe(self, fn, *args) -> None:
        try:
            fn(*args)
        except Exception as e:  # noqa: BLE001 — lỗi trong callback không được làm sập vòng lặp khay
            self.log(f"tray: {type(e).__name__}: {e}")

    def _menu(self) -> None:
        menu = CreatePopupMenu()
        try:
            for command, text, checked, enabled in self.items():
                if command is None:
                    AppendMenuW(menu, MF_SEPARATOR, 0, None)
                else:
                    flags = MF_STRING | (MF_CHECKED if checked else 0) | (0 if enabled else MF_GRAYED)
                    AppendMenuW(menu, flags, command, text)
            if self.default_command:
                SetMenuDefaultItem(menu, self.default_command, False)
            pt = wintypes.POINT()
            GetCursorPos(ctypes.byref(pt))
            SetForegroundWindow(self.hwnd)  # thiếu bước này menu không tự đóng khi bấm ra ngoài
            command = TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_NONOTIFY | TPM_RETURNCMD, pt.x, pt.y, 0, self.hwnd, None)
            PostMessageW(self.hwnd, WM_NULL, 0, 0)
        finally:
            DestroyMenu(menu)
        if command:
            self.on_command(command)

    def _on_message(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY:
            if lparam in (WM_LBUTTONUP, NIN_BALLOONUSERCLICK):
                self._safe(self.on_click)
            elif lparam in (WM_RBUTTONUP, WM_CONTEXTMENU):
                self._safe(self._menu)
            return 0
        if msg == WM_COMMAND:
            self._safe(self.on_command, wparam & 0xFFFF)
            return 0
        if msg == WM_REFRESH:
            self._shell(NIM_MODIFY)
            return 0
        if msg == WM_BALLOON and self._balloon:
            title, text, warning = self._balloon
            nid = self._data(NIF_INFO)
            nid.szInfoTitle, nid.szInfo = title[:63], text[:255]
            nid.dwInfoFlags = NIIF_WARNING if warning else NIIF_INFO
            Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))
            return 0
        if msg == self._taskbar_created:  # Explorer khởi động lại: thêm lại biểu tượng
            self.shown = self._shell(NIM_ADD)
            return 0
        if msg == WM_CLOSE:
            DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._data(0)))
            PostQuitMessage(0)
            return 0
        return None
