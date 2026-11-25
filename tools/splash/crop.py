"""Crop a region of a PNG for close inspection:  blender -b -P tools/splash/crop.py -- in.png out.png x0 y0 w h [scale]"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, '..', '..', 'build', 'venv', 'lib', 'python%d.%d' % sys.version_info[:2], 'site-packages'))
import numpy as np, bpy
a = sys.argv[sys.argv.index('--') + 1:]
src, dst = a[0], a[1]; x0, y0, w, h = map(int, a[2:6]); sc = int(a[6]) if len(a) > 6 else 1
im = bpy.data.images.load(os.path.abspath(src))
W, H = im.size
px = np.empty(W * H * 4, np.float32); im.pixels.foreach_get(px)
px = px.reshape(H, W, 4)[::-1][y0:y0 + h, x0:x0 + w]
px = np.repeat(np.repeat(px, sc, 0), sc, 1)
o = bpy.data.images.new('c', px.shape[1], px.shape[0], alpha=True)
o.pixels.foreach_set(px[::-1].ravel()); o.filepath_raw = os.path.abspath(dst); o.file_format = 'PNG'; o.save()
