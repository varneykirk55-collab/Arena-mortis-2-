"""Builds side-by-side before/after sheets from docs/visual_pass/{before,after}.
Usage: python3 tools/preview/compare_sheet.py docs/visual_pass
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

root = sys.argv[1] if len(sys.argv) > 1 else "docs/visual_pass"
shots = sorted(f[len("before_"):] for f in os.listdir(os.path.join(root, "before")) if f.startswith("before_"))
W = 960
try:
    font = ImageFont.truetype("assets/fonts/Oswald-Variable.ttf", 28)
except OSError:
    font = ImageFont.load_default()
rows = []
for s in shots:
    b = os.path.join(root, "before", "before_" + s)
    a = os.path.join(root, "after", "after_" + s)
    if not os.path.exists(a):
        continue
    ib = Image.open(b).convert("RGB")
    ia = Image.open(a).convert("RGB")
    h = int(ib.height * W / ib.width)
    ib, ia = ib.resize((W, h)), ia.resize((W, h))
    row = Image.new("RGB", (W * 2 + 12, h + 44), (18, 18, 20))
    row.paste(ib, (0, 44))
    row.paste(ia, (W + 12, 44))
    d = ImageDraw.Draw(row)
    name = s[:-4]
    d.text((10, 6), "BEFORE  " + name, fill=(220, 220, 220), font=font)
    d.text((W + 22, 6), "AFTER  " + name, fill=(230, 200, 140), font=font)
    row.save(os.path.join(root, "compare_" + s))
    rows.append(row)
# one overview sheet of the gameplay shots
g = [r for r, s in zip(rows, shots) if s.startswith("G")]
if g:
    sheet = Image.new("RGB", (g[0].width, sum(r.height for r in g)), (18, 18, 20))
    y = 0
    for r in g:
        sheet.paste(r, (0, y))
        y += r.height
    sheet.resize((sheet.width // 2, sheet.height // 2)).save(os.path.join(root, "stageB_before_after.png"))
print(len(rows), "comparison images")
