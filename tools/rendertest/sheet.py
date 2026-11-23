"""Contact sheet: centre crop of every RT shot in a shots dir -> sheet.png"""
import sys, os, glob
from PIL import Image, ImageDraw
d = sys.argv[1]
fs = sorted(f for f in glob.glob(os.path.join(d, '[0-9][0-9]_*.png')))
crops = []
for f in fs:
    im = Image.open(f); w, h = im.size
    c = im.crop((w // 2 - 260, h // 2 - 230, w // 2 + 260, h // 2 + 170)).resize((390, 300))
    ImageDraw.Draw(c).text((5, 5), os.path.basename(f)[:-4], fill=(255, 255, 0))
    crops.append(c)
cols = 4
sheet = Image.new('RGB', (390 * cols, 300 * ((len(crops) + cols - 1) // cols)))
for i, c in enumerate(crops):
    sheet.paste(c, ((i % cols) * 390, (i // cols) * 300))
sheet.save(os.path.join(d, 'sheet.png')); print(os.path.join(d, 'sheet.png'))
