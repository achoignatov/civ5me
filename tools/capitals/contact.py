"""Contact sheet of the capital previews (run in Blender): blender -b -P contact.py -- out.png [view]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, '..', '..', 'build', 'venv', 'lib', 'python%d.%d' % sys.version_info[:2], 'site-packages'))
import bpy, numpy as np
from pipeline import CAPITALS, WORK
args = sys.argv[sys.argv.index('--') + 1:]
out, view = args[0], int(args[1]) if len(args) > 1 else 0
tiles = []
for civ, mod, name, *_ in CAPITALS:
    p = os.path.join(WORK, '%s_%d.png' % (name, view))
    im = bpy.data.images.load(p)
    w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)
    a = a.reshape(h // 2, 2, w // 2, 2, 4).mean((1, 3))
    tiles.append(a)
th, tw = tiles[0].shape[:2]
cols = 4
rows = (len(tiles) + cols - 1) // cols
sheet = np.zeros((rows * th, cols * tw, 4), np.float32)
for i, t in enumerate(tiles):
    r, c = divmod(i, cols)
    sheet[(rows - 1 - r) * th:(rows - r) * th, c * tw:(c + 1) * tw] = t
img = bpy.data.images.new('sheet', cols * tw, rows * th)
img.pixels.foreach_set(sheet.ravel())
img.filepath_raw = out; img.file_format = 'PNG'; img.save()
