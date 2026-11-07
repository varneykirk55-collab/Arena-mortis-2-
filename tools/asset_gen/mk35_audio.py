"""Original MK35 audio synthesis; no commercial game recordings or samples.
Run python3 tools/asset_gen/mk35_audio.py from the checkout.
"""
from pathlib import Path
import audio as a
import numpy as np

a.OUT = str(Path(__file__).resolve().parents[2] / 'assets/audio')
a.rng = np.random.default_rng(3507)
a.write('mk35_fire', a.gunshot(.65, (115, 42), (1100, 8200), .011, .075, .8, .23))
a.write('mk35_fire_upgraded', a.mix(
    a.gunshot(.7, (145, 45), (1400, 9500), .012, .08, .9, .25),
    a.sweep(1800, 330, .45) * a.env_exp(.45, .13) * .3))
a.write('reload_mk35', a.mix(
    a.at(a.click(2400), .03), a.at(a.clack(650), .55),
    a.at(a.clack(820), 1.45), a.at(a.click(3100), 1.72),
    a.at(a.clack(1100), 2.12), a.at(a.click(2800), 2.29)), peak=.7)
print('MK35 original audio generated')
