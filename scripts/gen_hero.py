"""Generates the comic-hero animated SVG artwork for the MSaadShahid1 GitHub profile README.

Usage: python gen_hero.py <out-dir> [panel ...]   (no panels = build them all)
Every panel is a self-contained SVG (CSS + SMIL animation, subsetted OFL fonts embedded as data URIs),
so it animates inside GitHub's <img> sandbox with no external requests.
"""
import base64
import datetime as dt
import html
import io
import math
import os
import random
import re
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, 'fonts')
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

BG0 = '#0d1117'  # GitHub dark background: the stack fades into it only at the very top and bottom
SEAM = '#0b0f2a'  # colour every panel edge meets, so stacked panels read as one canvas
INK = '#0b0b16'
GREEN, TEAL, CYAN, BLUE = '#39ff88', '#14b8a6', '#22d3ee', '#3b82f6'
PINK, MAGENTA, PURPLE = '#ff3d9a', '#d946ef', '#8b5cf6'
ORANGE, GOLD, RED, WHITE = '#ff8a3d', '#ffd23f', '#ff4757', '#f8fafc'
SOFT = '#dbe4ff'
MUTED = '#9fb0d6'

SKIN, SKIN_SH = '#c68a5e', '#a5683f'
HAIR, HAIR_HI = '#16101f', '#41336a'
JACKET, JACKET_SH = '#232842', '#171b2e'
PANTS = '#2c3557'

FONTS = {
    'fb': ('Bangers', 400, 'bangers.woff2'),
    'fc': ('Chakra Petch', 500, 'chakra500.woff2'),
    'fcb': ('Chakra Petch', 700, 'chakra700.woff2'),
}

# ── Fonts & text ───────────────────────────────────────────────────────────
_metrics = {}


def _font(key):
    if key not in _metrics:
        f = TTFont(os.path.join(FONT_DIR, FONTS[key][2]))
        _metrics[key] = (f.getBestCmap(), f['hmtx'], f['head'].unitsPerEm)
    return _metrics[key]


def tw(s, key, size, ls=0):
    """Rendered width of a string, from the font's advance widths."""
    cmap, hmtx, upm = _font(key)
    adv = sum(hmtx[cmap.get(ord(c), cmap[ord('?')])][0] for c in s)
    return adv * size / upm + ls * len(s)


def esc(s):
    return html.escape(s, quote=False)


def font_faces(body):
    chars = set(' ')
    for m in re.finditer(r'<text\b[^>]*>(.*?)</text>', body, re.S):
        chars |= set(html.unescape(re.sub(r'<[^>]+>', '', m.group(1))))
    css = ''
    for key, (family, weight, fname) in FONTS.items():
        if not re.search(rf'class="(?:[^"]*\s)?{key}(?:\s[^"]*)?"', body):
            continue
        opts = subset.Options()
        opts.flavor = 'woff'
        opts.name_IDs = ['*']  # keep the OFL copyright and licence records
        opts.layout_features = ['kern']
        font = subset.load_font(os.path.join(FONT_DIR, fname), opts)
        sub = subset.Subsetter(opts)
        sub.populate(text=''.join(sorted(chars)))
        sub.subset(font)
        buf = io.BytesIO()
        subset.save_font(font, buf, opts)
        data = base64.b64encode(buf.getvalue()).decode()
        css += f"@font-face{{font-family:'{family}';font-weight:{weight};src:url(data:font/woff;base64,{data}) format('woff')}}"
    return css


def T(x, y, s, key='fc', size=18, fill=WHITE, anchor='start', ls=0, extra=''):
    a = f' text-anchor="{anchor}"' if anchor != 'start' else ''
    a += f' letter-spacing="{ls}"' if ls else ''
    return f'<text class="{key}" x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}"{a} {extra}>{esc(s)}</text>'


def comic(x, y, s, size, fill, anchor='start', ls=2, depth=None, sw=None, extra=''):
    """Comic-book lettering: thick ink outline plus a solid extruded shadow."""
    depth = size * 0.07 if depth is None else depth
    sw = size * 0.12 if sw is None else sw
    a = (f'class="fb" font-size="{size}" text-anchor="{anchor}" letter-spacing="{ls}" '
         f'stroke="{INK}" stroke-width="{sw:.1f}" stroke-linejoin="round"')
    return (f'<text {a} x="{x + depth:.1f}" y="{y + depth:.1f}" fill="{INK}">{esc(s)}</text>'
            f'<text {a} x="{x:.1f}" y="{y:.1f}" fill="{fill}" paint-order="stroke" {extra}>{esc(s)}</text>')


def chip(x, y, s, fill, color=INK, size=19, key='fb', pad=15, ls=1, skew=9, h=None):
    """Slanted comic tag. Returns (svg, width)."""
    h = h or round(size * 1.75)
    w = tw(s, key, size, ls) + pad * 2

    def pts(dx, dy):
        return (f'{x + skew + dx:.1f},{y + dy:.1f} {x + w + skew + dx:.1f},{y + dy:.1f} '
                f'{x + w + dx:.1f},{y + h + dy:.1f} {x + dx:.1f},{y + h + dy:.1f}')
    out = (f'<polygon points="{pts(4, 4)}" fill="{INK}"/>'
           f'<polygon points="{pts(0, 0)}" fill="{fill}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
           + T(x + skew / 2 + w / 2, y + h / 2 + size * 0.36, s, key, size, color, 'middle', ls))
    return out, w + skew


def g(content, transform=None, cls=None, style=None):
    a = f' transform="{transform}"' if transform else ''
    a += f' class="{cls}"' if cls else ''
    a += f' style="{style}"' if style else ''
    return f'<g{a}>{content}</g>'


def hexpts(cx, cy, r, start=-90):
    return ' '.join(f'{cx + r * math.cos(math.radians(start + 60 * i)):.1f},'
                    f'{cy + r * math.sin(math.radians(start + 60 * i)):.1f}' for i in range(6))


def limb(points, w, color):
    d = 'M' + ' L'.join(f'{x},{y}' for x, y in points)
    common = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    return (f'<path d="{d}" {common} stroke="{INK}" stroke-width="{w + 8}"/>'
            f'<path d="{d}" {common} stroke="{color}" stroke-width="{w}"/>')


def emblem(r, color=GREEN, base=INK):
    k = r / 10
    bolt = f'M{2*k:.1f},{-7*k:.1f} L{-5*k:.1f},{1*k:.1f} L{-.5*k:.1f},{1*k:.1f} L{-2*k:.1f},{7*k:.1f} L{5*k:.1f},{-1*k:.1f} L{.5*k:.1f},{-1*k:.1f} Z'
    return (f'<polygon points="{hexpts(0, 0, r)}" fill="{base}" stroke="{color}" stroke-width="{max(1.5, r * .16):.1f}" stroke-linejoin="round"/>'
            f'<path d="{bolt}" fill="{color}"/>')


# ── Shared CSS & defs ──────────────────────────────────────────────────────
BASE_CSS = '''
.fb{font-family:'Bangers',Impact,'Arial Black',sans-serif;font-weight:400}
.fc{font-family:'Chakra Petch','Segoe UI',sans-serif;font-weight:500}
.fcb{font-family:'Chakra Petch','Segoe UI',sans-serif;font-weight:700}
.bob{animation:bob 3.2s ease-in-out infinite}
.bob-s{animation:bobs 2.8s ease-in-out infinite}
@keyframes bob{50%{transform:translateY(-12px)}}
@keyframes bobs{50%{transform:translateY(-4px)}}
.blink{animation:blink 5s infinite;transform-box:fill-box;transform-origin:center}
@keyframes blink{0%,93%,100%{transform:scaleY(1)}95%{transform:scaleY(.08)}}
.tw{animation:tw 3s ease-in-out infinite}
@keyframes tw{0%,100%{opacity:.15}50%{opacity:1}}
.spin{animation:spin 18s linear infinite;transform-box:fill-box;transform-origin:center}
.spin-r{animation:spin 26s linear infinite reverse;transform-box:fill-box;transform-origin:center}
.spin-f{animation:spin 3s linear infinite;transform-box:fill-box;transform-origin:center}
@keyframes spin{to{transform:rotate(360deg)}}
.pulse{animation:pulse 1.6s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes pulse{50%{transform:scale(1.14)}}
.glow{animation:glow 2.2s ease-in-out infinite}
@keyframes glow{0%,100%{opacity:.45}50%{opacity:1}}
.ring{animation:ring 2.1s ease-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes ring{0%{transform:scale(.25);opacity:1}100%{transform:scale(2.7);opacity:0}}
.flame{animation:flame .16s ease-in-out infinite alternate;transform-box:fill-box;transform-origin:50% 0}
@keyframes flame{from{transform:scale(.9,.75)}to{transform:scale(1.06,1.2)}}
.rise{animation:rise 3.6s linear infinite}
@keyframes rise{0%{transform:translateY(0);opacity:0}15%{opacity:1}100%{transform:translateY(-150px);opacity:0}}
.dash{animation:dash 1s linear infinite}
@keyframes dash{to{stroke-dashoffset:-26}}
.zap{animation:zap 1.3s steps(1) infinite}
@keyframes zap{0%,100%{opacity:0}10%,22%{opacity:1}16%{opacity:.2}30%{opacity:0}}
.blinkfast{animation:bf 1s steps(1) infinite}
@keyframes bf{50%{opacity:.15}}
.look{animation:look 6s ease-in-out infinite}
@keyframes look{0%,100%{transform:translate(0,0)}18%,40%{transform:translate(-15px,3px)}55%,78%{transform:translate(11px,-6px)}}
.sway{animation:sway 2.6s ease-in-out infinite;transform-box:fill-box;transform-origin:50% 0}
@keyframes sway{0%,100%{transform:rotate(-7deg)}50%{transform:rotate(7deg)}}
.breathe{animation:breathe 3.4s ease-in-out infinite}
@keyframes breathe{50%{transform:translateY(-3px)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
'''

COMMON_DEFS = f'''
<linearGradient id="fadeTop" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG0}" stop-opacity="0"/></linearGradient>
<linearGradient id="fadeBot" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG0}" stop-opacity="0"/><stop offset="1" stop-color="{BG0}"/></linearGradient>
<linearGradient id="seamTop" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{SEAM}"/><stop offset="1" stop-color="{SEAM}" stop-opacity="0"/></linearGradient>
<linearGradient id="seamBot" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{SEAM}" stop-opacity="0"/><stop offset="1" stop-color="{SEAM}"/></linearGradient>
<linearGradient id="gFlame" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff7c2"/><stop offset=".35" stop-color="{GOLD}"/><stop offset=".75" stop-color="{ORANGE}"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></linearGradient>
<radialGradient id="gByte" cx=".38" cy=".3" r=".8"><stop offset="0" stop-color="#ffffff"/><stop offset=".6" stop-color="#e8eefc"/><stop offset="1" stop-color="#b9c6ea"/></radialGradient>
<radialGradient id="gGreen"><stop offset="0" stop-color="{GREEN}" stop-opacity=".75"/><stop offset=".45" stop-color="{GREEN}" stop-opacity=".22"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></radialGradient>
<radialGradient id="gCyan"><stop offset="0" stop-color="{CYAN}" stop-opacity=".6"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
<radialGradient id="gPink"><stop offset="0" stop-color="{PINK}" stop-opacity=".55"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient>
<radialGradient id="gGold"><stop offset="0" stop-color="{GOLD}" stop-opacity=".6"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
<radialGradient id="gWhite"><stop offset="0" stop-color="#ffffff" stop-opacity=".9"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>
<radialGradient id="gCore" cx=".4" cy=".35"><stop offset="0" stop-color="#eafff2"/><stop offset=".45" stop-color="{GREEN}"/><stop offset="1" stop-color="#0f9d58"/></radialGradient>
<radialGradient id="gIris" cx=".4" cy=".35"><stop offset="0" stop-color="#b7ffd6"/><stop offset=".6" stop-color="{GREEN}"/><stop offset="1" stop-color="#079c63"/></radialGradient>
<linearGradient id="gTitleA" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fffbc2"/><stop offset=".5" stop-color="{GOLD}"/><stop offset="1" stop-color="{ORANGE}"/></linearGradient>
<linearGradient id="gTitleB" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e3fff0"/><stop offset=".5" stop-color="{GREEN}"/><stop offset="1" stop-color="{TEAL}"/></linearGradient>
<linearGradient id="gTitleC" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe0f0"/><stop offset=".5" stop-color="{PINK}"/><stop offset="1" stop-color="#b5179e"/></linearGradient>
<linearGradient id="gTitleD" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e0fbff"/><stop offset=".5" stop-color="{CYAN}"/><stop offset="1" stop-color="{BLUE}"/></linearGradient>
<linearGradient id="gBeamUp" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#fff3c4" stop-opacity=".5"/><stop offset="1" stop-color="#fff3c4" stop-opacity="0"/></linearGradient>
<linearGradient id="gBeamL" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="{GREEN}" stop-opacity=".6"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></linearGradient>
<linearGradient id="gHolo" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{GREEN}" stop-opacity=".45"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></linearGradient>
<pattern id="dots" width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="4.5" cy="4.5" r="1.6" fill="#ffffff"/></pattern>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40,0 L0,0 0,40" fill="none" stroke="#7aa2ff" stroke-width="1"/></pattern>
'''


def write_svg(name, w, h, label, body, css='', defs=''):
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
           f'role="img" aria-label="{html.escape(label)}"><title>{esc(label)}</title>'
           f'<defs><style>{font_faces(body)}{BASE_CSS}{css}</style>{COMMON_DEFS}{defs}</defs>{body}</svg>\n')
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        f.write(doc)
    print(f'{name}: {len(doc) // 1024} KB')


# ── Scenery helpers ────────────────────────────────────────────────────────
TITLE_BAND = ((250, 0, 950, 182),)


def stars(rng, n, x0, y0, x1, y1, avoid=(), colors=('#ffffff', '#bfe9ff', '#ffe9b0', '#ffd0ec'), rects=TITLE_BAND):
    out = []
    for _ in range(n):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if any(math.hypot(x - ax, y - ay) < ar for ax, ay, ar in avoid):
            continue
        if any(rx0 - 8 <= x <= rx1 + 8 and ry0 - 8 <= y <= ry1 + 8 for rx0, ry0, rx1, ry1 in rects):
            continue
        r = rng.choice([0.7, 0.9, 1.1, 1.3, 1.6, 2.2])
        c = rng.choice(colors)
        st = f'animation-duration:{rng.uniform(1.8, 5):.1f}s;animation-delay:-{rng.uniform(0, 5):.1f}s'
        if r > 2:
            s = r * 3.4
            out.append(f'<path class="tw" style="{st}" fill="{c}" d="M{x:.1f},{y - s:.1f} Q{x:.1f},{y:.1f} {x + s:.1f},{y:.1f} '
                       f'Q{x:.1f},{y:.1f} {x:.1f},{y + s:.1f} Q{x:.1f},{y:.1f} {x - s:.1f},{y:.1f} Q{x:.1f},{y:.1f} {x:.1f},{y - s:.1f} Z"/>')
        else:
            out.append(f'<circle class="tw" style="{st}" cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{c}"/>')
    return ''.join(out)


def edges(w, h, top=34, bottom=46, top_to=SEAM, bottom_to=SEAM):
    tid = 'fadeTop' if top_to == BG0 else 'seamTop'
    bid = 'fadeBot' if bottom_to == BG0 else 'seamBot'
    return (f'<rect width="{w}" height="{top}" fill="url(#{tid})"/>'
            f'<rect y="{h - bottom}" width="{w}" height="{bottom}" fill="url(#{bid})"/>')


def halftone(uid, cx, cy, r, opacity=0.08):
    """Comic halftone dots that fade out radially."""
    return (f'<radialGradient id="ht{uid}"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/></radialGradient>'
            f'<mask id="htm{uid}"><circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#ht{uid})"/></mask>'
            f'<rect x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" fill="url(#dots)" opacity="{opacity}" mask="url(#htm{uid})"/>')


def shooting_stars(specs):
    out = []
    for x, y, delay, dur in specs:
        out.append(f'<g transform="translate({x},{y})"><g class="shoot" style="animation-delay:{delay}s;animation-duration:{dur}s">'
                   f'<line x1="0" y1="0" x2="130" y2="-44" stroke="url(#gShoot)" stroke-width="3" stroke-linecap="round"/>'
                   f'<circle r="3" fill="#fff"/></g></g>')
    return ''.join(out)


SHOOT_CSS = '''
.shoot{opacity:0;animation:shoot 7s ease-in infinite}
@keyframes shoot{0%{transform:translate(0,0);opacity:0}2%{opacity:1}13%{transform:translate(-460px,156px);opacity:0}100%{opacity:0}}
'''
SHOOT_DEF = '<linearGradient id="gShoot" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'


def hills(rng, w, base, amp, fill, seed_phase=0.0, opacity=1.0):
    pts = []
    for i in range(0, w + 41, 40):
        y = base - amp * (0.55 + 0.3 * math.sin(i / 97 + seed_phase) + 0.15 * math.sin(i / 31 + seed_phase * 2))
        pts.append((i, y))
    d = f'M0,{base + 200} L' + ' L'.join(f'{x},{y:.1f}' for x, y in pts) + f' L{w},{base + 200} Z'
    return f'<path d="{d}" fill="{fill}" opacity="{opacity}"/>'


def city(rng, x0, x1, base, hmin, hmax, fill='#120a2c', rim='#ff5ea8', depth=200, low=()):
    """Silhouette skyline with lit, flickering windows and blinking antenna lights."""
    out, x = [], x0
    while x < x1:
        w = rng.randint(34, 78)
        h = rng.randint(hmin, hmax)
        if any(a <= x + w / 2 <= b for a, b, _ in low):
            h = min(h, next(m for a, b, m in low if a <= x + w / 2 <= b))
        top = base - h
        out.append(f'<rect x="{x}" y="{top}" width="{w}" height="{h + depth}" fill="{fill}"/>')
        out.append(f'<rect x="{x}" y="{top}" width="{w}" height="2" fill="{rim}" opacity=".55"/>')
        for wx in range(x + 6, x + w - 8, 10):
            for wy in range(top + 10, base - 4, 14):
                if rng.random() < 0.3:
                    c = rng.choice(['#ffd36b', '#7dd3fc', '#f0abfc', '#fff3c4'])
                    if rng.random() < 0.12:
                        out.append(f'<rect class="tw" style="animation-duration:{rng.uniform(3, 8):.1f}s;animation-delay:-{rng.uniform(0, 8):.1f}s" '
                                   f'x="{wx}" y="{wy}" width="4" height="6" fill="{c}"/>')
                    else:
                        out.append(f'<rect x="{wx}" y="{wy}" width="4" height="6" fill="{c}" opacity=".75"/>')
        if h > hmin + (hmax - hmin) * 0.6 and rng.random() < 0.6:
            ax = x + w // 2
            out.append(f'<rect x="{ax - 1}" y="{top - 26}" width="2" height="26" fill="{fill}"/>'
                       f'<circle class="blinkfast" style="animation-delay:-{rng.uniform(0, 1):.2f}s" cx="{ax}" cy="{top - 27}" r="3" fill="{RED}"/>')
        x += w + rng.randint(-4, 5)
    return ''.join(out)


def pagoda(x, base, w, h, fill='#120a2c', rim='#ff5ea8'):
    """San Fransokyo-style tower: a skyscraper wearing stacked pagoda roofs."""
    top = base - h
    s = [f'<rect x="{x}" y="{top}" width="{w}" height="{h + 200}" fill="{fill}"/>']
    for i, (rw, ry) in enumerate(((w + 34, top), (w + 18, top - 22), (w + 4, top - 42))):
        cx = x + w / 2
        s.append(f'<path d="M{cx - rw / 2 - 8:.1f},{ry - 2} Q{cx - rw / 2:.1f},{ry - 8} {cx - rw / 2 + 10:.1f},{ry - 12} L{cx + rw / 2 - 10:.1f},{ry - 12} '
                 f'Q{cx + rw / 2:.1f},{ry - 8} {cx + rw / 2 + 8:.1f},{ry - 2} Z" fill="{fill}" stroke="{rim}" stroke-opacity=".6" stroke-width="1.5"/>')
        s.append(f'<rect x="{cx - rw / 2 + 12:.1f}" y="{ry - 22}" width="{rw - 24:.1f}" height="10" fill="{fill}"/>')
    cx = x + w / 2
    s.append(f'<rect x="{cx - 1.5}" y="{top - 84}" width="3" height="30" fill="{fill}"/>'
             f'<circle class="blinkfast" cx="{cx}" cy="{top - 86}" r="3.5" fill="{RED}"/>')
    for wy in range(top + 12, base - 6, 16):
        s.append(f'<rect x="{x + 8}" y="{wy}" width="{w - 16}" height="4" fill="#ff9ecf" opacity=".35"/>')
    return ''.join(s)


def faisal_mosque(cx, base, sc=1.0, fill='#1c1145', rim='#ff8fc4'):
    s = []
    for mx, mh in ((-60, 118), (60, 118), (-98, 152), (98, 152)):
        x, top, w = cx + mx * sc, base - mh * sc, 7 * sc
        s.append(f'<rect x="{x - w / 2:.1f}" y="{top:.1f}" width="{w:.1f}" height="{mh * sc:.1f}" fill="{fill}"/>'
                 f'<path d="M{x - w / 2 - 1:.1f},{top:.1f} L{x:.1f},{top - 26 * sc:.1f} L{x + w / 2 + 1:.1f},{top:.1f} Z" fill="{fill}"/>'
                 f'<rect x="{x - w:.1f}" y="{top + mh * sc * .36:.1f}" width="{2 * w:.1f}" height="{4 * sc:.1f}" fill="{fill}"/>'
                 f'<line x1="{x + w / 2:.1f}" y1="{top:.1f}" x2="{x + w / 2:.1f}" y2="{base:.1f}" stroke="{rim}" stroke-opacity=".35" stroke-width="1"/>'
                 f'<circle class="tw" cx="{x:.1f}" cy="{top - 30 * sc:.1f}" r="{2.2 * sc:.1f}" fill="#fff3c4"/>')
    p = lambda dx, dy: f'{cx + dx * sc:.1f},{base - dy * sc:.1f}'
    s.append(f'<path d="M{p(-80, 0)} L{p(-54, 34)} L{p(0, 94)} L{p(54, 34)} L{p(80, 0)} Z" fill="{fill}"/>')
    s.append(f'<path d="M{p(-54, 34)} L{p(0, 94)} L{p(54, 34)}" fill="none" stroke="{rim}" stroke-opacity=".7" stroke-width="2"/>'
             f'<path d="M{p(0, 94)} L{p(0, 0)}" stroke="{rim}" stroke-opacity=".3" stroke-width="1.5"/>'
             f'<rect x="{cx - 112 * sc:.1f}" y="{base - 6 * sc:.1f}" width="{224 * sc:.1f}" height="{10 * sc:.1f}" fill="{fill}"/>')
    return ''.join(s)


def pk_monument(cx, base, sc=1.0, fill='#1c1145', rim='#ff8fc4'):
    s = []
    for sign in (-1, 1):
        for big, (a, b, c, d) in ((True, (12, 64, 48, 84)), (False, (6, 44, 24, 60))):
            p = lambda dx, dy: f'{cx + sign * dx * sc:.1f},{base - dy * sc:.1f}'
            s.append(f'<path d="M{p(0, 0)} Q{p(a, b * .7)} {p(c, d)} Q{p(c * .82, d * .4)} {p(c * .62, 0)} Z" fill="{fill}" '
                     f'stroke="{rim}" stroke-opacity="{.6 if big else .35}" stroke-width="1.5"/>')
    s.append(f'<circle class="tw" cx="{cx}" cy="{base - 30 * sc:.1f}" r="{3 * sc:.1f}" fill="{GOLD}"/>')
    return ''.join(s)


def cloud(cx, cy, s, fill, opacity=1.0, cls=None, style=None):
    parts = ''.join(f'<circle cx="{cx + dx * s:.1f}" cy="{cy + dy * s:.1f}" r="{r * s:.1f}"/>'
                    for dx, dy, r in ((-46, 6, 26), (-18, -12, 34), (18, -18, 38), (52, 0, 28), (0, 10, 30)))
    a = f' class="{cls}"' if cls else ''
    a += f' style="{style}"' if style else ''
    return f'<g fill="{fill}" opacity="{opacity}"{a}>{parts}<rect x="{cx - 70 * s:.1f}" y="{cy:.1f}" width="{140 * s:.1f}" height="{28 * s:.1f}" rx="{14 * s:.1f}"/></g>'


def section_title(cx, y, episode, title, subtitle, grad='url(#gTitleA)', size=74):
    ew = tw(episode, 'fcb', 14, 4) + 30
    sw = tw(subtitle, 'fcb', 16, 3)
    return (f'<rect x="{cx - ew / 2:.1f}" y="{y - size - 42}" width="{ew:.1f}" height="28" rx="14" fill="{INK}" stroke="{GREEN}" stroke-width="2"/>'
            + T(cx, y - size - 23, episode, 'fcb', 14, GREEN, 'middle', 4)
            + comic(cx, y, title, size, grad, 'middle', 3)
            + T(cx, y + 36, subtitle, 'fcb', 16, CYAN, 'middle', 3)
            + f'<rect class="blinkfast" x="{cx + sw / 2 + 4:.1f}" y="{y + 22}" width="10" height="17" fill="{CYAN}"/>')


def corner_brackets(x, y, w, h, color=GREEN, L=22, sw=4):
    return (f'<path d="M{x},{y + L} L{x},{y} L{x + L},{y} M{x + w - L},{y} L{x + w},{y} L{x + w},{y + L} '
            f'M{x + w},{y + h - L} L{x + w},{y + h} L{x + w - L},{y + h} M{x + L},{y + h} L{x},{y + h} L{x},{y + h - L}" '
            f'fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round"/>')


# ── Characters ─────────────────────────────────────────────────────────────
def hero(pose='power'):
    """Cartoon Saad: origin at the feet, ~440 units tall. pose: 'power' (dial raised) or 'hips'."""
    s = []
    if pose == 'power':
        s.append('<circle cx="98" cy="-340" r="80" fill="url(#gGreen)" class="glow"/>')
    # legs + shoes
    for x0 in (-37, 11):
        s.append(f'<path d="M{x0},-140 L{x0 + 26},-140 L{x0 + 24},-24 L{x0 + 2},-24 Z" fill="{PANTS}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>')
        s.append(f'<path d="M{x0 + 18},-136 L{x0 + 20},-28 L{x0 + 23},-28 L{x0 + 25},-136 Z" fill="#1d2440"/>')
        s.append(f'<rect x="{x0 + 1}" y="-86" width="23" height="7" rx="3" fill="{GREEN}" opacity=".85"/>')
    for x0 in (-54, 8):
        s.append(f'<rect x="{x0}" y="-32" width="46" height="26" rx="12" fill="{WHITE}" stroke="{INK}" stroke-width="4"/>'
                 f'<rect x="{x0}" y="-11" width="46" height="11" rx="5" fill="{GREEN}" stroke="{INK}" stroke-width="3"/>'
                 f'<path d="M{x0 + 14},-26 l10,6 M{x0 + 21},-29 l10,6" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>')
    # neck + torso
    s.append(f'<rect x="-12" y="-284" width="24" height="30" fill="{SKIN_SH}" stroke="{INK}" stroke-width="3"/>')
    s.append(f'<path d="M-58,-244 Q-30,-264 0,-264 Q30,-264 58,-244 L64,-200 L50,-138 L-50,-138 L-64,-200 Z" fill="{JACKET}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>')
    s.append(f'<path d="M-50,-138 L-64,-200 L-58,-244 Q-50,-238 -46,-200 L-36,-138 Z" fill="{JACKET_SH}"/>')
    s.append(f'<path d="M-19,-261 L0,-214 L19,-261 Z" fill="#f1f5f9" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>')
    s.append(f'<path d="M-24,-262 L-6,-212 L-2,-140 M24,-262 L6,-212 L2,-140" fill="none" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>')
    s.append(f'<path d="M0,-212 L0,-140" stroke="{GREEN}" stroke-width="3"/>')
    s.append(f'<path d="M-52,-232 L-42,-142 M52,-232 L42,-142" stroke="{GREEN}" stroke-width="5" stroke-linecap="round" opacity=".9"/>')
    s.append(f'<rect x="-52" y="-150" width="104" height="13" rx="5" fill="{JACKET_SH}" stroke="{INK}" stroke-width="3"/>')
    s.append(g(emblem(10), 'translate(-28,-196)'))
    # arms
    if pose == 'power':
        s.append(limb([(-54, -236), (-88, -196), (-52, -158)], 22, JACKET))
        s.append(f'<circle cx="-48" cy="-154" r="12" fill="{SKIN}" stroke="{INK}" stroke-width="3.5"/>')
        s.append(limb([(54, -236), (90, -282), (98, -336)], 22, JACKET))
        s.append(f'<circle cx="99" cy="-367" r="16" fill="{SKIN}" stroke="{INK}" stroke-width="3.5"/>'
                 f'<path d="M88,-376 Q99,-382 110,-376 M88,-368 Q99,-374 110,-368" fill="none" stroke="{SKIN_SH}" stroke-width="2.5" stroke-linecap="round"/>')
        s.append(g(f'<rect x="-18" y="-12" width="36" height="25" rx="7" fill="#2b3044" stroke="{INK}" stroke-width="3"/>'
                   f'<circle r="11" fill="url(#gCore)" stroke="{INK}" stroke-width="3" class="pulse"/>'
                   f'<polygon points="{hexpts(0, 0, 5)}" fill="{INK}"/>', 'translate(98,-338) rotate(-6)'))
        for i in range(3):
            s.append(f'<circle cx="98" cy="-338" r="18" fill="none" stroke="{GREEN}" stroke-width="3" class="ring" style="animation-delay:{i * .7:.1f}s"/>')
        for i, d in enumerate(('M120,-380 l16,-9 l-6,-3 l16,-11', 'M76,-388 l-14,-12 l6,-2 l-12,-14', 'M112,-400 l4,-18 l-6,2 l4,-18')):
            s.append(f'<path class="zap" style="animation-delay:{i * .4:.1f}s" d="{d}" fill="none" stroke="{GREEN}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>')
        for i, dx in enumerate((-14, 4, 18, -4, 10)):
            s.append(f'<g class="rise" style="animation-delay:-{i * .7:.1f}s"><polygon points="{hexpts(98 + dx, -390, 4)}" fill="{GREEN}"/></g>')
    else:
        for sign in (-1, 1):
            s.append(limb([(54 * sign, -236), (88 * sign, -196), (52 * sign, -158)], 22, JACKET))
            s.append(f'<circle cx="{48 * sign}" cy="-154" r="12" fill="{SKIN}" stroke="{INK}" stroke-width="3.5"/>')
        s.append(g(f'<rect x="-11" y="-9" width="22" height="18" rx="5" fill="#2b3044" stroke="{INK}" stroke-width="2.5"/>'
                   f'<circle r="7" fill="url(#gCore)" stroke="{INK}" stroke-width="2" class="pulse"/>', 'translate(68,-176) rotate(-50)'))
    # head
    for ex in (-46, 46):
        s.append(f'<ellipse cx="{ex}" cy="-326" rx="9" ry="13" fill="{SKIN}" stroke="{INK}" stroke-width="3.5"/>')
    s.append(f'<path d="M-44,-338 Q-47,-290 -22,-274 Q0,-262 22,-274 Q47,-290 44,-338 Q42,-384 0,-386 Q-42,-384 -44,-338 Z" fill="{SKIN}" stroke="{INK}" stroke-width="4"/>')
    s.append(f'<path d="M30,-300 Q41,-318 43,-340 Q46,-294 22,-276 Z" fill="{SKIN_SH}" opacity=".55"/>')
    s.append(f'<path d="M-50,-330 Q-58,-368 -40,-390 Q-44,-412 -18,-414 Q-10,-436 14,-424 Q36,-436 44,-410 Q64,-402 56,-372 '
             f'Q60,-352 50,-334 Q46,-356 34,-362 L28,-352 Q14,-370 -2,-362 Q-16,-376 -30,-360 Q-42,-366 -44,-350 Z" '
             f'fill="{HAIR}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>')
    s.append(f'<path d="M-30,-398 Q-8,-416 18,-408 M24,-418 Q38,-412 44,-398" fill="none" stroke="{HAIR_HI}" stroke-width="4" stroke-linecap="round"/>')
    s.append(f'<path d="M-31,-347 Q-20,-355 -8,-348 M8,-348 Q20,-355 31,-347" fill="none" stroke="{HAIR}" stroke-width="5" stroke-linecap="round"/>')
    eyes = ''.join(f'<ellipse cx="{ex}" cy="-330" rx="9.5" ry="11" fill="#fff" stroke="{INK}" stroke-width="2.5"/>'
                   f'<circle cx="{ex + 1}" cy="-329" r="6" fill="#4a2c17"/><circle cx="{ex + 1}" cy="-329" r="3" fill="{INK}"/>'
                   f'<circle cx="{ex + 3}" cy="-332" r="2" fill="#fff"/>' for ex in (-19, 19))
    s.append(f'<g class="blink">{eyes}</g>')
    s.append(f'<path d="M-1,-322 Q-6,-310 1,-307" fill="none" stroke="{SKIN_SH}" stroke-width="3" stroke-linecap="round"/>')
    s.append(f'<path d="M-15,-296 Q1,-279 17,-297 Q1,-289 -15,-296 Z" fill="#fff" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>')
    return g(''.join(s), cls='breathe')


def byte_bot(wave=True):
    """Byte, the robot sidekick: origin at body centre, radius ~60."""
    s = ['<path class="flame" d="M-13,58 Q0,114 13,58 Z" fill="url(#gFlame)"/>',
         f'<rect x="-17" y="46" width="34" height="15" rx="6" fill="#94a3b8" stroke="{INK}" stroke-width="3.5"/>',
         f'<ellipse cx="-66" cy="20" rx="11" ry="21" transform="rotate(28 -66 20)" fill="#e2e8f7" stroke="{INK}" stroke-width="4"/>']
    arm = f'<ellipse cx="72" cy="-22" rx="11" ry="22" transform="rotate(38 72 -22)" fill="#e2e8f7" stroke="{INK}" stroke-width="4"/>'
    if wave:
        arm = (f'<g>{arm}<animateTransform attributeName="transform" type="rotate" values="0 54 0;-30 54 0;0 54 0;-30 54 0;0 54 0;0 54 0" '
               f'keyTimes="0;.12;.24;.36;.48;1" dur="2.8s" repeatCount="indefinite"/></g>')
    s.append(arm)
    s.append(f'<ellipse rx="60" ry="57" fill="url(#gByte)" stroke="{INK}" stroke-width="5"/>')
    s.append('<path d="M-40,40 Q0,62 44,36 Q58,18 56,-4 Q50,34 -40,40 Z" fill="#b4c0e2" opacity=".7"/>')
    for ex in (-58, 58):
        s.append(f'<circle cx="{ex}" cy="-16" r="9" fill="{CYAN}" stroke="{INK}" stroke-width="3.5"/>')
    s.append(f'<rect x="-41" y="-36" width="82" height="48" rx="21" fill="#0b1230" stroke="{INK}" stroke-width="3.5"/>')
    s.append(f'<g class="blink"><rect x="-23" y="-24" width="12" height="19" rx="6" fill="{CYAN}"/><rect x="11" y="-24" width="12" height="19" rx="6" fill="{CYAN}"/></g>')
    s.append(f'<path d="M-8,1 Q0,8 8,1" fill="none" stroke="{CYAN}" stroke-width="3" stroke-linecap="round"/>')
    s.append('<circle cx="-31" cy="2" r="4" fill="#ff7ab6" opacity=".8"/><circle cx="31" cy="2" r="4" fill="#ff7ab6" opacity=".8"/>')
    s.append('<path d="M-32,-28 Q-20,-33 -6,-32" stroke="#fff" stroke-opacity=".35" stroke-width="3" fill="none" stroke-linecap="round"/>')
    s.append(f'<path d="M0,-56 L0,-76" stroke="{INK}" stroke-width="4.5" stroke-linecap="round"/>'
             f'<circle cy="-84" r="9" fill="{ORANGE}" stroke="{INK}" stroke-width="3.5"/><circle cy="-84" r="5" fill="#fff3c4" class="blinkfast"/>')
    s.append(f'<circle cy="32" r="7" fill="{GREEN}" stroke="{INK}" stroke-width="2.5" class="pulse"/>')
    return ''.join(s)


def speech(x, y, text, size=18, fill=WHITE, tail='left'):
    """Comic speech bubble whose tail points down-left/right from (x, y) = bubble's bottom-left corner."""
    w = tw(text, 'fb', size, 1) + 28
    h = size * 1.9
    tx = x + 22 if tail == 'left' else x + w - 22
    td = -14 if tail == 'left' else 14
    return (f'<path d="M{x + 12},{y - h} L{x + w - 12},{y - h} Q{x + w},{y - h} {x + w},{y - h + 12} L{x + w},{y - 12} Q{x + w},{y} {x + w - 12},{y} '
            f'L{tx + 10},{y} L{tx + td},{y + 18} L{tx - 2},{y} L{x + 12},{y} Q{x},{y} {x},{y - 12} L{x},{y - h + 12} Q{x},{y - h} {x + 12},{y - h} Z" '
            f'fill="{fill}" stroke="{INK}" stroke-width="3.5" stroke-linejoin="round"/>'
            + T(x + w / 2, y - h / 2 + size * 0.36, text, 'fb', size, INK, 'middle', 1)), w


# ── Hero forms (the four "transformations") ────────────────────────────────
def form_vision(props=True):
    TE, TD = '#16c2a8', '#0e7d6e'
    s = [] if not props else ['<path d="M-48,-214 L-200,-282 L-200,-146 Z" fill="url(#gBeamL)" class="glow"/>',
         g(f'<path d="M-15,-6 L-13,-22 L-4,-12 L4,-12 L13,-22 L15,-6 Q16,14 0,15 Q-16,14 -15,-6 Z" fill="#fbbf24" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>'
           f'<circle cx="-6" cy="-1" r="2.4" fill="{INK}"/><circle cx="6" cy="-1" r="2.4" fill="{INK}"/><path d="M-3,5 L3,5 L0,8 Z" fill="#ff7ab6"/>'
           f'<path d="M-8,6 L-20,3 M-8,9 L-20,10 M8,6 L20,3 M8,9 L20,10" stroke="{INK}" stroke-width="1.4"/>', 'translate(-205,-206)', 'bob-s'),
         f'<rect x="-238" y="-244" width="66" height="70" fill="none" stroke="{GREEN}" stroke-width="2.5" stroke-dasharray="9 4" class="dash"/>',
         f'<rect x="-238" y="-262" width="70" height="18" fill="{GREEN}"/>' + T(-203, -248.5, 'CAT 0.98', 'fcb', 12, INK, 'middle')]
    for x0 in (-40, 16):
        s.append(f'<rect x="{x0}" y="-68" width="24" height="58" rx="10" fill="{TD}" stroke="{INK}" stroke-width="4"/>')
        s.append(f'<ellipse cx="{x0 + 12}" cy="-10" rx="20" ry="11" fill="#1e293b" stroke="{INK}" stroke-width="4"/>')
    s.append(limb([(-48, -128), (-86, -96), (-92, -62)], 16, TE) + f'<circle cx="-92" cy="-58" r="10" fill="{TE}" stroke="{INK}" stroke-width="3.5"/>')
    s.append(limb([(48, -132), (84, -152), (112, -178)], 16, TE) + f'<circle cx="115" cy="-181" r="10" fill="{TE}" stroke="{INK}" stroke-width="3.5"/>')
    s.append(f'<path d="M-56,-62 Q-64,-150 0,-172 Q64,-150 56,-62 Q40,-46 0,-46 Q-40,-46 -56,-62 Z" fill="{TE}" stroke="{INK}" stroke-width="5"/>')
    s.append(f'<ellipse cx="0" cy="-96" rx="32" ry="28" fill="{TD}" stroke="{INK}" stroke-width="3"/>' + g(emblem(13), 'translate(0,-96)', 'pulse'))
    s.append(f'<path d="M-30,-270 Q-44,-292 -58,-302 M30,-270 Q44,-292 58,-302" fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
             f'<circle cx="-60" cy="-304" r="8" fill="{GREEN}" stroke="{INK}" stroke-width="3" class="blinkfast"/><circle cx="60" cy="-304" r="8" fill="{GREEN}" stroke="{INK}" stroke-width="3"/>')
    s.append(f'<circle cx="0" cy="-214" r="66" fill="{TE}" stroke="{INK}" stroke-width="5"/>')
    s.append(f'<circle cx="0" cy="-214" r="50" fill="#fff" stroke="{INK}" stroke-width="3.5"/>')
    s.append(g(g(f'<circle r="25" fill="url(#gIris)" stroke="{INK}" stroke-width="3"/><circle r="11" fill="{INK}"/><circle cx="-7" cy="-7" r="5" fill="#fff"/>', cls='look'), 'translate(0,-212)'))
    s.append(f'<path d="M-52,-224 Q0,-290 52,-224 Q0,-250 -52,-224 Z" fill="{TD}" stroke="{INK}" stroke-width="3.5" stroke-linejoin="round"/>')
    return ''.join(s)


def form_neuro():
    s = ['<ellipse cx="0" cy="-6" rx="70" ry="11" fill="#000" opacity=".35"/>']
    body = []
    for i in range(6):
        x0 = -50 + i * 20
        d = f'M{x0},-120 C{x0 - 14},-96 {x0 + 14},-72 {x0},-44'
        body.append(f'<g class="sway" style="animation-delay:-{i * .37:.2f}s;animation-duration:{2.2 + (i % 3) * .4:.1f}s">'
                    f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="15" stroke-linecap="round"/>'
                    f'<path d="{d}" fill="none" stroke="#c026d3" stroke-width="8" stroke-linecap="round"/></g>')
    body.append(f'<path d="M-88,-140 C-94,-262 94,-262 88,-140 Q62,-116 30,-132 Q0,-112 -30,-132 Q-62,-116 -88,-140 Z" fill="url(#gJelly)" stroke="{INK}" stroke-width="5"/>')
    layers = [[(-50, -222), (-50, -192), (-50, -162)], [(0, -232), (0, -204), (0, -176)], [(50, -222), (50, -192), (50, -162)]]
    for a, b in ((0, 1), (1, 2)):
        for p in layers[a]:
            for q in layers[b]:
                body.append(f'<line x1="{p[0]}" y1="{p[1]}" x2="{q[0]}" y2="{q[1]}" stroke="#fff" stroke-opacity=".45" stroke-width="1.6" stroke-dasharray="4 4" class="dash"/>')
    for li, layer in enumerate(layers):
        for ni, (x, y) in enumerate(layer):
            body.append(f'<circle class="tw" style="animation-duration:1.6s;animation-delay:{li * .35 + ni * .12:.2f}s" cx="{x}" cy="{y}" r="6.5" fill="#fff" stroke="{INK}" stroke-width="2"/>')
    body.append('<ellipse cx="-44" cy="-222" rx="12" ry="24" transform="rotate(-25 -44 -222)" fill="#fff" opacity=".3"/>')
    eyes = ''.join(f'<ellipse cx="{ex}" cy="-148" rx="11" ry="13" fill="#fff" stroke="{INK}" stroke-width="2.5"/>'
                   f'<circle cx="{ex + 2}" cy="-146" r="6" fill="{INK}"/><circle cx="{ex + 4}" cy="-149" r="2.2" fill="#fff"/>' for ex in (-26, 26))
    body.append(f'<g class="blink">{eyes}</g>')
    body.append(f'<path d="M-11,-130 Q0,-120 11,-130" fill="none" stroke="{INK}" stroke-width="3.5" stroke-linecap="round"/>')
    body.append('<circle cx="-44" cy="-134" r="6" fill="#ff7ab6" opacity=".7"/><circle cx="44" cy="-134" r="6" fill="#ff7ab6" opacity=".7"/>')
    s.append(g(''.join(body), cls='bob'))
    return ''.join(s)


def form_stack():
    s = []
    for x0 in (-46, 14):
        s.append(f'<rect x="{x0}" y="-56" width="32" height="50" rx="6" fill="#1e3a8a" stroke="{INK}" stroke-width="4"/>'
                 f'<rect x="{x0 - 6}" y="-14" width="44" height="14" rx="6" fill="#0f172a" stroke="{INK}" stroke-width="3.5"/>')
    s.append(f'<rect x="-62" y="-112" width="124" height="58" fill="#2563eb" stroke="{INK}" stroke-width="5"/>'
             f'<ellipse cx="0" cy="-54" rx="62" ry="14" fill="#1d4ed8" stroke="{INK}" stroke-width="5"/>'
             f'<rect x="-59.5" y="-112" width="119" height="56" fill="#2563eb"/>'
             f'<path d="M-62,-84 Q0,-66 62,-84" fill="none" stroke="{INK}" stroke-width="3" opacity=".6"/>'
             f'<ellipse cx="0" cy="-112" rx="62" ry="14" fill="#60a5fa" stroke="{INK}" stroke-width="5"/>'
             + T(0, -70, 'DB', 'fb', 26, WHITE, 'middle', 2))
    s.append(limb([(-66, -170), (-104, -134), (-108, -96)], 18, ORANGE))
    s.append(f'<rect x="-124" y="-104" width="32" height="32" rx="8" fill="#fde68a" stroke="{INK}" stroke-width="4"/>' + T(-108, -80, '{', 'fcb', 22, INK, 'middle'))
    s.append(g(limb([(66, -170), (104, -196), (110, -236)], 18, ORANGE)
               + f'<rect x="94" y="-268" width="32" height="32" rx="8" fill="#fde68a" stroke="{INK}" stroke-width="4"/>' + T(110, -244, '}', 'fcb', 22, INK, 'middle'),
               cls='bob-s'))
    s.append(f'<rect x="-72" y="-196" width="144" height="80" rx="12" fill="{ORANGE}" stroke="{INK}" stroke-width="5"/>')
    teeth = ''.join(f'<rect x="-4" y="-21" width="8" height="10" rx="2" fill="#fde68a" stroke="{INK}" stroke-width="2" transform="rotate({a})"/>' for a in range(0, 360, 45))
    s.append(g(g(teeth + f'<circle r="14" fill="#fde68a" stroke="{INK}" stroke-width="3"/><circle r="5" fill="{INK}"/>', cls='spin-f'), 'translate(-40,-156)'))
    s.append(T(16, -142, 'API', 'fb', 32, WHITE, 'middle', 2, f'stroke="{INK}" stroke-width="4" paint-order="stroke"'))
    s.append(f'<path d="M-72,-118 L72,-118" stroke="{GREEN}" stroke-width="3" class="glow"/><path d="M-62,-198 L62,-198" stroke="{GREEN}" stroke-width="3" class="glow"/>')
    head = (f'<rect x="-66" y="-298" width="132" height="96" rx="12" fill="{WHITE}" stroke="{INK}" stroke-width="5"/>'
            f'<path d="M-61,-276 L61,-276" stroke="{INK}" stroke-width="3"/>'
            f'<circle cx="-50" cy="-287" r="4.5" fill="{RED}"/><circle cx="-36" cy="-287" r="4.5" fill="{GOLD}"/><circle cx="-22" cy="-287" r="4.5" fill="{GREEN}"/>'
            f'<g class="blink"><circle cx="-24" cy="-246" r="10" fill="{INK}"/><circle cx="24" cy="-246" r="10" fill="{INK}"/></g>'
            f'<circle cx="-20" cy="-250" r="3.5" fill="#fff"/><circle cx="28" cy="-250" r="3.5" fill="#fff"/>'
            f'<path d="M-22,-224 Q0,-208 22,-224 Q0,-216 -22,-224 Z" fill="{RED}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
            f'<rect class="blinkfast" x="40" y="-236" width="4" height="16" fill="{BLUE}"/>')
    s.append(g(head, cls='bob-s'))
    return ''.join(s)


def form_mole(props=True):
    s = [f'<path d="M-118,0 Q-60,-48 0,-40 Q60,-48 118,0 Z" fill="#5b3a1e" stroke="{INK}" stroke-width="4"/>']
    if props:
        s.append('<path d="M30,-262 L190,-330 L190,-200 Z" fill="url(#gLamp)" class="glow"/>')
    for i, (x, y, c) in enumerate(((-84, -26, CYAN), (88, -22, MAGENTA), (64, -48, GREEN), (-60, -44, GOLD))):
        s.append(g(f'<polygon points="{x},{y - 11} {x + 9},{y} {x},{y + 11} {x - 9},{y}" fill="{c}" stroke="{INK}" stroke-width="2.5"/>',
                   cls='rise', style=f'animation-delay:-{i * .9:.1f}s;animation-duration:3.6s'))
    body = [f'<ellipse cx="-36" cy="-14" rx="22" ry="11" fill="#ff9eb5" stroke="{INK}" stroke-width="3.5"/>'
            f'<ellipse cx="36" cy="-14" rx="22" ry="11" fill="#ff9eb5" stroke="{INK}" stroke-width="3.5"/>',
            f'<ellipse cx="0" cy="-112" rx="72" ry="84" fill="#8d6e63" stroke="{INK}" stroke-width="5"/>',
            '<ellipse cx="0" cy="-88" rx="46" ry="52" fill="#bcaaa4"/>',
            f'<ellipse cx="-66" cy="-96" rx="15" ry="11" fill="#ff9eb5" stroke="{INK}" stroke-width="3.5"/>',
            f'<ellipse cx="0" cy="-146" rx="32" ry="21" fill="#d7ccc8" stroke="{INK}" stroke-width="3"/>',
            f'<ellipse cx="0" cy="-158" rx="13" ry="10" fill="#ff6b9a" stroke="{INK}" stroke-width="3"/><circle cx="-4" cy="-162" r="3" fill="#fff" opacity=".7"/>',
            f'<rect x="-7" y="-134" width="14" height="12" rx="2" fill="#fff" stroke="{INK}" stroke-width="2.5"/><path d="M0,-134 L0,-122" stroke="{INK}" stroke-width="2"/>',
            f'<path d="M-16,-146 L-46,-152 M-16,-140 L-46,-136 M16,-146 L46,-152 M16,-140 L46,-136" stroke="{INK}" stroke-width="2" stroke-linecap="round"/>',
            f'<g class="blink"><ellipse cx="-24" cy="-180" rx="8" ry="9" fill="{INK}"/><ellipse cx="24" cy="-180" rx="8" ry="9" fill="{INK}"/></g>'
            '<circle cx="-21" cy="-183" r="3" fill="#fff"/><circle cx="27" cy="-183" r="3" fill="#fff"/>',
            f'<path d="M-60,-196 Q0,-268 60,-196 Z" fill="{GOLD}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
            f'<rect x="-70" y="-200" width="140" height="12" rx="6" fill="#f59e0b" stroke="{INK}" stroke-width="4"/>'
            f'<circle cx="26" cy="-238" r="12" fill="#fffbe0" stroke="{INK}" stroke-width="4"/><circle cx="26" cy="-238" r="5" fill="{GOLD}" class="blinkfast"/>']
    pick = (f'<path d="M60,-108 L104,-226" stroke="{INK}" stroke-width="13" stroke-linecap="round"/><path d="M60,-108 L104,-226" stroke="#a16207" stroke-width="7" stroke-linecap="round"/>'
            f'<path d="M62,-232 Q104,-252 148,-214 Q108,-232 70,-218 Z" fill="#cbd5e1" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
            f'<ellipse cx="66" cy="-112" rx="15" ry="11" fill="#ff9eb5" stroke="{INK}" stroke-width="3.5"/>')
    body.append(f'<g>{pick}<animateTransform attributeName="transform" type="rotate" values="0 62 -110;-28 62 -110;6 62 -110;0 62 -110" keyTimes="0;.45;.6;1" dur="1.1s" repeatCount="indefinite"/></g>')
    s.append(g(''.join(body), cls='bob-s'))
    return ''.join(s)


FORM_DEFS = f'''
<radialGradient id="gJelly" cx=".45" cy=".35" r=".75"><stop offset="0" stop-color="#fbcfe8"/><stop offset=".45" stop-color="#e879f9"/><stop offset="1" stop-color="#a21caf"/></radialGradient>
<linearGradient id="gLamp" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff3c4" stop-opacity=".6"/><stop offset="1" stop-color="#fff3c4" stop-opacity="0"/></linearGradient>
'''

FORMS = [
    ('VISION-X', 'COMPUTER VISION FORM', form_vision, GREEN,
     ['Sees everything. Detects, classifies', 'and segments whatever it looks at —', 'MRI scans included.'],
     ['DETECTION', 'SEGMENTATION', 'CLASSIFY']),
    ('NEURONIX', 'DEEP LEARNING FORM', form_neuro, MAGENTA,
     ['A brain made of neurons that trains', 'deep nets until they actually learn.', 'Speaks fluent LLM.'],
     ['PYTORCH', 'TENSORFLOW', 'NLP + LLMS']),
    ('STACKFORGE', 'FULL-STACK WEB FORM', form_stack, ORANGE,
     ['Forges fast, responsive web apps', 'from the database to the last pixel.', 'Never drops a request.'],
     ['LARAVEL', 'VUE', 'REACT']),
    ('DATAMOLE', 'DATA MINING FORM', form_mole, GOLD,
     ['Tunnels through messy datasets', 'and surfaces the gems hidden inside.', 'Pipelines are its burrows.'],
     ['PYTHON', 'SQL', 'PIPELINES']),
]


# ── Panels ─────────────────────────────────────────────────────────────────
def typer(x, y, phrases, size, color, period=4.6, clip_h=40):
    """Types each phrase out, holds it, backspaces it, then moves on (SMIL, discrete steps)."""
    n = len(phrases)
    total = period * n
    caret_t, caret_x, out, defs = [], [], [], []
    for i, ph in enumerate(phrases):
        start = i * period
        steps = []
        type_end, hold_end, erase_end = start + period * .45, start + period * .8, start + period * .93
        for k in range(len(ph) + 1):
            steps.append((start + (type_end - start) * k / len(ph), tw(ph[:k], 'fc', size)))
        steps.append((hold_end, tw(ph, 'fc', size)))
        for k in range(len(ph), -1, -3):
            steps.append((hold_end + (erase_end - hold_end) * (len(ph) - k) / len(ph), tw(ph[:k], 'fc', size)))
        steps.append((erase_end, 0))
        times = [0.0] + [t / total for t, _ in steps] + [min(1.0, (start + period) / total)]
        widths = [0.0] + [wd for _, wd in steps] + [0.0]
        if i == 0:
            times, widths = times[1:], widths[1:]
        times = [round(min(max(t, 0), 1), 4) for t in times]
        for j in range(1, len(times)):
            times[j] = max(times[j], times[j - 1])
        kt = ';'.join(str(t) for t in times)
        vals = ';'.join(f'{w + (3 if w else 0):.1f}' for w in widths)
        defs.append(f'<clipPath id="ty{i}"><rect x="{x}" y="{y - clip_h * .75:.1f}" width="0" height="{clip_h}">'
                    f'<animate attributeName="width" values="{vals}" keyTimes="{kt}" dur="{total}s" calcMode="discrete" repeatCount="indefinite"/></rect></clipPath>')
        out.append(f'<g clip-path="url(#ty{i})">{T(x, y, ph, "fc", size, color)}</g>')
        caret_t += times
        caret_x += widths
    pairs = sorted(zip(caret_t, caret_x), key=lambda p: p[0])
    kt = ';'.join(str(t) for t, _ in pairs)
    vals = ';'.join(f'{x + w + 3:.1f}' for _, w in pairs)
    out.append(f'<rect class="blinkfast" x="{x}" y="{y - size * .82:.1f}" width="{size * .5:.1f}" height="{size:.1f}" fill="{color}">'
               f'<animate attributeName="x" values="{vals}" keyTimes="{kt}" dur="{total}s" calcMode="discrete" repeatCount="indefinite"/></rect>')
    return ''.join(out), ''.join(defs)


def panel_hero():
    W, H = 1200, 690
    rng = random.Random(3)
    b, defs = [], [SHOOT_DEF]
    defs.append('<linearGradient id="heroSky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#050a22"/><stop offset=".36" stop-color="#140c3e"/>'
                '<stop offset=".58" stop-color="#3a1366"/><stop offset=".76" stop-color="#8c2378"/><stop offset=".88" stop-color="#ff6a4d"/><stop offset="1" stop-color="#ffb347"/></linearGradient>'
                '<radialGradient id="gMoon" cx=".38" cy=".32" r=".75"><stop offset="0" stop-color="#fffbe8"/><stop offset=".7" stop-color="#ffe2a8"/><stop offset="1" stop-color="#ffbf7a"/></radialGradient>'
                '<radialGradient id="gMoonGlow"><stop offset=".45" stop-color="#ffd9a0" stop-opacity=".5"/><stop offset=".7" stop-color="#ff8fb1" stop-opacity=".16"/><stop offset="1" stop-color="#ff8fb1" stop-opacity="0"/></radialGradient>')
    b.append(f'<rect width="{W}" height="{H}" fill="url(#heroSky)"/>')
    b.append(halftone('h1', 140, 120, 260, opacity=.07))
    b.append(stars(rng, 170, 0, 0, W, 440, avoid=[(930, 232, 172)], rects=((60, 92, 420, 134), (60, 400, 760, 434))))
    b.append('<circle cx="930" cy="232" r="300" fill="url(#gMoonGlow)"/><circle cx="930" cy="232" r="150" fill="url(#gMoon)"/>')
    for cx, cy, r in ((-52, -40, 22), (40, 30, 30), (-30, 66, 14), (70, -54, 12), (-86, 30, 10)):
        b.append(f'<circle cx="{930 + cx}" cy="{232 + cy}" r="{r}" fill="#f2c98a" opacity=".45"/>')
    b.append(shooting_stars([(640, 40, 1, 7), (1150, 120, 3.6, 8), (420, 20, 5.8, 9)]))
    # sweeping searchlights
    for bx, by, dl in ((190, 650, 0), (560, 660, -3.5)):
        b.append(f'<polygon class="search" style="transform-origin:{bx}px {by}px;animation-delay:{dl}s" '
                 f'points="{bx - 7},{by} {bx + 7},{by} {bx + 80},{by - 560} {bx - 80},{by - 560}" fill="url(#gBeamUp)"/>')
    # koi blimp drifting across the sky
    koi = (f'<g><path d="M128,0 L172,-24 Q162,0 172,24 Z" fill="{ORANGE}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
           f'<animateTransform attributeName="transform" type="rotate" values="-9 128 0;9 128 0;-9 128 0" dur="1.6s" repeatCount="indefinite"/></g>'
           f'<path d="M0,0 C18,-30 92,-32 132,-6 L132,6 C92,32 18,30 0,0 Z" fill="#fff4ea" stroke="{INK}" stroke-width="3.5"/>'
           f'<path d="M40,-21 Q60,-8 80,-24 Q66,-28 40,-21 Z M86,18 Q100,4 118,10 Q104,22 86,18 Z M30,14 Q44,6 56,20 Z" fill="{ORANGE}"/>'
           f'<path d="M58,22 L64,40 L84,40 L90,20" fill="#2b3044" stroke="{INK}" stroke-width="3"/>'
           f'<circle cx="74" cy="34" r="3" fill="{GOLD}" class="blinkfast"/>'
           f'<circle cx="22" cy="-5" r="5" fill="#fff" stroke="{INK}" stroke-width="2.5"/><circle cx="21" cy="-5" r="2.5" fill="{INK}"/>'
           f'<path d="M60,-27 Q72,-46 92,-30" fill="{ORANGE}" stroke="{INK}" stroke-width="3"/>')
    b.append(f'<g transform="translate(0,62)"><g class="koi">{koi}</g></g>')
    # hover cars
    for i, (y, dur, delay, c) in enumerate(((168, 13, -2, CYAN), (300, 17, -9, PINK), (236, 21, -14, GOLD))):
        car = (f'<path d="M-46,0 L-6,0" stroke="{c}" stroke-opacity=".5" stroke-width="3" stroke-linecap="round"/>'
               f'<rect x="0" y="-8" width="36" height="14" rx="7" fill="#1b1f36" stroke="{INK}" stroke-width="2"/>'
               f'<rect x="8" y="-12" width="16" height="7" rx="3" fill="{c}" opacity=".8"/>'
               f'<circle cx="34" cy="-1" r="2.5" fill="#fff"/><circle cx="2" cy="-1" r="2" fill="{RED}"/>')
        b.append(f'<g transform="translate(0,{y})"><g class="car" style="animation-duration:{dur}s;animation-delay:{delay}s">{car}</g></g>')
    # hills, landmarks, skyline
    b.append(hills(rng, W, 560, 90, '#2b1257', 0.3, .95))
    b.append(hills(rng, W, 600, 70, '#1e0d43', 2.1))
    b.append(faisal_mosque(736, 602, 0.95))
    b.append(pk_monument(1128, 612, 0.9))
    b.append(pagoda(328, 690, 58, 172))
    b.append(city(rng, -10, 790, 690, 70, 150, low=((300, 400, 60), (560, 800, 54))))
    b.append(city(rng, 1040, 1210, 690, 50, 110))
    # rooftop the hero stands on
    b.append(f'<rect x="782" y="622" width="268" height="80" fill="#0e0922"/><rect x="776" y="614" width="280" height="12" fill="#1d1440" stroke="{INK}" stroke-width="3"/>'
             f'<rect x="776" y="612" width="280" height="3" fill="{GREEN}" class="glow"/>'
             f'<rect x="806" y="560" width="3" height="54" fill="#1d1440"/><circle cx="807.5" cy="557" r="4" fill="{RED}" class="blinkfast"/>'
             f'<rect x="1002" y="590" width="34" height="24" fill="#1d1440" stroke="{INK}" stroke-width="2"/>')
    b.append(g(hero('power'), 'translate(922,614) scale(1.22)'))
    b.append(g(g(byte_bot(), cls='bob'), 'translate(1110,330) scale(.85)'))
    # name block
    b.append(g(''.join(f'<polygon points="0,0 {math.cos(math.radians(a - 2)) * 700:.0f},{math.sin(math.radians(a - 2)) * 700:.0f} '
                       f'{math.cos(math.radians(a + 2)) * 700:.0f},{math.sin(math.radians(a + 2)) * 700:.0f}" fill="#fff"/>' for a in range(0, 360, 15)),
               'translate(320,270)', None, 'opacity:.05'))
    b.append(T(68, 126, "HI THERE, I'M", 'fcb', 30, CYAN, ls=5))
    b.append(comic(64, 244, 'MUHAMMAD', 120, 'url(#gTitleA)', ls=3))
    b.append(comic(64, 386, 'SAAD', 156, 'url(#gTitleB)', ls=4))
    saad_w = tw('SAAD', 'fb', 156, 4)
    burst = ' '.join(f'{math.cos(math.radians(a)) * (54 if i % 2 == 0 else 34):.1f},{math.sin(math.radians(a)) * (54 if i % 2 == 0 else 34):.1f}'
                     for i, a in enumerate(range(0, 360, 20)))
    b.append(g(g(f'<polygon points="{burst}" fill="{PINK}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
                 + T(0, -3, 'AI', 'fb', 30, WHITE, 'middle', 1, f'stroke="{INK}" stroke-width="4" paint-order="stroke"')
                 + T(0, 22, 'HERO', 'fb', 20, GOLD, 'middle', 1, f'stroke="{INK}" stroke-width="3" paint-order="stroke"'), cls='pulse'),
               f'translate({64 + saad_w + 70:.0f},318) rotate(-12)'))
    x = 68
    for i, word in enumerate(('AI ENGINEER', 'COMPUTER VISION', 'FULL-STACK WEB')):
        if i:
            b.append(f'<polygon points="{hexpts(x + 10, 418, 6)}" fill="{PINK}"/>')
            x += 26
        b.append(T(x, 426, word, 'fcb', 22, WHITE, ls=2))
        x += tw(word, 'fcb', 22, 2) + 6
    pill_w = 560
    b.append(f'<rect x="64" y="446" width="{pill_w}" height="50" rx="25" fill="#060818" fill-opacity=".8" stroke="{GREEN}" stroke-opacity=".6" stroke-width="2"/>')
    b.append(T(88, 478, 'saad@hq:~$', 'fcb', 20, PINK))
    tx = 88 + tw('saad@hq:~$', 'fcb', 20) + 12
    phrases = ['training models that see the world', 'building web apps that feel alive', 'turning messy data into answers']
    assert max(tw(p, 'fc', 20) for p in phrases) + tx < 64 + pill_w - 20, 'typing line overflows its pill'
    typed, tdefs = typer(tx, 478, phrases, 20, GREEN)
    b.append(typed)
    defs.append(tdefs)
    x = 64
    for label, fill, color in (('ISLAMABAD, PK', PINK, WHITE), ('MS ARTIFICIAL INTELLIGENCE', PURPLE, WHITE), ('OPEN TO FREELANCE', GREEN, INK)):
        c, w = chip(x, 518, label, fill, color, 18)
        b.append(c)
        x += w + 14
    assert x < 650, f'chips run into the mosque ({x})'
    b.append(edges(W, H, 20, 60, top_to=BG0))
    css = SHOOT_CSS + '''
.search{animation:search 8s ease-in-out infinite alternate}
@keyframes search{from{transform:rotate(-26deg)}to{transform:rotate(26deg)}}
.koi{animation:koi 46s linear infinite}
@keyframes koi{from{transform:translateX(1260px)}to{transform:translateX(-260px)}}
.car{animation:car 15s linear infinite}
@keyframes car{from{transform:translateX(-80px)}to{transform:translateX(1280px)}}
'''
    write_svg('hero.svg', W, H, 'Muhammad Saad — AI Engineer, Computer Vision and Full-Stack Web Developer from Islamabad, Pakistan', ''.join(b), css, ''.join(defs))


def button(name, label, sub, grad, icon, text_color=WHITE):
    W, H = 300, 130
    rng = random.Random(len(name))
    b = [f'<rect width="{W}" height="{H}" fill="#0b0f2a"/>', stars(rng, 16, 0, 0, W, H, rects=())]
    defs = f'<linearGradient id="bg{name}" x1="0" y1="0" x2="1" y2="1">{grad}</linearGradient>'
    poly = lambda dx, dy: f'{30 + dx},{24 + dy} {286 + dx},{24 + dy} {270 + dx},{104 + dy} {14 + dx},{104 + dy}'
    defs += f'<clipPath id="cl{name}"><polygon points="{poly(0, 0)}"/></clipPath>'
    b.append(f'<polygon points="{poly(6, 6)}" fill="{INK}"/>')
    b.append(f'<polygon points="{poly(0, 0)}" fill="url(#bg{name})" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>')
    b.append(f'<g clip-path="url(#cl{name})"><rect x="0" y="0" width="60" height="140" fill="#fff" opacity=".35" class="shine"/>'
             f'<rect x="0" y="24" width="300" height="24" fill="#fff" opacity=".12"/></g>')
    b.append(f'<circle cx="66" cy="64" r="27" fill="{INK}"/><circle cx="64" cy="62" r="27" fill="#fff" stroke="{INK}" stroke-width="3.5"/>')
    b.append(g(icon, 'translate(64,62)'))
    b.append(T(104, 66, label, 'fb', 34, text_color, ls=2, extra=f'stroke="{INK}" stroke-width="5" stroke-linejoin="round" paint-order="stroke"'))
    sub_size = 13 if len(sub) < 18 else 11.5
    b.append(T(105, 88, sub, 'fcb', sub_size, text_color, ls=1, extra=f'stroke="{INK}" stroke-width="3" stroke-linejoin="round" paint-order="stroke"'))
    assert 105 + tw(sub, 'fcb', sub_size, 1) < 268, sub
    b.append(edges(W, H, 14, 18))
    css = '.shine{animation:shine 3.4s ease-in-out infinite}@keyframes shine{0%,55%{transform:translateX(-80px) skewX(-20deg)}100%{transform:translateX(360px) skewX(-20deg)}}'
    write_svg(f'btn-{name}.svg', W, H, f'{label} — {sub}', ''.join(b), css, defs)


def panel_about():
    W, H = 1200, 690
    rng = random.Random(21)
    b = [f'<rect width="{W}" height="{H}" fill="url(#aboutBg)"/>', '<rect width="1200" height="690" fill="url(#grid)" opacity=".05"/>',
         stars(rng, 60, 0, 0, W, H), halftone('a1', 1100, 600, 240, opacity=.06)]
    defs = ['<linearGradient id="aboutBg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0b1030"/><stop offset=".5" stop-color="#101442"/><stop offset="1" stop-color="#0a0f26"/></linearGradient>'
            '<linearGradient id="scanG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#39ff88" stop-opacity="0"/><stop offset="1" stop-color="#39ff88" stop-opacity=".5"/></linearGradient>'
            '<clipPath id="frameClip"><rect x="72" y="176" width="376" height="440" rx="18"/></clipPath>']
    # circuit traces with travelling pulses
    for i in range(7):
        y = rng.randint(180, 650)
        x0 = rng.choice([0, 1200])
        d = f'M{x0},{y} L{x0 + (180 if x0 == 0 else -180)},{y} l{(30 if x0 == 0 else -30)},{-30 if i % 2 else 30} L{x0 + (360 if x0 == 0 else -360)},{y + (-30 if i % 2 else 30)}'
        b.append(f'<path d="{d}" fill="none" stroke="#2a3a7a" stroke-width="2"/>'
                 f'<path d="{d}" fill="none" stroke="{CYAN}" stroke-width="2.5" stroke-dasharray="10 400" class="trace" style="animation-delay:-{i * .8:.1f}s"/>')
    b.append(section_title(600, 128, 'EPISODE 01', 'HERO PROFILE', '// SUBJECT SCAN COMPLETE — ACCESS GRANTED', 'url(#gTitleB)'))
    # scanner frame with hero bust
    b.append('<rect x="72" y="176" width="376" height="440" rx="18" fill="#0d1a3a" stroke="#2a3a7a" stroke-width="3"/>')
    b.append('<g clip-path="url(#frameClip)">'
             '<rect x="72" y="176" width="376" height="440" fill="url(#grid)" opacity=".12"/>'
             '<circle cx="260" cy="330" r="190" fill="url(#gGreen)" opacity=".35"/>'
             + g(hero('hips'), 'translate(260,800) scale(1.45)')
             + '<g class="scan"><rect x="72" y="140" width="376" height="36" fill="url(#scanG)"/><rect x="72" y="174" width="376" height="3" fill="#39ff88"/></g></g>')
    b.append(corner_brackets(64, 168, 392, 456, GREEN, 30, 5))
    b.append(f'<g class="pulse">{corner_brackets(178, 176, 164, 250, GOLD, 18, 3.5)}</g>')
    b.append(f'<rect x="178" y="434" width="164" height="22" fill="{GOLD}"/>' + T(260, 450, 'HUMAN · 99.7% · FRIENDLY', 'fcb', 12, INK, 'middle'))
    bub, bw = speech(250, 560, "THAT'S MY HUMAN!", 18)
    b.append(g(g(byte_bot(), cls='bob'), 'translate(120,566) scale(.5)'))
    b.append(bub)
    # dossier
    rows = [('NAME', 'MUHAMMAD SAAD'), ('ORIGIN', 'ISLAMABAD, PAKISTAN'), ('CLASS', 'AI ENGINEER · FULL-STACK WEB DEV'),
            ('RANK', 'MS ARTIFICIAL INTELLIGENCE'), ('BASE', 'AIR UNIVERSITY, ISLAMABAD'),
            ('THESIS', 'BREAST-CANCER MRI · CLASSIFY + SEGMENT'), ('ACTIVE', 'WEB SINCE 2019 · AI SINCE 2021')]
    b.append(f'<rect x="496" y="176" width="636" height="440" rx="18" fill="#0a1230" fill-opacity=".85" stroke="#2a3a7a" stroke-width="3"/>')
    b.append(f'<rect x="496" y="176" width="636" height="40" rx="18" fill="{GREEN}"/><rect x="496" y="198" width="636" height="18" fill="{GREEN}"/>')
    b.append(T(520, 203, 'CLASSIFIED HERO FILE  #MS-001', 'fcb', 17, INK, ls=3))
    b.append(f'<circle cx="1104" cy="196" r="7" fill="{RED}" class="blinkfast"/>')
    for i, (k, v) in enumerate(rows):
        y = 250 + i * 32
        b.append(T(520, y, k, 'fcb', 14, GREEN, ls=3) + T(626, y, v, 'fcb', 18, WHITE, ls=1))
        assert 626 + tw(v, 'fcb', 18, 1) < 1120, v
        b.append(f'<line x1="520" y1="{y + 10}" x2="1108" y2="{y + 10}" stroke="#2a3a7a" stroke-dasharray="3 5"/>')
    b.append(T(520, 497, 'POWER LEVELS', 'fb', 24, GOLD, ls=3))
    bars = [('COMPUTER VISION', 12, GREEN), ('DEEP LEARNING', 11, CYAN), ('NLP + LLMS', 10, MAGENTA), ('WEB DEVELOPMENT', 11, ORANGE), ('DATA ENGINEERING', 10, GOLD)]
    for r, (k, lit, c) in enumerate(bars):
        y = 512 + r * 20
        b.append(T(520, y + 13, k, 'fcb', 13, SOFT, ls=2))
        for i in range(14):
            x = 726 + i * 27
            if i < lit:
                b.append(f'<rect class="seg" style="animation-delay:{r * .18 + i * .06:.2f}s" x="{x}" y="{y}" width="23" height="14" rx="3" fill="{c}"/>')
            else:
                b.append(f'<rect x="{x}" y="{y}" width="23" height="14" rx="3" fill="#1b2550"/>')
    b.append(edges(W, H, 50, 60))
    css = '''
.scan{animation:scan 3.2s ease-in-out infinite alternate}
@keyframes scan{from{transform:translateY(0)}to{transform:translateY(440px)}}
.trace{animation:trace 4s linear infinite}
@keyframes trace{from{stroke-dashoffset:410}to{stroke-dashoffset:0}}
.seg{animation:seg 6s ease-out infinite both}
@keyframes seg{0%{opacity:.12}6%{opacity:1}88%{opacity:1}100%{opacity:.12}}
'''
    write_svg('about.svg', W, H, 'Hero profile: Muhammad Saad — AI engineer and full-stack web developer from Islamabad, MS in Artificial Intelligence (Air University), thesis on breast-cancer MRI classification and segmentation', ''.join(b), css, ''.join(defs))


def panel_forms():
    W, H = 1200, 720
    rng = random.Random(5)
    cyc = 14
    dcx, dcy = 235, 430
    b = [f'<rect width="{W}" height="{H}" fill="url(#formBg)"/>', stars(rng, 90, 0, 0, W, H), halftone('f1', 640, 420, 330, opacity=.05)]
    defs = [FORM_DEFS, '<linearGradient id="formBg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a0f26"/><stop offset=".5" stop-color="#0b2a2a"/><stop offset="1" stop-color="#0a0f26"/></linearGradient>']
    b.append(section_title(600, 128, 'EPISODE 02', 'HERO FORMS', '// MORPH-DIAL ONLINE — CYCLING 4 POWER MODES', 'url(#gTitleB)'))
    # watch strap + dial
    b.append(f'<rect x="{dcx - 72}" y="150" width="144" height="620" rx="34" fill="#1a2030" stroke="{INK}" stroke-width="5"/>'
             f'<rect x="{dcx - 58}" y="164" width="116" height="600" rx="26" fill="none" stroke="{GREEN}" stroke-opacity=".35" stroke-width="2" stroke-dasharray="8 7"/>')
    b.append(f'<circle cx="{dcx}" cy="{dcy}" r="230" fill="url(#gGreen)" opacity=".5" class="glow"/>')
    b.append(f'<circle cx="{dcx}" cy="{dcy}" r="158" fill="#2a3045" stroke="{INK}" stroke-width="6"/>')
    for a in range(0, 360, 45):
        bx, by = dcx + 146 * math.cos(math.radians(a + 22.5)), dcy + 146 * math.sin(math.radians(a + 22.5))
        b.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="4" fill="#8892b0" stroke="{INK}" stroke-width="1.5"/>')
    b.append(f'<circle cx="{dcx}" cy="{dcy}" r="134" fill="#111521" stroke="#3a4157" stroke-width="3"/>')
    ticks = ''.join(f'<rect x="{dcx - 2}" y="{dcy - 130}" width="4" height="{14 if a % 30 == 0 else 8}" fill="{GREEN}" transform="rotate({a} {dcx} {dcy})"/>' for a in range(0, 360, 10))
    b.append(f'<g class="spin">{ticks}<circle cx="{dcx}" cy="{dcy}" r="131" fill="none" stroke="none"/></g>')
    slots = [(0, -96), (96, 0), (0, 96), (-96, 0)]
    for i, ((sx, sy), (name, _, fn, color, _, _)) in enumerate(zip(slots, FORMS)):
        cx, cy = dcx + sx, dcy + sy
        defs.append(f'<clipPath id="slot{i}"><circle cx="{cx}" cy="{cy}" r="33"/></clipPath>')
        b.append(f'<circle cx="{cx}" cy="{cy}" r="36" fill="#0b0f1e" stroke="#3a4157" stroke-width="3"/>')
        b.append(f'<g clip-path="url(#slot{i})">{g(fn(), f"translate({cx},{cy + 30}) scale(.2)")}</g>')
        b.append(f'<circle class="slot" style="animation-delay:{i * cyc / 4 - cyc if i else 0}s" cx="{cx}" cy="{cy}" r="40" fill="none" stroke="{GREEN}" stroke-width="5"/>')
    b.append(f'<g class="ptr"><path d="M{dcx - 10},{dcy - 50} L{dcx},{dcy - 64} L{dcx + 10},{dcy - 50} Z" fill="{GREEN}" stroke="{INK}" stroke-width="2.5"/></g>')
    b.append(f'<circle cx="{dcx}" cy="{dcy}" r="50" fill="url(#gCore)" stroke="{INK}" stroke-width="5"/>')
    b.append(g(g(emblem(24), cls='pulse'), f'translate({dcx},{dcy})'))
    b.append(T(dcx, dcy + 196, 'MORPH-DIAL v2.0', 'fcb', 15, GREEN, 'middle', 3))
    # hologram stage
    sx, sy = 640, 612
    b.append(f'<polygon points="{sx - 150},{sy} {sx + 150},{sy} {sx + 210},{sy - 400} {sx - 210},{sy - 400}" fill="url(#gHolo)" class="glow"/>')
    b.append(f'<ellipse cx="{sx}" cy="{sy + 8}" rx="164" ry="30" fill="#0b1a1a" stroke="{GREEN}" stroke-width="4"/>'
             f'<ellipse cx="{sx}" cy="{sy + 8}" rx="140" ry="22" fill="none" stroke="{GREEN}" stroke-width="2" stroke-dasharray="14 10" class="dash"/>')
    b.append(f'<circle class="burst" cx="{sx}" cy="{sy - 150}" r="120" fill="url(#gWhite)"/>')
    for i, (name, sub, fn, color, lines, tags) in enumerate(FORMS):
        b.append(g(g(fn(), cls='form', style=f'animation-delay:{i * cyc / 4 - cyc if i else 0}s'), f'translate({sx},{sy})'))
        info = [comic(840, 352, name, 64, f'url(#gForm{i})', ls=2),
                T(842, 386, sub, 'fcb', 16, color, ls=3)]
        for j, ln in enumerate(lines):
            info.append(T(842, 426 + j * 27, ln, 'fc', 18, SOFT))
            assert 842 + tw(ln, 'fc', 18) < 1185, ln
        x = 842
        for t in tags:
            c, w = chip(x, 518, t, color, INK, 15, pad=11)
            info.append(c)
            x += w + 10
        assert x < 1190, tags
        b.append(g(''.join(info), cls='info', style=f'animation-delay:{i * cyc / 4 - cyc if i else 0}s'))
        defs.append(f'<linearGradient id="gForm{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="{color}"/></linearGradient>')
    b.append(f'<rect class="flash" width="{W}" height="{H}" fill="{GREEN}"/>')
    b.append(edges(W, H, 50, 70))
    q = cyc / 4
    css = f'''
.form{{animation:form {cyc}s infinite both;transform-box:fill-box;transform-origin:50% 100%}}
@keyframes form{{0%{{opacity:0;transform:scale(.15)}}3%{{opacity:1;transform:scale(1.14)}}5.5%{{transform:scale(1)}}22%{{opacity:1;transform:scale(1)}}24.5%{{opacity:0;transform:scale(.4)}}100%{{opacity:0;transform:scale(.4)}}}}
.info{{animation:info {cyc}s infinite both}}
@keyframes info{{0%{{opacity:0;transform:translateX(30px)}}4%{{opacity:1;transform:translateX(0)}}22%{{opacity:1;transform:translateX(0)}}24.5%{{opacity:0;transform:translateX(-20px)}}100%{{opacity:0}}}}
.slot{{animation:slot {cyc}s infinite both}}
@keyframes slot{{0%,23.5%{{opacity:1}}25%,100%{{opacity:0}}}}
.ptr{{animation:ptr {cyc}s infinite;transform-origin:{dcx}px {dcy}px}}
@keyframes ptr{{0%,22%{{transform:rotate(0deg)}}25%,47%{{transform:rotate(90deg)}}50%,72%{{transform:rotate(180deg)}}75%,97%{{transform:rotate(270deg)}}100%{{transform:rotate(360deg)}}}}
.flash{{opacity:0;animation:flash {q}s infinite}}
@keyframes flash{{0%{{opacity:.38}}9%{{opacity:0}}100%{{opacity:0}}}}
.burst{{animation:burst {q}s ease-out infinite;transform-box:fill-box;transform-origin:center}}
@keyframes burst{{0%{{transform:scale(.2);opacity:.9}}18%{{transform:scale(1.6);opacity:0}}100%{{opacity:0}}}}
'''
    write_svg('forms.svg', W, H, 'Hero forms: computer vision, deep learning, full-stack web development and data mining', ''.join(b), css, ''.join(defs))


TECH = {
    'AI CORE': [('Py', 'PYTHON', '#3776AB'), ('PT', 'PYTORCH', '#EE4C2C'), ('TF', 'TENSORFLOW', '#FF6F00'), ('JU', 'JUPYTER', '#F37626'),
                ('CV', 'COMPUTER|VISION', '#8b5cf6'), ('DL', 'DEEP|LEARNING', '#6d28d9'), ('LLM', 'NLP + LLMS', '#ff3d9a')],
    'WEB CORE': [('TS', 'TYPESCRIPT', '#3178C6'), ('JS', 'JAVASCRIPT', '#d4b40a'), ('RE', 'REACT', '#1f2a44'), ('VUE', 'VUE.JS', '#2f9e6e'),
                 ('LA', 'LARAVEL', '#FF2D20'), ('PHP', 'PHP', '#777BB4'), ('JQ', 'JQUERY', '#0769AD'), ('H5', 'HTML5', '#E34F26'),
                 ('CSS', 'CSS', '#1572B6'), ('VI', 'VITE', '#646CFF'), ('SQL', 'SQL', '#336791')],
    'TOOLKIT': [('GIT', 'GIT', '#F05032'), ('GH', 'GITHUB', '#24292f'), ('GP', 'GITHUB|PAGES', '#3d4451'), ('VS', 'VS CODE', '#007ACC')],
}


def hex_tile(cx, cy, r, mono, name, color, delay):
    lines = name.split('|')
    t = [f'<polygon points="{hexpts(cx + 5, cy + 6, r)}" fill="{INK}"/>',
         f'<polygon points="{hexpts(cx, cy, r)}" fill="{color}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>',
         f'<polygon points="{hexpts(cx, cy, r - 9)}" fill="#000" opacity=".18"/>',
         f'<path d="M{cx - r * .8:.1f},{cy - r * .38:.1f} L{cx:.1f},{cy - r * .86:.1f} L{cx + r * .8:.1f},{cy - r * .38:.1f}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="3" stroke-linecap="round"/>']
    if mono == 'RE':
        t.append(''.join(f'<ellipse cx="{cx}" cy="{cy - 8}" rx="17" ry="6.5" fill="none" stroke="#61DAFB" stroke-width="2.6" transform="rotate({a} {cx} {cy - 8})"/>' for a in (0, 60, 120))
                 + f'<circle cx="{cx}" cy="{cy - 8}" r="3.6" fill="#61DAFB"/>')
    else:
        t.append(T(cx, cy + 2, mono, 'fb', 30 if len(mono) < 3 else 25, WHITE, 'middle', 1, f'stroke="{INK}" stroke-width="4.5" paint-order="stroke"'))
    for j, ln in enumerate(lines):
        t.append(T(cx, cy + 20 + j * 11 - (6 if len(lines) > 1 else 0), ln, 'fcb', 9 if len(ln) > 8 else 10.5, WHITE, 'middle', 1 if len(ln) <= 8 else .5))
    return f'<g class="hexw" style="animation-delay:{delay:.2f}s">{"".join(t)}</g>'


def panel_arsenal():
    W, H = 1200, 640
    rng = random.Random(9)
    b = [f'<rect width="{W}" height="{H}" fill="url(#arsBg)"/>', '<rect width="1200" height="640" fill="url(#grid)" opacity=".05"/>', stars(rng, 70, 0, 0, W, H)]
    defs = ['<linearGradient id="arsBg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a0f26"/><stop offset=".55" stop-color="#1a0f3a"/><stop offset="1" stop-color="#0a0f26"/></linearGradient>']
    # perspective lab floor
    for i in range(-12, 13):
        b.append(f'<line x1="{600 + i * 34}" y1="470" x2="{600 + i * 140}" y2="660" stroke="{PURPLE}" stroke-opacity=".28" stroke-width="1.5"/>')
    for k, y in enumerate((478, 492, 512, 540, 578, 628)):
        b.append(f'<line x1="0" y1="{y}" x2="1200" y2="{y}" stroke="{PURPLE}" stroke-opacity="{.15 + k * .04:.2f}" stroke-width="1.5"/>')
    b.append(section_title(600, 128, 'EPISODE 03', 'GADGET LAB', '// TECH ARSENAL — ALL CORES FULLY CHARGED', 'url(#gTitleD)'))
    r = 44
    wv = r * math.sqrt(3) * 1.12
    clusters = {'AI CORE': (196, 352, GREEN), 'WEB CORE': (612, 352, CYAN), 'TOOLKIT': (1010, 352, ORANGE)}
    pos = {}
    ax, ay, _ = clusters['AI CORE']
    pos['AI CORE'] = [(ax, ay)] + [(ax + wv * math.cos(math.radians(a)), ay + wv * math.sin(math.radians(a))) for a in range(0, 360, 60)]
    wx, wy, _ = clusters['WEB CORE']
    dy = wv * math.sqrt(3) / 2
    pos['WEB CORE'] = ([(wx - 1.5 * wv + i * wv, wy - dy) for i in range(4)] + [(wx - wv + i * wv, wy) for i in range(3)]
                       + [(wx - 1.5 * wv + i * wv, wy + dy) for i in range(4)])
    tx, ty, _ = clusters['TOOLKIT']
    pos['TOOLKIT'] = [(tx - wv / 2, ty - dy / 2), (tx + wv / 2, ty - dy / 2), (tx, ty + dy / 2), (tx + wv, ty + dy / 2)]
    # energy conduits between cores
    for (x1, x2) in ((350, 430), (800, 900)):
        d = f'M{x1},352 C{x1 + 40},292 {x2 - 40},412 {x2},352'
        b.append(f'<path d="{d}" fill="none" stroke="#2a2f6a" stroke-width="10" stroke-linecap="round"/>'
                 f'<path d="{d}" fill="none" stroke="{GREEN}" stroke-width="4" stroke-dasharray="6 14" stroke-linecap="round" class="dash"/>')
    for name, (cx, cy, color) in clusters.items():
        b.append(f'<circle cx="{cx}" cy="{cy}" r="170" fill="url(#gCyan)" opacity=".18"/>')
        top = min(y for p in pos.values() for _, y in p) - r - 16
        b.append(T(cx + (wv / 2 if name == 'TOOLKIT' else 0), top, name, 'fb', 30, color, 'middle', 3, f'stroke="{INK}" stroke-width="5" paint-order="stroke"'))
        for (x, y), (mono, label, c) in zip(pos[name], TECH[name]):
            b.append(hex_tile(x, y, r, mono, label, c, x / 1200 * 1.6))
    # microbot swarm
    swarm = 'M150,560 C300,470 450,650 600,560 C750,470 900,650 1050,560 C900,470 750,650 600,560 C450,470 300,650 150,560 Z'
    for i in range(18):
        b.append(f'<rect x="-6" y="-2.5" width="12" height="5" rx="2.5" fill="#1b1f36" stroke="{CYAN}" stroke-width="1.2">'
                 f'<animateMotion dur="16s" begin="-{i * .32:.2f}s" repeatCount="indefinite" rotate="auto" path="{swarm}"/></rect>')
    bub, _ = speech(944, 518, 'ALL SYSTEMS CHARGED!', 17)
    b.append(g(g(byte_bot(), cls='bob'), 'translate(1124,560) scale(.52)'))
    b.append(bub)
    b.append(edges(W, H, 50, 60))
    css = '''
.hexw{animation:hexw 3.2s ease-in-out infinite}
@keyframes hexw{0%,60%,100%{transform:translateY(0)}20%{transform:translateY(-9px)}}
'''
    write_svg('arsenal.svg', W, H, 'Tech arsenal: Python, PyTorch, TensorFlow, Jupyter, computer vision, deep learning, NLP and LLMs, TypeScript, JavaScript, React, Vue.js, Laravel, PHP, jQuery, HTML5, CSS, Vite, SQL, Git, GitHub, GitHub Pages and VS Code', ''.join(b), css, ''.join(defs))


def panel_missions_title():
    W, H = 1200, 250
    rng = random.Random(13)
    b = [f'<rect width="{W}" height="{H}" fill="#0b0f2a"/>', stars(rng, 50, 0, 0, W, H)]
    defs = [f'<pattern id="hazard" width="34" height="34" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="34" height="34" fill="{GOLD}"/><rect width="17" height="34" fill="{INK}"/></pattern>']
    for ang, y in ((-4, 104), (3, 122)):
        tape = (f'<rect x="-60" y="-19" width="1320" height="38" fill="url(#hazard)" stroke="{INK}" stroke-width="3"/>'
                f'<rect x="-60" y="-11" width="1320" height="22" fill="{GOLD}"/>')
        words = ''.join(T(x, 6, 'TOP SECRET • MISSION LOG •', 'fb', 18, INK, ls=3) for x in range(-400, 1700, 300))
        tape += f'<g class="tape">{words}</g>'
        b.append(g(tape, f'translate(0,{y}) rotate({ang} 600 0)', None, 'opacity:.9'))
    b.append(section_title(600, 150, 'EPISODE 04', 'MISSION LOG', '// CLICK A FILE TO OPEN THE MISSION', 'url(#gTitleC)', 80))
    b.append(edges(W, H, 40, 40))
    css = '.tape{animation:tape 10s linear infinite}@keyframes tape{to{transform:translateX(300px)}}'
    write_svg('missions.svg', W, H, 'Mission log: featured projects', ''.join(b), css, ''.join(defs))


def heart_path(cx, cy, s):
    return (f'M{cx},{cy + 30 * s} C{cx - 50 * s},{cy - 4 * s} {cx - 34 * s},{cy - 46 * s} {cx},{cy - 22 * s} '
            f'C{cx + 34 * s},{cy - 46 * s} {cx + 50 * s},{cy - 4 * s} {cx},{cy + 30 * s} Z')


def art_valentine():
    s = ['<rect x="44" y="64" width="512" height="200" fill="url(#artV)"/>']
    for i, (x, sc) in enumerate(((90, .25), (180, .18), (260, .3), (380, .2), (470, .26), (520, .16))):
        s.append(g(f'<path d="{heart_path(x, 250, sc)}" fill="#ff8fc4" opacity=".7"/>', cls='rise', style=f'animation-delay:-{i * .6:.1f}s;animation-duration:4.2s'))
    s.append(g(f'<path d="{heart_path(150, 170, 1.65)}" fill="{INK}" transform="translate(5,6)"/>'
               f'<path d="{heart_path(150, 170, 1.65)}" fill="{PINK}" stroke="{INK}" stroke-width="4"/>'
               + T(150, 162, 'YES', 'fb', 40, WHITE, 'middle', 2, f'stroke="{INK}" stroke-width="5" paint-order="stroke"'), cls='pulse'))
    legs = (f'<g><path d="M-12,22 L-18,38" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
            f'<animateTransform attributeName="transform" type="rotate" values="-30 -12 22;30 -12 22;-30 -12 22" dur=".32s" repeatCount="indefinite"/></g>'
            f'<g><path d="M12,22 L18,38" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
            f'<animateTransform attributeName="transform" type="rotate" values="30 12 22;-30 12 22;30 12 22" dur=".32s" repeatCount="indefinite"/></g>')
    no = (legs + f'<rect x="-40" y="-20" width="80" height="42" rx="21" fill="#cbd5e1" stroke="{INK}" stroke-width="4"/>'
          + T(0, 10, 'NO', 'fb', 28, '#475569', 'middle', 2)
          + f'<path d="M30,-30 Q36,-20 30,-14 Q24,-20 30,-30 Z" fill="{CYAN}" stroke="{INK}" stroke-width="2" class="blinkfast"/>'
          + f'<path d="M-58,-6 L-76,-6 M-56,6 L-82,6 M-60,16 L-72,16" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".7"/>')
    cursor = f'<path d="M0,0 L0,30 L8,23 L14,36 L20,33 L14,21 L24,21 Z" fill="#fff" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>'
    s.append(f'<g transform="translate(400,196)"><g class="runner">{g(no, cls="bob-s")}</g></g>')
    s.append(f'<g transform="translate(300,200)"><g class="runner" style="animation-delay:.25s">{cursor}</g></g>')
    bub, _ = speech(330, 120, "CAN'T CATCH ME!", 16)
    s.append(g(bub, cls='bob-s'))
    return ''.join(s), '<linearGradient id="artV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3b0a45"/><stop offset="1" stop-color="#a3195b"/></linearGradient>'


def art_scholar():
    s = ['<rect x="44" y="64" width="512" height="200" fill="url(#artS)"/>', stars(random.Random(2), 22, 44, 64, 556, 260, rects=())]
    paper = (f'<rect x="300" y="92" width="190" height="150" rx="8" fill="#fff" stroke="{INK}" stroke-width="4" transform="rotate(4 395 167)"/>'
             + ''.join(f'<line x1="320" y1="{122 + i * 22}" x2="{470 - (i % 2) * 30}" y2="{122 + i * 22}" stroke="#94a3b8" stroke-width="5" stroke-linecap="round" '
                       f'stroke-dasharray="160" class="write" style="animation-delay:{i * .9:.1f}s" transform="rotate(4 395 167)"/>' for i in range(5)))
    s.append(paper)
    quill = (f'<path d="M0,0 Q30,-60 70,-84 Q50,-40 8,4 Z" fill="#fff" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
             f'<path d="M4,0 L42,-52" stroke="#94a3b8" stroke-width="2"/><path d="M0,0 L-6,10" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>')
    s.append(f'<g transform="translate(330,150)"><g class="quill">{quill}</g></g>')
    brain = (f'<path d="M-62,10 C-84,-6 -74,-48 -46,-52 C-40,-80 0,-82 6,-60 C26,-84 70,-70 62,-38 C88,-24 78,20 52,22 C40,44 -40,44 -62,10 Z" fill="#f9a8d4" stroke="{INK}" stroke-width="4.5"/>'
             f'<path d="M-40,-30 Q-20,-14 -36,6 M0,-58 Q-8,-30 10,-10 Q24,8 8,26 M36,-36 Q26,-16 44,0" fill="none" stroke="#db2777" stroke-width="3" stroke-linecap="round"/>'
             f'<g class="blink"><circle cx="-18" cy="-6" r="8" fill="#fff" stroke="{INK}" stroke-width="2.5"/><circle cx="20" cy="-6" r="8" fill="#fff" stroke="{INK}" stroke-width="2.5"/>'
             f'<circle cx="-16" cy="-5" r="4" fill="{INK}"/><circle cx="22" cy="-5" r="4" fill="{INK}"/></g>'
             f'<path d="M-8,14 Q2,22 12,14" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>'
             f'<path d="M-50,-70 L6,-92 L62,-70 L6,-50 Z" fill="#1e1b4b" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
             f'<path d="M-30,-64 L-30,-44 Q6,-30 42,-44 L42,-64" fill="#1e1b4b" stroke="{INK}" stroke-width="4"/>'
             f'<g><path d="M60,-70 L64,-38" stroke="{GOLD}" stroke-width="4" stroke-linecap="round"/><circle cx="64" cy="-36" r="5" fill="{GOLD}" stroke="{INK}" stroke-width="2"/>'
             f'<animateTransform attributeName="transform" type="rotate" values="-12 60 -70;12 60 -70;-12 60 -70" dur="1.4s" repeatCount="indefinite"/></g>')
    s.append(g(g(brain, cls='bob-s'), 'translate(170,186)'))
    for i, (x, t) in enumerate(((250, '[1]'), (520, '[2]'), (280, '[3]'))):
        s.append(g(T(x, 120, t, 'fcb', 20, GOLD, 'middle', 0, f'stroke="{INK}" stroke-width="4" paint-order="stroke"'), cls='rise', style=f'animation-delay:-{i * 1.2:.1f}s'))
    return ''.join(s), '<linearGradient id="artS" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1e1b4b"/><stop offset="1" stop-color="#5b21b6"/></linearGradient>'


def art_claims():
    s = ['<rect x="44" y="64" width="512" height="200" fill="url(#artC)"/>',
         f'<rect x="44" y="214" width="512" height="26" fill="#1f2937" stroke="{INK}" stroke-width="4"/>',
         f'<line x1="44" y1="227" x2="556" y2="227" stroke="#94a3b8" stroke-width="3" stroke-dasharray="14 12" class="belt"/>']
    for x in range(70, 560, 60):
        roller = f'<circle r="11" fill="#475569" stroke="{INK}" stroke-width="3"/><path d="M-8,0 L8,0 M0,-8 L0,8" stroke="{INK}" stroke-width="2.5"/>'
        s.append(g(g(roller, cls='spin-f'), f'translate({x},252)'))
    for i in range(4):
        ok = i % 3 != 1
        stamp = (f'<g class="stamp" style="animation-delay:-{i * 1.75:.2f}s"><circle cx="26" cy="-4" r="15" fill="{GREEN if ok else RED}" stroke="{INK}" stroke-width="3"/>'
                 + (f'<path d="M19,-4 L24,2 L34,-10" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>' if ok else
                    f'<path d="M20,-10 L32,2 M32,-10 L20,2" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>') + '</g>')
        doc = (f'<rect x="-22" y="-56" width="46" height="58" rx="5" fill="#fff" stroke="{INK}" stroke-width="3.5"/>'
               f'<path d="M-2,-44 L4,-44 L4,-38 L10,-38 L10,-32 L4,-32 L4,-26 L-2,-26 L-2,-32 L-8,-32 L-8,-38 L-2,-38 Z" fill="{RED}"/>'
               f'<path d="M-14,-16 L16,-16 M-14,-8 L10,-8" stroke="#94a3b8" stroke-width="3" stroke-linecap="round"/>' + stamp)
        s.append(f'<g transform="translate(40,212)"><g class="claim" style="animation-delay:-{i * 1.75:.2f}s">{doc}</g></g>')
    s.append(f'<rect x="268" y="96" width="16" height="120" fill="#334155" stroke="{INK}" stroke-width="3.5"/><rect x="356" y="96" width="16" height="120" fill="#334155" stroke="{INK}" stroke-width="3.5"/>'
             f'<rect x="258" y="80" width="124" height="30" rx="8" fill="#0f172a" stroke="{INK}" stroke-width="4"/>'
             + T(320, 101, 'AI CHECK', 'fcb', 15, CYAN, 'middle', 2)
             + f'<rect x="284" y="110" width="72" height="104" fill="{CYAN}" opacity=".18" class="glow"/>'
             f'<line x1="284" y1="140" x2="356" y2="140" stroke="{CYAN}" stroke-width="3" class="scanl"/>'
             f'<circle cx="268" cy="88" r="5" fill="{RED}" class="blinkfast"/><circle cx="372" cy="88" r="5" fill="{GREEN}" class="blinkfast" style="animation-delay:.5s"/>')
    shield = (f'<path d="M0,-34 L28,-24 Q28,14 0,30 Q-28,14 -28,-24 Z" fill="#e0f2fe" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
              f'<path d="M-4,-14 L4,-14 L4,-6 L12,-6 L12,2 L4,2 L4,10 L-4,10 L-4,2 L-12,2 L-12,-6 L-4,-6 Z" fill="{RED}"/>')
    s.append(g(g(shield, cls='bob-s'), 'translate(106,120)'))
    s.append(T(500, 104, 'VALID', 'fb', 20, GREEN, 'middle', 2, f'stroke="{INK}" stroke-width="4" paint-order="stroke"'))
    s.append(T(500, 130, 'RESUBMIT', 'fb', 20, GOLD, 'middle', 2, f'stroke="{INK}" stroke-width="4" paint-order="stroke"'))
    return ''.join(s), '<linearGradient id="artC" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#083344"/><stop offset="1" stop-color="#0e7490"/></linearGradient>'


def art_portfolio():
    s = ['<rect x="44" y="64" width="512" height="200" fill="url(#artP)"/>', stars(random.Random(4), 26, 44, 64, 556, 200, rects=())]
    s.append(f'<circle cx="486" cy="112" r="26" fill="#f472b6" stroke="{INK}" stroke-width="4"/><ellipse cx="486" cy="112" rx="46" ry="10" fill="none" stroke="{GOLD}" stroke-width="4" transform="rotate(-18 486 112)"/>')
    win = (f'<rect x="80" y="98" width="230" height="150" rx="12" fill="#f8fafc" stroke="{INK}" stroke-width="4.5"/>'
           f'<path d="M84,122 L306,122" stroke="{INK}" stroke-width="3"/><circle cx="98" cy="110" r="4.5" fill="{RED}"/><circle cx="112" cy="110" r="4.5" fill="{GOLD}"/><circle cx="126" cy="110" r="4.5" fill="{GREEN}"/>'
           f'<rect x="96" y="134" width="96" height="62" rx="6" fill="#bae6fd" stroke="{INK}" stroke-width="2.5"/>'
           f'<path d="M100,192 L130,160 L150,178 L166,164 L188,192 Z" fill="#22c55e"/><circle cx="174" cy="148" r="7" fill="{GOLD}"/>'
           f'<rect x="204" y="136" width="90" height="10" rx="5" fill="#94a3b8"/><rect x="204" y="154" width="70" height="8" rx="4" fill="#cbd5e1"/>'
           f'<rect x="204" y="168" width="80" height="8" rx="4" fill="#cbd5e1"/><rect x="204" y="186" width="54" height="16" rx="8" fill="{PINK}" stroke="{INK}" stroke-width="2"/>'
           f'<rect x="96" y="208" width="198" height="8" rx="4" fill="#e2e8f0"/><rect x="96" y="224" width="150" height="8" rx="4" fill="#e2e8f0"/>')
    s.append(g(win, cls='bob-s'))
    for i in range(4):
        s.append(f'<circle class="puff" style="animation-delay:-{i * .45:.2f}s" cx="376" cy="184" r="11" fill="#e2e8f0" stroke="{INK}" stroke-width="2"/>')
    rocket = (f'<path class="flame" d="M-10,34 Q0,74 10,34 Z" fill="url(#gFlame)"/>'
              f'<path d="M-22,10 L-34,34 L-12,28 Z M22,10 L34,34 L12,28 Z" fill="{RED}" stroke="{INK}" stroke-width="3.5" stroke-linejoin="round"/>'
              f'<path d="M0,-46 Q24,-20 18,32 L-18,32 Q-24,-20 0,-46 Z" fill="#f8fafc" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
              f'<circle cy="-6" r="9" fill="{CYAN}" stroke="{INK}" stroke-width="3.5"/><path d="M-10,-34 Q0,-44 10,-34" fill="none" stroke="{RED}" stroke-width="6"/>')
    s.append(f'<g transform="translate(400,150) rotate(38)"><g class="bob-s">{rocket}</g></g>')
    return ''.join(s), '<linearGradient id="artP" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0c1445"/><stop offset=".7" stop-color="#7c2d12"/><stop offset="1" stop-color="#f97316"/></linearGradient>'


CARD_CSS = '''
.runner{animation:runner 2.6s ease-in-out infinite alternate}
@keyframes runner{from{transform:translateX(-30px)}to{transform:translateX(90px)}}
.write{stroke-dashoffset:160;animation:write 4.5s linear infinite}
@keyframes write{0%{stroke-dashoffset:160}20%,100%{stroke-dashoffset:0}}
.quill{animation:quill 4.5s linear infinite}
@keyframes quill{0%{transform:translate(0,-36px)}20%{transform:translate(140px,-36px)}21%{transform:translate(0,-14px)}40%{transform:translate(110px,-14px)}41%{transform:translate(0,8px)}60%{transform:translate(140px,8px)}61%{transform:translate(0,30px)}80%{transform:translate(110px,30px)}81%,100%{transform:translate(0,52px)}}
.belt{animation:dash .8s linear infinite}
.claim{animation:claim 7s linear infinite}
@keyframes claim{from{transform:translateX(0)}to{transform:translateX(560px)}}
.stamp{animation:stamp 7s linear infinite;transform-box:fill-box;transform-origin:center}
@keyframes stamp{0%,48%{opacity:0;transform:scale(2.4)}52%{opacity:1;transform:scale(1)}100%{opacity:1;transform:scale(1)}}
.scanl{animation:scanl 1.2s ease-in-out infinite alternate}
@keyframes scanl{to{transform:translateY(70px)}}
.puff{animation:puff 1.8s ease-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes puff{0%{transform:translate(0,0) scale(.4);opacity:.9}100%{transform:translate(-46px,46px) scale(1.7);opacity:0}}
'''


def card(slug, num, title, lines, tags, accent, status, art):
    W, H = 600, 460
    art_svg, art_def = art()
    b = [f'<rect width="{W}" height="{H}" fill="#0b0f2a"/>', stars(random.Random(num * 7), 24, 0, 0, W, H, rects=())]
    defs = [art_def, f'<clipPath id="art{num}"><rect x="44" y="64" width="512" height="200" rx="14"/></clipPath>',
            f'<linearGradient id="cardBg{num}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#171d44"/><stop offset="1" stop-color="#0c1027"/></linearGradient>']
    b.append(f'<rect x="30" y="30" width="548" height="404" rx="22" fill="{accent}" stroke="{INK}" stroke-width="5"/>')
    b.append(f'<rect x="22" y="22" width="548" height="404" rx="22" fill="url(#cardBg{num})" stroke="{INK}" stroke-width="5"/>')
    b.append(f'<rect x="22" y="22" width="548" height="404" rx="22" fill="url(#dots)" opacity=".05"/>')
    b.append(f'<g clip-path="url(#art{num})">{art_svg}</g>')
    b.append(f'<rect x="44" y="64" width="512" height="200" rx="14" fill="none" stroke="{INK}" stroke-width="4"/>')
    c, _ = chip(36, 34, f'MISSION 0{num}', accent, INK, 17)
    b.append(c)
    sw = tw(status, 'fcb', 13, 2) + 34
    b.append(f'<rect x="{548 - sw:.1f}" y="38" width="{sw:.1f}" height="24" rx="12" fill="{INK}" stroke="{accent}" stroke-width="2"/>'
             f'<circle cx="{562 - sw:.1f}" cy="50" r="5" fill="{GREEN}" class="blinkfast"/>' + T(572 - sw, 55, status, 'fcb', 13, WHITE, ls=2))
    b.append(comic(48, 318, title, 42, f'url(#cardT{num})', ls=2))
    defs.append(f'<linearGradient id="cardT{num}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="{accent}"/></linearGradient>')
    assert 48 + tw(title, 'fb', 42, 2) < 560, title
    for i, ln in enumerate(lines):
        b.append(T(50, 348 + i * 24, ln, 'fc', 17, SOFT))
        assert 50 + tw(ln, 'fc', 17) < 556, ln
    x = 48
    for t in tags:
        tw_ = tw(t, 'fcb', 13, 1) + 22
        b.append(f'<rect x="{x}" y="390" width="{tw_:.1f}" height="24" rx="12" fill="{accent}" fill-opacity=".16" stroke="{accent}" stroke-width="1.5"/>'
                 + T(x + tw_ / 2, 406, t, 'fcb', 13, WHITE, 'middle', 1))
        x += tw_ + 8
    assert x < 470, tags
    b.append(T(548, 408, 'OPEN FILE', 'fb', 18, accent, 'end', 2) + f'<path d="M552,402 L566,402 M560,396 L566,402 L560,408" fill="none" stroke="{accent}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    write_svg(f'card-{slug}.svg', W, H, f'Mission 0{num}: {title}', ''.join(b), CARD_CSS, ''.join(defs))


def catmull(points):
    segs = []
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i else points[i]
        p1, p2 = points[i], points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        segs.append((p1, c1, c2, p2))
    d = f'M{points[0][0]},{points[0][1]} ' + ' '.join(f'C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]},{p2[1]}' for _, c1, c2, p2 in segs)
    lengths = []
    for p1, c1, c2, p2 in segs:
        L, prev = 0, p1
        for k in range(1, 201):
            t = k / 200
            pt = tuple((1 - t) ** 3 * p1[j] + 3 * (1 - t) ** 2 * t * c1[j] + 3 * (1 - t) * t * t * c2[j] + t ** 3 * p2[j] for j in range(2))
            L += math.dist(prev, pt)
            prev = pt
        lengths.append(L)
    total = sum(lengths)
    fracs = [0.0]
    for L in lengths:
        fracs.append(fracs[-1] + L / total)
    return d, fracs


def milestone_icon(kind, color):
    if kind == 'cap':
        return f'<path d="M-16,-4 L0,-12 L16,-4 L0,4 Z" fill="{INK}"/><path d="M-9,0 L-9,8 Q0,13 9,8 L9,0" fill="{INK}"/><path d="M14,-4 L14,8" stroke="{INK}" stroke-width="2.5"/>'
    if kind == 'laptop':
        return f'<rect x="-13" y="-11" width="26" height="17" rx="2" fill="{INK}"/><rect x="-10" y="-8" width="20" height="11" fill="{color}"/><path d="M-17,8 L17,8" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>'
    if kind == 'globe':
        return f'<circle r="13" fill="none" stroke="{INK}" stroke-width="3"/><ellipse rx="6" ry="13" fill="none" stroke="{INK}" stroke-width="2.5"/><path d="M-13,0 L13,0" stroke="{INK}" stroke-width="2.5"/>'
    if kind == 'robot':
        return f'<rect x="-12" y="-9" width="24" height="18" rx="5" fill="{INK}"/><circle cx="-5" cy="0" r="3" fill="{color}"/><circle cx="5" cy="0" r="3" fill="{color}"/><path d="M0,-9 L0,-15" stroke="{INK}" stroke-width="2.5"/><circle cy="-16" r="2.5" fill="{INK}"/>'
    if kind == 'gem':
        return f'<path d="M-12,-5 L-6,-12 L6,-12 L12,-5 L0,12 Z" fill="{INK}"/><path d="M-12,-5 L12,-5 M-6,-12 L0,12 L6,-12" stroke="{color}" stroke-width="1.6" fill="none"/>'
    if kind == 'brain':
        return f'<path d="M0,-12 C-14,-14 -16,0 -10,6 C-8,12 0,12 0,8 C0,12 8,12 10,6 C16,0 14,-14 0,-12 Z" fill="{INK}"/><path d="M0,-11 L0,8 M-6,-4 Q-2,0 -6,4 M6,-4 Q2,0 6,4" stroke="{color}" stroke-width="1.8" fill="none"/>'
    return f'<path d="M0,-14 L4,-4 L14,-4 L6,3 L9,13 L0,7 L-9,13 L-6,3 L-14,-4 L-4,-4 Z" fill="{INK}"/>'


def panel_journey():
    W, H = 1200, 700
    rng = random.Random(17)
    b = [f'<rect width="{W}" height="{H}" fill="url(#jBg)"/>', stars(rng, 110, 0, 0, W, 420, rects=TITLE_BAND + ((0, 185, 1200, 272),))]
    defs = ['<linearGradient id="jBg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a0f26"/><stop offset=".55" stop-color="#2a1050"/><stop offset=".8" stop-color="#6b1d5c"/><stop offset="1" stop-color="#0d1117"/></linearGradient>']
    for i, (x, y, s, dur) in enumerate(((150, 210, .8, 70), (700, 180, 1.0, 90), (1050, 240, .7, 60))):
        b.append(f'<g class="drift" style="animation-duration:{dur}s;animation-delay:-{i * 20}s">{cloud(x, y, s, "#3b1d6e", .55)}</g>')
    b.append(hills(rng, W, 640, 120, '#2a0f4f', 1.2, .9))
    b.append(city(rng, 0, 1200, 700, 30, 80, '#170b33', '#ff7ab6'))
    b.append(hills(rng, W, 690, 60, '#12082a', 3.3))
    b.append(section_title(600, 128, 'EPISODE 05', 'ORIGIN STORY', '// EVERY HERO STARTS SOMEWHERE', 'url(#gTitleA)'))
    pts = [(120, 470), (280, 330), (444, 470), (608, 330), (772, 470), (936, 330), (1092, 440)]
    d, fracs = catmull(pts)
    b.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="44" stroke-linecap="round"/>'
             f'<path d="{d}" fill="none" stroke="#28305e" stroke-width="34" stroke-linecap="round"/>'
             f'<path d="{d}" fill="none" stroke="{GOLD}" stroke-width="3.5" stroke-dasharray="16 14" class="road"/>')
    stones = [('2017–21', 'BS INFORMATION TECH', 'University of Sargodha', 'cap', CYAN),
              ('2018–19', 'WEB DEV INTERN', 'Dixeam', 'laptop', PINK),
              ('2019–NOW', 'FREELANCE WEB DEV', 'Laravel · Vue · PHP', 'globe', GREEN),
              ('2021–22', 'AI DEVELOPER INTERN', 'DataYard · computer vision', 'robot', CYAN),
              ('2022–23', 'DATA MINING', 'Ares Projects', 'gem', GOLD),
              ('2022–24', 'MS ARTIFICIAL INTELLIGENCE', 'Air University, Islamabad', 'brain', MAGENTA),
              ('NOW', 'FREELANCE AI + WEB', 'Open to new missions', 'star', GREEN)]
    cyc, travel = 20, .88
    for (x, y), f, (year, title, org, icon, color) in zip(pts, fracs, stones):
        t = round(f * travel, 4)
        kt_glow = f'0;{t};{min(t + .015, 1):.4f};{min(t + .05, 1):.4f};.97;1'
        b.append(f'<circle cx="{x}" cy="{y}" r="34" fill="none" stroke="{color}" stroke-width="5" opacity="0">'
                 f'<animate attributeName="r" values="30;30;64;64;64;64" keyTimes="{kt_glow}" dur="{cyc}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="opacity" values="0;0;1;0;0;0" keyTimes="{kt_glow}" dur="{cyc}s" repeatCount="indefinite"/></circle>')
        b.append(f'<circle cx="{x}" cy="{y}" r="44" fill="url(#gWhite)" opacity="0">'
                 f'<animate attributeName="opacity" values="0;0;.9;.35;.35;0" keyTimes="{kt_glow}" dur="{cyc}s" repeatCount="indefinite"/></circle>')
        b.append(f'<circle cx="{x + 3}" cy="{y + 4}" r="28" fill="{INK}"/><circle cx="{x}" cy="{y}" r="28" fill="{color}" stroke="{INK}" stroke-width="4.5"/>')
        b.append(g(milestone_icon(icon, color), f'translate({x},{y})'))
        up = y < 400
        ty = y - 110 if up else y + 74
        b.append(comic(x, ty, year, 30, color, 'middle', 2, depth=2.5, sw=4.5))
        b.append(T(x, ty + 24, title, 'fcb', 15, WHITE, 'middle', 1))
        b.append(T(x, ty + 44, org, 'fc', 14, MUTED, 'middle'))
        if up:
            b.append(f'<line x1="{x}" y1="{ty + 52}" x2="{x}" y2="{y - 30}" stroke="{color}" stroke-opacity=".5" stroke-width="2" stroke-dasharray="3 4"/>')
    rider = g(byte_bot(False), 'translate(0,-26) scale(.34)')
    sparkle = ''.join(f'<circle cx="{-26 - k * 14}" cy="{-18 + (k % 2) * 8}" r="{4 - k * .8:.1f}" fill="{GOLD}" opacity="{.9 - k * .2:.1f}"/>' for k in range(4))
    b.append(f'<g>{sparkle}{rider}<animateMotion dur="{cyc}s" repeatCount="indefinite" keyPoints="0;1;1" keyTimes="0;{travel};1" calcMode="linear" path="{d}"/>'
             f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.02;.96;1" dur="{cyc}s" repeatCount="indefinite"/></g>')
    b.append(edges(W, H, 50, 40))
    css = '''
.drift{animation:drift 70s linear infinite}
@keyframes drift{from{transform:translateX(-200px)}to{transform:translateX(200px)}}
.road{animation:dash 1.4s linear infinite}
'''
    write_svg('journey.svg', W, H, 'Origin story timeline, 2017 to now', ''.join(b), css, ''.join(defs))


def panel_signal():
    W, H = 1200, 560
    rng = random.Random(29)
    b = [f'<rect width="{W}" height="{H}" fill="url(#sBg)"/>', stars(rng, 120, 0, 0, W, 380, rects=((640, 140, 1200, 520),))]
    defs = ['<linearGradient id="sBg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d1117"/><stop offset=".15" stop-color="#0a0f2c"/><stop offset=".7" stop-color="#1b1452"/><stop offset="1" stop-color="#3a1466"/></linearGradient>'
            '<linearGradient id="sigBeam" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#fff3c4" stop-opacity=".55"/><stop offset="1" stop-color="#fff3c4" stop-opacity=".12"/></linearGradient>']
    for i, (x, y, s, dur) in enumerate(((150, 120, 1.3, 60), (600, 80, 1.1, 80), (980, 140, 1.4, 70), (420, 190, .9, 90))):
        b.append(f'<g class="drift" style="animation-duration:{dur}s;animation-delay:-{i * 17}s">{cloud(x, y, s, "#2c2366", .8)}</g>')
    b.append(f'<polygon points="292,470 312,470 440,170 260,150" fill="url(#sigBeam)" class="glow"/>')
    b.append(f'<g class="pulse"><circle cx="352" cy="150" r="78" fill="#fff3c4" opacity=".9"/><circle cx="352" cy="150" r="88" fill="url(#gGold)"/>'
             f'{g(emblem(44, "#fff3c4", "#1b1452"), "translate(352,150)")}</g>')
    b.append(city(rng, -10, 1210, 560, 40, 120, '#120a2c', '#ff5ea8'))
    b.append(f'<rect x="40" y="470" width="420" height="100" fill="#0e0922"/><rect x="34" y="462" width="432" height="12" fill="#1d1440" stroke="{INK}" stroke-width="3"/>'
             f'<rect x="34" y="460" width="432" height="3" fill="{GREEN}" class="glow"/>'
             f'<rect x="280" y="440" width="44" height="24" rx="4" fill="#475569" stroke="{INK}" stroke-width="3"/><circle cx="302" cy="440" r="16" fill="#fff3c4" stroke="{INK}" stroke-width="3"/>')
    b.append(g(hero('power'), 'translate(150,462) scale(.86)'))
    b.append(g(g(byte_bot(), cls='bob'), 'translate(412,330) scale(.6)'))
    b.append(comic(1150, 230, 'NEED A HERO?', 86, 'url(#gTitleA)', 'end', 3))
    b.append(comic(1150, 296, 'FOR YOUR NEXT PROJECT', 44, 'url(#gTitleB)', 'end', 2))
    for i, ln in enumerate(('Freelance missions open: AI & machine learning,', 'computer vision and fast, beautiful web apps.')):
        b.append(T(1150, 340 + i * 28, ln, 'fc', 21, SOFT, 'end'))
    label = 'SEND THE SIGNAL'
    w = tw(label, 'fb', 34, 2) + 120
    x0 = 1150 - w
    poly = lambda dx, dy: f'{x0 + 14 + dx},{404 + dy} {1150 + dx},{404 + dy} {1136 + dx},{466 + dy} {x0 + dx},{466 + dy}'
    defs.append(f'<clipPath id="ctaClip"><polygon points="{poly(0, 0)}"/></clipPath><linearGradient id="ctaG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{PINK}"/><stop offset="1" stop-color="{ORANGE}"/></linearGradient>')
    b.append(g(f'<polygon points="{poly(6, 6)}" fill="{INK}"/><polygon points="{poly(0, 0)}" fill="url(#ctaG)" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
               f'<g clip-path="url(#ctaClip)"><rect x="{x0}" y="400" width="60" height="80" fill="#fff" opacity=".4" class="shine"/></g>'
               + T(x0 + 30, 447, label, 'fb', 34, WHITE, 'start', 2, f'stroke="{INK}" stroke-width="5" paint-order="stroke"')
               + f'<path d="M{1150 - 70},{435} L{1150 - 40},{435} M{1150 - 52},{424} L{1150 - 40},{435} L{1150 - 52},{446}" fill="none" stroke="{WHITE}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>',
               cls='bob-s'))
    ew = tw('bilalft05@gmail.com', 'fcb', 18, 1) + 36
    b.append(f'<rect x="{1143 - w / 2 - ew / 2:.1f}" y="481" width="{ew:.1f}" height="30" rx="15" fill="{INK}" stroke="{CYAN}" stroke-width="2"/>'
             + T(1143 - w / 2, 502, 'bilalft05@gmail.com', 'fcb', 18, CYAN, 'middle', 1))
    b.append(edges(W, H, 30, 40))
    css = f'''
.drift{{animation:drift 70s linear infinite}}
@keyframes drift{{from{{transform:translateX(-160px)}}to{{transform:translateX(160px)}}}}
.shine{{animation:shine 3.4s ease-in-out infinite}}
@keyframes shine{{0%,50%{{transform:translateX(-80px) skewX(-20deg)}}100%{{transform:translateX({w + 80:.0f}px) skewX(-20deg)}}}}
'''
    write_svg('signal.svg', W, H, 'Need a hero for your next project? Send the signal: bilalft05@gmail.com', ''.join(b), css, ''.join(defs))


def firework(i, x, y, colors, delay, dur=3.6, R=60, launch=520):
    """Rocket climbs from the skyline, then bursts into a ring of sparks. Returns (svg, css)."""
    rays = []
    for k in range(16):
        a = math.radians(k * 22.5)
        c = colors[k % len(colors)]
        rays.append(f'<line x1="{math.cos(a) * 12:.1f}" y1="{math.sin(a) * 12:.1f}" x2="{math.cos(a) * R:.1f}" y2="{math.sin(a) * R:.1f}" '
                    f'stroke="{c}" stroke-width="3.2" stroke-linecap="round"/>'
                    f'<circle cx="{math.cos(a) * (R + 7):.1f}" cy="{math.sin(a) * (R + 7):.1f}" r="3.6" fill="{c}"/>'
                    f'<circle cx="{math.cos(a + .2) * R * .55:.1f}" cy="{math.sin(a + .2) * R * .55:.1f}" r="2" fill="#fff"/>')
    burst = (f'<circle r="{R * 1.25:.0f}" fill="url(#gWhite)" opacity=".35"/>' + ''.join(rays))
    rise = launch - y
    svg = (f'<g transform="translate({x},{y})"><g class="fwr{i}" style="animation-delay:{delay}s">'
           f'<line x1="0" y1="0" x2="0" y2="26" stroke="{colors[0]}" stroke-width="3" stroke-linecap="round" opacity=".7"/><circle r="3.5" fill="#fff"/></g>'
           f'<g class="fwb{i}" style="animation-delay:{delay}s">{burst}</g></g>')
    css = (f'.fwr{i}{{opacity:0;animation:fwr{i} {dur}s ease-out infinite}}'
           f'@keyframes fwr{i}{{0%{{transform:translateY({rise}px);opacity:1}}28%{{transform:translateY(0);opacity:1}}30%,100%{{transform:translateY(0);opacity:0}}}}'
           f'.fwb{i}{{opacity:0;animation:fwb{i} {dur}s ease-out infinite}}'
           f'@keyframes fwb{i}{{0%,28%{{transform:scale(.05);opacity:0}}31%{{transform:scale(.3);opacity:1}}55%{{transform:scale(1);opacity:1}}88%{{transform:scale(1.12);opacity:0}}100%{{opacity:0}}}}')
    return svg, css


def panel_footer():
    W, H = 1200, 720
    rng = random.Random(41)
    css = []
    b = [f'<rect width="{W}" height="{H}" fill="url(#fBg)"/>',
         stars(rng, 90, 0, 0, W, 430, rects=((300, 40, 900, 190),))]
    defs = ['<linearGradient id="fBg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0b0f2a"/><stop offset=".3" stop-color="#1a0f45"/>'
            '<stop offset=".5" stop-color="#4a1466"/><stop offset=".62" stop-color="#a3267a"/><stop offset=".68" stop-color="#ff6a4d"/>'
            '<stop offset=".69" stop-color="#140b30"/><stop offset="1" stop-color="#0b0f2a"/></linearGradient>'
            '<linearGradient id="ground" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#120a2c"/><stop offset="1" stop-color="#0b0f2a"/></linearGradient>'
            '<linearGradient id="spot" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff3c4" stop-opacity=".05"/><stop offset="1" stop-color="#fff3c4" stop-opacity=".32"/></linearGradient>']
    # comic speed-lines behind the title
    b.append(g(g(''.join(f'<polygon points="0,0 {math.cos(math.radians(a - 2.5)) * 720:.0f},{math.sin(math.radians(a - 2.5)) * 720:.0f} '
                         f'{math.cos(math.radians(a + 2.5)) * 720:.0f},{math.sin(math.radians(a + 2.5)) * 720:.0f}" fill="#fff"/>' for a in range(0, 360, 15)),
                 cls='spin'), 'translate(600,112)', None, 'opacity:.05'))
    # fireworks over the city
    shows = [(150, 120, (PINK, GOLD), 0.0), (330, 64, (GREEN, CYAN), 1.2), (880, 70, (GOLD, ORANGE), .5),
             (1060, 130, (CYAN, PURPLE), 1.9), (210, 270, (MAGENTA, GOLD), 2.6), (1000, 280, (GREEN, PINK), .9), (720, 230, (ORANGE, CYAN), 3.0)]
    for i, (x, y, cols, dl) in enumerate(shows):
        fs, fc = firework(i, x, y, cols, dl, 3.6 + (i % 3) * .5, 54 + (i % 3) * 10)
        b.append(fs)
        css.append(fc)
    # skyline behind the stage
    b.append(hills(rng, W, 470, 70, '#2b1257', .8, .95))
    b.append(faisal_mosque(250, 478, .6))
    b.append(pk_monument(1110, 476, .6))
    b.append(city(rng, 360, 1060, 482, 24, 96, '#170b33', '#ff7ab6'))
    b.append(city(rng, -10, 170, 482, 20, 70, '#170b33', '#ff7ab6'))
    b.append(f'<rect y="540" width="{W}" height="{H - 540}" fill="url(#ground)"/>')
    # sweeping spotlights onto the stage
    for x0, dl in ((60, 0), (1140, -4)):
        b.append(f'<polygon class="spotl" style="transform-origin:{x0}px 0px;animation-delay:{dl}s" points="{x0 - 8},0 {x0 + 8},0 {600 + (x0 - 600) * .2 + 120:.0f},490 {600 + (x0 - 600) * .2 - 120:.0f},490" fill="url(#spot)"/>')
    # stage with marquee bulbs
    b.append(f'<path d="M30,474 L1170,474 L1186,502 L14,502 Z" fill="#2a1a5e" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
             f'<path d="M30,474 L1170,474" stroke="{GREEN}" stroke-width="3" class="glow"/>'
             f'<rect x="14" y="502" width="1172" height="50" fill="#140b30" stroke="{INK}" stroke-width="4"/>')
    for k, x in enumerate(range(34, 1180, 26)):
        b.append(f'<circle class="bulb{k % 2}" cx="{x}" cy="527" r="5.5" fill="{GOLD}" stroke="{INK}" stroke-width="1.5"/>')
    # the cast
    cast = [(150, form_mole(False), .5, 'DATAMOLE', GOLD, '-.4s'), (330, form_stack(), .5, 'STACKFORGE', ORANGE, '-1.2s'),
            (590, hero('power'), .64, 'MUHAMMAD SAAD', GREEN, '0s'), (900, form_vision(False), .52, 'VISION-X', TEAL, '-.8s'),
            (1062, form_neuro(), .5, 'NEURONIX', MAGENTA, '-1.6s')]
    for x, art, sc, name, color, dl in cast:
        b.append(f'<ellipse cx="{x}" cy="478" rx="{70 * sc + 18:.0f}" ry="7" fill="#000" opacity=".35"/>')
        b.append(g(g(art, f'scale({sc})'), f'translate({x},476)'))
        w = tw(name, 'fcb', 12, 2) + 22
        b.append(f'<rect x="{x - w / 2:.1f}" y="480" width="{w:.1f}" height="19" rx="9.5" fill="{INK}" stroke="{color}" stroke-width="2"/>'
                 + T(x, 494, name, 'fcb', 12, color, 'middle', 2))
    b.append(g(g(byte_bot(), cls='bob'), 'translate(758,330) scale(.55)'))
    bub, _ = speech(790, 268, 'BYE BYE!', 18)
    b.append(g(bub, cls='bob-s'))
    # title
    b.append(comic(600, 134, 'THANKS FOR WATCHING!', 80, 'url(#gTitleA)', 'middle', 3))
    b.append(T(600, 172, '// SEE YOU IN THE NEXT EPISODE', 'fcb', 17, CYAN, 'middle', 4, f'stroke="{INK}" stroke-width="4" paint-order="stroke"'))
    # confetti
    for k in range(46):
        x = rng.uniform(0, W)
        c = rng.choice([PINK, GOLD, GREEN, CYAN, ORANGE, MAGENTA])
        w_, h_ = rng.choice([(6, 10), (8, 5), (5, 5)])
        b.append(f'<g transform="translate({x:.0f},-20)"><rect class="conf" style="animation-duration:{rng.uniform(6, 11):.1f}s;animation-delay:-{rng.uniform(0, 11):.1f}s" '
                 f'width="{w_}" height="{h_}" fill="{c}"/></g>')
    # credits roll
    reel = 'STARRING MUHAMMAD SAAD • BYTE • VISION-X • NEURONIX • STACKFORGE • DATAMOLE • FILMED ON LOCATION IN ISLAMABAD • '
    rw = tw(reel, 'fb', 22, 2)
    copies = math.ceil((W + rw) / rw) + 1
    b.append(f'<rect x="0" y="566" width="{W}" height="42" fill="{INK}"/><rect x="0" y="566" width="{W}" height="3" fill="{GOLD}"/><rect x="0" y="605" width="{W}" height="3" fill="{GOLD}"/>')
    b.append(f'<g class="reel">{"".join(T(k * rw, 595, reel, "fb", 22, GOLD if k % 2 else WHITE, ls=2) for k in range(copies))}</g>')
    css.append(f'.reel{{animation:reel 26s linear infinite}}@keyframes reel{{to{{transform:translateX(-{rw:.1f}px)}}}}')
    # to be continued...
    label = 'TO BE CONTINUED...'
    w = tw(label, 'fb', 34, 3) + 70
    x0 = 600 - w / 2 - 16
    box = (f'<polygon points="{x0 + 6},{630} {x0 + w + 6},{630} {x0 + w + 40},{656} {x0 + w + 6},{682} {x0 + 6},{682}" fill="{INK}"/>'
           f'<polygon points="{x0},{624} {x0 + w},{624} {x0 + w + 34},{650} {x0 + w},{676} {x0},{676}" fill="{GOLD}" stroke="{INK}" stroke-width="4.5" stroke-linejoin="round"/>'
           + T(x0 + w / 2 + 4, 662, label, 'fb', 34, INK, 'middle', 3))
    b.append(g(box, cls='bob-s'))
    b.append(edges(W, H, 40, 34, bottom_to=BG0))
    css.append('''
.spotl{animation:spotl 7s ease-in-out infinite alternate}
@keyframes spotl{from{transform:rotate(-9deg)}to{transform:rotate(9deg)}}
.bulb0{animation:bf .9s steps(1) infinite}
.bulb1{animation:bf .9s steps(1) infinite;animation-delay:-.45s}
.conf{animation:conf 8s linear infinite;transform-box:fill-box;transform-origin:center}
@keyframes conf{from{transform:translate(0,0) rotate(0deg)}to{transform:translate(46px,760px) rotate(900deg)}}
''')
    write_svg('footer.svg', W, H, 'Thanks for watching — the whole cast takes a bow under the fireworks. To be continued!', ''.join(b), ''.join(css), ''.join(defs))


# ── Training log (contribution city) ───────────────────────────────────────
def fetch_calendar(user='MSaadShahid1'):
    """The public contribution calendar, exactly as visitors see it on the profile page."""
    import urllib.request
    req = urllib.request.Request(f'https://github.com/users/{user}/contributions', headers={'User-Agent': 'Mozilla/5.0 (profile-art generator)'})
    page = urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
    counts = {}
    for m in re.finditer(r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
        n = re.match(r'\s*(\d[\d,]*) contributions?\b', m.group(2))
        counts[m.group(1)] = int(n.group(1).replace(',', '')) if n else 0
    days = []
    for m in re.finditer(r'<td\b[^>]*\bdata-date="[^"]+"[^>]*>', page):
        tag = m.group(0)
        day = dt.date.fromisoformat(re.search(r'data-date="([^"]+)"', tag).group(1))
        cid = re.search(r'\bid="([^"]+)"', tag).group(1)
        level = int(re.search(r'data-level="(\d)"', tag).group(1))
        days.append((day, counts.get(cid, 0), level))
    days.sort()
    assert len(days) > 300, f'calendar parse failed ({len(days)} days)'
    return days


def streaks(days):
    longest = run = 0
    for _, c, _ in days:
        run = run + 1 if c else 0
        longest = max(longest, run)
    seq = [c for _, c, _ in days]
    if seq and not seq[-1]:
        seq = seq[:-1]  # today isn't over yet, so a quiet today doesn't break the streak
    cur = 0
    for c in reversed(seq):
        if not c:
            break
        cur += 1
    return cur, longest


TOWER = {1: ('#2fbf6d', '#13733f', '#0c522d'), 2: ('#4ade80', '#16a34a', '#0f6b33'),
         3: ('#86efac', '#22c55e', '#15803d'), 4: ('#d9ffe9', GREEN, '#16a34a')}


def panel_training(days=None):
    days = days or fetch_calendar()
    W, H = 1200, 720
    rng = random.Random(77)
    start = days[0][0] - dt.timedelta(days=(days[0][0].weekday() + 1) % 7)
    cells = {((d - start).days // 7, (d.weekday() + 1) % 7): (d, c, lv) for d, c, lv in days}
    cols = max(k[0] for k in cells) + 1
    total = sum(c for _, c, _ in days)
    active = sum(1 for _, c, _ in days if c)
    best_day, best = max(((d, c) for d, c, _ in days), key=lambda t: (t[1], t[0]))
    cur, longest = streaks(days)
    per = 25
    level, xp = 1 + total // per, total % per

    b = [f'<rect width="{W}" height="{H}" fill="url(#tBg)"/>', '<rect width="1200" height="720" fill="url(#grid)" opacity=".04"/>',
         stars(rng, 80, 0, 0, W, 300)]
    defs = ['<linearGradient id="tBg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0b0f2a"/><stop offset=".45" stop-color="#0d1d3a"/><stop offset="1" stop-color="#0b0f2a"/></linearGradient>'
            '<linearGradient id="sweepG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#39ff88" stop-opacity="0"/><stop offset=".5" stop-color="#39ff88" stop-opacity=".22"/><stop offset="1" stop-color="#39ff88" stop-opacity="0"/></linearGradient>'
            '<linearGradient id="xpG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#14b8a6"/><stop offset="1" stop-color="#39ff88"/></linearGradient>']
    css = []
    b.append(section_title(600, 128, 'EPISODE 06', 'TRAINING LOG', '// EVERY CONTRIBUTION POWERS UP THE HERO', 'url(#gTitleB)'))

    # the city: one tile per day, a tower for every day with contributions
    sx, rh, gap = -8, 10, 3
    cw = (1060 - 7 * abs(sx)) / cols
    gx0, gy0 = 70 + 7 * abs(sx), 344
    fy = gy0 + 7 * rh + 4
    right = gx0 + cols * cw + 4
    # Neo-city skyline behind the training ground (scenery only; the green towers are the data)
    defs.append(f'<clipPath id="horizon"><rect width="{W}" height="{gy0 - 3}"/></clipPath>')
    b.append('<g clip-path="url(#horizon)">'
             '<circle cx="980" cy="250" r="64" fill="#ffd9a0" opacity=".9"/><circle cx="980" cy="250" r="130" fill="url(#gGold)" opacity=".35"/>'
             + hills(rng, W, gy0 - 30, 60, '#14204a', 1.7, .9)
             + pagoda(250, gy0 - 4, 40, 96, '#101a3f', '#2bd96b')
             + faisal_mosque(620, gy0 - 4, .55, '#101a3f', '#2bd96b')
             + city(rng, 60, 1140, gy0 - 4, 18, 92, '#0f1838', '#2bd96b', depth=4, low=((520, 720, 26),)) + '</g>')
    b.append(f'<path d="M{gx0 - 8:.1f},{gy0 - 5} L{right:.1f},{gy0 - 5} L{right + 7 * sx:.1f},{fy} L{gx0 - 8 + 7 * sx:.1f},{fy} Z" fill="#0d1434" stroke="{GREEN}" stroke-opacity=".45" stroke-width="2"/>'
             f'<rect x="{gx0 - 8 + 7 * sx:.1f}" y="{fy}" width="{right - gx0 + 8:.1f}" height="20" fill="#080c22" stroke="{INK}" stroke-width="3"/>'
             f'<line x1="{gx0 - 8 + 7 * sx:.1f}" y1="{fy}" x2="{right + 7 * sx:.1f}" y2="{fy}" stroke="{GREEN}" stroke-width="2" class="glow"/>')
    prev_month = None
    for col in range(cols):
        sunday = start + dt.timedelta(days=7 * col)
        if sunday.month != prev_month and col < cols - 2:
            if prev_month is not None or sunday.day <= 7:
                b.append(T(gx0 + col * cw + 7 * sx + 2, fy + 15, sunday.strftime('%b').upper(), 'fcb', 11, MUTED, ls=1))
            prev_month = sunday.month
    for row, name in ((1, 'MON'), (3, 'WED'), (5, 'FRI')):
        b.append(T(gx0 + row * sx - 12, gy0 + row * rh + 8, name, 'fcb', 9, MUTED, 'end', 1))
    maxc = max(1, best)
    tops = []
    for row in range(7):
        for col in range(cols):
            if (col, row) not in cells:
                continue
            d, c, lv = cells[(col, row)]
            bx, by = gx0 + col * cw + row * sx, gy0 + row * rh
            w = cw - gap
            if not c:
                b.append(f'<polygon points="{bx:.1f},{by} {bx + w:.1f},{by} {bx + w + sx:.1f},{by + rh - 2} {bx + sx:.1f},{by + rh - 2}" fill="#131a40" stroke="#22306a" stroke-width="1"/>')
                continue
            h = 12 + 118 * (c / maxc) ** .75
            top, front, side = TOWER[max(1, min(4, lv))]
            yt = by - h
            faces = (f'<polygon points="{bx + w:.1f},{yt:.1f} {bx + w + sx:.1f},{yt + rh:.1f} {bx + w + sx:.1f},{by + rh:.1f} {bx + w:.1f},{by:.1f}" fill="{side}" stroke="{INK}" stroke-width="1.2" stroke-linejoin="round"/>'
                     f'<rect x="{bx + sx:.1f}" y="{yt + rh:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{front}" stroke="{INK}" stroke-width="1.2"/>'
                     + ''.join(f'<rect x="{bx + sx + w / 2 - 2:.1f}" y="{yy:.1f}" width="4" height="3" fill="#eafff2" opacity=".55"/>' for yy in range(int(yt + rh + 6), int(by + rh - 4), 9))
                     + f'<polygon points="{bx:.1f},{yt:.1f} {bx + w:.1f},{yt:.1f} {bx + w + sx:.1f},{yt + rh:.1f} {bx + sx:.1f},{yt + rh:.1f}" fill="{top}" stroke="{INK}" stroke-width="1.2" stroke-linejoin="round"/>')
            b.append(f'<g class="grow" style="animation-delay:{col * .025 + row * .03:.2f}s">{faces}'
                     f'<circle cx="{bx + w / 2 + sx / 2:.1f}" cy="{yt + rh / 2:.1f}" r="{8 + 6 * c / maxc:.1f}" fill="url(#gGreen)" class="glow"/></g>')
            tops.append((c, bx + w / 2 + sx / 2, yt, d))
    b.append(f'<rect class="sweep" x="-120" y="190" width="120" height="{fy + 22 - 190}" fill="url(#sweepG)"/>')
    css.append('.sweep{animation:sweep 6s linear infinite}@keyframes sweep{from{transform:translateX(0)}to{transform:translateX(1440px)}}'
               '.grow{animation:grow 16s cubic-bezier(.3,1.6,.5,1) infinite both;transform-box:fill-box;transform-origin:50% 100%}'
               '@keyframes grow{0%{transform:scaleY(0)}9%,92%{transform:scaleY(1)}98%,100%{transform:scaleY(0)}}')

    # Byte flies the route, collecting an energy orb above each of the biggest towers
    route = sorted(sorted(tops, key=lambda t: -t[0])[:12], key=lambda t: t[1])
    pts = [(24, 236)] + [(x, max(196, y - 44)) for _, x, y, _ in route] + [(1176, 236)]
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    run, fr = 0, []
    for L in seg:
        run += L
        fr.append(run / sum(seg))
    cyc, travel = 16, .9
    for (c, x, y, d), f in zip(route, fr):
        t = round(f * travel, 4)
        oy = max(196, y - 44)
        b.append(f'<g><circle cx="{x:.1f}" cy="{oy:.1f}" r="7" fill="{GOLD}" stroke="{INK}" stroke-width="2"/><circle cx="{x - 2:.1f}" cy="{oy - 2:.1f}" r="2.5" fill="#fff"/>'
                 f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;{t};{t + .01:.4f};.97;1" dur="{cyc}s" repeatCount="indefinite"/></g>')
        b.append(f'<g opacity="0">' + T(x, oy - 14, f'+{c}', 'fb', 22, GOLD, 'middle', 1, f'stroke="{INK}" stroke-width="4" paint-order="stroke"')
                 + f'<animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;{t};{t + .01:.4f};{t + .08:.4f};1" dur="{cyc}s" repeatCount="indefinite"/>'
                 f'<animateTransform attributeName="transform" type="translate" values="0 0;0 0;0 -28;0 -28" keyTimes="0;{t};{t + .08:.4f};1" dur="{cyc}s" repeatCount="indefinite"/></g>')
    path = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    b.append(f'<path d="{path}" fill="none" stroke="{CYAN}" stroke-opacity=".25" stroke-width="2" stroke-dasharray="4 8" class="dash"/>')
    b.append(f'<g>{g(byte_bot(False), "scale(.36)")}<animateMotion dur="{cyc}s" repeatCount="indefinite" keyPoints="0;1;1" keyTimes="0;{travel};1" calcMode="linear" path="{path}"/></g>')

    # stat cards
    cards = [('CONTRIBUTIONS', f'{total}', 'IN THE LAST YEAR', GREEN), ('ACTIVE DAYS', f'{active}', 'DAYS POWERED UP', CYAN),
             ('BEST DAY', f'{best}', 'ON ' + best_day.strftime('%d %b').upper() if best else 'STILL CHARGING', GOLD),
             ('CURRENT STREAK', f'{cur}', 'DAY' if cur == 1 else 'DAYS', PINK), ('LONGEST STREAK', f'{longest}', 'DAY' if longest == 1 else 'DAYS', PURPLE)]
    for i, (label, value, sub, color) in enumerate(cards):
        x, y = 70 + i * 216, 470
        b.append(f'<rect x="{x + 5}" y="{y + 5}" width="196" height="108" rx="16" fill="{color}"/>'
                 f'<rect x="{x}" y="{y}" width="196" height="108" rx="16" fill="#0c1230" stroke="{INK}" stroke-width="3.5"/>'
                 + T(x + 98, y + 26, label, 'fcb', 13, color, 'middle', 2)
                 + g(T(x + 98, y + 78, value, 'fb', 50, WHITE, 'middle', 2, f'stroke="{INK}" stroke-width="6" paint-order="stroke"'), cls='pulse')
                 + T(x + 98, y + 98, sub, 'fc', 12, MUTED, 'middle', 1))
    # hero XP bar
    frac = xp / per
    b.append(comic(70, 640, f'HERO LV {level}', 34, 'url(#gTitleB)', ls=2, depth=2.5, sw=4.5))
    bx0, bw = 270, 720
    b.append(f'<rect x="{bx0}" y="614" width="{bw}" height="24" rx="12" fill="#131a40" stroke="{INK}" stroke-width="3"/>')
    if xp:
        b.append(f'<rect class="xp" x="{bx0 + 3}" y="617" width="{(bw - 6) * frac:.1f}" height="18" rx="9" fill="url(#xpG)"/>')
    css.append('.xp{animation:xp 16s ease-out infinite both;transform-box:fill-box;transform-origin:0 50%}'
               '@keyframes xp{0%{transform:scaleX(0)}14%,92%{transform:scaleX(1)}100%{transform:scaleX(0)}}')
    for k in range(1, 10):
        b.append(f'<line x1="{bx0 + bw * k / 10:.1f}" y1="617" x2="{bx0 + bw * k / 10:.1f}" y2="635" stroke="{INK}" stroke-opacity=".35" stroke-width="2"/>')
    b.append(T(1130, 634, f'{xp} / {per} XP', 'fcb', 18, GREEN, 'end', 1))
    b.append(T(70, 668, '1 TILE = 1 DAY · TOWER HEIGHT = CONTRIBUTIONS', 'fc', 12, MUTED, ls=2))
    b.append(T(1130, 668, f'SNAPSHOT {dt.date.today().strftime("%d %b %Y").upper()} · {per - xp} MORE TO LEVEL {level + 1}', 'fc', 12, MUTED, 'end', 2))
    b.append(edges(W, H, 40, 40))
    write_svg('training.svg', W, H, f'Training log: {total} contributions in the last year, {active} active days, best day {best}, current streak {cur}, longest streak {longest}',
              ''.join(b), ''.join(css), ''.join(defs))


# ── Build ──────────────────────────────────────────────────────────────────
GLOBE = f'<circle r="15" fill="none" stroke="{INK}" stroke-width="3.5"/><ellipse rx="7" ry="15" fill="none" stroke="{INK}" stroke-width="3"/><path d="M-15,0 L15,0 M-12,-8 L12,-8 M-12,8 L12,8" stroke="{INK}" stroke-width="2.5"/>'
LINKEDIN = T(0, 10, 'in', 'fcb', 30, '#0A66C2', 'middle')
XLOGO = f'<path d="M-12,-13 L12,13 M12,-13 L-12,13" stroke="{INK}" stroke-width="5" stroke-linecap="round"/><path d="M-12,-13 L12,13" stroke="#fff" stroke-width="1.5"/>'
MAIL = f'<rect x="-15" y="-11" width="30" height="22" rx="3" fill="{PINK}" stroke="{INK}" stroke-width="3"/><path d="M-14,-9 L0,3 L14,-9" fill="none" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'

def build_buttons():
    button('portfolio', 'PORTFOLIO', 'SEE MY WORK', f'<stop offset="0" stop-color="{GREEN}"/><stop offset="1" stop-color="#0d9488"/>', GLOBE)
    button('linkedin', 'LINKEDIN', "LET'S CONNECT", '<stop offset="0" stop-color="#2d8cf0"/><stop offset="1" stop-color="#0A66C2"/>', LINKEDIN)
    button('x', 'FOLLOW ON X', '@MUHAMMA06001032', '<stop offset="0" stop-color="#3a3f52"/><stop offset="1" stop-color="#0b0b16"/>', XLOGO)
    button('email', 'EMAIL ME', 'BILALFT05@GMAIL.COM', f'<stop offset="0" stop-color="{PINK}"/><stop offset="1" stop-color="{ORANGE}"/>', MAIL)


def build_cards():
    card('valentine', 1, 'VALENTINE QUESTION', ['A cinematic proposal site: starry intro, love quiz,', 'an uncatchable NO button and canvas fireworks.'],
         ['REACT', 'TYPESCRIPT', 'MOTION', 'CANVAS'], PINK, 'LIVE', art_valentine)
    card('scholarmind', 2, 'SCHOLARMIND', ['LLM-powered academic co-author: semantic paper', 'search, research questions and structured writing.'],
         ['LLMS', 'NLP', 'PYTHON', 'TEAM · ITSOLERA'], PURPLE, 'COMPLETE', art_scholar)
    card('claims', 3, 'HEALTHCARE CLAIMS', ['Loads and validates EMR insurance claims, explains', 'every exclusion, outputs resubmission candidates.'],
         ['DATA ENGINEERING', 'PYTHON', 'JSON'], CYAN, 'COMPLETE', art_claims)
    card('portfolio', 4, 'PERSONAL PORTFOLIO', ['My portfolio site: about, skills, experience', 'and projects — live on GitHub Pages.'],
         ['HTML', 'CSS', 'JAVASCRIPT', 'PHP'], ORANGE, 'LIVE', art_portfolio)


PANELS = {'hero': panel_hero, 'buttons': build_buttons, 'about': panel_about, 'forms': panel_forms, 'arsenal': panel_arsenal,
          'missions': panel_missions_title, 'cards': build_cards, 'journey': panel_journey, 'training': panel_training,
          'signal': panel_signal, 'footer': panel_footer}

if __name__ == '__main__':
    for name in sys.argv[2:] or PANELS:
        PANELS[name]()
