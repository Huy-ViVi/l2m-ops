"""Kiểm tra máy này có tới được tool nội bộ không (DNS + cổng), để báo lỗi dễ hiểu trước khi mở trình duyệt.

NC Billing Admin (RC) chỉ tra được tên miền khi đã kết nối VPN của NC (GlobalProtect trên máy này).
"""
from __future__ import annotations

import socket
import sys
from urllib.parse import urlparse

from .i18n import t

VPN_HINT = "Tool này chỉ vào được trong mạng nội bộ — hãy kết nối VPN (GlobalProtect) rồi thử lại."

# Mã lỗi mạng của Chromium/Playwright -> (giải thích, có kèm gợi ý VPN). Dịch lúc báo lỗi, theo ngôn ngữ giao diện.
NET_ERRORS = {
    "ERR_NAME_NOT_RESOLVED": ("Máy này không tra được tên miền của tool (DNS).", True),
    "ERR_ADDRESS_UNREACHABLE": ("Không tới được địa chỉ của tool.", True),
    "ERR_CONNECTION_TIMED_OUT": ("Hết thời gian chờ kết nối tới tool.", True),
    "ERR_TIMED_OUT": ("Hết thời gian chờ kết nối tới tool.", True),
    "ERR_CONNECTION_REFUSED": ("Tool từ chối kết nối — có thể đang bảo trì hoặc sai địa chỉ trong Cài đặt.", False),
    "ERR_CONNECTION_RESET": ("Kết nối bị ngắt giữa chừng. Thử lại; nếu lặp lại, kiểm tra VPN/tường lửa.", False),
    "ERR_INTERNET_DISCONNECTED": ("Máy đang mất kết nối mạng.", False),
    "ERR_TUNNEL_CONNECTION_FAILED": ("Proxy không kết nối được tới tool.", False),
    "ERR_PROXY_CONNECTION_FAILED": ("Không kết nối được proxy của máy.", False),
    "ERR_CERT_": ("Lỗi chứng chỉ HTTPS của tool (có thể do VPN/proxy chặn HTTPS).", False),
}


def explain(error_text: str) -> str | None:
    for code, (message, vpn) in NET_ERRORS.items():
        if code in (error_text or ""):
            host = ""
            for token in error_text.split():
                if token.startswith("http"):
                    host = urlparse(token).hostname or ""
                    break
            text = t(message) + (" " + t(VPN_HINT) if vpn else "")
            return text + (t(" (tên miền: {host})", host=host) if host else "")
    return None


def system_proxy_configured() -> bool:
    """Có proxy hệ thống (Windows) thì trình duyệt tự tra tên miền qua proxy — khi đó không chặn sớm theo DNS."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as k:
            def val(name):
                try:
                    return winreg.QueryValueEx(k, name)[0]
                except OSError:
                    return None
            return bool(val("ProxyEnable")) or bool(val("AutoConfigURL"))
    except OSError:
        return False


def check(url: str, timeout: float = 5) -> dict:
    """{'url', 'host', 'ok', 'step': dns|connect|ok|config, 'message'}"""
    parsed = urlparse(url or "")
    host = parsed.hostname
    if not host:
        return {"url": url, "host": "", "ok": False, "step": "config", "message": t("Chưa cấu hình URL")}
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return {"url": url, "host": host, "ok": False, "step": "dns",
                "message": t("Không tra được tên miền {host}.", host=host) + " " + t(VPN_HINT)}
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError as e:
        return {"url": url, "host": host, "ok": False, "step": "connect",
                "message": t("Tra được {host} nhưng không kết nối được cổng {port} ({error}). Có thể cần VPN hoặc bị tường lửa chặn.",
                             host=host, port=port, error=e.__class__.__name__)}
    return {"url": url, "host": host, "ok": True, "step": "ok", "message": t("Kết nối được")}


def blocking_problem(url: str) -> str | None:
    """Lý do chắc chắn không mở được URL (để dừng sớm), hoặc None."""
    result = check(url, timeout=4)
    if result["step"] == "dns" and not system_proxy_configured():
        return result["message"]
    return None
