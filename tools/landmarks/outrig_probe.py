"""Root-cause probe "invisible outriggers" (docs/CITY_MODELS.md §18).

Question: does the engine react to the landmark's BOUNDS (bounding box / radius) or to its VISIBLE geometry?

Input : build/landmarks/out/MEC_LM_Moria_Tall.gr2  (+-10.5 x +-12.1, 29 high; drew 11/11 in step 7, incl. the
        city-states that later failed at +-20)
Output: build/landmarks/out/MEC_LM_Moria_Outrig.*  = the SAME mesh, textures and material, plus 6 tiny triangles
        (0.1 world units across, 1 cm-scale specks) at the 6 corners of MEC_LM_Moria_Wide's hexagon (circumradius 27.7,
        x +-24, y +-27.7). Its horizontal bounding box and radius are therefore exactly the Wide model's (which failed
        9/10), while nothing visible changes. Height range stays Tall's.

No Blender needed:  build/venv/bin/python tools/landmarks/outrig_probe.py
"""
import json
import math
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'capitals'))
import gr2  # noqa: E402

sys.path.insert(0, HERE)
import landmarks  # noqa: E402

SRC = 'MEC_LM_Moria_Tall'
DST = 'MEC_LM_Moria_Outrig'
FSCALE = 0.05                 # the rows' fScale: world = file units * FSCALE
RADIUS = 27.7128              # world units: Wide's circumradius (pointy-top hexagon, x extent = R * cos 30 = 24.0)
SPECK = 0.1                   # world units: size of each outrigger triangle
SPECK_Z = -1.0                # world units: just below flat ground (Tall already reaches z -3.4)


def V(x):
    return x.value if isinstance(x, gr2.Variant) else x


def _rename(v, old, new, seen=None):
    seen = set() if seen is None else seen
    if id(v) in seen:
        return
    seen.add(id(v))
    if isinstance(v, dict):
        for k, x in v.items():
            if isinstance(x, str) and x.startswith(old):
                v[k] = new + x[len(old):]
            else:
                _rename(x, old, new, seen)
    elif isinstance(v, list):
        for i, x in enumerate(v):
            if isinstance(x, str) and x.startswith(old):
                v[i] = new + x[len(old):]
            else:
                _rename(x, old, new, seen)
    elif isinstance(v, gr2.Variant):
        _rename(v.value, old, new, seen)


def main():
    out = landmarks.OUT
    f = gr2.read(os.path.join(out, SRC + '.gr2'))
    root = f.root()
    model = [m for m in root['Models'] if m['Name'] == SRC][0]
    mesh = model['MeshBindings'][0]['Mesh']
    verts = V(mesh['PrimaryVertexData']['Vertices'])
    topo = mesh['PrimaryTopology']
    idx = topo['Indices16']
    assert len(topo['Groups']) == 1 and topo['Groups'][0]['TriFirst'] == 0
    assert topo['Groups'][0]['TriCount'] * 3 == len(idx)
    n0, t0 = len(verts), len(idx) // 3
    proto = verts[0]
    s = SPECK / FSCALE
    for k in range(6):                              # corners at 90, 150, ... degrees: (0, +-R), (+-R cos30, +-R/2)
        a = math.radians(90 + 60 * k)
        cx, cy, cz = (RADIUS * math.cos(a) / FSCALE, RADIUS * math.sin(a) / FSCALE, SPECK_Z / FSCALE)
        base = len(verts)
        for dx, dy in ((0.0, 0.0), (s, 0.0), (0.0, s)):
            v = {key: list(val) if isinstance(val, list) else val for key, val in proto.items()}
            v['Position'] = [cx + dx, cy + dy, cz]
            v['Normal'] = [0.0, 0.0, 1.0]
            v['Tangent'] = [1.0, 0.0, 0.0]
            v['Binormal'] = [0.0, -1.0, 0.0]
            verts.append(v)
        idx += [base, base + 1, base + 2]           # counter-clockwise seen from above (front face up)
    topo['Groups'][0]['TriCount'] = len(idx) // 3
    assert len(verts) < 32768
    # every string starting with the source model name (model, mesh, skeleton, bone, bone binding) gets the new name,
    # like the other size-test copies (Wide/Tall use their own name everywhere)
    _rename(root, SRC, DST)
    gr2.write(os.path.join(out, DST + '.gr2'), f.root_type, root, f.tag)

    # textures + fxsxml copied from Tall under the new name
    for suf in ('_DIFF.dds', '_SREF.dds'):
        shutil.copy2(os.path.join(out, SRC + suf), os.path.join(out, DST + suf))
    fx = open(os.path.join(out, SRC + '.fxsxml'), encoding='utf-8').read().replace(SRC, DST)
    open(os.path.join(out, DST + '.fxsxml'), 'w', encoding='utf-8', newline='\r\n').write(fx)
    files = [DST + '.fxsxml', DST + '.gr2', DST + '_DIFF.dds', DST + '_SREF.dds']
    json.dump({'files': files}, open(os.path.join(out, DST + '.files.json'), 'w'), indent=1)

    # verify by reading back
    r = gr2.read(os.path.join(out, DST + '.gr2')).root()
    me = [m for m in r['Models'] if m['Name'] == DST][0]['MeshBindings'][0]['Mesh']
    ps = [v['Position'] for v in V(me['PrimaryVertexData']['Vertices'])]
    box = [(min(p[i] for p in ps) * FSCALE, max(p[i] for p in ps) * FSCALE) for i in range(3)]
    rad = max(math.hypot(p[0], p[1]) for p in ps) * FSCALE
    print('%s: %d -> %d verts, %d -> %d tris; world x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f, radius %.1f'
          % (DST, n0, len(ps), t0, me['PrimaryTopology']['Groups'][0]['TriCount'], box[0][0], box[0][1],
             box[1][0], box[1][1], box[2][0], box[2][1], rad))


if __name__ == '__main__':
    main()
