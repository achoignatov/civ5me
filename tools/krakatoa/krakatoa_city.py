"""Krakatoa as THE city model (experiment, build_dlc.py --krakatoa-cities).

Civ 5 draws a city's look from a per-culture/era "house library" (<CityDefines> -> PopulationBuildings ->
one .gr2). A stock library (e.g. Euro_Anc_City.gr2) holds 20 models; each model is one house = a building
mesh (BuildingShader, bound to the model's root bone) + a flat footprint decal (LandmarkShader, CityBase
textures, bound to the second bone). The exe places more of them as the city grows.

Krakatoa has no mesh of its own (its mountain is a terrain heightmap, Assets/terrain/pieces/Wonder_Krakatoa),
so this script builds one from that heightmap (volcano_H.dds) textured with the stock volcano rock
(generic_volcano_d.dds), filling the whole hexagon, and writes a library with the stock file's exact
structure where EVERY one of the 20 houses is that same Krakatoa at the origin with a whole-hex footprint.
Whatever subset the exe shows at any city size, the city looks like one Krakatoa.

    build/venv/bin/python tools/krakatoa/krakatoa_city.py      -> build/krakatoa/MEC_KrakatoaCity.*
"""
import copy
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'capitals'))
import gr2  # noqa: E402
import dds  # noqa: E402
import fpk  # noqa: E402

GAME = os.path.expanduser("~/.local/share/Steam/steamapps/common/Sid Meier's Civilization V")
OUT = os.path.join(ROOT, 'build', 'krakatoa')
NAME = 'MEC_KrakatoaCity'

# Size in the library's model units (stock house: ~107 x 135 wide, 140 tall; footprint decal 225 x 275).
# Calibrate from screenshots: R_OUT = hexagon corner radius (pointy-top: corners north/south).
R_OUT = float(os.environ.get('KRAK_R', 600.0))
HEIGHT = float(os.environ.get('KRAK_H', 420.0))
N_MODELS = 20           # as many as the stock library
RINGS, SPOKES = 28, 96  # mesh resolution (2.7k verts)
TILE = 0.45             # rock texture repeats per R_OUT


def _resource(fpk_name, entry):
    for dp, _, fs in os.walk(os.path.join(GAME, 'Resource')):
        if fpk_name in fs:
            for n, data in fpk.entries(os.path.join(dp, fpk_name)):
                if n.lower() == entry.lower():
                    return data
    raise FileNotFoundError(entry)


def heightmap():
    d = open(os.path.join(GAME, 'Assets', 'terrain', 'pieces', 'Wonder_Krakatoa', 'Europe', 'volcano_H.dds'), 'rb').read()
    assert struct.unpack_from('<I', d, 84)[0] == 0x24          # A16B16G16R16, 128x128
    a = np.frombuffer(d, '<u2', 128 * 128 * 4, 128).reshape(128, 128, 4)[..., 0].astype(np.float32)
    edge = np.median(np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]))
    h = np.clip((a - edge) / (a.max() - edge), 0.0, 1.0)
    return h


def sample(h, u, v):
    """bilinear, u/v in [0,1] (u = east, v = north; image row 0 = north)"""
    n = h.shape[0] - 1
    x, y = np.clip(u * n, 0, n), np.clip((1.0 - v) * n, 0, n)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    x1, y1 = np.minimum(x0 + 1, n), np.minimum(y0 + 1, n)
    fx, fy = x - x0, y - y0
    return (h[y0, x0] * (1 - fx) * (1 - fy) + h[y0, x1] * fx * (1 - fy) + h[y1, x0] * (1 - fx) * fy + h[y1, x1] * fx * fy)


def hex_radius(theta):
    """distance centre -> pointy-top hexagon boundary (corners at 90 deg / north) for corner radius 1"""
    t = (theta - np.pi / 2) % (np.pi / 3) - np.pi / 6
    return np.cos(np.pi / 6) / np.cos(t)


def volcano_mesh():
    h = heightmap()
    pts, idx = [(0.0, 0.0)], []
    for i in range(1, RINGS + 1):
        rho = i / RINGS
        for j in range(SPOKES):
            th = 2 * np.pi * j / SPOKES
            r = rho * hex_radius(th)
            pts.append((r * np.cos(th), r * np.sin(th)))
    pts = np.array(pts)
    # height: the heightmap's square spans the hexagon's bounding circle; rim sinks just below the ground
    u, v = pts[:, 0] * 0.5 + 0.5, pts[:, 1] * 0.5 + 0.5
    z = sample(h, u, v) * HEIGHT
    ring = np.zeros(len(pts), int)
    ring[1:] = np.repeat(np.arange(1, RINGS + 1), SPOKES)
    z[ring == RINGS] = -8.0
    pos = np.stack([pts[:, 0] * R_OUT, pts[:, 1] * R_OUT, z], 1)
    for j in range(SPOKES):                                         # centre fan
        idx.append((0, 1 + j, 1 + (j + 1) % SPOKES))
    for i in range(1, RINGS):
        a, b = 1 + (i - 1) * SPOKES, 1 + i * SPOKES
        for j in range(SPOKES):
            j1 = (j + 1) % SPOKES
            idx.append((a + j, b + j, b + j1))
            idx.append((a + j, b + j1, a + j1))
    idx = np.array(idx)
    nrm = np.zeros_like(pos)
    fn = np.cross(pos[idx[:, 1]] - pos[idx[:, 0]], pos[idx[:, 2]] - pos[idx[:, 0]])
    for k in range(3):
        np.add.at(nrm, idx[:, k], fn)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    assert (nrm[:, 2] > 0).all(), 'winding must face up'
    tan = np.array([1.0, 0.0, 0.0]) - nrm * nrm[:, :1]
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    bin_ = np.cross(tan, nrm)
    uv = np.stack([pts[:, 0] / TILE * 0.5 + 0.5, 0.5 - pts[:, 1] / TILE * 0.5, np.zeros(len(pts))], 1)
    verts = [{'Position': list(map(float, pos[k])), 'Normal': list(map(float, nrm[k])),
              'Tangent': list(map(float, tan[k])), 'Binormal': list(map(float, bin_[k])),
              'TextureCoordinates0': list(map(float, uv[k]))} for k in range(len(pos))]
    return verts, [int(x) for x in idx.reshape(-1)]


def footprint_mesh():
    """flat whole-hex decal (the stock houses' ground patch), CityBase textures"""
    pts = [(0.0, 0.0)] + [(np.cos(np.pi / 2 + k * np.pi / 3), np.sin(np.pi / 2 + k * np.pi / 3)) for k in range(6)]
    verts = [{'Position': [x * R_OUT, y * R_OUT, 0.0], 'Normal': [0.0, 0.0, 1.0], 'Tangent': [1.0, 0.0, 0.0],
              'Binormal': [0.0, -1.0, 0.0], 'TextureCoordinates0': [x * 0.5 + 0.5, 0.5 - y * 0.5, 0.5]} for x, y in pts]
    idx = []
    for k in range(6):
        idx += [0, 1 + k, 1 + (k + 1) % 6]
    return verts, idx


def _bbox(verts):
    p = np.array([v['Position'] for v in verts])
    return list(map(float, p.min(0))), list(map(float, p.max(0)))


def _rename(v, names, seen=None):
    """replace every hashed string ('#xxxxxxxx') with a plain name (we write plain text like our landmarks)"""
    seen = set() if seen is None else seen
    if id(v) in seen:
        return v
    seen.add(id(v))
    if isinstance(v, dict):
        for k, x in v.items():
            v[k] = _rename(x, names, seen)
    elif isinstance(v, list):
        for i, x in enumerate(v):
            v[i] = _rename(x, names, seen)
    elif isinstance(v, gr2.Variant):
        v.value = _rename(v.value, names, seen)
    elif isinstance(v, str) and len(v) == 9 and v[0] == '#':
        return names.get(v, 'mec_' + v[1:])
    return v


def build():
    os.makedirs(OUT, exist_ok=True)
    tmpl_path = os.path.join(OUT, 'euro_anc_city.gr2')
    open(tmpl_path, 'wb').write(_resource('CityModels.fpk', 'euro_anc_city.gr2'))
    f = gr2.read(tmpl_path)
    r = f.root()
    assert len(r['Models']) == N_MODELS and len(r['Materials']) == 2

    # materials: [0] LandmarkShader (footprint: CityBase textures), [1] BuildingShader (house)
    land, bld = r['Materials']
    assert land['ExtendedData'].value['ShaderSet'] == 'LandmarkShader'
    assert bld['ExtendedData'].value['ShaderSet'] == 'BuildingShader'
    names = {land['Name']: NAME + '_Base', bld['Name']: NAME + '_Rock'}
    tex = {'BaseTextureMap': 'CityBase_Diff_anc.dds', 'HeightTextureMap': 'CityBase_HT.dds',
           'SpecTextureMap': 'CityBase_SREF.dds', 'Diffuse': NAME + '_DIFF.dds',
           'BuildingSREF': NAME + '_SREF.dds', 'ColorCorrection': NAME + '_DIFF.dds'}
    for m in (land, bld):
        for mp in m['Maps']:
            t = mp['Map']['Texture']
            names[t['FromFileName']] = tex[mp['Usage']]
            names[mp['Map']['Name']] = tex[mp['Usage']].rsplit('.', 1)[0]

    proto_fp, proto_b = r['Models'][0]['MeshBindings'][0]['Mesh'], r['Models'][0]['MeshBindings'][1]['Mesh']
    assert proto_fp['MaterialBindings'][0]['Material'] is land and proto_b['MaterialBindings'][0]['Material'] is bld
    vv, vi = volcano_mesh()
    fv, fi = footprint_mesh()

    def mesh(proto, name, verts, idx):
        m = copy.copy(proto)
        vd = copy.copy(proto['PrimaryVertexData'])
        var = proto['PrimaryVertexData']['Vertices']
        vd['Vertices'] = gr2.Variant(var.members, verts)
        vd['VertexComponentNames'] = [{'String': mm.name} for mm in var.members]   # as our landmark writer
        vd['VertexAnnotationSets'] = []
        topo = copy.copy(proto['PrimaryTopology'])
        g = dict(topo['Groups'][0])
        g.update(MaterialIndex=0, TriFirst=0, TriCount=len(idx) // 3)
        topo['Groups'] = [g]
        assert len(verts) < 32768
        topo['Indices16'] = [{'Int16': i} for i in idx]
        topo['Indices'] = []
        for k in ('VertexToVertexMap', 'VertexToTriangleMap', 'SideToNeighborMap', 'BonesForTriangle',
                  'TriangleToBoneIndices', 'TriAnnotationSets'):
            topo[k] = []
        m['PrimaryVertexData'], m['PrimaryTopology'], m['Name'] = vd, topo, name
        bb = dict(proto['BoneBindings'][0])
        bb['BoneName'] = name
        m['BoneBindings'] = [bb]
        return m

    models, meshes = [], []
    for i in range(N_MODELS):
        proto_m = r['Models'][i]
        mn = '%s_%02d' % (NAME, i)
        fp = mesh(proto_fp, mn + '_Base', fv, fi)
        vb = mesh(proto_b, mn, vv, vi)
        sk = copy.copy(proto_m['Skeleton'])
        bones = []
        for bone, bn in zip(proto_m['Skeleton']['Bones'], (mn, mn + '_Base')):
            b = copy.deepcopy(bone)
            b['Name'] = bn
            b['Transform']['Position'] = [0.0, 0.0, 0.0]
            b['InverseWorldTransform'] = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]
            bones.append(b)
        sk['Bones'], sk['Name'] = bones, mn
        m = copy.copy(proto_m)
        m['Name'], m['Skeleton'] = mn, sk
        m['InitialPlacement'] = copy.deepcopy(proto_m['InitialPlacement'])
        m['InitialPlacement']['Position'] = [0.0, 0.0, 0.0]
        # same order as stock: footprint first, then the building
        m['MeshBindings'] = [{'Mesh': fp}, {'Mesh': vb}]
        models.append(m)
        meshes += [fp, vb]
    r['Models'], r['Meshes'] = models, meshes
    r['Skeletons'] = [m['Skeleton'] for m in models]
    r['VertexDatas'] = [m['PrimaryVertexData'] for m in meshes]
    r['TriTopologies'] = [m['PrimaryTopology'] for m in meshes]
    r['FromFileName'] = NAME + '.max'
    _rename(r, names)
    out = os.path.join(OUT, NAME + '.gr2')
    gr2.write(out, f.root_type, r, f.tag, sections=True)

    # verify: read back, nothing hashed left, geometry intact
    g = gr2.read(out).root()
    assert len(g['Models']) == N_MODELS and len(g['Meshes']) == 2 * N_MODELS
    flat = []
    def strs(v, acc, seen=set()):
        if id(v) in seen:
            return
        seen.add(id(v))
        if isinstance(v, dict):
            [strs(x, acc) for x in v.values()]
        elif isinstance(v, list):
            [strs(x, acc) for x in v]
        elif isinstance(v, gr2.Variant):
            strs(v.value, acc)
        elif isinstance(v, str):
            acc.append(v)
    strs(g, flat)
    assert not [s for s in flat if s.startswith('#')], 'hashed strings left'
    vol = g['Meshes'][1]['PrimaryVertexData']['Vertices'].value
    print('%s.gr2: %d models, volcano %d verts / %d tris, bbox %s' % (
        NAME, len(g['Models']), len(vol), len(vi) // 3, _bbox(vol)))

    # textures: stock volcano rock as diffuse (copied as is, DXT5 256x256), low-spec SREF
    open(os.path.join(OUT, NAME + '_DIFF.dds'), 'wb').write(_resource('TerrainTextures.fpk', 'generic_volcano_d.dds'))
    sref = np.zeros((64, 64, 4), np.uint8)
    sref[..., :3] = 18
    dds.write_dxt3(os.path.join(OUT, NAME + '_SREF.dds'), sref)
    open(os.path.join(OUT, NAME + '.fxsxml'), 'w', encoding='utf-8', newline='\r\n').write(
        '<Asset>\n  <Mesh file="%s.gr2" source="Max" />\n' % NAME
        + ''.join('  <Texture file="%s" source="Max" />\n' % t for t in
                  (NAME + '_DIFF.dds', NAME + '_SREF.dds', 'CityBase_Diff_anc.dds', 'CityBase_HT.dds', 'CityBase_SREF.dds'))
        + '</Asset>\n')
    os.remove(tmpl_path)
    return [NAME + x for x in ('.gr2', '.fxsxml', '_DIFF.dds', '_SREF.dds')]


if __name__ == '__main__':
    print(build())
