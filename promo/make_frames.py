#!/usr/bin/env python3
"""Frame renderer for the cyberviber.ninja trailer.

1920x1080 @ 30fps, ~25s, beat-locked to make_audio.py (125 BPM, BAR=1.92s).
numpy for fields, Pillow for type + blur. Renders with multiprocessing.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from multiprocessing import Pool

W, H = 1920, 1080
FPS = 30
BEAT = 0.48
BAR = 1.92
TOTAL = 13 * BAR                      # 24.96
FRAMES = int(round(TOTAL * FPS))      # 749
LB = 138                              # letterbox bar height (2.39:1)
CX, CY = W / 2, H / 2

S1_END, S2_END, S3_END, S4_END = 3.84, 7.68, 15.36, 19.20
CUTS = [3.84, 5.12, 6.40, 7.68, 15.36, 16.32, 17.28, 18.24, 19.20]

F_IMPACT = "/System/Library/Fonts/Supplemental/Impact.ttf"
F_BLACK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
F_FUTURA = "/System/Library/Fonts/Supplemental/Futura.ttc"
F_MENLO = "/System/Library/Fonts/Menlo.ttc"

CYAN = np.array([0.05, 0.95, 1.0], np.float32)
MAGENTA = np.array([1.0, 0.15, 0.75], np.float32)
WHITE = np.array([1.0, 1.0, 1.0], np.float32)
GREEN = np.array([0.4, 1.0, 0.55], np.float32)

DEMO_TITLES = [
    ("DIV VADERS", CYAN), ("RUG PULL", MAGENTA), ("MATRIX RAIN", GREEN),
    ("PLASMA", CYAN), ("KEFRENS BARS", MAGENTA), ("SCREAM INTO THE VOID", CYAN),
    ("THE <DIV> O' MATIC 9000", MAGENTA), ("CLAUDE-LIZA v20.26", CYAN),
]

# ------------------------------------------------------------- worker state
X = Y = VIGNETTE = SCAN = None
STREAK_ANG = STREAK_PH = None
_fonts = {}
_masks = {}


def init_worker():
    global X, Y, VIGNETTE, SCAN, STREAK_ANG, STREAK_PH
    ys, xs = np.mgrid[0:H, 0:W]
    X = xs.astype(np.float32)
    Y = ys.astype(np.float32)
    r = np.sqrt(((X - CX) / (W / 2)) ** 2 + ((Y - CY) / (H / 2)) ** 2)
    VIGNETTE = (1.0 - 0.42 * np.clip(r, 0, 1.4) ** 2.2).astype(np.float32)[..., None]
    SCAN = (1.0 - 0.13 * (0.5 + 0.5 * np.sin(Y * (2 * np.pi / 3.0))))[..., None].astype(np.float32)
    g = np.random.default_rng(99)
    STREAK_ANG = g.uniform(0, 2 * np.pi, 70)
    STREAK_PH = g.uniform(0, 900, 70)


def font(path, px):
    key = (path, px)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, px)
    return _fonts[key]


def text_mask(text, path, px, spacing=0):
    """Rendered text -> (float mask h*w, w, h). Cached."""
    px = max(8, int(px))
    key = (text, path, px, spacing)
    if key in _masks:
        return _masks[key]
    f = font(path, px)
    pad = px // 2
    if spacing:
        widths = [f.getbbox(c)[2] for c in text]
        tw = int(sum(widths) + spacing * (len(text) - 1))
    else:
        bb = f.getbbox(text)
        tw = bb[2] - bb[0]
    bb2 = f.getbbox(text if not spacing else "Hg")
    th = bb2[3] - bb2[1]
    img = Image.new("L", (tw + 2 * pad, th + 2 * pad), 0)
    d = ImageDraw.Draw(img)
    if spacing:
        x = pad
        for c, cw in zip(text, widths):
            d.text((x, pad - bb2[1]), c, font=f, fill=255)
            x += cw + spacing
    else:
        d.text((pad - f.getbbox(text)[0], pad - bb2[1]), text, font=f, fill=255)
    m = np.asarray(img, np.float32) / 255.0
    if len(_masks) > 400:
        _masks.clear()
    _masks[key] = m
    return m


def blur_mask(m, radius):
    img = Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8))
    return np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), np.float32) / 255.0


def stamp(frame, m, color, cx, cy, alpha=1.0):
    """Additively stamp mask m (h,w) tinted `color`, centred at (cx, cy)."""
    h, w = m.shape
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    sx0, sy0 = max(0, -x0), max(0, -y0)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x0 + w - sx0), min(H, y0 + h - sy0)
    if x1 <= x0 or y1 <= y0:
        return
    sub = m[sy0:sy0 + (y1 - y0), sx0:sx0 + (x1 - x0), None]
    frame[y0:y1, x0:x1] += sub * (np.asarray(color, np.float32) * alpha)


def glow_text(frame, text, path, px, cx, cy, color, alpha=1.0, glow=1.0,
              spacing=0, core=WHITE, core_amt=0.55, shade=0.0):
    m = text_mask(text, path, px, spacing)
    if shade > 0:
        sh = blur_mask(m, max(4, px * 0.22))
        h, w = sh.shape
        x0, y0 = int(cx - w / 2), int(cy - h / 2)
        sx0, sy0 = max(0, -x0), max(0, -y0)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(W, x0 + w - sx0), min(H, y0 + h - sy0)
        if x1 > x0 and y1 > y0:
            sub = sh[sy0:sy0 + (y1 - y0), sx0:sx0 + (x1 - x0), None]
            frame[y0:y1, x0:x1] *= 1.0 - sub * shade * alpha
    if glow > 0:
        stamp(frame, blur_mask(m, max(2, px * 0.10)), color, cx, cy, alpha * 0.55 * glow)
        stamp(frame, blur_mask(m, max(6, px * 0.30)), color, cx, cy, alpha * 0.30 * glow)
    stamp(frame, m, color * (1 - core_amt) + core * core_amt, cx, cy, alpha)


def beat_pulse(t, decay=4.0):
    if t < S1_END:
        return 0.0
    return float(np.exp(-decay * ((t / BEAT) % 1.0)))


# ------------------------------------------------------------- backdrops
def synthwave_bg(t, intensity=1.0, sun_scale=1.0, speed=260.0):
    """Neon grid floor + sun + stars. Returns float32 (H,W,3)."""
    frame = np.zeros((H, W, 3), np.float32)
    horizon = H * 0.55
    bp = beat_pulse(t)

    # sky gradient: deep violet -> hot pink at the horizon
    skyf = np.clip(Y / horizon, 0, 1)[..., None]
    sky_top = np.array([0.045, 0.0, 0.12], np.float32)
    sky_bot = np.array([0.35, 0.03, 0.28], np.float32)
    frame += (sky_top + (sky_bot - sky_top) * skyf ** 2.2) * (Y < horizon)[..., None]

    # floor base
    floor_col = np.array([0.06, 0.0, 0.10], np.float32)
    frame += floor_col * (Y >= horizon)[..., None]

    # stars (twinkling, fixed constellation)
    g = np.random.default_rng(7)
    sx = g.uniform(0, W, 240).astype(int)
    sy = g.uniform(0, horizon * 0.92, 240).astype(int)
    tw = 0.4 + 0.6 * np.sin(t * 3.0 + g.uniform(0, 6.28, 240)) ** 2
    frame[sy, sx] += WHITE * tw[:, None] * 0.8
    frame[sy, np.minimum(sx + 1, W - 1)] += WHITE * tw[:, None] * 0.35

    # the sun
    sun_r = 190.0 * sun_scale
    sun_cy = horizon - 55.0 * sun_scale
    d = np.sqrt((X - CX) ** 2 + (Y - sun_cy) ** 2)
    sun = np.clip(1.0 - (d - sun_r) / 6.0, 0, 1)
    yf = np.clip((Y - (sun_cy - sun_r)) / (2 * sun_r), 0, 1)
    sun_col = (np.array([1.0, 0.88, 0.35], np.float32)[None, None] * (1 - yf[..., None])
               + np.array([1.0, 0.15, 0.55], np.float32)[None, None] * yf[..., None])
    slat = (np.sin(Y * 0.11 - t * 1.2) > 1.0 - 1.3 * yf) & (Y > sun_cy)
    sun = sun * ~slat
    frame += sun[..., None] * sun_col * (0.95 + 0.15 * bp)
    halo = np.clip(1.0 - d / (sun_r * 2.6), 0, 1) ** 2
    frame += halo[..., None] * np.array([0.5, 0.1, 0.3], np.float32) * 0.5

    # perspective grid
    fy = Y - horizon
    below = fy > 1
    fy_safe = np.where(below, fy, 1.0)
    u = (X - CX) / fy_safe * 1.9
    v = 5200.0 / fy_safe + t * speed / 100.0
    du = np.abs(((u + 0.5) % 1.0) - 0.5) / np.clip(np.abs(u) * 0.04 + 0.014, 0.008, 0.08)
    dv = np.abs(((v + 0.5) % 1.0) - 0.5) / 0.10
    line = np.maximum(np.clip(1 - du, 0, 1), np.clip(1 - dv, 0, 1)) ** 2
    depth_fade = np.clip(fy / (H - horizon), 0, 1) ** 0.5
    grid = line * below * depth_fade * (0.75 + 0.5 * bp)
    frame += grid[..., None] * MAGENTA * 1.1
    # cyan glow bleeding up from the horizon
    hglow = np.clip(1.0 - np.abs(Y - horizon) / 60.0, 0, 1) ** 2
    frame += hglow[..., None] * CYAN * (0.35 + 0.25 * bp)

    return frame * intensity


def warp_streaks(frame, t, amount=1.0):
    ov = Image.new("RGB", (W, H), 0)
    d = ImageDraw.Draw(ov)
    for ang, ph in zip(STREAK_ANG, STREAK_PH):
        r2 = (t * 700 + ph * 3) % 1100 + 90
        r1 = r2 - (40 + r2 * 0.25)
        ca, sa = np.cos(ang), np.sin(ang) * 0.55
        a = int(90 * amount * min(1, r2 / 500))
        d.line([(CX + ca * r1, CY + sa * r1), (CX + ca * r2, CY + sa * r2)],
               fill=(a // 2, a, a), width=2)
    frame += np.asarray(ov, np.float32) / 255.0


# ------------------------------------------------------------- scenes
def scene_ident(frame, t):
    """0 - 3.84  CRT power-on -> studio card."""
    g = np.random.default_rng(int(t * 977) % 100000)
    if t < 0.45:
        h = 1.5 + (t / 0.45) ** 2.6 * H
        band = np.exp(-((Y - CY) / max(h, 1.5)) ** 2)
        frame += band[..., None] * WHITE * np.clip(1.2 - t, 0.4, 1.2)
    vis = np.clip((t - 0.35) / 0.25, 0, 1)
    if vis <= 0:
        return
    flick = 0.93 + 0.07 * g.random()
    a = vis * flick
    glow_text(frame, "CYBERVIBER", F_FUTURA, 128, CX, CY - 95, CYAN, a)
    glow_text(frame, "STUDIOS", F_FUTURA, 54, CX, CY + 15, MAGENTA, a, spacing=42)
    if t > 1.35:
        a2 = min(1, (t - 1.35) / 0.3) * flick
        glow_text(frame, "presents", F_MENLO, 34, CX, CY + 120, WHITE, a2 * 0.85, glow=0.4)
    if t > 2.3:
        a3 = min(1, (t - 2.3) / 0.25) * flick
        glow_text(frame, "a $5,000,000 production", F_MENLO, 30, CX, CY + 205, GREEN, a3 * 0.9, glow=0.5)
        glow_text(frame, "(*rounded up from $0)", F_MENLO, 22, CX, CY + 255, GREEN, a3 * 0.55, glow=0.3)


def slam_card(frame, t0, t, lines, accent):
    """Big Impact-type card that punches in at t0."""
    p = t - t0
    sc = 1.0 + 0.35 * np.exp(-p * 14)                 # slams from big to rest
    a = min(1.0, p / 0.06)
    # sweeping diagonal sheen
    sheen = np.clip(1 - np.abs((X + Y * 0.6) / W - (p * 1.4 % 2)), 0, 1) ** 8
    frame += sheen[..., None] * accent * 0.10
    n = len(lines)
    for i, (txt, path, px, col) in enumerate(lines):
        cy = CY + (i - (n - 1) / 2) * (px * 1.55)
        glow_text(frame, txt, path, int(px * sc), CX, cy, col * 0.92, a,
                  glow=0.35, core_amt=0.3)


def scene_cards(frame, t):
    """3.84 - 7.68  three snark cards."""
    idx = min(2, int((t - S1_END) / 1.28))
    t0 = S1_END + idx * 1.28
    texts = [
        [("NO FRAMEWORKS.", F_IMPACT, 150, WHITE)],
        [("NO DEPENDENCIES.", F_IMPACT, 150, WHITE)],
        [("NO ADULT", F_IMPACT, 140, WHITE), ("SUPERVISION.", F_IMPACT, 140, MAGENTA)],
    ]
    accents = [CYAN, MAGENTA, CYAN]
    bp = beat_pulse(t)
    frame += np.array([0.03, 0.0, 0.06], np.float32) * (1 + bp)
    slam_card(frame, t0, t, texts[idx], accents[idx])


def scene_warp(frame, t):
    """7.68 - 15.36  hyperspace over the grid, demo titles flying past."""
    p = (t - S2_END) / (S3_END - S2_END)
    frame += synthwave_bg(t, intensity=1.0, sun_scale=1.0 + p * 0.35,
                          speed=260 + 340 * p)
    warp_streaks(frame, t, amount=0.5 + p)
    for k, (title, col) in enumerate(DEMO_TITLES):
        spawn = S2_END + 0.12 + k * 0.93
        life = 1.5
        q = (t - spawn) / life
        if not (0 <= q < 1):
            continue
        px = 4 * int((26 * np.exp(2.35 * q)) / 4 + 1)
        a = float(np.sin(np.pi * q) ** 0.7)
        dx = [-0.26, 0.28, -0.22, 0.24][k % 4] * W * (0.5 + 0.9 * q)
        dy = [-0.30, 0.24, 0.32, -0.26][k % 4] * H * (0.5 + 0.9 * q)
        glow_text(frame, title, F_BLACK, px, CX + dx, CY + dy, col, a, shade=0.9)


def scene_stats(frame, t):
    """15.36 - 19.20  rapid-fire stat cards over a dimmed grid."""
    frame += synthwave_bg(t, intensity=0.20, speed=420)
    idx = min(3, int((t - S3_END) / 0.96))
    t0 = S3_END + idx * 0.96
    stats = [("38", "DEMOS"), ("0", "FRAMEWORKS"), ("100%", "VIBES"), ("∞", "SCANLINES")]
    num, label = stats[idx]
    p = t - t0
    sc = 1.0 + 0.4 * np.exp(-p * 15)
    a = min(1.0, p / 0.05)
    col = CYAN if idx % 2 == 0 else MAGENTA
    glow_text(frame, num, F_BLACK, int(230 * sc), CX, CY - 70, col, a, core_amt=0.35)
    glow_text(frame, label, F_FUTURA, 64, CX, CY + 135, WHITE, a, spacing=26, glow=0.5)


def scene_finale(frame, t):
    """19.20 - end  chrome logo slam + taglines."""
    p = t - S4_END
    frame += synthwave_bg(t, intensity=0.85, sun_scale=1.5, speed=150)
    a = min(1.0, p / 0.05)
    sc = 1.0 + 0.5 * np.exp(-p * 12)

    # shockwave ring
    if p < 0.9:
        rr = 80 + p * 1600
        d = np.sqrt((X - CX) ** 2 + ((Y - CY) * 1.7) ** 2)
        ring = np.exp(-((d - rr) / 42.0) ** 2) * (1 - p / 0.9)
        frame += ring[..., None] * WHITE * 0.8

    # cinematic dim strip behind the logo so the sun doesn't wash it out
    px = int(148 * sc)
    m = text_mask("CYBERVIBER.NINJA", F_BLACK, px)
    h, w = m.shape
    band_m = np.exp(-((Y - (CY - 30)) / (h * 0.62)) ** 4)[..., None]
    frame *= 1.0 - 0.62 * band_m * a
    yf = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    top = np.clip(yf / 0.46, 0, 1)[..., None]
    chrome = ((np.array([0.80, 0.97, 1.0], np.float32) * (1 - top)
               + np.array([0.10, 0.42, 0.95], np.float32) * top))
    lowf = np.clip((yf - 0.52) / 0.48, 0, 1)[..., None]
    low = (np.array([1.0, 0.45, 0.10], np.float32) * (1 - lowf)
           + np.array([1.0, 0.92, 0.60], np.float32) * lowf)
    band = np.clip(1 - np.abs(yf - 0.49) / 0.045, 0, 1)[..., None]
    grad = np.where(yf[..., None] < 0.49, chrome, low)
    grad = grad * (1 - band * 0.9) + np.array([0.03, 0.0, 0.08], np.float32) * band
    colored = m[..., None] * grad
    bp = beat_pulse(t)
    gl = blur_mask(m, px * 0.16)
    stamp(frame, gl, MAGENTA * 0.7 + CYAN * 0.3, CX, CY - 30, a * (0.7 + 0.5 * bp))
    x0, y0 = int(CX - w / 2), int(CY - 30 - h / 2)
    xs0, ys0 = max(0, x0), max(0, y0)
    frame[ys0:ys0 + h, xs0:xs0 + w] += colored[: H - ys0, : W - xs0] * a

    if p > 1.9:
        a2 = min(1, (p - 1.9) / 0.3)
        glow_text(frame, "Your GPU called. It's scared.", F_MENLO, 40, CX, CY + 150,
                  GREEN, a2, glow=0.6)
    if p > 2.6:
        a3 = min(1, (p - 2.6) / 0.3)
        glow_text(frame, "CYBERSPACE • VIBE CODE • 8BIT RETRO • SHIT POSTS",
                  F_FUTURA, 30, CX, CY + 235, MAGENTA, a3 * 0.9, spacing=6, glow=0.5)


# ------------------------------------------------------------- post fx
def post(frame, t, i):
    g = np.random.default_rng(i * 31 + 7)

    # glitch burst right after every hard cut
    cut_age = min((t - c for c in CUTS if 0 <= t - c), default=99)
    ca_px = 2
    if cut_age < 0.14:
        k = 1 - cut_age / 0.14
        ca_px = int(2 + 9 * k)
        for _ in range(int(6 * k) + 1):
            y0 = g.integers(0, H - 40)
            hh = int(g.integers(8, 60))
            off = int(g.integers(-70, 70) * k)
            frame[y0:y0 + hh] = np.roll(frame[y0:y0 + hh], off, axis=1)
        if g.random() < 0.5 * k:
            frame = frame[:, ::-1] * 0.9 + frame * 0.1
        frame = np.roll(frame, int(g.integers(-8, 9) * k), axis=0)

    # bloom
    img = Image.fromarray((np.clip(frame, 0, 1) * 255).astype(np.uint8))
    small = img.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(7))
    bloom = np.asarray(small.resize((W, H), Image.BILINEAR), np.float32) / 255.0
    frame = frame + bloom ** 2 * 0.85

    # chromatic aberration
    ca = ca_px + int(2 * beat_pulse(t))
    out = frame.copy()
    out[:, :, 0] = np.roll(frame[:, :, 0], -ca, axis=1)
    out[:, :, 2] = np.roll(frame[:, :, 2], ca, axis=1)
    frame = out

    # scanlines, vignette, grain, flicker
    frame *= SCAN
    frame *= VIGNETTE
    frame += g.standard_normal((H, W, 1)).astype(np.float32) * 0.014
    frame *= 0.97 + 0.03 * np.sin(t * 52.0)

    # fade to black at the very end
    if t > TOTAL - 0.7:
        frame *= max(0.0, (TOTAL - t) / 0.7)

    # letterbox
    frame[:LB] = 0
    frame[-LB:] = 0
    return frame


def render(i):
    t = i / FPS
    frame = np.zeros((H, W, 3), np.float32)
    if t < S1_END:
        scene_ident(frame, t)
    elif t < S2_END:
        scene_cards(frame, t)
    elif t < S3_END:
        scene_warp(frame, t)
    elif t < S4_END:
        scene_stats(frame, t)
    else:
        scene_finale(frame, t)
    frame = post(frame, t, i)
    img = Image.fromarray((np.clip(frame, 0, 1) * 255).astype(np.uint8))
    img.save(f"promo/frames/f{i:04d}.png")
    return i


if __name__ == "__main__":
    os.makedirs("promo/frames", exist_ok=True)
    with Pool(10, initializer=init_worker) as pool:
        for n, _ in enumerate(pool.imap_unordered(render, range(FRAMES), chunksize=8)):
            if n % 75 == 0:
                print(f"{n}/{FRAMES} frames", flush=True)
    print(f"done: {FRAMES} frames")
