"""End-to-end check (run in Blender): load a written .gr2 + its _DIFF.dds with our own reader and
render it the way the game would see the file.  blender -b -P gr2preview.py -- Name out.png"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, '..', '..', 'build', 'venv', 'lib', 'python%d.%d' % sys.version_info[:2], 'site-packages'))
import bpy, numpy as np
import gr2, dds, pipeline
name, out = sys.argv[sys.argv.index('--') + 1:][:2]
r = gr2.read(os.path.join(pipeline.OUT, name + '.gr2')).root()
verts, tris = [], []
for mo in r['Models']:
    if mo['Name'] == 'Tree cut':
        continue
    for mb in mo['MeshBindings']:
        m = mb['Mesh']
        base = len(verts)
        for v in m['PrimaryVertexData']['Vertices'].value:
            verts.append((tuple(v['Position']), tuple(v['Normal']), None, None, tuple(v['TextureCoordinates0'][:2])))
        idx = [x['Int16'] for x in m['PrimaryTopology']['Indices16']] or [x['Int32'] for x in m['PrimaryTopology']['Indices']]
        tris += [(base + idx[i], base + idx[i + 1], base + idx[i + 2]) for i in range(0, len(idx), 3)]
tex = r['Materials'][1]['Maps'][0]['Map']['Texture']['FromFileName']
img = dds.decode_dxt3(os.path.join(pipeline.OUT, tex))
pipeline.WORK = os.path.dirname(out)
pipeline.PREVIEW = os.path.dirname(out)
pipeline.preview(os.path.splitext(os.path.basename(out))[0], verts, tris, img)
print('rendered', name, len(verts), 'verts', len(tris), 'tris from', tex)
