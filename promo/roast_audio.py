#!/usr/bin/env python3
"""AI Sizzler Reel score: dial-up -> airhorns -> 150 BPM rave -> BSOD beeps
-> harder rave + siren -> record scratch -> tape stop. Pure numpy.

Beat grid shared with roast_frames.py: BEAT=0.4, BAR=1.6, 18 bars = 28.8s.
"""
import numpy as np
import wave

SR = 44100
BEAT = 0.4
BAR = 1.6
BARS = 18
TOTAL = BARS * BAR            # 28.8
N = int(TOTAL * SR)

rng = np.random.default_rng(6969)


def sec(x):
    return int(x * SR)


def add(buf, start, sig, gain=1.0):
    i = sec(start)
    j = min(N, i + len(sig))
    if i < N:
        buf[i:j] += sig[: j - i] * gain


def lowpass(sig, cutoff):
    spec = np.fft.rfft(sig)
    freqs = np.fft.rfftfreq(len(sig), 1 / SR)
    spec *= 1.0 / (1.0 + (freqs / max(cutoff, 20.0)) ** 2)
    return np.fft.irfft(spec, len(sig))


def highpass(sig, cutoff):
    return sig - lowpass(sig, cutoff)


def env_ad(n, a, curve=5.0):
    at = np.linspace(0, 1, max(1, sec(a)))
    dt = np.exp(-curve * np.linspace(0, 1, max(1, n - len(at))))
    return np.concatenate([at, dt])[:n]


def saw(freq, n, detune=0.0):
    if np.isscalar(freq):
        freq = np.full(n, freq)
    ph = np.cumsum(freq * (1 + detune) / SR)
    return 2.0 * (ph % 1.0) - 1.0


def square(freq, n, duty=0.5):
    if np.isscalar(freq):
        freq = np.full(n, freq)
    ph = np.cumsum(freq / SR) % 1.0
    return np.where(ph < duty, 1.0, -1.0)


def sine(freq, n):
    if np.isscalar(freq):
        freq = np.full(n, freq)
    return np.sin(2 * np.pi * np.cumsum(freq) / SR)


# ---------------------------------------------------------------- toys
def dialup():
    """~3.1s of glorious 56k nostalgia."""
    out = np.zeros(sec(3.2))
    dtmf = {'1': (697, 1209), '9': (852, 1477), '7': (852, 1209),
            '5': (770, 1336), '0': (941, 1336), '4': (770, 1209)}
    t = 0.02
    for d in "1900975":
        f1, f2 = dtmf[d]
        n = sec(0.07)
        add(out, t, (sine(f1, n) + sine(f2, n)) * env_ad(n, 0.005, 2) * 0.5)
        t += 0.105
    # answer tone
    n = sec(0.4)
    add(out, 0.85, sine(2100, n) * env_ad(n, 0.01, 0.6) * 0.4)
    # FSK warble
    n = sec(1.1)
    blocks = np.repeat(rng.choice([980.0, 1650.0, 1200.0], size=n // 882 + 1), 882)[:n]
    add(out, 1.3, sine(blocks, n) * 0.35)
    add(out, 1.3, sine(blocks * 0.5, n) * 0.15)
    # broadband hiss crescendo
    n = sec(0.8)
    hiss = highpass(rng.standard_normal(n), 900) * np.linspace(0.1, 0.5, n)
    add(out, 2.4, hiss)
    return out * 0.85


def airhorn(dur):
    """The MLG classic. bwaaaaah."""
    n = sec(dur)
    tt = np.arange(n) / SR
    f = 311.0 * (1 + 0.15 * np.exp(-tt * 25)) * (1 + 0.012 * np.sin(2 * np.pi * 5.5 * tt))
    sig = saw(f, n) + saw(f, n, 0.008) + 0.5 * square(f * 2.001, n)
    sig = lowpass(sig, 2200)
    e = env_ad(n, 0.01, 1.6)
    e[-sec(0.03):] *= np.linspace(1, 0, sec(0.03))
    return sig * e * 0.5


def airhorn_triplet(buf, t):
    add(buf, t, airhorn(0.5))
    add(buf, t + 0.62, airhorn(0.18))
    add(buf, t + 0.86, airhorn(0.18))
    add(buf, t + 1.10, airhorn(0.30))


def hard_kick():
    n = sec(0.3)
    tt = np.arange(n) / SR
    f = 160 * np.exp(-tt * 24) + 45
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 7)
    return np.tanh(body * 3.2) * 0.9


def clap():
    n = sec(0.35)
    tt = np.arange(n) / SR
    c = rng.standard_normal(n) * np.exp(-tt * 14)
    for off in (0.012, 0.024):
        c[sec(off):] += rng.standard_normal(n - sec(off)) * np.exp(-tt[: n - sec(off)] * 20) * 0.7
    return highpass(c, 800) * 0.55


def hat_16():
    n = sec(0.04)
    return highpass(rng.standard_normal(n), 6000) * np.exp(-np.arange(n) / SR * 120) * 0.4


def rave_stab(freqs, dur=0.22):
    n = sec(dur)
    tt = np.arange(n) / SR
    sig = np.zeros(n)
    for f in freqs:
        bend = f * (1 + 0.06 * np.exp(-tt * 40))
        sig += saw(bend, n) + saw(bend, n, 0.01)
    sig = lowpass(sig, 3000)
    return sig * env_ad(n, 0.004, 4.5) * 0.24


def hoover(f0, dur):
    n = sec(dur)
    tt = np.arange(n) / SR
    f = f0 * (0.5 + 0.5 * np.minimum(tt / (dur * 0.4), 1.0))
    sig = np.zeros(n)
    for det in (-0.02, -0.008, 0.0, 0.009, 0.021):
        sig += saw(f, n, det)
    sig = lowpass(sig, 1800)
    e = np.ones(n)
    e[-sec(0.08):] *= np.linspace(1, 0, sec(0.08))
    return sig * e * 0.16


def sub_drop(t0, buf):
    n = sec(0.6)
    tt = np.arange(n) / SR
    f = 85 * np.exp(-tt * 4) + 28
    add(buf, t0, np.tanh(sine(f, n) * 2.5) * env_ad(n, 0.005, 1.2) * 0.9)


def error_beep():
    n = sec(0.22)
    sig = square(880, n) * 0.4 + square(660, n) * 0.3
    return lowpass(sig, 3500) * env_ad(n, 0.004, 2.0) * 0.6


def record_scratch():
    n = sec(0.65)
    tt = np.arange(n) / SR
    wob = np.abs(np.sin(2 * np.pi * 3.2 * tt + 1.2)) ** 0.5
    f = 400 + 2800 * wob
    nz = rng.standard_normal(n)
    sig = lowpass(nz * 2, 200)[:n] * 0  # placeholder base
    sig = sine(f, n) * 0.25 + highpass(nz, 1500) * wob * 0.5
    return sig * env_ad(n, 0.01, 1.0)


# ---------------------------------------------------------------- tracks
drums = np.zeros(N)
music = np.zeros(N)
fx = np.zeros(N)
kick_times = []

STAB = [220.0, 261.63, 329.63]        # Am
STAB2 = [261.63, 329.63, 440.0]
PENTA = [440.0, 523.25, 587.33, 659.26, 783.99, 880.0]

KICK_BARS = list(range(4, 10)) + list(range(12, 17))

for bar in range(BARS):
    bt = bar * BAR
    if bar in KICK_BARS:
        for b in range(4):
            kt = bt + b * BEAT
            add(drums, kt, hard_kick())
            kick_times.append(kt)
        # offbeat hats + 16ths in the harder half
        for k in range(8):
            add(drums, bt + (k + 0.5) * BEAT / 2, hat_16())
        add(drums, bt + 1 * BEAT, clap())
        add(drums, bt + 3 * BEAT, clap())
        # rave stabs
        chord = STAB if bar % 2 == 0 else STAB2
        add(music, bt + 1.5 * BEAT, rave_stab(chord))
        add(music, bt + 3.25 * BEAT, rave_stab(chord, 0.15))
        # 8-bit arp 16ths
        for s in range(16):
            st = bt + s * BEAT / 4
            f = PENTA[(s * 3 + bar) % len(PENTA)]
            n = sec(0.09)
            add(music, st, square(f, n, 0.25) * env_ad(n, 0.002, 6) * 0.05)
    # hoover riff every 4 bars in beat sections
    if bar in (5, 9, 13, 15):
        add(music, bt, hoover(440, 0.7))
        add(music, bt + 0.8, hoover(330, 0.6))

# snare roll build into the dialog scene and the scratch
for k in range(16):
    add(drums, 9 * BAR + k * BEAT / 4, clap(), gain=0.3 + 0.05 * k)
for k in range(16):
    add(drums, 16 * BAR + k * BEAT / 4, clap(), gain=0.3 + 0.05 * k)

# ---- intro
add(fx, 0.0, dialup())
airhorn_triplet(fx, 2 * BAR)          # 3.2s, over the title card
sub_drop(4 * BAR, fx)                 # beat drop 6.4
airhorn_single_times = [5 * BAR, 7 * BAR, 12 * BAR]
for t in airhorn_single_times:
    add(fx, t, airhorn(0.35), gain=0.8)

# ---- dialog scene 16.0-17.6: music already stops (no kick bars 10-11)
for k, t in enumerate([16.05, 16.45, 16.85, 17.15]):
    add(fx, t, error_beep(), gain=1.0 - k * 0.1)
# BSOD drone + riser 17.6-19.2
n = sec(1.6)
tt = np.arange(n) / SR
drone = (sine(55, n) + sine(55.7, n)) * 0.35 * np.linspace(0.4, 1, n)
add(fx, 17.6, np.tanh(drone * 2))
nz = highpass(rng.standard_normal(n), 400) * np.linspace(0.02, 0.55, n) ** 1.4
add(fx, 17.6, nz)
sub_drop(12 * BAR, fx)                # slam back at 19.2
airhorn_triplet(fx, 14 * BAR)         # finale fanfare 22.4

# ---- siren over final rave bars
n = sec(2 * BAR)
tt = np.arange(n) / SR
add(fx, 14 * BAR, sine(850 + 380 * np.sin(2 * np.pi * 2.8 * tt), n) * 0.055)

# ---- record scratch + everything dies
add(fx, 17 * BAR - 0.15, record_scratch(), gain=1.1)

mix = drums + music + fx

# sidechain the musical bed to the kick
duck = np.ones(N)
dip_n = sec(0.22)
dip = 1 - 0.6 * np.exp(-np.linspace(0, 6, dip_n))
for kt in kick_times:
    i = sec(kt)
    j = min(N, i + dip_n)
    duck[i:j] = np.minimum(duck[i:j], dip[: j - i])
mix = drums + (music * duck) + fx

# ---- tape stop: resample the tail so pitch dives to zero
stop_t = 17 * BAR + 0.3               # 27.5
head = mix[: sec(stop_t)]
dur_out = 1.0
n_out = sec(dur_out)
speed = np.linspace(1.0, 0.0, n_out) ** 1.4
src_pos = sec(stop_t) + np.cumsum(speed)
src_pos = np.clip(src_pos, 0, N - 2)
frac = src_pos - src_pos.astype(int)
ip = src_pos.astype(int)
tail = mix[ip] * (1 - frac) + mix[ip + 1] * frac
tail *= np.linspace(1, 0, n_out) ** 0.7
out = np.zeros(N)
out[: len(head)] = head
out[len(head): len(head) + n_out] = tail

# stereo + master
w = sec(0.011)
side = music * duck
left = out + np.concatenate([side[w:], np.zeros(w)]) * 0.3
right = out + np.concatenate([np.zeros(w), side[:-w]]) * 0.3
fi, fo = sec(0.02), sec(0.15)
for ch in (left, right):
    ch[:fi] *= np.linspace(0, 1, fi)
    ch[-fo:] *= np.linspace(1, 0, fo)
stereo = np.stack([left, right], axis=1)
stereo = np.tanh(stereo * 1.35)
stereo /= np.abs(stereo).max() * 1.02

pcm = (stereo * 32767).astype(np.int16)
with wave.open("promo/roast_score.wav", "wb") as f:
    f.setnchannels(2)
    f.setsampwidth(2)
    f.setframerate(SR)
    f.writeframes(pcm.tobytes())
print(f"roast_score.wav: {TOTAL}s, peak {np.abs(stereo).max():.3f}")
