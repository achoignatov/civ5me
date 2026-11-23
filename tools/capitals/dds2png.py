"""Debug helper (run in Blender): convert a DXT3 .dds to .png.  blender -b -P dds2png.py -- in.dds out.png"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, '..', '..', 'build', 'venv', 'lib', 'python%d.%d' % sys.version_info[:2], 'site-packages'))
import bpy, numpy as np, dds
src, dst = sys.argv[sys.argv.index('--') + 1:][:2]
im = dds.decode_dxt3(src)
h, w = im.shape[:2]
img = bpy.data.images.new('x', w, h)
img.pixels.foreach_set((np.flipud(im).astype(np.float32) / 255).ravel())
img.filepath_raw = dst; img.file_format = 'PNG'; img.save()
