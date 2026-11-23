"""The searching beam: an animated MODEL EFFECT cloned from the stock industrial lighthouse beam.

Stock FX_Ind_Lighthouse: 5 stacked additive planes (FXShader_Skinned, AlphaMode 8) along +Y,
skinned to bones World -> Point01 (base, turned by its IdleA animation) -> Point02 (tip), the beam's
shape carried by the texture's alpha. Ours keeps that mesh, material and skeleton, but:
  * the geometry points SOUTH (-Y, towards the camera at rest) and tilts down by TILT degrees,
    so it sweeps the land in front of the tower;
  * Point01 turns with the SAME gaze curve as the Eye (granim), instead of a full turn;
  * a fiery texture (orange, alpha-shaped like the stock one but wider).
The effect is attached to a STATIC bone at the Eye's pivot and turns itself, so it can never
inherit the Eye's turn twice.
"""
import copy
import math
import os

import dds
import gr2
import lmodel
import numpy as np

BEAM = 'MEC_EyeBeam'


def _rot(tilt_deg):
    """Rz(180) then Rx(tilt): +Y -> -Y, tilted down."""
    a = math.radians(tilt_deg)
    ca, sa = math.cos(a), math.sin(a)

    def f(v):
        x, y, z = -v[0], -v[1], v[2]
        return [x, y * ca - z * sa, y * sa + z * ca]
    return f


def texture(path, size=128):
    """Fiery beam: colour constant, the shape in alpha (bright core along the axis, fading to the tip)."""
    u = (np.arange(size) + 0.5) / size
    v = (np.arange(size) + 0.5) / size              # row 0 = tip (v = 0), last row = base (v = 1)
    across = np.exp(-((u - 0.5) / 0.10) ** 2)        # a searchlight: a soft halo ...
    core = np.exp(-((u - 0.5) / 0.035) ** 2)         # ... round a hot core
    along = np.clip(v / 0.75, 0, 1) ** 1.2 * np.clip((1.0 - v) / 0.08, 0, 1)    # fade to tip, soft start
    a = np.clip(along[:, None] * (0.35 * across[None, :] + 0.65 * core[None, :]), 0, 1)
    img = np.zeros((size, size, 4), np.float32)
    img[..., 0] = 255
    img[..., 1] = 150 + 70 * core[None, :]
    img[..., 2] = 40 + 60 * core[None, :]
    img[..., 3] = 170 * a
    dds.write_dxt3(path, np.clip(img, 0, 255).astype(np.uint8))


def write(out_dir, gaze, tilt):
    """Writes MEC_EyeBeam.gr2/.fxsxml, MEC_EyeBeam_IdleA.gr2, MEC_EyeBeam_DIFF.dds. Returns file names."""
    f = gr2.read(lmodel.FX_TEMPLATE)
    root = f.root()
    R = _rot(tilt)
    mesh = root['Meshes'][0]
    for vtx in mesh['PrimaryVertexData']['Vertices'].value:
        for k in ('Position', 'Normal', 'Tangent', 'Binormal'):
            vtx[k] = R(vtx[k])
    bones = root['Skeletons'][0]['Bones']
    world = {}
    for b in bones:                         # identity orientations; re-place the positions
        name = b['Name']
        parent = bones[b['ParentIndex']]['Name'] if b['ParentIndex'] >= 0 else None
        p0 = b['Transform']['Position']
        wp_orig = [p0[i] + (world[parent][1][i] if parent else 0.0) for i in range(3)]
        wp = R(wp_orig)
        local = [wp[i] - (world[parent][0][i] if parent else 0.0) for i in range(3)]
        b['Transform']['Position'] = local
        b['InverseWorldTransform'] = lmodel.inv_translation(wp)
        world[name] = (wp, wp_orig)
    verts = mesh['PrimaryVertexData']['Vertices'].value
    for j, bb in enumerate(mesh['BoneBindings']):   # OBBs in bone space, from the vertices bound to each bone
        wp = world[bb['BoneName']][0]
        pts = [[v['Position'][i] - wp[i] for i in range(3)] for v in verts if v['BoneIndices'][0] == j]
        if pts:
            bb['OBBMin'], bb['OBBMax'] = lmodel.obb(pts)
    tex = BEAM + '_DIFF.dds'

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
    root['FromFileName'] = BEAM + '.blend'
    os.makedirs(out_dir, exist_ok=True)
    gr2.write(os.path.join(out_dir, BEAM + '.gr2'), f.root_type, root, f.tag)
    texture(os.path.join(out_dir, tex))

    # animation: the stock IdleA, with Point01 turning by the gaze curve and the moved bone positions
    a = gr2.read(lmodel.ANIM_TEMPLATE)
    ar = a.root()
    curves = lmodel.Curves(ar)
    c = lmodel.granim.yaw_curve_value(gaze['fn'], gaze['T'], gaze['spans'])
    local = {b['Name']: b['Transform']['Position'] for b in bones}
    for t in ar['TrackGroups'][0]['TransformTracks']:
        p = local[t['Name']]
        t['PositionCurve'] = curves.const3(p) if any(abs(x) > 1e-9 for x in p) else curves.identity(3)
        t['OrientationCurve'] = curves.yaw(c) if t['Name'] == 'Point01' else curves.identity(4)
    ar['Animations'][0]['Duration'] = float(gaze['T'])
    ar['Animations'][0]['Name'] = BEAM + '_IdleA'
    ar['FromFileName'] = BEAM + '.blend'
    gr2.write(os.path.join(out_dir, BEAM + '_IdleA.gr2'), a.root_type, ar, a.tag)

    L = ['<Asset>', '\t<Mesh file="%s.gr2"/>' % BEAM,
         '\t<Animation file="%s_IdleA.gr2" name="IdleA" ec="1000" source="Max"/>' % BEAM,
         '\t<Texture file="FX_Blk_Blk4x4.dds"/>', '\t<Texture file="FX_Wht_Wht4x4.dds"/>',
         '\t<Texture file="%s"/>' % tex,
         '\t<DecisionTree file="AnimatedModelEffect_DecisionTree.ddtxml" source="Tool"/>', '</Asset>']
    with open(os.path.join(out_dir, BEAM + '.fxsxml'), 'w', newline='\r\n') as fh:
        fh.write('\n'.join(L) + '\n')
    return [BEAM + '.gr2', BEAM + '_IdleA.gr2', BEAM + '.fxsxml', tex]
