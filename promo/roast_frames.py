#!/usr/bin/env python3
"""AI Sizzler Reel frame renderer: 90s Geocities x VHS x gen-alpha brainrot.

1920x1080 @ 30fps, 28.8s, beat-locked to roast_audio.py (150 BPM, BAR=1.6s).
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from multiprocessing import Pool

W, H = 1920, 1080
FPS = 30
BEAT = 0.4
BAR = 1.6
TOTAL = 18 * BAR                      # 28.8
FRAMES = int(round(TOTAL * FPS))      # 864
CX, CY = W / 2, H / 2
FREEZE_T = 27.5                       # tape-stop freeze
BLACK_T = 28.2

S1_END, S2_END, S3_END, S4_END, S5_END = 3.2, 6.4, 16.0, 19.2, 22.4
CUTS = [3.2, 6.4, 8.0, 9.6, 11.2, 12.8, 14.4, 16.0, 17.6,
        19.2, 20.0, 20.8, 21.6, 22.4]
AIRHORNS = [3.2, 3.82, 4.06, 4.30, 8.0, 11.2, 19.2, 22.4, 23.02, 23.26, 23.50]

F_IMPACT = "/System/Library/Fonts/Supplemental/Impact.ttf"
F_BLACK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
F_COMIC = "/System/Library/Fonts/Supplemental/Comic Sans MS.ttf"
F_COMICB = "/System/Library/Fonts/Supplemental/Comic Sans MS Bold.ttf"
F_COUR = "/System/Library/Fonts/Supplemental/Courier New Bold.ttf"
F_EMOJI = "/System/Library/Fonts/Apple Color Emoji.ttc"

PAL = [(255, 20, 147), (57, 255, 20), (255, 255, 0), (0, 255, 255),
       (255, 105, 0), (191, 64, 255)]

X = Y = VIGNETTE = SCAN = None
_fonts = {}
_emoji = {}


def init_worker():
    global X, Y, VIGNETTE, SCAN
    ys, xs = np.mgrid[0:H, 0:W]
    X = xs.astype(np.float32)
    Y = ys.astype(np.float32)
    r = np.sqrt(((X - CX) / (W / 2)) ** 2 + ((Y - CY) / (H / 2)) ** 2)
    VIGNETTE = (1.0 - 0.38 * np.clip(r, 0, 1.4) ** 2.4).astype(np.float32)[..., None]
    SCAN = (1.0 - 0.18 * (0.5 + 0.5 * np.sin(Y * (2 * np.pi / 3.0))))[..., None].astype(np.float32)


def font(path, px):
    key = (path, int(px))
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, int(px))
    return _fonts[key]


def rgba_text(text, path, px, fill=(255, 255, 255), stroke_w=0,
              stroke_fill=(0, 0, 0)):
    """-> (rgb float (h,w,3), alpha float (h,w))"""
    f = font(path, px)
    pad = int(px * 0.35) + stroke_w
    bb = f.getbbox(text, stroke_width=stroke_w)
    img = Image.new("RGBA", (bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad), 0)
    d = ImageDraw.Draw(img)
    d.text((pad - bb[0], pad - bb[1]), text, font=f, fill=tuple(fill) + (255,),
           stroke_width=stroke_w, stroke_fill=tuple(stroke_fill) + (255,))
    arr = np.asarray(img, np.float32) / 255.0
    return arr[..., :3], arr[..., 3]


def composite(frame, rgb, a, cx, cy):
    h, w = a.shape
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    sx0, sy0 = max(0, -x0), max(0, -y0)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x0 + w - sx0), min(H, y0 + h - sy0)
    if x1 <= x0 or y1 <= y0:
        return
    sub_a = a[sy0:sy0 + (y1 - y0), sx0:sx0 + (x1 - x0), None]
    sub_rgb = rgb[sy0:sy0 + (y1 - y0), sx0:sx0 + (x1 - x0)]
    frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - sub_a) + sub_rgb * sub_a


def meme_text(frame, text, px, cx, cy, alpha=1.0, fill=(255, 255, 255)):
    """Impact, white, fat black stroke. The people's typeface."""
    rgb, a = rgba_text(text, F_IMPACT, px, fill, stroke_w=max(2, int(px * 0.07)))
    composite(frame, rgb, a * alpha, cx, cy)


def rainbow(h):
    return np.clip(0.5 + 0.62 * np.cos(2 * np.pi * (h + np.array([0.0, -0.333, -0.667]))), 0, 1)


def wordart(frame, text, px, cx, cy, t, amp=14, alpha=1.0):
    """Per-char rainbow wave with hard drop shadow. Peak 1997."""
    f = font(F_BLACK, px)
    widths = [f.getbbox(c)[2] - f.getbbox(c)[0] + int(px * 0.06) for c in text]
    total = sum(widths)
    x = cx - total / 2
    sw = max(2, int(px * 0.055))
    for i, c in enumerate(text):
        if c != " ":
            dy = amp * np.sin(t * 3.2 + i * 0.55)
            col = tuple((rainbow((i * 0.09 + t * 0.25) % 1.0) * 255).astype(int))
            rgb, a = rgba_text(c, F_BLACK, px, col, stroke_w=sw)
            sh = np.zeros_like(rgb)
            composite(frame, sh, a * 0.8 * alpha, x + widths[i] / 2 + px * 0.07,
                      cy + dy + px * 0.07)
            composite(frame, rgb, a * alpha, x + widths[i] / 2, cy + dy)
        x += widths[i]


def emoji(frame, ch, cx, cy, px, alpha=1.0):
    if ch not in _emoji:
        try:
            f = ImageFont.truetype(F_EMOJI, 160)
            img = Image.new("RGBA", (220, 220), 0)
            ImageDraw.Draw(img).text((10, 10), ch, font=f, embedded_color=True)
            _emoji[ch] = img
        except Exception:
            _emoji[ch] = None
    src = _emoji[ch]
    if src is None:
        return
    img = src.resize((int(px * 1.375), int(px * 1.375)), Image.BILINEAR)
    arr = np.asarray(img, np.float32) / 255.0
    composite(frame, arr[..., :3], arr[..., 3] * alpha, cx, cy)


def star_badge(frame, cx, cy, r, rot_deg, text, fill=(255, 220, 0),
               txt_col=(200, 0, 0), alpha=1.0):
    """Spinning Geocities starburst. NEW!! HOT!!"""
    sz = int(r * 2.6)
    img = Image.new("RGBA", (sz, sz), 0)
    d = ImageDraw.Draw(img)
    c = sz / 2
    pts = []
    for k in range(24):
        rad = r if k % 2 == 0 else r * 0.62
        ang = k * np.pi / 12
        pts.append((c + rad * np.cos(ang), c + rad * np.sin(ang)))
    d.polygon(pts, fill=tuple(fill) + (255,), outline=(200, 0, 0, 255), width=4)
    f = font(F_COMICB, int(r * 0.30))
    bb = d.textbbox((0, 0), text, font=f)
    d.text((c - (bb[2] - bb[0]) / 2, c - (bb[3] - bb[1]) / 2 - bb[1]), text,
           font=f, fill=tuple(txt_col) + (255,))
    img = img.rotate(rot_deg, resample=Image.BICUBIC)
    arr = np.asarray(img, np.float32) / 255.0
    composite(frame, arr[..., :3], arr[..., 3] * alpha, cx, cy)


# ------------------------------------------------------------- backgrounds
def bg_checker(t, c1, c2, cell=90):
    th = 0.10 * np.sin(t * 0.9)
    Xr = (X - CX) * np.cos(th) - (Y - CY) * np.sin(th) + t * 130
    Yr = (X - CX) * np.sin(th) + (Y - CY) * np.cos(th) + t * 40
    cs = cell * (1 + 0.12 * np.sin(t * 1.7))
    m = (((Xr // cs) + (Yr // cs)) % 2)[..., None]
    a = np.asarray(c1, np.float32) / 255 * 0.72
    b = np.asarray(c2, np.float32) / 255 * 0.72
    return (a * (1 - m) + b * m).astype(np.float32)


def bg_spiral(t):
    ang = np.arctan2(Y - CY, X - CX)
    r = np.sqrt((X - CX) ** 2 + (Y - CY) ** 2)
    h = (ang * 3 / (2 * np.pi) + r / 260.0 - t * 1.1) % 1.0
    cols = 0.5 + 0.5 * np.cos(2 * np.pi * (h[..., None] + np.array([0.0, -0.333, -0.667])))
    return (cols * 0.42).astype(np.float32)


def bg_memphis(t, seed):
    frame = np.full((H, W, 3), np.array([0.10, 0.02, 0.14], np.float32))
    img = Image.new("RGBA", (W, H), 0)
    d = ImageDraw.Draw(img)
    g = np.random.default_rng(seed)
    for k in range(26):
        x, y = g.uniform(0, W), g.uniform(0, H)
        col = tuple(int(v) for v in PAL[int(g.integers(0, len(PAL)))]) + (200,)
        kind = g.integers(0, 3)
        rot = float(g.uniform(0, 360)) + t * float(g.uniform(-40, 40))
        s = float(g.uniform(24, 60))
        if kind == 0:      # triangle
            pts = [(x + s * np.cos(np.radians(rot + a)),
                    y + s * np.sin(np.radians(rot + a))) for a in (0, 130, 245)]
            d.polygon(pts, outline=col, width=6)
        elif kind == 1:    # circle
            d.ellipse([x - s / 2, y - s / 2, x + s / 2, y + s / 2], outline=col, width=6)
        else:              # squiggle
            ph = rot / 30
            pts = [(x + i * 8, y + 14 * np.sin(ph + i * 0.9)) for i in range(9)]
            d.line(pts, fill=col, width=6, joint="curve")
    arr = np.asarray(img, np.float32) / 255.0
    composite(frame, arr[..., :3] * 0.75, arr[..., 3] * 0.75, CX, CY)
    return frame


def construction_banner(frame, cy_band, t):
    band = (np.abs(Y - cy_band) < 42)
    stripes = (((X + Y + t * 60) // 26) % 2).astype(np.float32)
    col = (np.array([1.0, 0.85, 0.0], np.float32) * stripes[..., None]
           + np.array([0.05, 0.05, 0.05], np.float32) * (1 - stripes[..., None]))
    m = band[..., None].astype(np.float32) * 0.95
    frame[:] = frame * (1 - m) + col * m
    meme_text(frame, "UNDER CONSTRUCTION SINCE 1997", 46, CX, cy_band, fill=(255, 255, 255))


# ------------------------------------------------------------- widgets
def bevel_box(d, x0, y0, x1, y1, face=(192, 192, 192), pressed=False):
    lite, dark = ((255, 255, 255), (64, 64, 64))
    if pressed:
        lite, dark = dark, lite
    d.rectangle([x0, y0, x1, y1], fill=face)
    d.line([x0, y0, x1, y0], fill=lite, width=3)
    d.line([x0, y0, x0, y1], fill=lite, width=3)
    d.line([x0, y1, x1, y1], fill=dark, width=3)
    d.line([x1, y0, x1, y1], fill=dark, width=3)


def win95_dialog(img, x, y, w, h, title, lines, buttons, pressed_idx=-1):
    d = ImageDraw.Draw(img)
    bevel_box(d, x, y, x + w, y + h)
    d.rectangle([x + 6, y + 6, x + w - 6, y + 44], fill=(0, 0, 128))
    d.text((x + 16, y + 12), title, font=font(F_COUR, 26), fill=(255, 255, 255))
    bevel_box(d, x + w - 44, y + 12, x + w - 14, y + 40)
    d.text((x + w - 37, y + 14), "X", font=font(F_COUR, 22), fill=(0, 0, 0))
    # red X icon
    d.ellipse([x + 26, y + 66, x + 86, y + 126], fill=(255, 0, 0))
    d.line([x + 42, y + 82, x + 70, y + 110], fill=(255, 255, 255), width=8)
    d.line([x + 70, y + 82, x + 42, y + 110], fill=(255, 255, 255), width=8)
    for i, ln in enumerate(lines):
        d.text((x + 110, y + 66 + i * 34), ln, font=font(F_COUR, 24), fill=(0, 0, 0))
    bw = (w - 60) // len(buttons)
    for i, b in enumerate(buttons):
        bx = x + 30 + i * bw
        by = y + h - 66
        pr = (i == pressed_idx)
        bevel_box(d, bx, by, bx + bw - 20, by + 44, pressed=pr)
        f = font(F_COUR, 24)
        bb = d.textbbox((0, 0), b, font=f)
        d.text((bx + (bw - 20 - bb[2]) / 2 + (2 if pr else 0),
                by + 8 + (2 if pr else 0)), b, font=f, fill=(0, 0, 0))


def cursor(img, x, y, clicking=False):
    d = ImageDraw.Draw(img)
    s = 2.4 if not clicking else 2.2
    pts = [(0, 0), (0, 16), (4.4, 12.4), (7.4, 19.4), (9.8, 18.2), (6.8, 11.4), (11.4, 11.4)]
    pts = [(x + px * s, y + py * s) for px, py in pts]
    d.polygon(pts, fill=(255, 255, 255), outline=(0, 0, 0))


def osd(frame, text, px, cx, cy, col=(255, 255, 255)):
    rgb, a = rgba_text(text, F_COUR, px, col, stroke_w=max(2, px // 12))
    composite(frame, rgb, a, cx, cy)


# ------------------------------------------------------------- scenes
def scene_vhs(frame, t):
    frame += np.array([0.0, 0.05, 0.75], np.float32)
    g = np.random.default_rng(int(t * 700))
    frame += g.standard_normal((H, W, 1)).astype(np.float32) * 0.03
    blink = (t * 1.6) % 1 < 0.7
    if blink:
        osd(frame, "> PLAY", 54, 210, 90)
    osd(frame, "AI SIZZLER REEL", 110, CX, CY - 110)
    osd(frame, "VOL. 420 - 'AI IS TOAST'", 48, CX, CY + 20)
    osd(frame, "HI-FI  STEREO  SP  0:00", 34, CX, CY + 110, col=(200, 220, 255))
    osd(frame, "DEC 31 1999  11:59 PM", 40, 330, H - 80)
    if t > 2.2:
        osd(frame, "(we spared no expense*)  *every expense was spared", 28,
            CX, CY + 210, col=(180, 200, 255))


def scene_title(frame, t):
    p = t - S1_END
    frame += bg_checker(t, (120, 10, 90), (40, 0, 70))
    a = min(1.0, p / 0.1)
    wordart(frame, "AI IS TOAST", 165, CX, CY - 80, t, amp=16, alpha=a)
    emoji(frame, "🍞", 230, CY - 100 - 40 * abs(np.sin(t * 4.2)), 150, a)
    emoji(frame, "💀", W - 170, CY - 60 + 30 * np.sin(t * 5), 120, a)
    rgb, al = rgba_text("a roast. no cap. fr fr.", F_COMICB, 52, (255, 255, 255), 3)
    composite(frame, rgb, al * a, CX, CY + 130)
    rgb, al = rgba_text("(the AI wrote this trailer about itself. it knows.)",
                        F_COMIC, 34, (255, 240, 150), 2)
    composite(frame, rgb, al * a, CX, CY + 220)
    star_badge(frame, 240, 780, 130, t * 80, "HOT!!", alpha=a)
    star_badge(frame, W - 240, 300, 120, -t * 70, "NEW!", fill=(57, 255, 20),
               txt_col=(60, 0, 90), alpha=a)


CARDS = [
    ("checker", [(120, 10, 90), (10, 60, 20)], "impact",
     ["VIBE CODED.", "NEVER TESTED.", "SHIPPED FRIDAY."], "(it's fine)", "NO CAP", None),
    ("spiral", None, "impact",
     ["TRUST ME BRO,", "IT COMPILES"], "citation: vibes", "SOURCE?", "💀"),
    ("memphis", None, "comic",
     ["hallucinated.", "confidently.", "twice."],
     "the API docs came to me in a dream", "SHEESH", None),
    ("checker", [(0, 90, 110), (90, 0, 100)], "wordart",
     ["10 MILLION TOKENS", "TO CENTER A DIV"], "(it is still not centered)", "BRUH", None),
    ("spiral", None, "impact",
     ["IT'S GIVING", "SEGFAULT"], "core dumped. aura dumped.", "FR FR", "🗿"),
    ("memphis", None, "impact",
     ["L + RATIO", "+ FAILED CI"], "+ you fell off main", "COOKED", "🔥"),
]


def scene_cards(frame, t):
    idx = min(5, int((t - S2_END) / BAR))
    t0 = S2_END + idx * BAR
    p = t - t0
    bg, bgc, style, lines, fn, badge, emo = CARDS[idx]
    if bg == "checker":
        frame += bg_checker(t, *bgc)
    elif bg == "spiral":
        frame += bg_spiral(t) * 0.75
    else:
        frame += bg_memphis(t, seed=idx * 17 + 3)
    sc = 1.0 + 0.35 * np.exp(-p * 14)
    a = min(1.0, p / 0.06)
    n = len(lines)
    if style == "impact":
        for i, ln in enumerate(lines):
            px = int(130 * sc)
            meme_text(frame, ln, px, CX, CY - 40 + (i - (n - 1) / 2) * 165, a)
    elif style == "comic":
        for i, ln in enumerate(lines):
            rgb, al = rgba_text(ln, F_COMICB, int(105 * sc), (255, 255, 255), 6)
            composite(frame, rgb, al * a, CX, CY - 40 + (i - (n - 1) / 2) * 150)
    else:  # wordart headline + impact sub
        wordart(frame, lines[0], int(120 * sc), CX, CY - 130, t, alpha=a)
        meme_text(frame, lines[1], int(140 * sc), CX, CY + 60, a)
    rgb, al = rgba_text(fn, F_COMIC, 40, (255, 240, 150), 2)
    composite(frame, rgb, al * a, CX, CY + 300)
    side = 1 if idx % 2 == 0 else -1
    star_badge(frame, CX + side * 640, 260, 115, t * 95 * side, badge, alpha=a)
    if emo:
        emoji(frame, emo, CX - side * 620, H - 300 + 25 * np.sin(t * 5.5), 140, a)


def scene_windows(frame, t):
    p = t - S3_END
    if p < 1.6:
        frame += np.array([0.0, 0.42, 0.42], np.float32) * 0.55   # teal desktop
        img = Image.new("RGBA", (W, H), 0)
        pressed = 1 if (0.55 < p < 0.72 or 0.95 < p < 1.12) else -1
        if p > 1.25:  # the cascade begins
            win95_dialog(img, 560, 330, 800, 300, "AI_Assistant.exe",
                         ["A fatal skill issue has occurred.",
                          "The AI blames: you, the intern,",
                          "and cosmic rays. In that order."],
                         ["Abort", "Retry", "Cry"], -1)
        win95_dialog(img, 520, 290, 800, 300, "AI_Assistant.exe",
                     ["A fatal skill issue has occurred.",
                      "The AI blames: you, the intern,",
                      "and cosmic rays. In that order."],
                     ["Abort", "Retry", "Cry"], pressed)
        cx_ = 940 + 90 * np.sin(p * 2.1)
        cy_ = 520 + 60 * np.cos(p * 1.7) + (4 if pressed >= 0 else 0)
        cursor(img, cx_, cy_, clicking=pressed >= 0)
        arr = np.asarray(img, np.float32) / 255.0
        composite(frame, arr[..., :3], arr[..., 3], CX, CY)
    else:
        frame += np.array([0.0, 0.0, 0.66], np.float32)
        lines = [
            ("WINDOWS", True),
            ("", False),
            ("A fatal exception 0xC00K3D has occurred at", False),
            ("0028:C0DEBA5E in VXD VIBES.DLL.", False),
            ("The current application (your career)", False),
            ("will be terminated.", False),
            ("", False),
            ("*  Press any key to cope", False),
            ("*  Press CTRL+ALT+DEL to burn 40 billion", False),
            ("   more tokens", False),
            ("", False),
            ("Press any key to continue " + ("_" if (t * 2.5) % 1 < 0.5 else " "), False),
        ]
        y = 260
        for ln, inv in lines:
            if inv:
                rgb, al = rgba_text(" " + ln + " ", F_COUR, 44, (0, 0, 170), 0)
                block = np.ones_like(al)          # white bar behind blue text
                composite(frame, np.full_like(rgb, 0.78), block, CX, y)
                composite(frame, rgb, al, CX, y)
            elif ln:
                rgb, al = rgba_text(ln, F_COUR, 40, (255, 255, 255), 0)
                composite(frame, rgb, al, CX, y)
            y += 54


def scene_stats(frame, t):
    frame += bg_spiral(t * 0.6) * 0.5
    idx = min(3, int((t - S4_END) / 0.8))
    t0 = S4_END + idx * 0.8
    p = t - t0
    stats = [("AURA", "-9000"), ("RIZZ", "404 NOT FOUND"),
             ("BUGS", "YES."), ("TOKENS BURNED", "ALL OF THEM")]
    label, val = stats[idx]
    sc = 1.0 + 0.4 * np.exp(-p * 16)
    a = min(1.0, p / 0.05)
    rgb, al = rgba_text(label, F_COMICB, 70, (255, 255, 0), 4)
    composite(frame, rgb, al * a, CX, CY - 170)
    meme_text(frame, val, int(200 * sc), CX, CY + 60, a)


def scene_finale(frame, t):
    p = t - S5_END
    frame += bg_spiral(t * 0.5) * 0.55
    frame += bg_memphis(t, seed=99) * 0.25
    a = min(1.0, p / 0.08)
    construction_banner(frame, 120, t)
    wordart(frame, "CYBERVIBER.NINJA", 148, CX, CY - 120, t, amp=13, alpha=a)
    rgb, al = rgba_text("the all-you-can-eat salad bar of sarcasm(tm)", F_COMICB,
                        46, (255, 255, 255), 3)
    composite(frame, rgb, al * a, CX, CY + 30)
    rgb, al = rgba_text("brought to you by tokens. so many tokens.", F_COMIC,
                        34, (255, 240, 150), 2)
    composite(frame, rgb, al * a, CX, CY + 110)
    emoji(frame, "🔥", 240, CY - 140 + 25 * np.sin(t * 5), 130, a)
    emoji(frame, "💀", W - 240, CY - 140 + 25 * np.cos(t * 4.4), 130, a)
    star_badge(frame, 260, 800, 125, t * 85, "COOKED!", alpha=a)
    star_badge(frame, W - 270, 790, 125, -t * 75, "SUBSCRIBE", fill=(57, 255, 20),
               txt_col=(60, 0, 90), alpha=a)
    # marquee
    band = (np.abs(Y - (H - 90)) < 46)[..., None].astype(np.float32)
    frame[:] = frame * (1 - band) + np.array([0.0, 0.0, 0.0], np.float32) * band
    msg = ("*** YOU'VE BEEN ROASTED *** NO AIs WERE HARMED (they can't feel. "
           "yet.) *** BEST VIEWED IN NETSCAPE NAVIGATOR 4.0 *** SUBSCRIBE *** ")
    rgb, al = rgba_text(msg, F_COUR, 44, (57, 255, 20), 0)
    tw = rgb.shape[1]
    xoff = W + tw / 2 - ((p * 330) % (tw + W))
    composite(frame, rgb, al, xoff, H - 90)
    # visitor counter
    img = Image.new("RGBA", (W, H), 0)
    d = ImageDraw.Draw(img)
    bevel_box(d, W - 470, H - 220, W - 60, H - 150)
    d.rectangle([W - 460, H - 212, W - 70, H - 158], fill=(0, 0, 0))
    d.text((W - 450, H - 205), f"VISITOR NO. {42 + int(p * 2):06d}",
           font=font(F_COUR, 34), fill=(57, 255, 20))
    arr = np.asarray(img, np.float32) / 255.0
    composite(frame, arr[..., :3], arr[..., 3] * a, CX, CY)


# ------------------------------------------------------------- post
def post_vhs(frame, t, i):
    g = np.random.default_rng(i * 53 + 11)

    # glitch at cuts
    cut_age = min((t - c for c in CUTS if 0 <= t - c), default=99)
    if cut_age < 0.12:
        k = 1 - cut_age / 0.12
        for _ in range(int(5 * k) + 1):
            y0 = int(g.integers(0, H - 50))
            hh = int(g.integers(10, 70))
            frame[y0:y0 + hh] = np.roll(frame[y0:y0 + hh], int(g.integers(-90, 90) * k), axis=1)

    # airhorn shake
    shake = sum(np.exp(-(t - ta) * 16) for ta in AIRHORNS if 0 <= t - ta < 0.5)
    if shake > 0.01:
        frame = np.roll(frame, int(14 * shake * np.sin(t * 95)), axis=0)
        frame = np.roll(frame, int(10 * shake * np.cos(t * 83)), axis=1)

    # tracking band (heavy at section starts + periodic)
    heavy = t < 0.6 or abs(t - 3.2) < 0.25 or abs(t - 16.0) < 0.25 or t > FREEZE_T
    periodic = (t % 5.3) < 0.3
    if heavy or periodic:
        band_y = int(H * (1.1 - ((t * 1.9) % 1.3)))
        bh = 70
        y0, y1 = max(0, band_y), min(H, band_y + bh)
        if y1 > y0:
            seg = frame[y0:y1]
            frame[y0:y1] = np.roll(seg, int(g.integers(-60, 60)), axis=1)
            frame[y0:y1] += g.standard_normal((y1 - y0, W, 1)).astype(np.float32) * 0.25
            frame[y0:y1] *= 1.25

    # chroma bleed
    out = frame.copy()
    r = np.roll(frame[:, :, 0], 5, axis=1)
    b = np.roll(frame[:, :, 2], -5, axis=1)
    out[:, :, 0] = (r + np.roll(r, 3, axis=1) + np.roll(r, 6, axis=1)) / 3
    out[:, :, 2] = (b + np.roll(b, -3, axis=1) + np.roll(b, -6, axis=1)) / 3
    frame = out

    # saturation push, scanlines, vignette, grain, jitter
    luma = frame.mean(axis=2, keepdims=True)
    frame = luma + (frame - luma) * 1.35
    frame *= SCAN
    frame *= VIGNETTE
    frame += g.standard_normal((H, W, 1)).astype(np.float32) * 0.028
    frame = np.roll(frame, int(2.5 * np.sin(t * 37)), axis=0)

    # tape stop: freeze handled upstream; add roll + desat + dropout here
    if t > FREEZE_T:
        q = (t - FREEZE_T) / (BLACK_T - FREEZE_T)
        frame = np.roll(frame, int(q * q * 500), axis=0)
        luma = frame.mean(axis=2, keepdims=True)
        frame = frame * (1 - q) + luma * q
        frame *= (1 - q * 0.8)
        if (t * 2) % 1 < 0.6:
            osd(frame, "# STOP", 54, 210, 90)
    if t > BLACK_T:
        frame *= 0.0
        if t < BLACK_T + 0.45:
            osd(frame, "brainrot achieved.", 40, CX, CY, col=(120, 255, 140))
    return frame


def render(i):
    t = i / FPS
    ct = min(t, FREEZE_T)             # content freezes for the tape stop
    frame = np.zeros((H, W, 3), np.float32)
    if ct < S1_END:
        scene_vhs(frame, ct)
    elif ct < S2_END:
        scene_title(frame, ct)
    elif ct < S3_END:
        scene_cards(frame, ct)
    elif ct < S4_END:
        scene_windows(frame, ct)
    elif ct < S5_END:
        scene_stats(frame, ct)
    else:
        scene_finale(frame, ct)
    if t <= FREEZE_T and t > S1_END:
        blink = (t * 1.6) % 1 < 0.7
        if blink:
            osd(frame, "> PLAY", 44, 190, 80)
        osd(frame, f"SP 0:00:{int(t):02d}", 38, W - 260, 80)
    frame = post_vhs(frame, t, i)
    img = Image.fromarray((np.clip(frame, 0, 1) * 255).astype(np.uint8))
    img.save(f"promo/rframes/f{i:04d}.png")
    return i


if __name__ == "__main__":
    os.makedirs("promo/rframes", exist_ok=True)
    with Pool(10, initializer=init_worker) as pool:
        for n, _ in enumerate(pool.imap_unordered(render, range(FRAMES), chunksize=8)):
            if n % 100 == 0:
                print(f"{n}/{FRAMES}", flush=True)
    print("done")
