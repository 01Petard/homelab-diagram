#!/usr/bin/env python3
"""The diagram of the flat in 春波南苑 (cbny): a single-segment home network.

    python3 sites/cbny/layout.py [--lang en|zh] [--unredacted]
                                 → out/cbny[-zh].svg + .png

Internet → ONT → router → the four clients that are really there, plus the tailnet.
Content comes from site.en.yaml (English) or site.zh.yaml (Chinese) in this directory,
the positions are hand-placed below.
Self-contained: nothing outside this directory except the icons and the fonts is
needed to draw it, so it can be edited without touching any other site.
"""
import base64
import html
import pathlib
import subprocess
import sys

import yaml

SITE = pathlib.Path(__file__).resolve().parent          # this directory: site.en.yaml and out/ live here
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
inventory = None
for i, arg in enumerate(sys.argv[1:], 1):
    if arg == "--inventory":
        if i + 1 >= len(sys.argv) or sys.argv[i + 1].startswith("--"):
            sys.exit("--inventory needs a file path")
        inventory = sys.argv[i + 1]
    elif arg.startswith("--inventory="):
        inventory = arg.split("=", 1)[1]
        if not inventory:
            sys.exit("--inventory needs a file path")
CFG = SITE / f"site.{LANG}.yaml"
if inventory is not None:
    CFG = pathlib.Path(inventory)
if not CFG.is_file():
    sys.exit(f"{CFG} not found — the {LANG} version needs its own content file")

INV = yaml.safe_load(CFG.read_text())
RED = INV["redact"]
DOMAIN = INV["meta"]["domain"]
SHOWN_DOMAIN = DOMAIN if (UNREDACTED or not RED["domain"]) else RED["domain_placeholder"]

W, H = 2400, 1200

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

# Interface strings. The content is in site.en.yaml / site.zh.yaml; these are the
# labels this layout draws itself, so they live with the coordinates.
UI = {
    "en": dict(
        internet="Internet", networks="Networks", legend="Legend", facts="Facts & gaps",
        hardware="HARDWARE", services="SERVICES", clients="CLIENTS", links="LINKS",
        tailnet="Tailnet", wifi="Wi-Fi", custom="custom build",
        speed_hint="line width = speed", legend_cable="cable, colored by network",
        legend_uplink="uplink to the ISP", legend_net="over the internet (not a cable)",
        legend_wifi="Wi-Fi (no cable)",
        state_online="online", state_offline="offline", state_idle="idle",
    ),
    "zh": dict(
        internet="互联网", networks="网络", legend="图例", facts="已知与未知",
        hardware="硬件", services="服务", clients="客户机", links="链路",
        tailnet="Tailnet", wifi="Wi-Fi", custom="自建",
        speed_hint="线宽 = 速率", legend_cable="网线，颜色代表所属网络",
        legend_uplink="上联至运营商", legend_net="走互联网（不是网线）",
        legend_wifi="Wi-Fi（无线接入）",
        state_online="在线", state_offline="离线", state_idle="空闲",
    ),
}[LANG]

WIDE = ((0x1100, 0x115F), (0x2E80, 0x303E), (0x3041, 0x33FF), (0x3400, 0x4DBF),
        (0x4E00, 0x9FFF), (0xA000, 0xA4CF), (0xAC00, 0xD7A3), (0xF900, 0xFAFF),
        (0xFE30, 0xFE4F), (0xFF00, 0xFF60), (0xFFE0, 0xFFE6))


def wide(ch):
    """CJK and full-width punctuation advance one em, unlike the latin estimate."""
    o = ord(ch)
    return any(a <= o <= b for a, b in WIDE)


def state_label(s):
    """'offline 3 h' → the state word in this language, the duration in its unit."""
    word, _, rest = str(s).partition(" ")
    text = UI.get(f"state_{word}", word)
    if rest and LANG == "zh" and rest.endswith("h"):
        rest = rest[:-1].strip() + " 小时"
    return f"{text} {rest}".strip()


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
    s = sub(s)
    if not any(wide(c) for c in s):        # pure latin keeps the original estimate
        return len(s) * size * (0.6 if mono else 0.53)
    return sum(size if wide(c) else size * (0.6 if mono else 0.53) for c in s)


def _font_file(pattern):
    """Path of an installed font via fontconfig (fc-match), or None."""
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}", pattern], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except Exception:
        return None


try:
    from PIL import ImageFont
    _FONTS = {700: _font_file("Fira Sans:bold"), 600: _font_file("Fira Sans:semibold"),
              400: _font_file("Fira Sans:regular")}
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
    S.text(tx_, y + 28 + dy, g.get("model") or UI["custom"], 14, TEXT if g.get("model") else MUTED, 500)
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
BG_IDX = len(S.p)
S.add("")
S.add("")

meta = INV["meta"]
title = meta["title"] if (UNREDACTED or not RED["domain"]) else meta["title_redacted"]
S.text(40, 86, title, 46, TEXT, 700, ls=-0.5)
S.text(W - 40, 74, meta["watermark"], 21, REDDIT, 700, "end")
S.text(W - 40, 100, meta["date"], 16, MUTED, 400, "end")

# ================================================================ left column: networks
vx, vy, vw = 40, 150, 500
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

# ================================================================ legend
LG_ROWS = ["speed", "access", "wan", "net", "wifi"]
lgx, lgy, lgw = 40, vy + vh + 32, 500
LR = 27
lgh = 52 + len(LG_ROWS) * LR + 8
S.rect(lgx, lgy, lgw, lgh, rx=14, fill=PANEL, stroke=BORDER, sw=1.4)
S.text(lgx + 20, lgy + 36, UI["legend"], 19, TEXT, 600)
SX, TX = lgx + 22, lgx + 178
for i, k in enumerate(LG_ROWS):
    y = lgy + 66 + i * LR
    t = None
    if k == "speed":
        S.text(SX, y + 4.5, UI["speed_hint"], 12.5, MUTED, 400)
        x0 = TX
        for lbl in ("10G", "2.5G", "1G", "100M"):
            S.line([(x0, y), (x0 + 24, y)], C["10"], SPEED_W[lbl], r=0, cap="butt")
            S.text(x0 + 29, y + 4.5, lbl, 12, TEXT, 500, mono=True)
            x0 += 29 + tw(lbl, 12, True) + 16
    elif k == "access":
        for jj, c in enumerate(["10", "wan"]):
            S.line([(SX + jj * 16, y), (SX + jj * 16 + 12, y)], C[c], 3.6, r=0, cap="butt")
        t = UI["legend_cable"]
    elif k == "wan":
        S.line([(SX, y), (SX + 50, y)], C["wan"], 3, r=0); t = UI["legend_uplink"]
    elif k == "net":
        S.line([(SX, y), (SX + 50, y)], MUTED, 1.8, dash="2 5", r=0); t = UI["legend_net"]
    elif k == "wifi":
        S.line([(SX, y), (SX + 50, y)], C["10"], 2, dash="3 4", r=0); t = UI["legend_wifi"]
    if t:
        S.text(TX, y + 4.5, t, 13, MUTED, 400)

# ================================================================ nothing exposed
ex = INV["exposed"]
exy = lgy + lgh + 32
S.rect(40, exy, 500, 116, rx=14, fill=PANEL, stroke=BORDER, sw=1.4)
S.text(60, exy + 34, ex["title"], 19, TEXT, 600)
S.text(60, exy + 60, ex["note"], 14, C["10"], 600)
S.text(60, exy + 86, ex["sub"], 12.5, MUTED, 400)

# ================================================================ footer notes (how the facts were gathered)
nq = INV["notes"]
ny0 = exy + 148
S.rect(40, ny0, 500, 56 + len(nq) * 26, rx=14, fill=PANEL, stroke=BORDER, sw=1.4)
S.text(60, ny0 + 34, UI["facts"], 19, TEXT, 600)
for i, n in enumerate(nq):
    y = ny0 + 62 + i * 26
    S.add(f'<circle cx="66" cy="{y - 4}" r="2.4" fill="{FAINT}"/>')
    S.text(80, y, n, 12.5, MUTED, 400)

# ================================================================ TOP: internet cloud
CX = 1150
cy0 = 176
rw = INV["remote"]
rx_, ry_ = 620, 146

blobs = [(-95, 18, 42), (-45, -8, 56), (25, -18, 62), (90, 6, 48), (130, 26, 30), (-130, 30, 28)]
for dx, dy, r in blobs:
    S.add(f'<circle cx="{CX+dx}" cy="{cy0+dy}" r="{r+2.5}" fill="#3a4a60"/>')
S.add(f'<rect x="{CX-150}" y="{cy0+12}" width="300" height="46" rx="23" fill="#3a4a60"/>')
for dx, dy, r in blobs:
    S.add(f'<circle cx="{CX+dx}" cy="{cy0+dy}" r="{r}" fill="#1a2433"/>')
S.add(f'<rect x="{CX-147.5}" y="{cy0+14.5}" width="295" height="41" rx="20.5" fill="#1a2433"/>')
S.text(CX, cy0 + 14, UI["internet"], 26, TEXT, 600, "middle")
S.text(CX, cy0 + 40, INV["internet"]["caption"], 13, MUTED, 400, "middle")

# remote access reaches the LAN over the internet (dotted = logical, not a cable)
S.line([(rx_ + 330, ry_ + 42), (CX - 116, ry_ + 42)], C["vpn"], 1.8, dash="2 5", r=0)
S.rect(rx_, ry_, 330, 84, rx=12, fill=PANEL, stroke=C["vpn"] + "aa", sw=1.6)
S.icon("tailscale", rx_ + 16, ry_ + 22, 38)
S.text(rx_ + 66, ry_ + 38, rw["name"], 18, TEXT, 600)
S.text(rx_ + 66, ry_ + 60, rw["note"], 13, MUTED, 400)

# cloud services (+ the dotted line that says "this is not a cable")
csx, csy = 1700, 146
for i, cs in enumerate(INV["internet"]["cloud_services"]):
    y = csy + i * 54
    S.rect(csx, y, 570, 44, rx=10, fill=PANEL2, stroke=BORDER)
    S.icon(cs["icon"], csx + 10, y + 9, 26)
    S.text(csx + 46, y + 20, cs["name"], 14, TEXT, 600)
    S.text(csx + 46, y + 36, cs["note"], 12, MUTED, 400)
S.line([(CX + 128, cy0 - 8), (csx, csy + 22)], FAINT, 1.6, dash="2 5", r=0)

# tailnet node list
tl = INV["tailnet"]
tly = csy + len(INV["internet"]["cloud_services"]) * 54 + 20
S.rect(csx, tly, 570, 62 + len(tl) * 38, rx=14, fill=PANEL, stroke=BORDER, sw=1.4)
S.text(csx + 20, tly + 34, UI["tailnet"], 19, TEXT, 600)
S.icon("tailscale", csx + 500, tly + 14, 24)
for i, n in enumerate(tl):
    y = tly + 62 + i * 38
    on = n["state"].startswith("online")
    dot = "#3fb950" if on else FAINT
    S.add(f'<circle cx="{csx + 26}" cy="{y - 4}" r="3.4" fill="{dot}"/>')
    S.text(csx + 40, y, n["name"], 13.5, TEXT, 600)
    S.text(csx + 210, y, n["ip"], 12.5, C["vpn"], 500, mono=True)
    S.text(csx + 356, y, n["os"], 12.5, MUTED, 400, mono=True)
    S.text(csx + 550, y, state_label(n["state"]), 12, MUTED if on else FAINT, 400, "end")

# ================================================================ ISP ONT
isp = INV["isp"]
OX, OY, OW, OH = 920, 304, 460, 100
device_card(OX, OY, OW, OH, [], isp, C["wan"])
# the fiber plugs into the top edge, right where the internet line lands
S.line([(CX, cy0 + 58), (CX, OY - 4)], "#6b7a90", 3)
S.add(f'<circle cx="{CX}" cy="{OY - 4}" r="10" fill="#0b0f15" stroke="#5a6b82" stroke-width="2"/>'
      f'<circle cx="{CX}" cy="{OY - 4}" r="2.6" fill="{C["wan"]}"/>')

# ================================================================ router
rt = INV["router"]
RX, RY, RW_, RH = 700, 470, 900, 470
device_card(RX, RY, RW_, RH, ["tp-link"], rt, C["10"], stroke=TRUNK_BORDER)

S.text(RX + 18, RY + 96, UI["hardware"], 11.5, HWC, 700, ls=1.4)
for i, hwi in enumerate(rt["hw"]):
    x, y = RX + 16, RY + 106 + i * 64
    S.rect(x, y, 210, 58, rx=11, fill="#151d29", stroke="#2e3a4c", sw=1.2)
    hw_bar(x, y, 58)
    S.icon(hwi["icon"], x + 12, y + 15, 28)
    S.text(x + 50, y + 17, hwi["label"], 10, "#c08a5c", 700, ls=1.3)
    vs = min(15.5, 15.5 * 148 / max(measure(hwi["value"], 15.5, 700), 1))
    S.text(x + 50, y + 35, hwi["value"], round(vs, 2), TEXT, 700)
    ss = min(10.5, 10.5 * 148 / max(measure(hwi["sub"], 10.5, 400), 1))
    S.text(x + 50, y + 50, hwi["sub"], round(ss, 2), MUTED, 400)

S.text(RX + 250, RY + 96, UI["services"], 11.5, HWC, 700, ls=1.4)
sw_, sh_ = 200, 50
for i, sv in enumerate(rt["services"]):
    col, row = i % 3, i // 3
    x = RX + 248 + col * (sw_ + 8)
    y = RY + 106 + row * (sh_ + 8)
    S.rect(x, y, sw_, sh_, rx=9, fill=CHIP, stroke=BORDER, sw=1)
    S.icon(sv["icon"], x + 9, y + 12, 26)
    S.text(x + 44, y + 22, sv["name"], 14, TEXT, 600)
    S.text(x + 44, y + 39, sv["note"], 11.5, MUTED, 400)

# what is on the LAN, and how it gets there (fills the space under the service tiles)
pmx, pmy = RX + 248, RY + 238
S.text(pmx, pmy, UI["clients"], 11.5, HWC, 700, ls=1.4)
for i, row in enumerate(rt["clients"]):
    y = pmy + 20 + i * 32
    S.rect(pmx, y, 624, 30, rx=7, fill=CHIP, stroke=BORDER, sw=1)
    S.text(pmx + 12, y + 20, row["name"], 13, TEXT, 600)
    S.text(pmx + 210, y + 20, row["ip"], 11.5, C["10"], 500, mono=True)
    S.text(pmx + 380, y + 20, row["link"], 11.5, MUTED, 400, mono=True)
    S.text(pmx + 612, y + 20, row["note"], 11.5, FAINT, 400, "end")

# every client here is wireless: the links leave the router's radio, drawn as antennas
S.text(RX + 18, RY + RH - 70, UI["links"], 11.5, HWC, 700, ls=1.4)
S.text(RX + 104, RY + RH - 70, rt["lan_note"], 12, FAINT, 400)

WIFI_X = [880, 1120, 1360, 1560]
for wx in WIFI_X:
    S.icon("glyph-antenna", wx - 11, RY + RH - 30, 22)

# cables into the router: ONT on top (WAN), devices below (LAN)
S.line([(CX, OY + OH), (CX, RY + 40)], C["wan"], SPEED_W[rt["wan_speed"]])
S.label(CX + 8, (OY + OH + RY + 40) / 2 + 4, rt["wan_speed"], C["wan"], 11, anchor="start", mono=True)

# ================================================================ device row
DY, DH, DW = 1080, 92, 340
dev = INV["devices"]
ORDER = ("mac", "iphone", "ios", "console")
BOXES = dict(zip(ORDER, (620, 970, 1320, 1670)))


def device(key):
    d = dev[key]
    x = BOXES[key]
    device_card(x, DY, DW, DH, d["icons"], d, C[d["vlan"]], stroke=TRUNK_BORDER if d.get("trunk") else None)
    return x, DW, DH, x + tab_width(d) + 34


DROUTE = 1000
for key, px in zip(ORDER, WIFI_X):
    d = dev[key]
    _, _, _, entry = device(key)
    col = C[d["vlan"]]
    if d["link"] == "wifi":
        S.line([(px, RY + RH), (px, DROUTE), (entry, DROUTE), (entry, DY)], col, 2, dash="3 4")
        S.label(px + 12, DROUTE + 26, UI["wifi"], col, 11, anchor="start")
    else:
        S.line([(px, RY + RH - 10), (px, DROUTE), (entry, DROUTE), (entry, DY)], col, SPEED_W[d["speed"]])
        S.label(px + 12, DROUTE + 26, d["speed"], col, 11, anchor="start", mono=True)

H = int(max(DY + DH, tly + 62 + len(tl) * 38, ny0 + 56 + len(nq) * 26) + 32)
S.rect(0, 0, W, H, rx=0, fill=BG, stroke=BG, sw=0)
S.rect(0, 0, W, H, rx=0, fill="url(#dots)", stroke="none", sw=0)
_dots = S.p.pop()
S.p[BG_IDX], S.p[BG_IDX + 1] = S.p.pop(), _dots

assert DY + DH + 20 <= H, f"canvas too short: devices end at {DY + DH}"
assert RX + RW_ <= 1700, "router card runs into the right column"

OUT.mkdir(exist_ok=True)
name = "-".join([SITE.name] + ([] if LANG == "en" else [LANG]) + (["unredacted"] if UNREDACTED else []))
svg_path = OUT / f"{name}.svg"
svg_path.write_text(S.render())
png_path = OUT / f"{name}.png"
subprocess.run(["rsvg-convert", "-z", "1.6", "-o", str(png_path), str(svg_path)], check=True)
print(svg_path, png_path)
