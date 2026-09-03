#!/usr/bin/env python3
"""Synthwave trailer score for the cyberviber.ninja promo.

125 BPM, A minor, ~25s. Pure numpy synthesis -> stereo WAV.
Beat grid is shared with make_frames.py: BAR = 1.92s, TOTAL = 13 bars.
"""
import numpy as np
import wave

SR = 44100
BPM = 125.0
BEAT = 60.0 / BPM          # 0.48 s
BAR = 4 * BEAT             # 1.92 s
BARS = 13
TOTAL = BARS * BAR         # 24.96 s
N = int(TOTAL * SR)

rng = np.random.default_rng(1337)
t_all = np.arange(N) / SR


def sec(x):
    return int(x * SR)


def add(buf, start, sig):
    i = sec(start)
    j = min(N, i + len(sig))
    if i < N:
        buf[i:j] += sig[: j - i]


def env_ad(n, a, d, curve=4.0):
    """Attack/decay envelope, exponential decay."""
    at = np.linspace(0, 1, max(1, sec(a)))
    dt = np.exp(-curve * np.linspace(0, 1, max(1, n - len(at))))
    e = np.concatenate([at, dt])[:n]
    return e


def lowpass(sig, cutoff):
    """One-pole lowpass, cheap and cheerful."""
    a = np.clip(2 * np.pi * cutoff / SR, 0, 0.99)
    out = np.empty_like(sig)
    y = 0.0
    # vectorised one-pole via lfilter-free scan is slow in python; use FFT brickwall-ish
    spec = np.fft.rfft(sig)
    freqs = np.fft.rfftfreq(len(sig), 1 / SR)
    spec *= 1.0 / (1.0 + (freqs / max(cutoff, 20.0)) ** 2)
    return np.fft.irfft(spec, len(sig))


def saw(freq, n, detune=0.0):
    ph = np.cumsum(np.full(n, freq * (1 + detune) / SR))
    return 2.0 * (ph % 1.0) - 1.0


def square(freq, n, duty=0.5):
    ph = np.cumsum(np.full(n, freq / SR)) % 1.0
    return np.where(ph < duty, 1.0, -1.0)


def supersaw(freq, n, voices=5, spread=0.006):
    out = np.zeros(n)
    for v in range(voices):
        det = spread * (v - (voices - 1) / 2)
        out += saw(freq, n, det)
    return out / voices


# ---------------------------------------------------------------- drums
def kick(n=None):
    n = n or sec(0.35)
    tt = np.arange(n) / SR
    f = 150 * np.exp(-tt * 22) + 42
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9)
    click = rng.standard_normal(sec(0.01)) * np.exp(-np.arange(sec(0.01)) / SR * 800)
    out = body
    out[: len(click)] += click * 0.4
    return out * 0.95


def snare(n=None):
    n = n or sec(0.45)
    tt = np.arange(n) / SR
    noise = rng.standard_normal(n) * np.exp(-tt * 11)
    body = np.sin(2 * np.pi * 185 * tt) * np.exp(-tt * 25) * 0.6
    s = noise * 0.8 + body
    # gated 80s tail: hold the reverb-ish noise then slam shut
    gate_len = sec(0.28)
    tail = rng.standard_normal(gate_len) * 0.35
    tail *= np.linspace(1, 0.75, gate_len)
    tail[-sec(0.02):] *= np.linspace(1, 0, sec(0.02))
    s[sec(0.05): sec(0.05) + gate_len] += tail[: max(0, n - sec(0.05))][: gate_len]
    return s * 0.8


def hat(open_=False):
    n = sec(0.18 if open_ else 0.05)
    tt = np.arange(n) / SR
    h = rng.standard_normal(n) * np.exp(-tt * (18 if open_ else 90))
    # crude highpass: subtract lowpassed copy
    return (h - lowpass(h, 5000)) * 0.5


def impact():
    n = sec(2.2)
    tt = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (48 * np.exp(-tt * 1.2) + 30) * tt) * np.exp(-tt * 1.8)
    crash = rng.standard_normal(n) * np.exp(-tt * 2.5)
    crash = crash - lowpass(crash, 2500)
    return boom * 1.1 + crash * 0.5


def riser(dur):
    n = sec(dur)
    tt = np.arange(n) / SR
    nz = rng.standard_normal(n)
    swept = lowpass(nz, 400)  # base rumble
    bright = nz - lowpass(nz, 800)
    mix = swept * (1 - tt / dur) + bright * (tt / dur) ** 2
    return mix * np.linspace(0.05, 0.9, n) ** 1.5


# ---------------------------------------------------------------- notes
A1, C2, D2, E2, F1, G1 = 55.0, 65.41, 73.42, 82.41, 43.65, 49.0
CHORDS = {  # per-bar progression: Am F C G
    0: [110.0, 130.81, 164.81],   # Am
    1: [87.31, 110.0, 130.81],    # F
    2: [130.81, 164.81, 196.0],   # C
    3: [98.0, 123.47, 146.83],    # G
}
BASS = {0: A1, 1: F1, 2: C2, 3: G1}
ARP = {0: [220.0, 261.63, 329.63, 440.0],
       1: [174.61, 220.0, 261.63, 349.23],
       2: [261.63, 329.63, 392.0, 523.25],
       3: [196.0, 246.94, 293.66, 392.0]}

kick_track = np.zeros(N)
snare_track = np.zeros(N)
hat_track = np.zeros(N)
bass_track = np.zeros(N)
pad_track = np.zeros(N)
arp_track = np.zeros(N)
fx_track = np.zeros(N)

kick_times = []

for bar in range(BARS):
    bt = bar * BAR
    prog = bar % 4

    # ---- pads: everywhere except the very end tail
    if bar < 12:
        n = sec(BAR * 1.05)
        chord = np.zeros(n)
        for f in CHORDS[prog]:
            chord += supersaw(f, n, voices=5, spread=0.008)
        chord = lowpass(chord, 900 + 500 * min(1, bar / 4))
        e = np.ones(n)
        e[: sec(0.05)] = np.linspace(0, 1, sec(0.05))
        e[-sec(0.15):] *= np.linspace(1, 0.6, sec(0.15))
        add(pad_track, bt, chord * e * 0.16)

    # ---- kick: bars 2..11, four on the floor
    if 2 <= bar < 12:
        for b in range(4):
            kt = bt + b * BEAT
            add(kick_track, kt, kick())
            kick_times.append(kt)

    # ---- bass: bars 2..11, driving 8ths
    if 2 <= bar < 12:
        for e8 in range(8):
            st = bt + e8 * BEAT / 2
            n = sec(BEAT / 2 * 0.95)
            b = saw(BASS[prog], n) + saw(BASS[prog], n, 0.004)
            b = lowpass(b, 350)
            b *= env_ad(n, 0.004, 0.4, curve=2.0)
            add(bass_track, st, b * 0.5)

    # ---- hats: bars 2..11 offbeat 8ths, 16ths from bar 4
    if 2 <= bar < 12:
        div = 4 if bar >= 4 else 2
        for k in range(4 * div // 2):
            st = bt + (k + 0.5) * BEAT * 2 / div
            add(hat_track, st, hat(open_=(k % 4 == 3)))

    # ---- snare: beats 2 & 4, bars 4..11
    if 4 <= bar < 12:
        add(snare_track, bt + 1 * BEAT, snare())
        add(snare_track, bt + 3 * BEAT, snare())

    # ---- arp: 16ths, bars 4..11
    if 4 <= bar < 12:
        notes = ARP[prog]
        for s16 in range(16):
            st = bt + s16 * BEAT / 4
            f = notes[s16 % len(notes)] * (2 if s16 % 8 >= 6 else 1)
            n = sec(BEAT / 4 * 1.1)
            a = square(f, n, duty=0.35)
            a = lowpass(a, 2800)
            a *= env_ad(n, 0.002, 5.0)
            add(arp_track, st, a * 0.16)

# ---- FX: risers into the drop (bar 4) and finale (bar 10), impacts on both
add(fx_track, 2 * BAR, riser(2 * BAR) * 0.7)
add(fx_track, 4 * BAR, impact() * 0.9)
add(fx_track, 8.5 * BAR, riser(1.5 * BAR) * 0.8)
add(fx_track, 10 * BAR, impact() * 1.1)

# ---- finale chord: big Am stab at bar 10 held to the end
n = sec(3 * BAR)
fin = np.zeros(n)
for f in [110.0, 130.81, 164.81, 220.0, 261.63]:
    fin += supersaw(f, n, voices=7, spread=0.01)
fin = lowpass(fin, 1800)
e = np.ones(n)
e[: sec(0.02)] = np.linspace(0, 1, sec(0.02))
e *= np.exp(-np.arange(n) / SR * 0.55)
add(pad_track, 10 * BAR, fin * e * 0.22)

# ---------------------------------------------------------------- mix
# sidechain pump on sustained tracks
duck = np.ones(N)
dip_n = sec(0.30)
dip = 1 - 0.65 * np.exp(-np.linspace(0, 6, dip_n))
dip = np.concatenate([np.full(sec(0.02), 0.35), dip])[:dip_n]
for kt in kick_times:
    i = sec(kt)
    j = min(N, i + dip_n)
    duck[i:j] = np.minimum(duck[i:j], dip[: j - i])

pad_track *= duck
bass_track *= duck
arp_track *= duck * 0.9 + 0.1

mono = kick_track + snare_track + hat_track + bass_track + pad_track + arp_track + fx_track

# stereo: haas-widen arp & pads, keep low end centred
left = mono.copy()
right = mono.copy()
w = sec(0.012)
side = pad_track * 0.5 + arp_track
left += np.concatenate([side[w:], np.zeros(w)]) * 0.35
right += np.concatenate([np.zeros(w), side[:-w]]) * 0.35

# master: fade edges, soft clip, normalise
fade_in = sec(0.03)
fade_out = sec(0.5)
for ch in (left, right):
    ch[:fade_in] *= np.linspace(0, 1, fade_in)
    ch[-fade_out:] *= np.linspace(1, 0, fade_out)

stereo = np.stack([left, right], axis=1)
stereo = np.tanh(stereo * 1.15)
stereo /= np.abs(stereo).max() * 1.02

pcm = (stereo * 32767).astype(np.int16)
with wave.open("promo/score.wav", "wb") as f:
    f.setnchannels(2)
    f.setsampwidth(2)
    f.setframerate(SR)
    f.writeframes(pcm.tobytes())

print(f"score.wav written: {TOTAL:.2f}s, peak {np.abs(stereo).max():.3f}")
