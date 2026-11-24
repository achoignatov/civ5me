"""A glowing picture: a static additive MODEL EFFECT, e.g. the ithildin of the Doors of Durin (Moria v4).

Built like the Eye's beam (beam.py), which drew in game: the stock industrial lighthouse beam's material
(FXShader_Skinned, AlphaMode 8 = additive), skeleton and IdleA animation, but
  * our own mesh: flat quads standing just in front of a wall, facing south (-Y, the camera), all on bone Point01;
  * our own texture: the colour is constant (pale ithildin blue-white), the picture is in the ALPHA (crisp lines
    with a soft halo), so on screen the lines add light to whatever is behind them;
  * every animation track is still (identity), so nothing moves.
Effects hang on a bone of the model and are drawn in the model's FILE units (the writer's x4 of in-game units at
improvement Scale 0.25; the beam's length proves the effect scales with the model), so the quads are written in
file units around the bone and the VisEffect Scale is 1.0.
"""
import os
import struct

import numpy as np

import dds
import gr2
import lmodel


def texture(path, lines, box, px=1024, color=(188, 226, 255), core=1.0, halo=0.32, sigma=(0.22, 0.9),
            alpha_keep=0.6):
    """lines: [(x0, z0, x1, z1, width)] in in-game units on the wall; box = (X0, X1, Z0, Z1) the quad.
    Alpha = crisp lines (core) + a narrow and a wide halo; row 0 = the top of the quad."""
    X0, X1, Z0, Z1 = box
    W = px
    H = px
    xs = X0 + (np.arange(W) + 0.5) / W * (X1 - X0)
    zs = Z1 - (np.arange(H) + 0.5) / H * (Z1 - Z0)          # top row first
    X, Z = np.meshgrid(xs, zs)
    d = np.full(X.shape, 1e9)
    for (x0, z0, x1, z1, w) in lines:
        vx, vz = x1 - x0, z1 - z0
        L2 = vx * vx + vz * vz or 1e-9
        t = np.clip(((X - x0) * vx + (Z - z0) * vz) / L2, 0, 1)
        d = np.minimum(d, np.hypot(X - (x0 + t * vx), Z - (z0 + t * vz)) - w / 2)
    pix = (X1 - X0) / W
    line = np.clip(0.5 - d / pix, 0, 1)                      # anti-aliased line coverage
    dd = np.maximum(d, 0)
    a = core * line + halo * (0.85 * np.exp(-(dd / sigma[0]) ** 2) + 0.15 * np.exp(-(dd / sigma[1]) ** 2))
    # fade out at the quad's border so its edge never shows
    ex = np.minimum(np.minimum(X - X0, X1 - X), np.minimum(Z - Z0, Z1 - Z)) / (0.04 * (X1 - X0))
    a *= np.clip(ex, 0, 1)
    img = np.zeros((H, W, 4), np.float32)
    img[..., 0], img[..., 1], img[..., 2] = color
    hot = np.clip(line, 0, 1)                                # line cores whiter
    for c in range(3):
        img[..., c] = img[..., c] + (255 - img[..., c]) * 0.6 * hot
    img[..., 3] = 255 * np.clip(a, 0, 1)
    dds.write_dxt3(path, np.clip(img, 0, 255).astype(np.uint8), alpha_keep=alpha_keep)
    return img


def write(out_dir, name, quads, tex_args):
    """quads: [(x0, x1, z0, z1, y)] in FILE units relative to the effect's bone (the quad faces -Y, u along +X,
    v down from z1). tex_args: kwargs for texture(). Writes <name>.gr2/.fxsxml, <name>_IdleA.gr2, <name>_DIFF.dds;
    returns the file names."""
    f = gr2.read(lmodel.FX_TEMPLATE)
    root = f.root()
    mesh = root['Meshes'][0]
    vd = mesh['PrimaryVertexData']
    members = vd['Vertices'].members
    assert [m.name for m in members] == ['Position', 'BoneWeights', 'BoneIndices', 'Normal', 'Tangent', 'Binormal',
                                         'TextureCoordinates0'], [m.name for m in members]
    vb = bytearray()
    tris = []
    for k, (x0, x1, z0, z1, y) in enumerate(quads):
        for (x, z, u, v) in ((x0, z0, 0.0, 1.0), (x1, z0, 1.0, 1.0), (x1, z1, 1.0, 0.0), (x0, z1, 0.0, 0.0)):
            # every vertex fully on mesh bone binding 0 (Point01, at the origin, never moved)
            vb += struct.pack('<3f4B4B12f', x, y, z, 255, 0, 0, 0, 0, 0, 0, 0,
                              0.0, -1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0, u, v, 0.0)
        b = 4 * k
        tris += [(b, b + 1, b + 2), (b, b + 2, b + 3)]      # counter-clockwise seen from -Y
    vd['Vertices'] = gr2.Variant(members, bytes(vb))
    mesh['PrimaryTopology'].update(lmodel.topology(tris))
    pts = [(x, y, z) for (x0, x1, z0, z1, y) in quads for x in (x0, x1) for z in (z0, z1)]
    lo, hi = lmodel.obb(pts)
    for bb in mesh['BoneBindings']:
        bb['OBBMin'], bb['OBBMax'] = ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
    mesh['BoneBindings'][0]['OBBMin'], mesh['BoneBindings'][0]['OBBMax'] = lo, hi
    tex = name + '_DIFF.dds'

    def swap(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and 'FX_Ind_Lighthouse_base_01' in v:
                    o[k] = tex
                else:
                    swap(v)
        elif isinstance(o, list):
            for x in o:
                swap(x)
        elif isinstance(o, gr2.Variant):
            swap(o.value)
    swap(root['Materials'])
    root['FromFileName'] = name + '.blend'
    os.makedirs(out_dir, exist_ok=True)
    gr2.write(os.path.join(out_dir, name + '.gr2'), f.root_type, root, f.tag)
    texture(os.path.join(out_dir, tex), **tex_args)

    # animation: the stock IdleA with every track still
    a = gr2.read(lmodel.ANIM_TEMPLATE)
    ar = a.root()
    curves = lmodel.Curves(ar)
    local = {b['Name']: b['Transform']['Position'] for b in root['Skeletons'][0]['Bones']}
    for t in ar['TrackGroups'][0]['TransformTracks']:
        p = local[t['Name']]
        t['PositionCurve'] = curves.const3(p) if any(abs(x) > 1e-9 for x in p) else curves.identity(3)
        t['OrientationCurve'] = curves.identity(4)
    ar['Animations'][0]['Name'] = name + '_IdleA'
    ar['FromFileName'] = name + '.blend'
    gr2.write(os.path.join(out_dir, name + '_IdleA.gr2'), a.root_type, ar, a.tag)

    L = ['<Asset>', '\t<Mesh file="%s.gr2"/>' % name,
         '\t<Animation file="%s_IdleA.gr2" name="IdleA" ec="1000" source="Max"/>' % name,
         '\t<Texture file="FX_Blk_Blk4x4.dds"/>', '\t<Texture file="FX_Wht_Wht4x4.dds"/>',
         '\t<Texture file="%s"/>' % tex,
         '\t<DecisionTree file="AnimatedModelEffect_DecisionTree.ddtxml" source="Tool"/>', '</Asset>']
    with open(os.path.join(out_dir, name + '.fxsxml'), 'w', newline='\r\n') as fh:
        fh.write('\n'.join(L) + '\n')
    return [name + '.gr2', name + '_IdleA.gr2', name + '.fxsxml', tex]
