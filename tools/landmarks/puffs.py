"""Puffs of pipe smoke: an animated MODEL EFFECT of soft cloud cards that appear, drift and thin away (Bag End).

The stock game has no gentle puff particle (its short smokes are musket/cannon blasts with a flash and a jet; the user
saw "ballistic missiles"). So, like the Eye's beam (beam.py) and the glows (glow.py), this is our own model effect on
the stock industrial-lighthouse effect's material (FXShader_Skinned, AlphaMode 8 = additive, up to 32 skinned bones):
  * the mesh: one flat card per bone, facing south (-Y, the camera), a soft round wisp of smoke in the texture's alpha;
  * the skeleton: World + one bone per card, all at the origin at rest;
  * the animation: each card bone's POSITION follows a D3K8uC8u curve, the format and layout of the stock oil rig's
    idle animation (vendor/civ5/fx_oil_heavy_idlea.gr2, from the game's packs): a clamped quadratic B-spline with 8-bit
    knots and 8-bit controls (value = byte * scale + offset per axis), one knot per tick (duration / 255 s);
  * a card is "off" EDGE-ON: turned 90 degrees about the vertical (the game's camera never turns, so an edge-on card
    has no width), on the stock rotation curves (D4nK16uC15u, as the Eye's); it only moves between its hiding place
    under the ground and its puff while edge-on (any jump is blended over ~0.2 s, and a visible card rushing up from
    the ground was what the user saw in v6). A puff = its cards open from slivers in front of a face, drift apart,
    upwards and downwind, then close to slivers one by one, so the cloud spreads, grows fainter and thins out to
    nothing. Scale is never animated (the stock game never does it either).
Effects hang on a bone of the landmark and are drawn in the model's FILE units (glow.py), so positions here are file
units relative to that bone and the VisEffect Scale is 1.0.
"""
import copy
import math
import os
import struct

import numpy as np

import dds
import gr2
import lmodel

OIL_ANIM = os.path.join(lmodel.VENDOR, 'fx_oil_heavy_idlea.gr2')


def texture(path, px=256, color=(236, 233, 226), strength=0.5, seed=5):
    """A soft round wisp: colour constant, the cloud in the alpha (a soft disc broken up by noise)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:px, 0:px]
    u, v = (xx + 0.5) / px * 2 - 1, (yy + 0.5) / px * 2 - 1
    r = np.hypot(u, v)
    noise = np.zeros((px, px))
    for octave, amp in ((4, 0.5), (8, 0.3), (16, 0.2)):        # value noise, upsampled
        g = rng.random((octave + 1, octave + 1))
        gi = np.kron(g, np.ones((px // octave + 1, px // octave + 1)))[:px, :px]
        k = max(1, px // octave // 2)
        ker = np.ones(k) / k
        gi = np.apply_along_axis(lambda m: np.convolve(m, ker, mode='same'), 0, gi)
        gi = np.apply_along_axis(lambda m: np.convolve(m, ker, mode='same'), 1, gi)
        noise += amp * gi
    disc = np.clip(1.0 - r, 0, 1) ** 1.6
    a = strength * disc * (0.55 + 0.9 * (noise - noise.min()) / (np.ptp(noise) + 1e-9))
    a *= np.clip((1.0 - r) / 0.15, 0, 1)                          # nothing at the card's edge
    img = np.zeros((px, px, 4), np.float32)
    img[..., :3] = color
    img[..., 3] = 255 * np.clip(a, 0, 1)
    dds.write_dxt3(path, np.clip(img, 0, 255).astype(np.uint8))


def _curve_d3k8(members, samples, T):
    """D3K8uC8u Variant for a position given at the Greville points of a clamped quadratic B-spline with one span
    per tick (255 ticks over T): samples = [(x, y, z)] * 257."""
    ooks = 255.0 / T
    trunc = struct.unpack('<I', struct.pack('<f', ooks))[0] >> 16     # the top 16 bits of the float, as stored
    ooks_t = struct.unpack('<f', struct.pack('<I', trunc << 16))[0]
    ticks = 255
    knots = [0, 0] + list(range(1, ticks)) + [ticks]                  # stock layout: 0, eps, interior, end
    assert len(knots) == len(samples) == ticks + 2
    P = np.array(samples, float)
    lo, hi = P.min(0), P.max(0)
    scale = np.where(hi - lo > 1e-6, (hi - lo) / 255.0, 1.0)
    q = np.clip(np.round((P - lo) / scale), 0, 255).astype(int)
    kc = knots + [int(c) for row in q for c in row]
    del ooks_t
    return gr2.Variant(members, {'CurveDataHeader_D3K8uC8u': {'Format': 11, 'Degree': 2}, 'OneOverKnotScaleTrunc': trunc,
                                 'ControlScales': [float(x) for x in scale], 'ControlOffsets': [float(x) for x in lo],
                                 'KnotsControls': [{'UInt8': x} for x in kc]})


def greville(T, ticks=255):
    """Greville abscissae of the clamped quadratic B-spline with `ticks` uniform spans on [0, T] (ticks + 2 points)."""
    h = T / ticks
    U = [0.0, 0.0, 0.0] + [h * i for i in range(1, ticks)] + [T, T, T]
    return [(U[i + 1] + U[i + 2]) / 2 for i in range(ticks + 2)]


def glow_texture(path, px=256, color=(255, 166, 78), core=(255, 226, 170), strength=0.55):
    """A soft round warm light (candlelight in a window): a wide halo round a whiter core, in the alpha."""
    yy, xx = np.mgrid[0:px, 0:px]
    r = np.hypot((xx + 0.5) / px * 2 - 1, (yy + 0.5) / px * 2 - 1)
    a = strength * (0.65 * np.exp(-(r / 0.42) ** 2) + 0.35 * np.exp(-(r / 0.16) ** 2))
    a *= np.clip((1.0 - r) / 0.2, 0, 1)
    k = np.exp(-(r / 0.25) ** 2)[..., None]
    img = np.zeros((px, px, 4), np.float32)
    img[..., :3] = np.array(color, np.float32) * (1 - k) + np.array(core, np.float32) * k
    img[..., 3] = 255 * np.clip(a, 0, 1)
    dds.write_dxt3(path, np.clip(img, 0, 255).astype(np.uint8))


def _yaw_curve(yaw_fn, T, spans=600):
    """D4nK16uC15u curve dict (lmodel.Curves.yaw) for a turn about +Z of yaw_fn(t) degrees: controls sampled at the
    Greville points of a clamped quadratic B-spline (no least-squares fit: it is far too slow at this many spans)."""
    import granim
    one_over = 65535.0 / T
    h = T / spans
    knots = [0.0, 0.002] + [h * i for i in range(1, spans)] + [T]
    ctrl = [yaw_fn(t) for t in greville(T, spans)]
    cq = []
    for deg in ctrl:
        cq += list(granim.quat_encode(granim.yaw_quat(deg)))
    return dict(knots=[int(round(k * one_over)) for k in knots], controls=cq, one_over=one_over, entries=0x0000,
                degrees=ctrl)


def write(out_dir, name, cards, T, tex_args=None, tex_fn=None, yaw_spans=600):
    """cards: [(half_size, fn, yaw_fn)] where fn(t) -> (x, y, z) in FILE units relative to the effect's bone at time t
    of the loop (T seconds) and yaw_fn(t) -> degrees about the vertical (90 = edge-on to the camera = hidden). Writes <name>.gr2/.fxsxml, <name>_IdleA.gr2, <name>_DIFF.dds; returns the file names."""
    assert len(cards) <= 30, 'FXShader_Skinned: at most 32 bones (World + cards)'
    f = gr2.read(lmodel.FX_TEMPLATE)
    root = f.root()
    skel = root['Skeletons'][0]
    proto = skel['Bones'][1]
    bones = [lmodel.make_bone(skel['Bones'][0], 'World', -1, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))]
    names = ['c%02d' % i for i in range(len(cards))]
    for n in names:
        bones.append(lmodel.make_bone(proto, n, 0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
    skel['Bones'] = bones
    mesh = root['Meshes'][0]
    vd = mesh['PrimaryVertexData']
    members = vd['Vertices'].members
    vb = bytearray()
    tris = []
    for i, (hs, _, _) in enumerate(cards):
        for (x, z, u, v) in ((-hs, -hs, 0.0, 1.0), (hs, -hs, 1.0, 1.0), (hs, hs, 1.0, 0.0), (-hs, hs, 0.0, 0.0)):
            vb += struct.pack('<3f4B4B12f', x, -0.01 * i, z, 255, 0, 0, 0, i, 0, 0, 0,
                              0.0, -1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0, u, v, 0.0)
        b = 4 * i
        tris += [(b, b + 1, b + 2), (b, b + 2, b + 3)]                # counter-clockwise seen from -Y
    vd['Vertices'] = gr2.Variant(members, bytes(vb))
    mesh['PrimaryTopology'].update(lmodel.topology(tris))
    bb0 = mesh['BoneBindings'][0]
    mesh['BoneBindings'] = []
    for n, (hs, _, _) in zip(names, cards):                           # binding i = card i (its BoneIndices)
        bb = copy.deepcopy(bb0)
        bb['BoneName'] = n
        bb['OBBMin'], bb['OBBMax'] = [-hs, -0.5, -hs], [hs, 0.5, hs]
        mesh['BoneBindings'].append(bb)
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
    (tex_fn or texture)(os.path.join(out_dir, tex), **(tex_args or {}))

    # the animation: the stock IdleA's track group, a track per bone; card positions on D3K8uC8u curves
    a = gr2.read(lmodel.ANIM_TEMPLATE)
    ar = a.root()
    curves = lmodel.Curves(ar)
    oil = gr2.read(OIL_ANIM).root()
    m_d3k8 = [t for t in oil['TrackGroups'][0]['TransformTracks'] if t['Name'] == 'Point01'][0][
        'PositionCurve']['CurveData'].members
    ts = greville(T)
    tracks = [lmodel.track(curves, 'World')]
    for n, (_, fn, yaw_fn) in zip(names, cards):
        tr = lmodel.track(curves, n, yaw=_yaw_curve(yaw_fn, T, yaw_spans))
        tr['PositionCurve'] = {'CurveData': _curve_d3k8(m_d3k8, [fn(t) for t in ts], T)}
        tracks.append(tr)
    tg = ar['TrackGroups'][0]
    tg['TransformTracks'] = sorted(tracks, key=lambda t: t['Name'].lower())
    ar['Animations'][0]['Duration'] = float(T)
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


def evaluate(curve_value, T, t):
    """Decode a D3K8uC8u curve written by write() at time t (for the self-check)."""
    v = curve_value
    kc = [x['UInt8'] for x in v['KnotsControls']]
    n = len(kc) // 4
    knots = kc[:n]
    ooks = struct.unpack('<f', struct.pack('<I', v['OneOverKnotScaleTrunc'] << 16))[0]
    ctrl = [[kc[n + 3 * i + d] * v['ControlScales'][d] + v['ControlOffsets'][d] for d in range(3)] for i in range(n)]
    Tk = knots[-1] / ooks
    import granim
    U = granim.full_knots(Tk, n - 2)
    w = granim.basis(min(t, Tk), U, n)
    return [sum(w[i] * ctrl[i][d] for i in range(n)) for d in range(3)]
