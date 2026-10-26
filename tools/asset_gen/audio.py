"""
Arena Mortis - procedural sound effects (all original, synthesized with numpy).
Writes 16-bit mono WAV files. Run: python3 audio.py <out_dir>
"""
import math
import os
import sys
import wave

import numpy as np
from scipy import signal

SR = 44100
OUT = sys.argv[1] if len(sys.argv) > 1 else "../../assets/audio"
rng = np.random.default_rng(31337)


def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def noise(dur):
    return rng.uniform(-1, 1, int(dur * SR))


def env_exp(dur, decay, attack=0.002):
    t = t_axis(dur)
    e = np.exp(-t / decay)
    a = np.clip(t / max(attack, 1e-5), 0, 1)
    return e * a


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="bandpass", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    sos = signal.butter(order, f, btype="lowpass", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def hp(x, f, order=2):
    sos = signal.butter(order, f, btype="highpass", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def sweep(f0, f1, dur, shape="exp"):
    t = t_axis(dur)
    if shape == "exp":
        f = f0 * (f1 / f0) ** (t / dur)
    else:
        f = f0 + (f1 - f0) * t / dur
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph)


def pad(x, dur):
    n = int(dur * SR)
    if len(x) >= n:
        return x[:n]
    return np.concatenate([x, np.zeros(n - len(x))])


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def at(x, offset, total=None):
    n = int(offset * SR)
    out = np.concatenate([np.zeros(n), x])
    return pad(out, total) if total else out


def reverb(x, size=1.2, wet=0.25, damp=3000):
    """Cheap convolution reverb with a decaying noise impulse (stone hall)."""
    ir_len = int(size * SR)
    ir = rng.normal(size=ir_len) * np.exp(-np.arange(ir_len) / (SR * size / 5))
    ir = lp(ir, damp)
    ir[0] = 0
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    dry = np.concatenate([x, np.zeros(ir_len)])
    wet_sig = pad(signal.fftconvolve(x, ir), len(dry) / SR)
    wet_sig = np.concatenate([wet_sig, np.zeros(max(0, len(dry) - len(wet_sig)))])[:len(dry)]
    return dry * (1 - wet) + wet_sig * wet


def softclip(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive)


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) + 1e-9
    return x / m * peak


def fade(x, fin=0.003, fout=0.02):
    x = x.copy()
    a = int(fin * SR)
    b = int(fout * SR)
    if a > 0:
        x[:a] *= np.linspace(0, 1, a)
    if b > 0:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def write(name, x, peak=0.9, loop=False):
    x = norm(x, peak)
    if not loop:
        x = fade(x)
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# ----------------------------------------------------------------- weapons

def gunshot(dur=0.9, body_f=(160, 45), crack_bp=(1200, 9000), crack_decay=0.012, body_decay=0.07, tail=1.0, wet=0.3):
    crack = bp(noise(dur), *crack_bp) * env_exp(dur, crack_decay)
    thump = sweep(body_f[0], body_f[1], dur) * env_exp(dur, body_decay)
    rumble = lp(noise(dur), 300) * env_exp(dur, body_decay * 2.5) * 0.6
    mech = bp(noise(dur), 3000, 7000) * env_exp(dur, 0.004) * 0.5
    x = crack * 1.0 + thump * 0.9 + rumble + mech
    x = softclip(x * 1.5, 2.0)
    return reverb(x, tail, wet)


def click(f=3200, decay=0.006, n=0.04):
    t = t_axis(n)
    return (np.sin(2 * np.pi * f * t) * 0.6 + bp(noise(n), 2000, 8000) * 0.8) * env_exp(n, decay)


def clack(f=900, decay=0.03, n=0.15):
    t = t_axis(n)
    return (np.sin(2 * np.pi * f * t) * 0.5 + np.sin(2 * np.pi * f * 2.7 * t) * 0.3 + bp(noise(n), 400, 5000)) * env_exp(n, decay)


def weapons():
    write("pistol_fire", gunshot(0.9, (180, 55), (1500, 9000), 0.01, 0.05, 0.9, 0.28))
    write("m4_fire", gunshot(0.6, (140, 50), (900, 7000), 0.014, 0.06, 0.7, 0.22))
    up = gunshot(0.9, (220, 60), (1500, 10000), 0.012, 0.06, 1.0, 0.3)
    shimmer = sweep(2000, 400, 0.5) * env_exp(0.5, 0.15) * 0.4
    write("pistol_fire_upgraded", mix(up, shimmer))
    write("m4_fire_upgraded", mix(gunshot(0.6, (160, 55), (1000, 9000), 0.014, 0.06, 0.8, 0.25), shimmer * 0.7))
    # Jupiter: electric zap + thunder crack + rolling rumble
    d = 2.2
    zap = np.sign(np.sin(2 * np.pi * np.cumsum(220 + 1800 * np.exp(-t_axis(0.35) / 0.08)) / SR)) * env_exp(0.35, 0.09)
    crackle = bp(noise(0.5), 2000, 12000) * (rng.random(int(0.5 * SR)) > 0.97) * env_exp(0.5, 0.12) * 3
    thunder_crack = hp(noise(0.25), 400) * env_exp(0.25, 0.03)
    roll = lp(noise(d), 180) * env_exp(d, 0.55) * 2.5
    roll *= 1 + 0.6 * np.sin(2 * np.pi * 3.0 * t_axis(d))
    x = mix(zap * 0.5, crackle, thunder_crack * 1.2, roll)
    write("jupiter_fire", reverb(softclip(x, 1.5), 1.6, 0.35))
    write("jupiter_fire_upgraded", reverb(softclip(mix(x, sweep(80, 40, d) * env_exp(d, 0.6) * 0.8), 1.6), 1.8, 0.35))
    # reloads
    write("reload_pistol", mix(at(click(2500, 0.008), 0.05), at(clack(700, 0.03), 0.35), at(clack(900, 0.025), 0.75),
                               at(click(3000, 0.01), 0.95), at(clack(600, 0.04), 1.25), at(click(4200, 0.008), 1.32)), 0.8)
    write("reload_rifle", mix(at(click(2200, 0.01), 0.1), at(clack(500, 0.04), 0.5), at(bp(noise(0.2), 800, 3000) * env_exp(0.2, 0.06) * 0.4, 0.75),
                              at(clack(800, 0.035), 1.25), at(click(3500, 0.01), 1.33), at(clack(400, 0.05), 1.85), at(clack(1100, 0.02), 2.0)), 0.8)
    hum = np.sin(2 * np.pi * 110 * t_axis(1.6)) * 0.3 + np.sin(2 * np.pi * 220 * t_axis(1.6)) * 0.15
    hum *= np.clip(t_axis(1.6) / 1.2, 0, 1) * (1 + 0.3 * np.sin(2 * np.pi * 9 * t_axis(1.6)))
    write("reload_jupiter", mix(at(clack(600, 0.04), 0.15), hum, at(sweep(300, 1600, 0.6) * env_exp(0.6, 0.3) * 0.4, 0.8), at(click(3000, 0.01), 1.5)), 0.8)
    write("dry_fire", click(2800, 0.005, 0.08))
    write("weapon_switch", mix(bp(noise(0.25), 300, 2000) * env_exp(0.25, 0.06) * 0.5, at(clack(1000, 0.02), 0.12)))
    write("hitmarker", click(5200, 0.004, 0.05) + click(3400, 0.006, 0.05) * 0.5, 0.6)
    write("impact_stone", mix(bp(noise(0.3), 800, 6000) * env_exp(0.3, 0.025), click(1800, 0.01, 0.1)), 0.7)
    write("impact_flesh", mix(lp(noise(0.25), 1200) * env_exp(0.25, 0.04), sweep(200, 80, 0.15) * env_exp(0.15, 0.03) * 0.6), 0.7)
    write("lightning_impact", reverb(mix(hp(noise(0.4), 600) * env_exp(0.4, 0.05), bp(noise(0.6), 3000, 12000) * (rng.random(int(0.6 * SR)) > 0.95) * env_exp(0.6, 0.15) * 2), 0.8, 0.25))


# ----------------------------------------------------------------- zombies

def voice(dur, f0_curve, formants, breath=0.25, rasp=0.5, seed=0):
    """Source-filter growl: buzzy glottal pulse + noise through formants."""
    r = np.random.default_rng(seed)
    t = t_axis(dur)
    f0 = f0_curve(t)
    jitter = 1 + 0.04 * lp(r.normal(size=len(t)), 30) * 10
    ph = 2 * np.pi * np.cumsum(f0 * jitter) / SR
    src = signal.sawtooth(ph) * 0.6 + np.sign(np.sin(ph)) * 0.2
    src += r.normal(size=len(t)) * breath
    # subharmonic rasp (vocal fry)
    src += signal.sawtooth(ph / 2) * rasp * 0.3
    out = np.zeros_like(t)
    for (f, bw, g) in formants:
        out += bp(src, max(f - bw, 40), f + bw) * g
    amp = np.clip(t / 0.08, 0, 1) * np.clip((dur - t) / 0.25, 0, 1)
    amp *= 1 + 0.3 * lp(r.normal(size=len(t)), 6) * 8
    return softclip(out * amp * 2, 2.5)


def zombies():
    forms_a = [(450, 120, 1.0), (900, 200, 0.6), (2400, 400, 0.25)]
    forms_o = [(380, 100, 1.0), (700, 150, 0.7), (2200, 350, 0.2)]
    forms_u = [(300, 80, 1.0), (600, 120, 0.5), (2500, 400, 0.15)]
    groans = [
        (1.6, lambda t: 95 + 15 * np.sin(t * 2.0), forms_o),
        (1.3, lambda t: 120 - 25 * t, forms_a),
        (1.9, lambda t: 85 + 30 * np.exp(-t * 2), forms_u),
        (1.1, lambda t: 140 - 50 * t, forms_a),
    ]
    for i, (d, f, fm) in enumerate(groans):
        write(f"zombie_groan_{i + 1}", reverb(voice(d, f, fm, seed=i), 0.9, 0.2), 0.8)
    write("zombie_attack_1", reverb(voice(0.7, lambda t: 170 + 60 * np.exp(-t * 6), [(700, 200, 1.0), (1400, 300, 0.7), (2800, 500, 0.4)], 0.5, 0.8, seed=11), 0.6, 0.2))
    write("zombie_attack_2", reverb(voice(0.6, lambda t: 150 + 80 * t, [(650, 180, 1.0), (1300, 250, 0.7), (3000, 500, 0.4)], 0.6, 0.8, seed=12), 0.6, 0.2))
    write("zombie_death_1", reverb(voice(1.2, lambda t: 130 * np.exp(-t * 0.8), forms_o, 0.4, 0.6, seed=21), 1.0, 0.25))
    write("zombie_death_2", reverb(voice(1.0, lambda t: 110 - 40 * t, forms_u, 0.5, 0.9, seed=22), 1.0, 0.25))


# ----------------------------------------------------------------- player

def player_sounds():
    thud = sweep(120, 50, 0.3) * env_exp(0.3, 0.06)
    grunt = voice(0.35, lambda t: 140 - 40 * t, [(500, 150, 1.0), (1000, 200, 0.5)], 0.3, 0.2, seed=40)
    write("player_hurt_1", mix(thud, grunt * 0.7, lp(noise(0.2), 2000) * env_exp(0.2, 0.03) * 0.5), 0.8)
    grunt2 = voice(0.4, lambda t: 160 - 60 * t, [(550, 150, 1.0), (1100, 200, 0.5)], 0.35, 0.2, seed=41)
    write("player_hurt_2", mix(thud, grunt2 * 0.7), 0.8)
    beat = mix(sweep(70, 40, 0.15) * env_exp(0.15, 0.05), at(sweep(65, 38, 0.15) * env_exp(0.15, 0.05) * 0.7, 0.22))
    death = mix(*[at(beat * (0.9 ** k), k * 0.8) for k in range(4)], lp(noise(3.2), 400) * env_exp(3.2, 1.2) * 0.3)
    write("player_death", reverb(death, 1.5, 0.3))
    for i in range(3):
        n = 0.18
        st = lp(bp(noise(n), 200, 3000), 2500) * env_exp(n, 0.035 + i * 0.006)
        st += bp(noise(n), 3000, 7000) * env_exp(n, 0.01) * 0.25
        write(f"footstep_sand_{i + 1}", st, 0.6)


# ----------------------------------------------------------------- machines / ui

def pluck(f, dur, decay=0.6):
    t = t_axis(dur)
    x = np.zeros_like(t)
    for h, a in ((1, 1.0), (2, 0.35), (3, 0.15), (4.2, 0.08)):
        x += np.sin(2 * np.pi * f * h * t) * a * np.exp(-t * h / decay)
    return x * np.clip(t / 0.003, 0, 1)


def note(n):
    """MIDI note number -> Hz."""
    return 440 * 2 ** ((n - 69) / 12)


def machines():
    # Mystery Box: an original music-box phrase in D minor, then a chime
    seq = [62, 65, 69, 74, 72, 69, 65, 67, 70, 74, 73, 69, 65, 64, 61, 62]
    parts = []
    for i, n in enumerate(seq):
        d = 0.19
        parts.append(at(pluck(note(n + 12), 1.2, 0.5) * 0.6, i * d))
    tune = mix(*parts)
    write("box_open", reverb(mix(tune, at(clack(300, 0.05), 0.0) * 0.6), 1.2, 0.3))
    chord = mix(*[pluck(note(n + 12), 2.0, 0.9) for n in (62, 65, 69, 74)])
    write("box_reveal", reverb(mix(chord, sweep(400, 1600, 0.4) * env_exp(0.4, 0.2) * 0.2), 1.4, 0.35))
    write("box_close", mix(clack(250, 0.06, 0.4), at(clack(180, 0.08, 0.4), 0.05)), 0.8)
    # Pack-a-Punch: machine whirr, hammer blows, then a triumphant brass chord
    d = 3.2
    t = t_axis(d)
    whirr = signal.sawtooth(2 * np.pi * np.cumsum(60 + 140 * np.clip(t / 1.5, 0, 1)) / SR) * 0.25
    whirr = lp(whirr, 1500) * np.clip(t / 0.4, 0, 1) * np.clip((d - t) / 0.4, 0, 1)
    anvil = []
    for k, tt in enumerate((0.6, 1.2, 1.8, 2.4)):
        ring = sum(np.sin(2 * np.pi * f * t_axis(1.0)) * a * np.exp(-t_axis(1.0) * dd) for f, a, dd in ((1250, 1, 4), (2730, 0.5, 6), (4100, 0.3, 9)))
        anvil.append(at((ring + bp(noise(1.0), 1000, 8000) * env_exp(1.0, 0.01) * 2) * 0.6, tt))
    write("pap_work", reverb(mix(whirr, *anvil), 1.3, 0.3))
    brass = brass_chord([50, 57, 62, 66], 2.2)
    write("pap_done", reverb(mix(brass, at(sum(np.sin(2 * np.pi * f * t_axis(1.5)) * np.exp(-t_axis(1.5) * 3) for f in (1250, 2730)) * 0.5, 0.0)), 1.6, 0.35))
    write("purchase", mix(pluck(note(79), 0.6, 0.3), at(pluck(note(84), 0.8, 0.4), 0.08)), 0.7)
    write("deny", mix(signal.square(2 * np.pi * 110 * t_axis(0.25)) * env_exp(0.25, 0.1), at(signal.square(2 * np.pi * 98 * t_axis(0.3)) * env_exp(0.3, 0.1), 0.12)) * 0.5, 0.6)


def brass_chord(notes, dur, vib=5.0):
    t = t_axis(dur)
    out = np.zeros_like(t)
    for i, n in enumerate(notes):
        f = note(n) * (1 + 0.004 * np.sin(2 * np.pi * vib * t + i))
        x = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR)
        att = np.clip(t / 0.12, 0, 1)
        cutoff = 600 + 2400 * np.clip(t / 0.3, 0, 1) * np.exp(-t / 1.5)
        x = lp(x, 2600) * att
        out += x * 0.3
    return out * np.clip((dur - t) / 0.4, 0, 1)


def horn(notes_seq, step=0.55):
    """Roman cornu call."""
    parts = []
    for i, (n, d) in enumerate(notes_seq):
        parts.append(at(brass_chord([n, n + 7], d, 4.5) * 1.2, i * step))
    return mix(*parts)


def stingers():
    call = horn([(45, 0.6), (52, 0.6), (57, 1.4)])
    drum = mix(*[at(mix(sweep(90, 45, 0.5) * env_exp(0.5, 0.15) * 1.5, lp(noise(0.3), 500) * env_exp(0.3, 0.05)), k * 0.55) for k in range(3)])
    write("round_start", reverb(mix(call, drum), 2.0, 0.35))
    end = horn([(57, 0.5), (52, 0.5), (45, 1.8)], 0.5)
    write("round_end", reverb(mix(end, at(sweep(80, 35, 1.2) * env_exp(1.2, 0.4) * 1.5, 1.0)), 2.2, 0.4))


# ----------------------------------------------------------------- ambience

def ambience():
    d = 24.0
    t = t_axis(d)
    wind = lp(noise(d), 500) * (0.6 + 0.4 * np.sin(2 * np.pi * t / d * 3 + 1.0))
    wind += bp(noise(d), 600, 1400) * 0.15 * (0.5 + 0.5 * np.sin(2 * np.pi * t / d * 2))
    # distant moaning crowd of the dead
    crowd = np.zeros_like(t)
    for k in range(9):
        st = rng.uniform(0, d - 3)
        g = voice(rng.uniform(1.5, 3.0), lambda tt, b=rng.uniform(70, 120): b + 10 * np.sin(tt * 2), [(400, 120, 1.0), (800, 160, 0.5)], 0.4, 0.4, seed=100 + k)
        g = lp(g, 900) * 0.25
        crowd[int(st * SR):int(st * SR) + len(g)] += g[:len(crowd) - int(st * SR)]
    crackle = (rng.random(len(t)) > 0.9993) * rng.uniform(0.2, 1.0, len(t))
    crackle = bp(signal.lfilter([1], [1, -0.6], crackle), 1500, 7000) * 0.8
    x = wind * 0.8 + reverb(crowd, 2.5, 0.6)[:len(t)] + crackle
    # make it loop: crossfade the end into the start
    xf = int(2.0 * SR)
    x[:xf] = x[:xf] * np.linspace(0, 1, xf) + x[-xf:] * np.linspace(1, 0, xf)
    x = x[:-xf]
    write("ambient_colosseum", x, 0.7, loop=True)
    d2 = 6.0
    fire = lp(noise(d2), 700) * 0.4 * (0.7 + 0.3 * lp(rng.normal(size=int(d2 * SR)), 3) * 30)
    pops = (rng.random(int(d2 * SR)) > 0.9985) * rng.uniform(0.3, 1.0, int(d2 * SR))
    fire += bp(signal.lfilter([1], [1, -0.7], pops), 1200, 6000)
    xf = int(0.5 * SR)
    fire[:xf] = fire[:xf] * np.linspace(0, 1, xf) + fire[-xf:] * np.linspace(1, 0, xf)
    write("fire_loop", fire[:-xf], 0.6, loop=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    weapons()
    zombies()
    player_sounds()
    machines()
    stingers()
    ambience()
    print("audio files:", len([f for f in os.listdir(OUT) if f.endswith(".wav")]))


if __name__ == "__main__":
    main()
