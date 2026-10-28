"""Hình hướng dẫn cài agent (SVG vẽ bằng code): dịch được theo ngôn ngữ giao diện, sắc nét ở mọi cỡ, không cần file ảnh.

Mỗi hàm trả về một chuỗi SVG cho st.image. Chữ của Windows / trình duyệt giữ tiếng Anh như trên máy thật;
chữ của app đi qua t(). Vòng đỏ + số = chỗ cần bấm.
"""
from __future__ import annotations

from html import escape
from urllib.parse import urlsplit

from core.i18n import t

W, H = 680, 320
FONT = "'Segoe UI', system-ui, -apple-system, sans-serif"
MONO = "'Cascadia Mono', Consolas, 'Courier New', monospace"
INK, MUTED, LINE = "#1F2328", "#5B6470", "#D0D7DE"
ACCENT = "#E5484D"   # vòng đánh dấu chỗ cần bấm
BLUE = "#0F6CBD"
GREEN, AGENT_BLUE, ORANGE = "#2EA043", "#1F6FEB", "#E38B1A"  # màu chấm tròn của agent (automation/desktop.COLORS)


def _svg(body: str, h: int = H) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" font-family="{FONT}">'
            f'<rect width="{W}" height="{h}" rx="14" fill="#EEF2F7"/>{body}</svg>')


def _text(x, y, s: str, size=13, fill=INK, weight=400, anchor="start", family: str | None = None, extra: str = "") -> str:
    fam = f' font-family="{family}"' if family else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}"{fam}{extra}>'
            f'{escape(s)}</text>')


def _rect(x, y, w, h, fill="#FFFFFF", rx=6, stroke: str | None = None, sw=1, extra: str = "") -> str:
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{st}{extra}/>'


def _mark(x, y, w, h, n: int | None = None) -> str:
    """Vòng đỏ quanh chỗ cần bấm (+ số thứ tự nếu có nhiều chỗ)."""
    out = _rect(x - 4, y - 4, w + 8, h + 8, fill="none", rx=9, stroke=ACCENT, sw=3)
    if n is not None:
        out += f'<circle cx="{x - 4}" cy="{y - 4}" r="11" fill="{ACCENT}"/>' + _text(x - 4, y, str(n), 13, "#FFFFFF", 700, "middle")
    return out


def _cursor(x, y) -> str:
    return (f'<path transform="translate({x} {y})" d="M0 0 L0 19 L5 14.5 L8.5 22 L11.5 20.7 L8 13.3 L14.5 13.3 Z" '
            'fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/>')


def _shadow(x, y, w, h, rx=10) -> str:
    return _rect(x + 2, y + 4, w, h, fill="#000", rx=rx, extra=' opacity="0.10"')


def _window(x, y, w, h, title: str, dark=False) -> str:
    """Khung cửa sổ Windows 11: thanh tiêu đề + nút thu nhỏ / phóng to / đóng."""
    bar, body, fg = ("#2B2B2B", "#0C0C0C", "#E6E6E6") if dark else ("#F3F3F3", "#FFFFFF", INK)
    out = _shadow(x, y, w, h) + _rect(x, y, w, h, fill=body, rx=10, stroke="#3A3A3A" if dark else LINE)
    out += f'<path d="M{x} {y + 10} a10 10 0 0 1 10 -10 h{w - 20} a10 10 0 0 1 10 10 v22 h-{w} z" fill="{bar}"/>'
    out += _text(x + 14, y + 21, title, 12, fg)
    for i, glyph in enumerate(("✕", "▢", "—")):
        out += _text(x + w - 22 - i * 40, y + 21, glyph, 12, fg, anchor="middle")
    return out


def _folder(x, y, s=1.0) -> str:
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M0 6 a3 3 0 0 1 3 -3 h10 l4 4 h17 a3 3 0 0 1 3 3 v18 '
            'a3 3 0 0 1 -3 3 h-31 a3 3 0 0 1 -3 -3z" fill="#F2C55C"/><path d="M0 11 h37 v17 a3 3 0 0 1 -3 3 h-31 a3 3 0 0 1 -3 -3z" '
            'fill="#FFD978"/></g>')


def _file(x, y, label: str = "", color="#8A94A6", s=1.0) -> str:
    out = (f'<g transform="translate({x} {y}) scale({s})"><path d="M2 0 h20 l10 10 v26 a2 2 0 0 1 -2 2 h-28 a2 2 0 0 1 -2 -2 v-34 '
           f'a2 2 0 0 1 2 -2z" fill="#FFFFFF" stroke="{LINE}"/><path d="M22 0 v10 h10" fill="#EEF1F4" stroke="{LINE}"/>')
    if label:
        out += _rect(-3, 19, 26, 12, fill=color, rx=2) + _text(10, 28.5, label, 8, "#FFFFFF", 700, "middle")
    return out + "</g>"


def _zip_icon(x, y, s=1.0) -> str:
    return _folder(x, y, s) + (f'<g transform="translate({x} {y}) scale({s})"><rect x="16" y="11" width="5" height="20" fill="#9AA4B2"/>'
                               '<rect x="16" y="13" width="5" height="2" fill="#5B6470"/><rect x="16" y="18" width="5" height="2" '
                               'fill="#5B6470"/><rect x="16" y="23" width="5" height="2" fill="#5B6470"/></g>')


def _site_host(site: str) -> str:
    return urlsplit(site).netloc or site or "l2m-ops.streamlit.app"


# ---- các bước -----------------------------------------------------------------------
def download(site: str, user: str) -> str:
    """Bước 1: bấm nút tải agent ở thanh bên trái website."""
    x, y, w, h = 20, 18, 640, 284
    out = _shadow(x, y, w, h) + _rect(x, y, w, h, fill="#FFFFFF", rx=10, stroke=LINE)
    out += f'<path d="M{x} {y + 10} a10 10 0 0 1 10 -10 h{w - 20} a10 10 0 0 1 10 10 v24 h-{w} z" fill="#DDE3EA"/>'
    out += _rect(x + 10, y + 7, 170, 27, fill="#FFFFFF", rx=7) + _text(x + 24, y + 25, "L2M Ops Toolkit", 12)
    out += _rect(x, y + 34, w, 34, fill="#FFFFFF") + "".join(
        f'<circle cx="{x + 18 + i * 22}" cy="{y + 51}" r="6" fill="#C9D1DA"/>' for i in range(3))
    out += _rect(x + 80, y + 40, 400, 22, fill="#F1F3F5", rx=11) + _text(x + 96, y + 55, "🔒 " + _site_host(site), 12, MUTED)
    out += f'<line x1="{x}" y1="{y + 68}" x2="{x + w}" y2="{y + 68}" stroke="{LINE}"/>'
    # thanh bên trái của app
    out += _rect(x, y + 69, 210, h - 69, fill="#F0F2F6", rx=0)
    out += _text(x + 16, y + 96, user, 14, INK, 700) + _text(x + 16, y + 114, t("Thành viên") + " · " + user, 11, MUTED)
    out += f'<circle cx="{x + 21}" cy="{y + 136}" r="5" fill="#FFFFFF" stroke="#9AA4B2" stroke-width="1.5"/>'
    out += _text(x + 32, y + 140, t("⚪ Chưa bật agent (agent.bat)").lstrip("⚪ "), 11, MUTED)  # emoji trong ảnh SVG vẽ lệch: vẽ tay
    bx, by, bw, bh = x + 16, y + 154, 178, 34
    out += _rect(bx, by, bw, bh, fill="#FFFFFF", rx=8, stroke="#C3CAD3") + _text(bx + bw / 2, by + 22, t("⬇ Tải agent cho máy này"),
                                                                             12.5, INK, 600, "middle")
    out += _mark(bx, by, bw, bh) + _cursor(bx + bw - 30, by + 20)
    # vùng chính + khung tải xuống của trình duyệt
    out += _text(x + 236, y + 104, "L2M Ops Toolkit", 20, INK, 700)
    out += "".join(_rect(x + 236, y + 122 + i * 18, 300 - i * 70, 8, fill="#E7EBF0", rx=4) for i in range(3))
    px, py = x + 392, y + 150
    out += _shadow(px, py, 232, 106, 8) + _rect(px, py, 232, 106, fill="#FFFFFF", rx=8, stroke=LINE)
    out += _text(px + 14, py + 24, "Downloads", 13, INK, 600) + _zip_icon(px + 14, py + 40, 0.9)
    out += _text(px + 56, py + 58, f"L2M-Ops-agent-{user}.zip", 12, INK, 600) + _text(px + 56, py + 76, "Open file", 12, BLUE)
    out += _rect(px + 56, py + 86, 160, 4, fill=GREEN, rx=2)
    return _svg(out)


def extract(user: str) -> str:
    """Bước 2: chuột phải file zip -> Extract All…"""
    x, y, w, h = 20, 18, 640, 284
    out = _window(x, y, w, h, "Downloads")
    out += _rect(x + 1, y + 32, w - 2, 30, fill="#F9F9F9", rx=0) + "".join(
        _rect(x + 14 + i * 46, y + 40, 36, 14, fill="#E4E7EB", rx=4) for i in range(5))
    nav = ["Home", "Desktop", "Downloads", "Documents", "Pictures"]
    for i, name in enumerate(nav):
        if name == "Downloads":
            out += _rect(x + 8, y + 72 + i * 28, 140, 24, fill="#DCE7F5", rx=5)
        out += _text(x + 22, y + 89 + i * 28, name, 12, INK)
    out += f'<line x1="{x + 156}" y1="{y + 62}" x2="{x + 156}" y2="{y + h}" stroke="{LINE}"/>'
    out += _text(x + 172, y + 84, "Name", 11, MUTED) + _text(x + 430, y + 84, "Type", 11, MUTED)
    out += _rect(x + 164, y + 94, 466, 30, fill="#CCE4F7", rx=5) + _zip_icon(x + 172, y + 97, 0.75)
    out += _text(x + 208, y + 114, f"L2M-Ops-agent-{user}.zip", 12.5, INK, 600) + _text(x + 430, y + 114, "Compressed (zipped)", 12, MUTED)
    out += _file(x + 175, y + 133, "XLS", "#1D6F42", 0.62) + _text(x + 208, y + 150, "report.xlsx", 12.5, MUTED)
    # menu chuột phải
    mx, my, mw = x + 300, y + 128, 230
    items = ["Open", "Extract All...", "Pin to Start", "Copy as path", "Properties", "Show more options"]
    out += _shadow(mx, my, mw, 26 * len(items) + 12, 8) + _rect(mx, my, mw, 26 * len(items) + 12, fill="#FFFFFF", rx=8, stroke=LINE)
    for i, item in enumerate(items):
        iy = my + 6 + i * 26
        if item == "Extract All...":
            out += _rect(mx + 6, iy, mw - 12, 24, fill="#EEF4FB", rx=4)
        out += _text(mx + 36, iy + 17, item, 12.5, INK, 600 if item == "Extract All..." else 400)
    out += _mark(mx + 6, my + 32, mw - 12, 24) + _cursor(mx + 150, my + 46)
    return _svg(out)


def run_bat(user: str) -> str:
    """Bước 3: nháy đúp agent.bat trong thư mục vừa giải nén."""
    x, y, w, h = 20, 18, 640, 284
    out = _window(x, y, w, h, f"L2M-Ops-agent-{user}")
    tiles = [("automation", "dir"), ("core", "dir"), ("data", "dir"), ("resources", "dir"), ("tools", "dir"), ("ui", "dir"),
             ("views", "dir"), ("agent.bat", "bat"), ("app.py", "py"), ("CHAY-AGENT.txt", "txt"), ("README.md", "txt"),
             ("requirements.txt", "txt"), ("run.bat", "bat")]
    for i, (name, kind) in enumerate(tiles):
        tx, ty = x + 22 + (i % 7) * 86, y + 52 + (i // 7) * 112
        if name == "agent.bat":
            out += _rect(tx - 6, ty - 6, 80, 96, fill="#CCE4F7", rx=6)
        if kind == "dir":
            out += _folder(tx + 14, ty + 6, 1.15)
        else:
            out += _file(tx + 18, ty + 2, {"bat": "BAT", "py": "PY", "txt": "TXT"}[kind],
                         {"bat": "#5B6470", "py": "#3572A5", "txt": "#8A94A6"}[kind], 1.05)
        out += _text(tx + 34, ty + 64, name if len(name) <= 12 else name[:11] + "…", 11.5, INK, 600 if name == "agent.bat" else 400,
                     "middle")
    ax, ay = x + 22, y + 164
    out += _mark(ax - 6, ay - 6, 80, 96) + _cursor(ax + 48, ay + 30)
    out += _rect(ax + 66, ay + 40, 34, 20, fill=ACCENT, rx=10) + _text(ax + 83, ay + 54, "×2", 12, "#FFFFFF", 700, "middle")
    return _svg(out)


def smartscreen() -> str:
    """Bước 4: Windows hỏi lại (agent không có chữ ký số): More info -> Run anyway."""
    x, y, w, h = 70, 20, 540, 280
    out = _shadow(x, y, w, h, 4) + _rect(x, y, w, h, fill="#0067B8", rx=4)
    out += _text(x + w - 18, y + 24, "✕", 13, "#FFFFFF", anchor="end")
    out += _text(x + 28, y + 62, "Windows protected your PC", 26, "#FFFFFF", 300)
    out += _text(x + 28, y + 96, "Microsoft Defender SmartScreen prevented an unrecognized app from", 13, "#FFFFFF")
    out += _text(x + 28, y + 114, "starting. Running this app might put your PC at risk.", 13, "#FFFFFF")
    out += _text(x + 28, y + 142, "More info", 13, "#FFFFFF", 600, extra=' text-decoration="underline"')
    out += _mark(x + 26, y + 128, 66, 20, 1)
    out += _text(x + 28, y + 176, "App:", 13, "#FFFFFF") + _text(x + 110, y + 176, "agent.bat", 13, "#FFFFFF")
    out += _text(x + 28, y + 196, "Publisher:", 13, "#FFFFFF") + _text(x + 110, y + 196, "Unknown publisher", 13, "#FFFFFF")
    out += f'<line x1="{x}" y1="{y + 222}" x2="{x + w}" y2="{y + 222}" stroke="#FFFFFF" stroke-opacity="0.35"/>'
    out += _rect(x + 262, y + 236, 120, 30, fill="none", rx=2, stroke="#FFFFFF", sw=1.5) + _text(x + 322, y + 256, "Run anyway", 13,
                                                                                               "#FFFFFF", 600, "middle")
    out += _rect(x + 394, y + 236, 120, 30, fill="#FFFFFF", rx=2) + _text(x + 454, y + 256, "Don't run", 13, "#0067B8", 600, "middle")
    out += _mark(x + 262, y + 236, 120, 30, 2) + _cursor(x + 350, y + 254)
    return _svg(out)


def console(user: str) -> str:
    """Bước 5: lần đầu tự cài Python + thư viện; xong thì cửa sổ tự đóng."""
    x, y, w, h = 20, 18, 640, 284
    out = _window(x, y, w, h, "agent.bat", dark=True)
    out += f'<clipPath id="con"><rect x="{x + 8}" y="{y + 36}" width="{w - 16}" height="{h - 44}"/></clipPath><g clip-path="url(#con)">'
    lines = [("[L2M Ops] Chua co Python 3.10+ tren may: tai Python 3.13 ban portable...", "#CCCCCC"),
             ("[L2M Ops] Giai nen Python...", "#CCCCCC"),
             ("[L2M Ops] Tao moi truong Python cho app (.venv)...", "#CCCCCC"),
             ("[L2M Ops] Cai thu vien cho app (lan dau mat vai phut)...", "#CCCCCC"),
             ("[L2M Ops] Cai dat xong.", "#CCCCCC"),
             ("[09:41:07] " + t("Đang bật agent chạy ngầm (bản {version})…", version="1a2b3c4d5e6f"), "#CCCCCC"),
             ("[09:41:10] " + t("✅ Agent đang chạy ngầm cho tài khoản {user} trên máy {host}.", user=user, host="PC"), "#7EE787"),
             ("", "#CCCCCC"),
             (t("Cửa sổ này tự đóng sau {n} giây — nhấn phím bất kỳ để tiếp tục xem log.", n=7), "#F2CC60")]
    for i, (line, color) in enumerate(lines):
        out += _text(x + 16, y + 60 + i * 23, line, 12.5, color, family=MONO)
    out += "</g>"
    return _svg(out)


def tray(user: str) -> str:
    """Bước 6: chấm tròn ở khay hệ thống (có thể nằm trong nút ^)."""
    out = f'<defs><linearGradient id="desk" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#CFE0F5"/>' \
          f'<stop offset="1" stop-color="#E9DDF5"/></linearGradient></defs>'
    out += _rect(0, 0, W, H, fill="url(#desk)", rx=14)
    # chú thích màu
    lx, ly = 28, 34
    out += _rect(lx - 12, ly - 22, 250, 104, fill="#FFFFFF", rx=10, extra=' opacity="0.92"')
    for i, (color, label) in enumerate([(GREEN, t("Đang chờ lệnh từ website")), (AGENT_BLUE, t("Đang chạy lệnh")),
                                        (ORANGE, t("Cần chú ý: mất mạng / có bản mới"))]):
        out += f'<circle cx="{lx + 6}" cy="{ly + i * 28}" r="7" fill="{color}"/>' + _text(lx + 22, ly + 5 + i * 28, label, 12.5)
    # thanh tác vụ
    ty = H - 52
    out += f'<path d="M0 {ty} h{W} v{52 - 14} a14 14 0 0 1 -14 14 h-{W - 28} a14 14 0 0 1 -14 -14z" fill="#F3F3F3"/>'
    out += f'<line x1="0" y1="{ty}" x2="{W}" y2="{ty}" stroke="#D6D6D6"/>'
    out += "".join(_rect(250 + i * 44, ty + 12, 28, 28, fill="#D9DEE5", rx=6) for i in range(4))
    cx = 474
    out += _text(cx, ty + 32, "^", 16, INK, 600, "middle") + _text(cx + 40, ty + 32, "📶 🔊 🔋", 13, INK)
    out += _text(W - 22, ty + 23, "9:41 AM", 11.5, INK, anchor="end") + _text(W - 22, ty + 40, "10/28/2026", 11.5, INK, anchor="end")
    # khay mở rộng (bấm ^)
    fx, fy = cx - 62, ty - 98
    out += _shadow(fx, fy, 124, 86, 8) + _rect(fx, fy, 124, 86, fill="#FFFFFF", rx=8, stroke=LINE)
    for i in range(6):
        ix, iy = fx + 22 + (i % 3) * 40, fy + 26 + (i // 3) * 36
        out += (f'<circle cx="{ix}" cy="{iy}" r="8" fill="{GREEN}" stroke="#1B7A31" stroke-width="1.5"/>' if i == 4
                else _rect(ix - 8, iy - 8, 16, 16, fill="#C9D1DA", rx=3))
    dx, dy = fx + 62, fy + 62
    out += _mark(dx - 10, dy - 10, 20, 20, 2) + _cursor(dx + 4, dy + 4)
    out += _mark(cx - 10, ty + 14, 20, 24, 1)
    # chú thích khi rê chuột vào chấm tròn
    tx, tty = fx - 244, fy + 38
    out += _shadow(tx, tty, 230, 46, 6) + _rect(tx, tty, 230, 46, fill="#FFFFFF", rx=6, stroke=LINE)
    out += _text(tx + 12, tty + 20, f"L2M Ops Agent — {user}", 12, INK, 600) + _text(tx + 12, tty + 38, t("Đang chờ lệnh từ website"),
                                                                                     12, MUTED)
    out += f'<path d="M{tx + 230} {tty + 20} l8 6 l-8 6z" fill="#FFFFFF" stroke="{LINE}"/>'
    return _svg(out)


def browser_prompt(site: str) -> str:
    """Bước 7: trình duyệt hỏi mở L2M Ops Agent -> Always allow + Open (để lần sau website tự bật agent)."""
    x, y, w, h = 20, 18, 640, 284
    host = _site_host(site)
    out = _shadow(x, y, w, h) + _rect(x, y, w, h, fill="#FFFFFF", rx=10, stroke=LINE)
    out += f'<path d="M{x} {y + 10} a10 10 0 0 1 10 -10 h{w - 20} a10 10 0 0 1 10 10 v24 h-{w} z" fill="#DDE3EA"/>'
    out += _rect(x + 80, y + 40, 400, 22, fill="#F1F3F5", rx=11) + _text(x + 96, y + 55, "🔒 " + host, 12, MUTED)
    out += "".join(_rect(x + 24, y + 96 + i * 22, 520 - i * 90, 9, fill="#EEF1F4", rx=4) for i in range(7))
    px, py, pw, ph = x + 100, y + 70, 440, 196
    out += _shadow(px, py, pw, ph, 10) + _rect(px, py, pw, ph, fill="#FFFFFF", rx=10, stroke=LINE)
    out += _text(px + 22, py + 34, "This site is trying to open L2M Ops Agent.", 15, INK, 600)
    out += _text(px + 22, py + 58, f"https://{host} wants to open this application.", 12, MUTED)
    out += _rect(px + 22, py + 80, 16, 16, fill=BLUE, rx=3) + (f'<path d="M{px + 26} {py + 88} l3.5 3.5 l6 -7" fill="none" '
                                                               'stroke="#fff" stroke-width="2"/>')
    out += _text(px + 48, py + 92, f"Always allow {host} to open links of", 12.5, INK)
    out += _text(px + 48, py + 110, "this type in the associated app", 12.5, INK)
    out += _mark(px + 20, py + 78, 20, 20, 1)
    out += _rect(px + pw - 196, py + 146, 84, 32, fill=BLUE, rx=6) + _text(px + pw - 154, py + 167, "Open", 13, "#FFFFFF", 600, "middle")
    out += _rect(px + pw - 102, py + 146, 84, 32, fill="#FFFFFF", rx=6, stroke="#C3CAD3") + _text(px + pw - 60, py + 167, "Cancel", 13,
                                                                                                 INK, 400, "middle")
    out += _mark(px + pw - 196, py + 146, 84, 32, 2) + _cursor(px + pw - 150, py + 162)
    return _svg(out)
