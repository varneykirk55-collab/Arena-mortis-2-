"""Install supplied LOD1 models verbatim; never remodel these assets."""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT/'assets/models'
OUT.mkdir(parents=True, exist_ok=True)
for folder, target in [('Modern_M4', 'weapon_m4'), ('MK35_ISR_BO7', 'weapon_mk35')]:
    source = ROOT/'assets/sources/grok/original'/folder/(folder+'_LOD1.glb')
    shutil.copyfile(source, OUT/(target+'.glb'))
    print('Installed supplied LOD1:', target)
