#!/usr/bin/env python3
"""The diagram of the network at hkzn: one flat office segment, 12 clients.

    python3 sites/hkzn/layout.py [--lang en|zh] [--unredacted]
                                 → out/hkzn[-zh].svg + .png

Internet → YouHua gateway (ONT + router + AP) → the segment, with every host the
sweep found drawn as its own card. Everything comes from probes: no device here is
invented, and unnamed hosts are labelled "unknown host" instead of being guessed.
Content comes from site.yaml (English) or site.zh.yaml (Chinese) in this directory,
the positions are hand-placed below. Self-contained: nothing outside this directory
except the icons and the fonts is needed to draw it, so it can be edited without
touching any other site.
"""
import base64
import html
import pathlib
import subprocess
import sys

import yaml

SITE = pathlib.Path(__file__).resolve().parent          # this directory: site.yaml and out/ live here
ROOT = SITE.parent.parent                               # repo root: the shared icons are there
ICONS = ROOT / "icons"
OUT = SITE / "out"


def opt(name, default=None):
    """Value of --name=value or --name value on the command line."""
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == f"--{name}" and i + 1 < len(args):
            return args[i + 1]
        if a.startswith(f"--{name}="):
            return a.split("=", 1)[1]
    return default


UNREDACTED = "--unredacted" in sys.argv
LANG = opt("lang", "en")
if LANG not in ("en", "zh"):
    sys.exit(f"unknown --lang '{LANG}' (en | zh)")

# Each language brings its own complete content file: reading both would mean
# guessing which of the two is authoritative, and a half-translated picture is
# worse than one that says which file it came from.
CFG = SITE / ("site.yaml" if LANG == "en" else f"site.{LANG}.yaml")
if not CFG.is_file():
    sys.exit(f"{CFG.relative_to(ROOT)} not found — the {LANG} version needs its own content file")

INV = yaml.safe_load(CFG.read_text())
RED = INV["redact"]
DOMAIN = INV["meta"]["domain"]
SHOWN_DOMAIN = DOMAIN if (UNREDACTED or not RED["domain"]) else RED["domain_placeholder"]

W, H = 2400, 1240

# ---------------------------------------------------------------- palette
BG = "#0b0f15"
GRID = "#151c26"
PANEL = "#111821"
PANEL2 = "#161f2b"
CHIP = "#19222e"
BORDER = "#253042"
TEXT = "#e6edf3"
MUTED = "#8d9aab"
FAINT = "#5d6a7c"
TRUNK = "#d5dde6"
TRUNK_BORDER = "#3a475a"   # border for devices that are not tied to a single VLAN
LINK = "#79c0ff"
REDDIT = "#ff5722"
DISK = "#1d2734"
DISK_EDGE = "#5a6b82"
PROTO = {"TCP": "#79c0ff", "UDP": "#39c5cf"}
SPEED_W = {"10G": 9.5, "2.5G": 3.8, "1G": 2.4, "100M": 1.4}   # access-line widths
VLAN = {v["key"]: v for v in INV["vlans"]}
C = {k: v["color"] for k, v in VLAN.items()}
SANS = "Fira Sans"
MONO = "Fira Code"
if LANG == "zh":
    # Fira has no CJK glyphs, so the renderer (Pango) falls back per character:
    # latin stays Fira, Chinese is handed to the system font. Without the stack
    # every Chinese character would come out as an empty box.
    CJK = ", PingFang SC, Noto Sans CJK SC, Hiragino Sans GB, sans-serif"
    SANS, MONO = SANS + CJK, MONO + CJK

# Interface strings. The content is in site.yaml / site.zh.yaml; these are the
# labels this layout draws itself, so they live with the coordinates.
UI = {
    "en": dict(
        internet="Internet", networks="Networks", legend="Legend", client_types="CLIENT TYPES",
        facts="Facts & gaps", hardware="HARDWARE", management="MANAGEMENT", lan="LAN",
        lan_clients="{subnet} · {n} clients found by ping + TCP sweep", lan_note="single flat segment · no VLANs",
        link_label="Wi-Fi + LAN ports", unknown_host="unknown host",
        link_cable="cable, colored by network", link_wifi="Wi-Fi (no cable)",
        link_tunnel="a tunnel, not a cable", link_uplink="uplink to the ISP",
        state_online="online", state_idle="idle",
    ),
    "zh": dict(
        internet="互联网", networks="网络", legend="图例", client_types="设备类型",
        facts="已知与未知", hardware="硬件", management="管理", lan="局域网",
        lan_clients="{subnet} · ping + TCP 扫描发现 {n} 台客户机",
        lan_note="单网段 · 无 VLAN",
        link_label="Wi-Fi + 网口", unknown_host="未知主机",
        link_cable="网线，颜色代表所属网络", link_wifi="Wi-Fi（无线接入）",
        link_tunnel="隧道，不是网线", link_uplink="上联至运营商",
        state_online="在线", state_idle="空闲",
    ),
}[LANG]

WIDE = ((0x1100, 0x115F), (0x2E80, 0x303E), (0x3041, 0x33FF), (0x3400, 0x4DBF),
        (0x4E00, 0x9FFF), (0xA000, 0xA4CF), (0xAC00, 0xD7A3), (0xF900, 0xFAFF),
        (0xFE30, 0xFE4F), (0xFF00, 0xFF60), (0xFFE0, 0xFFE6))


def wide(ch):
    """CJK and full-width punctuation advance one em, unlike the latin estimate."""
    o = ord(ch)
    return any(a <= o <= b for a, b in WIDE)


def trunk_w(speed):
    return SPEED_W[speed] + 3.4


def sub(s):
    """Fill {domain} placeholders and apply redaction."""
    s = str(s).replace("{domain}", SHOWN_DOMAIN)
    if not UNREDACTED and RED["domain"]:
        s = s.replace(DOMAIN, SHOWN_DOMAIN)
    return s


def esc(s):
    return html.escape(sub(s), quote=True)


def tw(s, size, mono=False):
    """Rough text width for layout decisions (a wide character is a full em)."""
    return sum(size if wide(c) else size * (0.6 if mono else 0.53) for c in sub(s))


def _font_file(pattern):
    """Path of an installed font via fontconfig (fc-match), or None."""
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}", pattern], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except Exception:
        return None


try:
    from PIL import ImageFont
    _FONTS = {700: _font_file("Fira Sans:bold"), 600: _font_file("Fira Sans:semibold")}
    if not all(_FONTS.values()):
        raise RuntimeError("Fira Sans not found")
    _FCACHE = {}

    def _latin(s, size, weight):
        key = (weight, size)
        if key not in _FCACHE:
            _FCACHE[key] = ImageFont.truetype(_FONTS[weight], size=size * 8)
        return _FCACHE[key].getlength(s) / 8

    def measure(s, size, weight=700):
        """Width of a mixed latin / CJK string, latin from the real font, CJK at one em."""
        total, buf = 0.0, ""
        for ch in str(s):
            if wide(ch):
                total += _latin(buf, size, weight) if buf else 0.0
                buf = ""
                total += size
            else:
                buf += ch
        return total + (_latin(buf, size, weight) if buf else 0.0)
except Exception:          # no Pillow / font file: rough estimate
    def measure(s, size, weight=700):
        return sum(size if wide(c) else (0.68 if c.isupper() else 0.58 if c.isdigit() else 0.5) * size
                   for c in str(s))


def fqdn(h):
    return f"{h}.{SHOWN_DOMAIN}"


class SVG:
    def __init__(self):
        self.p = []
        self._icon_cache = {}

    def add(self, s):
        self.p.append(s)

    def rect(self, x, y, w, h, rx=10, fill=PANEL, stroke=BORDER, sw=1.2, op=1, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"{d}/>')

    def text(self, x, y, s, size=14, fill=TEXT, weight=400, anchor="start", mono=False, ls=0, op=1):
        fam = MONO if mono else SANS
        lsa = f' letter-spacing="{ls}"' if ls else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" fill="{fill}" '
                 f'font-weight="{weight}" text-anchor="{anchor}" opacity="{op}"{lsa}>{esc(s)}</text>')

    def icon(self, name, x, y, size):
        if name not in self._icon_cache:
            f = ICONS / f"{name}.svg"
            if not f.exists():
                raise SystemExit(f"missing icon '{name}' – run: python3 fetch_icons.py")
            self._icon_cache[name] = base64.b64encode(f.read_bytes()).decode()
        self.add(f'<image x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" '
                 f'href="data:image/svg+xml;base64,{self._icon_cache[name]}"/>')

    def line(self, pts, color, sw=3, dash=None, r=10, op=1, cap="round"):
        self.add(f'<path d="{rounded(pts, r)}" fill="none" stroke="{color}" stroke-width="{sw}" '
                 f'stroke-linecap="{cap}" stroke-linejoin="round" opacity="{op}"'
                 + (f' stroke-dasharray="{dash}"' if dash else "") + "/>")

    def trunk(self, pts, r=12, sw=7):
        """Tagged trunk: light cable with a dark core."""
        self.line(pts, TRUNK, sw=sw, r=r)
        self.line(pts, BG, sw=sw - 4.4, r=r)

    def arrow(self, pts, color=MUTED, sw=1.8, dash=None, r=8):
        """Line with an arrowhead at the last point."""
        self.line(pts, color, sw, dash=dash, r=r)
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        dx, dy = x1 - x0, y1 - y0
        ln = max(abs(dx), abs(dy)) or 1
        ux, uy = dx / ln, dy / ln
        a, b = 8, 4.5
        p1 = (x1 - ux * a - uy * b, y1 - uy * a + ux * b)
        p2 = (x1 - ux * a + uy * b, y1 - uy * a - ux * b)
        self.add(f'<path d="M{x1},{y1} L{p1[0]:.1f},{p1[1]:.1f} L{p2[0]:.1f},{p2[1]:.1f} Z" fill="{color}"/>')

    def pill(self, x, y, s, color, size=12, fill=None, mono=False, anchor="start", h=None, pad=8, tcolor=None, weight=600):
        w = tw(s, size, mono) + pad * 2
        h = h or size + 10
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        self.rect(x, y, w, h, rx=h / 2, fill=fill or color + "22", stroke=color + "88", sw=1)
        self.text(x + w / 2, y + h / 2 + size * 0.36, s, size, tcolor or color, weight, "middle", mono)
        return w

    def label(self, x, y, s, color=MUTED, size=12, anchor="middle", mono=False, bg=BG):
        """Text on a line, with a background knock-out."""
        w = tw(s, size, mono) + 12
        bx = x - w / 2 if anchor == "middle" else (x if anchor == "start" else x - w)
        self.rect(bx, y - size - 2, w, size + 9, rx=5, fill=bg, stroke=bg, sw=0)
        self.text(bx + w / 2, y + 1, s, size, color, 500, "middle", mono)

    def render(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
                + "".join(self.p) + "</svg>")


def rounded(pts, r):
    """Orthogonal polyline with rounded corners."""
    if len(pts) == 2:
        return f"M{pts[0][0]},{pts[0][1]} L{pts[1][0]},{pts[1][1]}"
    d = f"M{pts[0][0]},{pts[0][1]}"
    for i in range(1, len(pts) - 1):
        (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
        l1 = max(abs(x1 - x0), abs(y1 - y0))
        l2 = max(abs(x2 - x1), abs(y2 - y1))
        rr = min(r, l1 / 2, l2 / 2)
        ax = x1 - (x1 - x0) / l1 * rr if l1 else x1
        ay = y1 - (y1 - y0) / l1 * rr if l1 else y1
        bx = x1 + (x2 - x1) / l2 * rr if l2 else x1
        by = y1 + (y2 - y1) / l2 * rr if l2 else y1
        d += f" L{ax:.1f},{ay:.1f} Q{x1},{y1} {bx:.1f},{by:.1f}"
    d += f" L{pts[-1][0]},{pts[-1][1]}"
    return d


S = SVG()


# ---------------------------------------------------------------- shared pieces
def hostname(g):
    """(text, color) for the second address line: public host, or <name>.internal."""
    if g.get("host"):
        return fqdn(g["host"]), LINK
    if g.get("internal"):
        return f"{g['internal']}.internal", None
    return None, None


def addr(x, y, ip, g, color, size=12):
    """Address line under a card's name: IP · hostname, in the VLAN color."""
    S.text(x, y, ip, size, color, 500, mono=True)
    name, ncol = hostname(g)
    if name:
        cw_ = size * 0.6                      # Fira Code advance width
        dx = x + len(ip) * cw_ + cw_ * 0.6
        S.text(dx, y, "·", size, MUTED, 400, mono=True)
        S.text(dx + cw_ * 1.6, y, name, size, ncol or color, 400, mono=True, op=1 if ncol else 0.85)


HWC = "#c08a5c"   # "physical hardware" accent (same tan as the HARDWARE labels)


def hw_bar(x, y, h):
    """Left accent bar = this card is a physical box / hardware part."""
    S.add(f'<rect x="{x+1}" y="{y+12}" width="4" height="{h-24}" rx="2" fill="{HWC}"/>')


TAB = 34   # height of the folder tab on physical-device cards


def tab_width(g):
    """Tab fits 'name · type' (name 20px bold, type 14px semibold), measured from the font."""
    return 16 + measure(g["name"], 20, 700) + 7 + measure("·", 20, 700) + 7 + measure(g["type"], 14, 600) + 18


def folder(x, y, w, h, tab_w, fill, stroke, sw):
    """Card body at (x, y, w, h) with a folder tab on its top-left edge, tab_w wide and TAB high."""
    t = y - TAB
    r, rt, sl = 12, 9, 16
    d = (f"M{x},{y+h-r} L{x},{t+rt} Q{x},{t} {x+rt},{t} L{x+tab_w-sl:.1f},{t} "
         f"C{x+tab_w-sl/3:.1f},{t} {x+tab_w-sl/3:.1f},{y} {x+tab_w+sl/2:.1f},{y} "
         f"L{x+w-r},{y} Q{x+w},{y} {x+w},{y+r} L{x+w},{y+h-r} Q{x+w},{y+h} {x+w-r},{y+h} "
         f"L{x+r},{y+h} Q{x},{y+h} {x},{y+h-r} Z")
    S.add(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def device_card(x, y, w, h, icons, g, color, fill=PANEL, stroke=None, sw=1.6):
    """Physical device: folder tab 'name · type'; body = icon, full device name, IP · hostname, OS."""
    folder(x, y, w, h, tab_width(g), fill, stroke or color + "aa", sw)
    S.add(f'<text x="{x+16}" y="{y-10}" font-family="{SANS}" fill="{TEXT}">'
          f'<tspan font-size="20" font-weight="700">{esc(g["name"])}</tspan>'
          f'<tspan dx="7" font-size="20" font-weight="700" fill-opacity="0.6">·</tspan>'
          f'<tspan dx="7" font-size="14" font-weight="600">{esc(g["type"])}</tspan></text>')
    ix = x + 14
    for ic in icons:                      # icon spans the three body lines (full name … OS)
        S.icon(ic, ix, y + 15, 54)
        ix += 58
    tx_ = ix + 8
    dy = 0 if g.get("os") else 8          # no OS line → center the two lines on the icon
    S.text(tx_, y + 28 + dy, g.get("model") or "custom build", 14, TEXT if g.get("model") else MUTED, 500)
    addr(tx_, y + 48 + dy, g["ip"], g, color)
    if g.get("os"):
        S.text(tx_, y + 66, g["os"], 12, MUTED, 400)
    if g.get("config"):                   # optional 4th line: how the device is set up
        S.text(tx_, y + 84, g["config"], 12, FAINT, 400)


def jack(x, y, w, h, fill, stroke, sfp=False):
    S.rect(x, y, w, h, rx=5, fill=fill, stroke=stroke, sw=1.4)
    if sfp:
        S.rect(x + 8, y + 9, w - 16, h - 18, rx=2, fill="#0b0f15", stroke="none", sw=0)
    else:
        S.add(f'<path d="M{x+10},{y+h-8} v-14 h6 v-5 h{w-32} v5 h6 v14 z" fill="#0b0f15"/>')


def ticks(cx, y, untagged=None, tagged=(), up=False):
    """VLAN indicator bars for a port: tall = untagged, short = tagged. up=True grows upwards."""
    vk = ([untagged] if untagged else []) + list(tagged)
    x0 = cx - (len(vk) * 7) / 2
    for j, k in enumerate(vk):
        hh = 8 if k == untagged else 5
        yy = y - hh if up else y
        S.add(f'<rect x="{x0 + j*7:.1f}" y="{yy}" width="5" height="{hh}" rx="1" fill="{C[k]}"/>')


def vlan_tag(vkey):
    v = VLAN[vkey]
    return f"{v['tag']} · {v['name']}" if v["tag"].startswith("VLAN") else v["name"]


def port_row(px_list, y, color_key, label_map):
    """A row of RJ45 jacks under a card edge; returns {label: x}."""
    out = {}
    for lbl, px in zip(label_map, px_list):
        jack(px - 22, y, 44, 36, C[color_key] + "55", C[color_key])
        ticks(px, y - 5, untagged=color_key, up=True)
        S.text(px, y + 54, lbl, 10.5, MUTED, 500, "middle")
        out[lbl] = px
    return out


# ================================================================ background + header
S.add(f'<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
      f'<circle cx="1.5" cy="1.5" r="1.3" fill="{GRID}"/></pattern></defs>')
S.rect(0, 0, W, H, rx=0, fill=BG, stroke=BG, sw=0)
S.rect(0, 0, W, H, rx=0, fill="url(#dots)", stroke="none", sw=0)

meta = INV["meta"]
title = meta["title"] if (UNREDACTED or not RED["domain"]) else meta["title_redacted"]
S.text(40, 86, title, 46, TEXT, 700, ls=-0.5)
S.text(W - 40, 74, meta["watermark"], 21, REDDIT, 700, "end")
S.text(W - 40, 100, meta["date"], 16, MUTED, 400, "end")

KIND = {k["key"]: k for k in INV["kinds"]}

# ================================================================ left column: networks
vx, vy, vw = 40, 140, 500
vh = 70 + len(INV["vlans"]) * 60
S.rect(vx, vy, vw, vh, rx=14, fill=PANEL, stroke=BORDER, sw=1.4)
S.text(vx + 20, vy + 36, UI["networks"], 19, TEXT, 600)
for i, v in enumerate(INV["vlans"]):
    y = vy + 56 + i * 60
    S.rect(vx + 14, y, vw - 28, 52, rx=9, fill=CHIP, stroke=v["color"] + "55", sw=1)
    S.add(f'<rect x="{vx+14}" y="{y}" width="6" height="52" rx="3" fill="{v["color"]}"/>')
    S.text(vx + 32, y + 22, v["tag"], 13, v["color"], 600, mono=True)
    S.text(vx + 152, y + 22, v["name"], 15.5, TEXT, 600)
    S.text(vx + vw - 28, y + 22, v["subnet"], 13.5, TEXT, 500, "end", mono=True)
    S.text(vx + 32, y + 42, v["note"], 12, MUTED, 400)

# ================================================================ how the facts were gathered
pb = INV["probes"]
py0 = vy + vh + 24
ph = 56 + len(pb["lines"]) * 26
S.rect(40, py0, 500, ph, rx=14, fill=PANEL, stroke=BORDER, sw=1.4)
S.text(60, py0 + 34, pb["title"], 19, TEXT, 600)
for i, ln in enumerate(pb["lines"]):
    y = py0 + 62 + i * 26
    S.add(f'<circle cx="66" cy="{y - 4}" r="2.4" fill="{FAINT}"/>')
    S.text(80, y, ln, 12.5, MUTED, 400)

# ================================================================ legend (links + client kinds)
kg = INV["kinds"]
lgx, lgw = 40, 500
lgy = py0 + ph + 24
lg_h = 66 + 4 * 27 + 34 + ((len(kg) + 1) // 2) * 26 + 14
S.rect(lgx, lgy, lgw, lg_h, rx=14, fill=PANEL, stroke=BORDER, sw=1.4)
S.text(lgx + 20, lgy + 36, UI["legend"], 19, TEXT, 600)
SX, TX = lgx + 22, lgx + 106
for i, (col, sw_, dash, lbl) in enumerate((
        (C["10"], 2.4, None, UI["link_cable"]),
        (C["10"], 2, "3 4", UI["link_wifi"]),
        (MUTED, 1.8, "2 5", UI["link_tunnel"]),
        (C["wan"], 3, None, UI["link_uplink"]))):
    y = lgy + 66 + i * 27
    S.line([(SX, y), (SX + 62, y)], col, sw_, dash=dash, r=0)
    S.text(TX, y + 4.5, lbl, 13, MUTED, 400)

ky = lgy + 66 + 4 * 27 + 6
S.text(lgx + 22, ky, UI["client_types"], 11.5, HWC, 700, ls=1.4)
for i, k in enumerate(kg):
    col_, row_ = i // 4, i % 4
    x, y = lgx + 22 + col_ * 232, ky + 26 + row_ * 26
    S.rect(x, y - 9, 10, 10, rx=2, fill=k["color"], stroke=k["color"], sw=0)
    S.text(x + 18, y, k["label"], 12.5, MUTED, 400)

# ================================================================ gaps
nq = INV["notes"]
ny0 = lgy + lg_h + 24
S.rect(40, ny0, 500, 56 + len(nq) * 26, rx=14, fill=PANEL, stroke=BORDER, sw=1.4)
S.text(60, ny0 + 34, UI["facts"], 19, TEXT, 600)
for i, n in enumerate(nq):
    y = ny0 + 62 + i * 26
    S.add(f'<circle cx="66" cy="{y - 4}" r="2.4" fill="{FAINT}"/>')
    S.text(80, y, n, 12.5, MUTED, 400)

# ================================================================ TOP: internet cloud
CX = 1120
cy0 = 168
rx_, ry_ = 600, 146

blobs = [(-95, 18, 42), (-45, -8, 56), (25, -18, 62), (90, 6, 48), (130, 26, 30), (-130, 30, 28)]
for dx, dy, r in blobs:
    S.add(f'<circle cx="{CX+dx}" cy="{cy0+dy}" r="{r+2.5}" fill="#3a4a60"/>')
S.add(f'<rect x="{CX-150}" y="{cy0+12}" width="300" height="46" rx="23" fill="#3a4a60"/>')
for dx, dy, r in blobs:
    S.add(f'<circle cx="{CX+dx}" cy="{cy0+dy}" r="{r}" fill="#1a2433"/>')
S.add(f'<rect x="{CX-147.5}" y="{cy0+14.5}" width="295" height="41" rx="20.5" fill="#1a2433"/>')
S.text(CX, cy0 + 14, UI["internet"], 26, TEXT, 600, "middle")
S.text(CX, cy0 + 40, INV["internet"]["caption"], 13, MUTED, 400, "middle")

# ================================================================ right column: egress + overlays
ov = INV["overlays"]
OX_, OY_, OW_ = 1690, 136, 670
S.rect(OX_, OY_, OW_, 500, rx=14, fill=PANEL, stroke=BORDER, sw=1.4)
S.text(OX_ + 20, OY_ + 36, ov["title"], 19, TEXT, 600)

S.text(OX_ + 20, OY_ + 72, ov["host_label"], 11.5, HWC, 700, ls=1.4)
for i, ln in enumerate(ov["host_lines"]):
    S.text(OX_ + 20, OY_ + 96 + i * 22, ln, 12.5, MUTED, 400, mono=True)

S.text(OX_ + 20, OY_ + 156, ov["tail_label"], 11.5, HWC, 700, ls=1.4)
S.icon("tailscale", OX_ + OW_ - 44, OY_ + 142, 24)
for i, n in enumerate(ov["tailnet"]):
    y = OY_ + 182 + i * 36
    on = n["state"] == "online"
    S.add(f'<circle cx="{OX_ + 26}" cy="{y - 4}" r="3.4" fill="{"#3fb950" if on else FAINT}"/>')
    S.text(OX_ + 40, y, n["name"], 13.5, TEXT, 600)
    S.text(OX_ + 200, y, n["ip"], 12.5, C["vpn"], 500, mono=True)
    S.text(OX_ + 340, y, n["os"], 12.5, MUTED, 400, mono=True)
    S.text(OX_ + OW_ - 24, y, UI[f"state_{n['state']}"], 12, MUTED if on else FAINT, 400, "end")

S.text(OX_ + 20, OY_ + 306, ov["egress_label"], 11.5, HWC, 700, ls=1.4)
for i, ln in enumerate(ov["egress_lines"]):
    S.text(OX_ + 20, OY_ + 330 + i * 22, ln, 12.5, MUTED, 400)

# the egress leaves the cloud over a tunnel, not a cable
S.line([(CX + 162, cy0 + 4), (OX_, OY_ + 44)], FAINT, 1.6, dash="2 5", r=0)

# ================================================================ gateway
gw = INV["gateway"]
GX, GY, GW_, GH = 680, 286, 880, 300
device_card(GX, GY, GW_, GH, ["glyph-nic"], gw, C["wan"])

# the fiber plugs into the top edge, right under the cloud
S.line([(CX, cy0 + 58), (CX, GY - 4)], "#6b7a90", 3)
S.add(f'<circle cx="{CX}" cy="{GY - 4}" r="10" fill="#0b0f15" stroke="#5a6b82" stroke-width="2"/>'
      f'<circle cx="{CX}" cy="{GY - 4}" r="2.6" fill="{C["wan"]}"/>')

S.text(GX + 18, GY + 96, UI["hardware"], 11.5, HWC, 700, ls=1.4)
for i, hwi in enumerate(gw["hw"]):
    x, y = GX + 16 + i * 212, GY + 106
    S.rect(x, y, 200, 70, rx=11, fill="#151d29", stroke="#2e3a4c", sw=1.2)
    hw_bar(x, y, 70)
    S.icon(hwi["icon"], x + 12, y + 18, 28)
    S.text(x + 50, y + 22, hwi["label"], 10, HWC, 700, ls=1.3)
    S.text(x + 50, y + 42, hwi["value"], 15, TEXT, 700)
    S.text(x + 50, y + 58, hwi["sub"], 10.5, MUTED, 400)

S.text(GX + 18, GY + 206, UI["management"], 11.5, HWC, 700, ls=1.4)
for i, ln in enumerate(gw["mgmt"]):
    S.text(GX + 18, GY + 228 + i * 22, ln, 12.5, MUTED, 400)

# ================================================================ LAN panel: the clients the sweep found
LX, LY, LW = 580, 676, 1674
cl = INV["clients"]
COLS, CW, CH_, GAPX, GAPY = 4, 390, 132, 22, 18
rows = (len(cl) + COLS - 1) // COLS
LH = 60 + rows * CH_ + (rows - 1) * GAPY + 24
S.rect(LX, LY, LW, LH, rx=14, fill="#0e151e", stroke=C["10"] + "44", sw=1.4)

S.text(LX + 24, LY + 34, UI["lan"], 15, C["10"], 700, mono=True)
S.text(LX + 78, LY + 34, UI["lan_clients"].format(n=len(cl), subnet=VLAN["10"]["subnet"]), 14, TEXT, 500)
S.text(LX + LW - 24, LY + 34, UI["lan_note"], 12.5, FAINT, 400, "end")

# one cable from the gateway into the segment, labelled for what it is
S.line([(CX, GY + GH), (CX, LY)], C["10"], 3)
S.label(CX + 8, GY + GH + 44, UI["link_label"], C["10"], 11, anchor="start")


def client_card(x, y, c):
    col = KIND[c["kind"]]["color"]
    named = c["name"] != "unknown"
    S.rect(x, y, CW, CH_, rx=12, fill=PANEL, stroke=col + "55", sw=1.3)
    S.add(f'<rect x="{x}" y="{y + 12}" width="4" height="{CH_ - 24}" rx="2" fill="{col}"/>')
    if c["icon"] == "none":                       # nothing known about it: a question mark, not a logo
        S.add(f'<circle cx="{x + 33}" cy="{y + 33}" r="17" fill="none" stroke="{FAINT}" '
              f'stroke-width="1.6" stroke-dasharray="3 3"/>')
        S.text(x + 33, y + 40, "?", 18, FAINT, 700, "middle")
    else:
        S.icon(c["icon"], x + 16, y + 16, 34)
    S.text(x + 60, y + 38, c["name"] if named else UI["unknown_host"], 15.5, TEXT if named else FAINT, 600)
    S.text(x + 60, y + 60, c["ip"], 12.5, col, 500, mono=True)
    S.text(x + CW - 16, y + 26, KIND[c["kind"]]["label"].upper(), 10 if LANG == "zh" else 9.5,
           col, 700, "end", ls=0.8)
    S.line([(x + 16, y + 76), (x + CW - 16, y + 76)], BORDER, 1)
    S.text(x + 16, y + 98, c["mac"], 11.5, MUTED, 400)
    S.text(x + 16, y + 120, c["ports"], 11.5, FAINT, 400, mono=True)


for i, c in enumerate(cl):
    cx_ = LX + 24 + (i % COLS) * (CW + GAPX)
    cy_ = LY + 60 + (i // COLS) * (CH_ + GAPY)
    client_card(cx_, cy_, c)

assert GX + GW_ <= OX_, "gateway card runs into the right column"
assert LX + LW <= W - 40, "client grid runs off the canvas"
assert LY + LH <= H - 20, f"canvas too short: the LAN panel ends at {LY + LH}"
assert ny0 + 56 + len(nq) * 26 <= H, "left column runs off the canvas"

OUT.mkdir(exist_ok=True)
name = "-".join([SITE.name] + ([] if LANG == "en" else [LANG]) + (["unredacted"] if UNREDACTED else []))
svg_path = OUT / f"{name}.svg"
svg_path.write_text(S.render())
png_path = OUT / f"{name}.png"
subprocess.run(["rsvg-convert", "-z", "1.6", "-o", str(png_path), str(svg_path)], check=True)
print(svg_path, png_path)
