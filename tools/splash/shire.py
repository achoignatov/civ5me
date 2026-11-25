"""Hobbits loading-screen wallpaper: a procedural Shire at golden hour, rendered with Cycles.

  blender -b --factory-startup -P tools/splash/shire.py -- [--res 960] [--samples 32] [--out build/splash/prev]

Writes <out>_rgb.exr (linear) and <out>_z.exr (depth). tools/splash/post.py turns them into the final PNG + DDS.
Everything is generated from fixed seeds, so the picture is reproducible.
"""
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.append(os.path.join(ROOT, 'build', 'venv', 'lib', 'python%d.%d' % sys.version_info[:2], 'site-packages'))
import numpy as np
import bpy
from mathutils import Vector, Matrix, Euler

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    return type(default)(ARGS[ARGS.index(name) + 1]) if name in ARGS else default
RES_X = arg('--res', 960)
RES_Y = RES_X * 9 // 16
SAMPLES = arg('--samples', 32)
OUT = os.path.join(ROOT, arg('--out', 'build/splash/prev'))
DETAIL = arg('--detail', 1.0)          # scales instance counts (previews can use less)

# --------------------------------------------------------------------------- layout
CAM = Vector((0.6, -2.0, 3.6))
CAM_YAW = math.radians(9.0)             # + turns left (toward -x)
CAM_PITCH = math.radians(-2.5)
SUN_AZ = math.radians(13.0)             # angle from +Y toward +X
SUN_EL = math.radians(6.5)
SUN_DIR = Vector((math.sin(SUN_AZ) * math.cos(SUN_EL), math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))

HILL_C = np.array([-12.0, 22.5])        # Bag-End style hill
HILL_R = 12.0
HILL_H = 3.6
DOOR_DIR = np.array([0.52, -0.85]); DOOR_DIR /= np.linalg.norm(DOOR_DIR)
WALL_R = 5.6
WALL_SPAN = math.radians(34)

def view_cx(y):
    return CAM.x - math.tan(CAM_YAW) * (y - CAM.y)

def view_hw(y):
    return (y - CAM.y) * 0.75 + 2.0

# --------------------------------------------------------------------------- noise
def _hash(ix, iy, seed):
    h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 + (seed * 1013904223 & 0xFFFFFFF)) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)

def vnoise(x, y, seed=0):
    xi, yi = np.floor(x), np.floor(y)
    fx, fy = x - xi, y - yi
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    xi = xi.astype(np.int64); yi = yi.astype(np.int64)
    a = _hash(xi, yi, seed); b = _hash(xi + 1, yi, seed)
    c = _hash(xi, yi + 1, seed); d = _hash(xi + 1, yi + 1, seed)
    return (a + (b - a) * ux) + ((c + (d - c) * ux) - (a + (b - a) * ux)) * uy

def fbm(x, y, octaves=5, seed=0, lac=2.03, gain=0.5):
    s, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        s = s + amp * (vnoise(x, y, seed + o * 17) * 2 - 1)
        norm += amp; amp *= gain; x = x * lac + 3.1; y = y * lac - 1.7
    return s / norm

def ridged(x, y, octaves=6, seed=0):
    s, amp, norm, w = 0.0, 1.0, 0.0, 1.0
    for o in range(octaves):
        n = 1 - np.abs(vnoise(x, y, seed + o * 31) * 2 - 1)
        n = n * n * w
        w = np.clip(n * 1.6, 0, 1)
        s = s + amp * n; norm += amp; amp *= 0.5; x = x * 2.1 + 5.3; y = y * 2.1 - 2.9
    return s / norm

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)

# --------------------------------------------------------------------------- terrain function
PATH_MAIN = np.array([[0.4, -4], [0.0, 3], [-1.2, 7], [-2.8, 10.5], [-4.6, 13.4], [-6.2, 15.4], [-8.0, 17.4]])
PATH_VALLEY = np.array([[-1.2, 7], [0.8, 13], [3.5, 21], [6.5, 31], [9.0, 46], [11.5, 64], [13.0, 80], [13.5, 95],
                        [15.0, 115], [19.0, 140]])

def river_y(x):
    return 86 + 13 * np.sin(x / 41.0 + 0.6) + 5 * np.sin(x / 13.0 + 1.3)

def seg_dist(px, py, poly):
    d = np.full(px.shape, 1e9)
    for (ax, ay), (bx, by) in zip(poly[:-1], poly[1:]):
        vx, vy = bx - ax, by - ay
        t = np.clip(((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy), 0, 1)
        d = np.minimum(d, np.hypot(px - ax - t * vx, py - ay - t * vy))
    return d

def hill_parts(x, y):
    dx, dy = x - HILL_C[0], y - HILL_C[1]
    r = np.hypot(dx, dy)
    prof = HILL_H * np.clip(1 - (r / HILL_R) ** 2, 0, 1) ** 1.5
    ang = np.arctan2(dx * DOOR_DIR[1] - dy * DOOR_DIR[0], dx * DOOR_DIR[0] + dy * DOOR_DIR[1])
    sector = smoothstep(WALL_SPAN + 0.12, WALL_SPAN - 0.05, np.abs(ang))
    # the front of the hill is cut vertically at WALL_R inside the sector (the hobbit-hole facade)
    cut = sector * smoothstep(WALL_R - 0.05, WALL_R + 0.05, r)
    return prof * (1 - cut), r, ang, sector

YARD_Z = 0.0

def height(x, y, with_path=True, with_yard=True):
    x = np.asarray(x, float); y = np.asarray(y, float)
    # near meadow: gentle slope down toward the valley
    yc = np.clip(y, -10, 75)
    # the right side drops steeply into the river valley; the left stays a ridge (Bag End) a little longer
    y0 = 9.0 + 24.0 * (1 - smoothstep(-11, -3, x))
    sd = yc - y0
    base = -0.05 * yc - 0.40 * (np.sqrt(sd * sd + 20) + sd) / 2
    base = np.maximum(base, -24.0 - 1.0 * fbm(x / 30, y / 30, 2, 9))
    knoll = 1.6 * np.exp(-((x - CAM.x) ** 2 / 110.0 + (y - 1.0) ** 2 / 50.0))
    base = base + knoll
    valley = -1.5 * smoothstep(60, 85, y) * (1 - smoothstep(95, 150, y))
    far = smoothstep(100, 300, y) * (30 + 0.05 * np.clip(y - 300, 0, 3000))
    rolling = (0.35 + 0.012 * np.clip(y, 0, 2000)) * fbm(x / 38.0, y / 38.0, 5, 3)
    hills_far = smoothstep(120, 400, y) * (35 * (fbm(x / 260.0, y / 260.0, 5, 11) + 0.35) + 14 * fbm(x / 90, y / 90, 3, 12))
    micro = 0.06 * fbm(x / 2.2, y / 2.2, 3, 5)
    h = base + valley + far + rolling + hills_far + micro
    # left foreground rises into the Bag End hill
    h = h + 2.6 * smoothstep(-2, -14, x) * smoothstep(-4, 8, y) * (1 - smoothstep(32, 48, y))
    hp, r, ang, sector = hill_parts(x, y)
    # flat front garden before the facade
    yard = sector * smoothstep(WALL_R + 5.0, WALL_R + 3.2, r) * smoothstep(WALL_R - 0.3, WALL_R, r) * with_yard
    h = h * (1 - yard) + YARD_Z * yard
    h = h + hp
    # river channel
    dr = np.abs(y - river_y(x))
    h = h - 2.0 * smoothstep(16, 3, dr) * smoothstep(60, 75, y) * (1 - smoothstep(110, 120, y))
    if with_path:
        dp = np.minimum(seg_dist(x, y, PATH_MAIN), seg_dist(x, y, PATH_VALLEY))
        h = h - 0.07 * smoothstep(0.9, 0.35, dp)
    return h

def path_mask(x, y):
    wob = 0.18 * fbm(x / 0.9, y / 0.9, 3, 41)
    d1 = seg_dist(x, y, PATH_MAIN)
    d2 = seg_dist(x, y, PATH_VALLEY)
    w2 = 0.75 + 0.25 * smoothstep(20, 80, y)
    return np.maximum(smoothstep(0.85, 0.55, d1 + wob), smoothstep(w2 + 0.15, w2 - 0.2, d2 + wob))

# --------------------------------------------------------------------------- blender helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def new_mesh_obj(name, verts, faces, coll=None):
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, np.float32)
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', verts.ravel())
    if faces is not None and len(faces):
        faces = np.asarray(faces, np.int32)
        k = faces.shape[1]
        me.loops.add(faces.size)
        me.loops.foreach_set('vertex_index', faces.ravel())
        me.polygons.add(len(faces))
        me.polygons.foreach_set('loop_start', np.arange(0, faces.size, k, dtype=np.int32))
        me.polygons.foreach_set('loop_total', np.full(len(faces), k, np.int32))
    me.update(calc_edges=True)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob

def set_attr(ob, name, vals, dom='POINT', typ='FLOAT'):
    a = ob.data.attributes.new(name, typ, dom)
    a.data.foreach_set('vector' if typ == 'FLOAT_VECTOR' else 'value', np.asarray(vals, np.float32).ravel())

def smooth(ob):
    ob.data.polygons.foreach_set('use_smooth', np.ones(len(ob.data.polygons), bool))

class NB:
    """tiny node-tree builder"""
    def __init__(self, mat):
        mat.use_nodes = True
        self.t = mat.node_tree
        self.t.nodes.clear()
        self.out = self.n('ShaderNodeOutputMaterial')
    def n(self, typ, **kw):
        nd = self.t.nodes.new(typ)
        for k, v in kw.items():
            if k.startswith('i_'):
                nd.inputs[k[2:].replace('_', ' ')].default_value = v
            else:
                setattr(nd, k, v)
        return nd
    def l(self, a, b):
        self.t.links.new(a, b)
        return b

def rgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)

def ramp(nb, stops, fac):
    r = nb.n('ShaderNodeValToRGB')
    els = r.color_ramp.elements
    while len(els) > len(stops):
        els.remove(els[-1])
    while len(els) < len(stops):
        els.new(0.5)
    for e, (p, c) in zip(els, stops):
        e.position = p; e.color = rgb(c) if isinstance(c, str) else c
    nb.l(fac, r.inputs['Fac'])
    return r

def tex_coord_obj(nb):
    return nb.n('ShaderNodeTexCoord').outputs['Object']

def noise(nb, vec, scale, detail=4, rough=0.55, dim=None):
    nd = nb.n('ShaderNodeTexNoise', i_Scale=scale, i_Detail=detail, i_Roughness=rough)
    if dim: nd.noise_dimensions = dim
    if vec is not None: nb.l(vec, nd.inputs['Vector'])
    return nd

def attr(nb, name, typ='GEOMETRY'):
    a = nb.n('ShaderNodeAttribute', attribute_name=name)
    a.attribute_type = typ
    return a

# --------------------------------------------------------------------------- materials
MATS = {}
def mat(name):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name)
    MATS[name] = m
    return m, NB(m)

def make_materials():
    # ---- terrain: grass / dry grass / dirt path / rock on steep
    m, nb = mat('terrain')
    geo = nb.n('ShaderNodeNewGeometry')
    pos = geo.outputs['Position']
    big = noise(nb, pos, 0.04, 5)
    mid = noise(nb, pos, 0.35, 6)
    fine = noise(nb, pos, 6.0, 8)
    grass1 = ramp(nb, [(0.3, '#2f4a14'), (0.5, '#4d6b1c'), (0.72, '#7a8a2e')], big.outputs['Fac'])
    dry = ramp(nb, [(0.35, '#6c7a2a'), (0.65, '#a59a4a')], mid.outputs['Fac'])
    mixg = nb.n('ShaderNodeMix', data_type='RGBA', i_Factor=0.35)
    nb.l(grass1.outputs['Color'], mixg.inputs[6]); nb.l(dry.outputs['Color'], mixg.inputs[7])
    nb.l(ramp(nb, [(0.45, (0, 0, 0, 1)), (0.7, (0.6, 0.6, 0.6, 1))], mid.outputs['Fac']).outputs['Color'], mixg.inputs['Factor'])
    dirt = ramp(nb, [(0.3, '#4a3624'), (0.6, '#7a5c3e'), (0.85, '#9a7a56')], fine.outputs['Fac'])
    rock = ramp(nb, [(0.3, '#4e4a42'), (0.7, '#7d776a')], fine.outputs['Fac'])
    pm = attr(nb, 'path')
    c1 = nb.n('ShaderNodeMix', data_type='RGBA')
    nb.l(mixg.outputs[2], c1.inputs[6]); nb.l(dirt.outputs['Color'], c1.inputs[7]); nb.l(pm.outputs['Fac'], c1.inputs['Factor'])
    # steepness from normal z
    sep = nb.n('ShaderNodeSeparateXYZ'); nb.l(geo.outputs['Normal'], sep.inputs[0])
    st = nb.n('ShaderNodeMapRange', i_From_Min=0.82, i_From_Max=0.55)
    nb.l(sep.outputs['Z'], st.inputs['Value'])
    c2 = nb.n('ShaderNodeMix', data_type='RGBA')
    nb.l(c1.outputs[2], c2.inputs[6]); nb.l(rock.outputs['Color'], c2.inputs[7]); nb.l(st.outputs['Result'], c2.inputs['Factor'])
    # Shire farmland: voronoi fields (wheat / pasture / fallow) with dark hedgerow seams, far from the camera only
    sepp = nb.n('ShaderNodeSeparateXYZ'); nb.l(pos, sepp.inputs[0])
    farm = nb.n('ShaderNodeMapRange', i_From_Min=70, i_From_Max=130)
    nb.l(sepp.outputs['Y'], farm.inputs['Value'])
    fmap = nb.n('ShaderNodeMapping', i_Scale=(1.0, 0.75, 1.0)); nb.l(pos, fmap.inputs['Vector'])
    fwarp = noise(nb, fmap.outputs['Vector'], 0.02, 3)
    fmix = nb.n('ShaderNodeMix', data_type='VECTOR', i_Factor=18.0)
    nb.l(fmap.outputs['Vector'], fmix.inputs[4]); nb.l(fwarp.outputs['Color'], fmix.inputs[5])
    fv = nb.n('ShaderNodeTexVoronoi', i_Scale=0.011, i_Randomness=0.85); nb.l(fmap.outputs['Vector'], fv.inputs['Vector'])
    fe = nb.n('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE', i_Scale=0.011, i_Randomness=0.85)
    nb.l(fmap.outputs['Vector'], fe.inputs['Vector'])
    fsep = nb.n('ShaderNodeSeparateColor'); nb.l(fv.outputs['Color'], fsep.inputs[0])
    fcol = ramp(nb, [(0.0, '#3e5a1a'), (0.3, '#5a7322'), (0.45, '#8a8a34'), (0.6, '#b39a48'), (0.72, '#6a7a2a'),
                     (0.86, '#4a6420'), (1.0, '#a08c3c')], fsep.outputs['Red'])
    fstripe = noise(nb, pos, 0.9, 2)
    fc2 = nb.n('ShaderNodeMix', data_type='RGBA', i_Factor=0.25)
    nb.l(fcol.outputs['Color'], fc2.inputs[6]); nb.l(c2.outputs[2], fc2.inputs[7])
    hedge = nb.n('ShaderNodeMapRange', i_From_Min=0.035, i_From_Max=0.0)
    nb.l(fe.outputs['Distance'], hedge.inputs['Value'])
    fc3 = nb.n('ShaderNodeMix', data_type='RGBA')
    nb.l(fc2.outputs[2], fc3.inputs[6]); fc3.inputs[7].default_value = rgb('#1d2a10'); nb.l(hedge.outputs['Result'], fc3.inputs['Factor'])
    farmf = nb.n('ShaderNodeMath', operation='MULTIPLY'); nb.l(farm.outputs['Result'], farmf.inputs[0])
    nb.l(st.outputs['Result'], farmf.inputs[1])
    farmf2 = nb.n('ShaderNodeMath', operation='SUBTRACT'); nb.l(farm.outputs['Result'], farmf2.inputs[0]); nb.l(farmf.outputs[0], farmf2.inputs[1])
    c3 = nb.n('ShaderNodeMix', data_type='RGBA')
    nb.l(c2.outputs[2], c3.inputs[6]); nb.l(fc3.outputs[2], c3.inputs[7]); nb.l(farmf2.outputs[0], c3.inputs['Factor'])
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.92)
    nb.l(c3.outputs[2], bs.inputs['Base Color'])
    bump = nb.n('ShaderNodeBump', i_Strength=0.35, i_Distance=0.05)
    nb.l(fine.outputs['Fac'], bump.inputs['Height']); nb.l(bump.outputs['Normal'], bs.inputs['Normal'])
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])

    # ---- mountains: rock + snow by height/normal, bluish
    m, nb = mat('mountain')
    geo = nb.n('ShaderNodeNewGeometry')
    sep = nb.n('ShaderNodeSeparateXYZ'); nb.l(geo.outputs['Position'], sep.inputs[0])
    sepn = nb.n('ShaderNodeSeparateXYZ'); nb.l(geo.outputs['Normal'], sepn.inputs[0])
    nz = noise(nb, geo.outputs['Position'], 0.004, 6)
    hz = nb.n('ShaderNodeMath', operation='ADD'); nb.l(sep.outputs['Z'], hz.inputs[0])
    nzs = nb.n('ShaderNodeMath', operation='MULTIPLY', i_Value=1.0); nzs.inputs[1].default_value = 500
    nb.l(nz.outputs['Fac'], nzs.inputs[0]); nb.l(nzs.outputs[0], hz.inputs[1])
    snowh = nb.n('ShaderNodeMapRange', i_From_Min=1500, i_From_Max=1750)
    nb.l(hz.outputs[0], snowh.inputs['Value'])
    snown = nb.n('ShaderNodeMapRange', i_From_Min=0.45, i_From_Max=0.7)
    nb.l(sepn.outputs['Z'], snown.inputs['Value'])
    sn = nb.n('ShaderNodeMath', operation='MULTIPLY')
    nb.l(snowh.outputs['Result'], sn.inputs[0]); nb.l(snown.outputs['Result'], sn.inputs[1])
    rock = ramp(nb, [(0.3, '#3d3c40'), (0.7, '#6a6460')], noise(nb, geo.outputs['Position'], 0.05, 6).outputs['Fac'])
    forest = ramp(nb, [(0.4, '#2a3518'), (0.6, '#3d4a22')], nz.outputs['Fac'])
    lowm = nb.n('ShaderNodeMapRange', i_From_Min=600, i_From_Max=1100)
    nb.l(hz.outputs[0], lowm.inputs['Value'])
    cr = nb.n('ShaderNodeMix', data_type='RGBA')
    nb.l(forest.outputs['Color'], cr.inputs[6]); nb.l(rock.outputs['Color'], cr.inputs[7]); nb.l(lowm.outputs['Result'], cr.inputs['Factor'])
    cs = nb.n('ShaderNodeMix', data_type='RGBA')
    nb.l(cr.outputs[2], cs.inputs[6]); cs.inputs[7].default_value = rgb('#f2f0f4'); nb.l(sn.outputs[0], cs.inputs['Factor'])
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.8)
    nb.l(cs.outputs[2], bs.inputs['Base Color'])
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])

    # ---- grass blades (instances): gradient base->tip + translucency (glows when backlit)
    for nm, (base, tip) in {'grass': ('#24380e', '#8fa23a'), 'grass_dry': ('#3d4512', '#c9b65e'),
                            'grass_dark': ('#1b2c0b', '#5f7a22')}.items():
        m, nb = mat(nm)
        t = attr(nb, 't')
        info = nb.n('ShaderNodeObjectInfo')
        var = noise(nb, nb.n('ShaderNodeNewGeometry').outputs['Position'], 0.6, 2)
        col = ramp(nb, [(0.0, base), (1.0, tip)], t.outputs['Fac'])
        hue = nb.n('ShaderNodeHueSaturation', i_Hue=0.5, i_Saturation=1.0, i_Value=1.0)
        mr = nb.n('ShaderNodeMapRange', i_To_Min=0.47, i_To_Max=0.53)
        nb.l(var.outputs['Fac'], mr.inputs['Value']); nb.l(mr.outputs['Result'], hue.inputs['Hue'])
        vv = nb.n('ShaderNodeMapRange', i_To_Min=0.7, i_To_Max=1.2)
        nb.l(info.outputs['Random'], vv.inputs['Value']); nb.l(vv.outputs['Result'], hue.inputs['Value'])
        nb.l(col.outputs['Color'], hue.inputs['Color'])
        bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.55)
        bs.inputs['Specular IOR Level'].default_value = 0.35
        nb.l(hue.outputs['Color'], bs.inputs['Base Color'])
        tr = nb.n('ShaderNodeBsdfTranslucent')
        nb.l(hue.outputs['Color'], tr.inputs['Color'])
        mx = nb.n('ShaderNodeMixShader', i_Fac=0.35)
        nb.l(bs.outputs[0], mx.inputs[1]); nb.l(tr.outputs[0], mx.inputs[2])
        nb.l(mx.outputs[0], nb.out.inputs['Surface'])

    # ---- leaves (per-leaf colour variation from the "lv" attribute)
    for nm, stops in {'leaf_oak': [(0.0, '#1e3410'), (0.55, '#3f5f1a'), (1.0, '#7d8f2a')],
                      'leaf_tree': [(0.0, '#1d3012'), (0.6, '#365520'), (1.0, '#6b7a28')],
                      'leaf_autumn': [(0.0, '#3a4a14'), (0.5, '#7d7420'), (1.0, '#b0782a')]}.items():
        m, nb = mat(nm)
        lv = attr(nb, 'lv')
        col = ramp(nb, stops, lv.outputs['Fac'])
        bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.5)
        bs.inputs['Specular IOR Level'].default_value = 0.4
        nb.l(col.outputs['Color'], bs.inputs['Base Color'])
        tr = nb.n('ShaderNodeBsdfTranslucent')
        tc = nb.n('ShaderNodeHueSaturation', i_Saturation=1.3, i_Value=1.4)
        nb.l(col.outputs['Color'], tc.inputs['Color']); nb.l(tc.outputs['Color'], tr.inputs['Color'])
        mx = nb.n('ShaderNodeMixShader', i_Fac=0.4)
        nb.l(bs.outputs[0], mx.inputs[1]); nb.l(tr.outputs[0], mx.inputs[2])
        nb.l(mx.outputs[0], nb.out.inputs['Surface'])

    # ---- bark
    m, nb = mat('bark')
    pos = nb.n('ShaderNodeTexCoord').outputs['Object']
    mp = nb.n('ShaderNodeMapping', i_Scale=(6, 6, 0.8)); nb.l(pos, mp.inputs['Vector'])
    nz = noise(nb, mp.outputs['Vector'], 4.0, 8, 0.65)
    col = ramp(nb, [(0.3, '#1d1712'), (0.6, '#3e352b'), (0.8, '#5c544a')], nz.outputs['Fac'])
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.9)
    nb.l(col.outputs['Color'], bs.inputs['Base Color'])
    bump = nb.n('ShaderNodeBump', i_Strength=0.8, i_Distance=0.03)
    nb.l(nz.outputs['Fac'], bump.inputs['Height']); nb.l(bump.outputs['Normal'], bs.inputs['Normal'])
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])

    # ---- painted green door (vertical planks)
    m, nb = mat('door')
    pos = tex_coord_obj(nb)
    wave = nb.n('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X', i_Scale=9.0, i_Distortion=0.0, i_Detail=0.0)
    nb.l(pos, wave.inputs['Vector'])
    planks = nb.n('ShaderNodeMath', operation='POWER', i_Value=1.0); planks.inputs[1].default_value = 0.08
    nb.l(wave.outputs['Fac'], planks.inputs[0])
    wear = noise(nb, pos, 9.0, 6)
    col = ramp(nb, [(0.35, '#0e3a1f'), (0.6, '#16502a'), (0.8, '#2b6a3a')], wear.outputs['Fac'])
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.45)
    nb.l(col.outputs['Color'], bs.inputs['Base Color'])
    bump = nb.n('ShaderNodeBump', i_Strength=0.6, i_Distance=0.01)
    nb.l(planks.outputs[0], bump.inputs['Height']); nb.l(bump.outputs['Normal'], bs.inputs['Normal'])
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])

    m, nb = mat('brass')
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Metallic=1.0, i_Roughness=0.28, i_Base_Color=rgb('#d9a441'))
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])

    # ---- weathered wood (frames, fence)
    m, nb = mat('wood')
    pos = tex_coord_obj(nb)
    mp = nb.n('ShaderNodeMapping', i_Scale=(1, 1, 12)); nb.l(pos, mp.inputs['Vector'])
    nz = noise(nb, mp.outputs['Vector'], 3.0, 8)
    col = ramp(nb, [(0.3, '#3b2a1c'), (0.6, '#6a5038'), (0.85, '#8c7458')], nz.outputs['Fac'])
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.8)
    nb.l(col.outputs['Color'], bs.inputs['Base Color'])
    bump = nb.n('ShaderNodeBump', i_Strength=0.5, i_Distance=0.01)
    nb.l(nz.outputs['Fac'], bump.inputs['Height']); nb.l(bump.outputs['Normal'], bs.inputs['Normal'])
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])

    # ---- mossy dry-stone facade (voronoi stones)
    m, nb = mat('stone')
    pos = tex_coord_obj(nb)
    mp = nb.n('ShaderNodeMapping', i_Scale=(2.2, 2.2, 3.4)); nb.l(pos, mp.inputs['Vector'])
    vor = nb.n('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE', i_Scale=2.2)
    nb.l(mp.outputs['Vector'], vor.inputs['Vector'])
    vorc = nb.n('ShaderNodeTexVoronoi', i_Scale=2.2); nb.l(mp.outputs['Vector'], vorc.inputs['Vector'])
    mortar = nb.n('ShaderNodeMapRange', i_From_Min=0.0, i_From_Max=0.07)
    nb.l(vor.outputs['Distance'], mortar.inputs['Value'])
    sc = ramp(nb, [(0.0, '#5a554c'), (0.5, '#857c6c'), (1.0, '#a39880')], vorc.outputs['Color'])
    moss = noise(nb, pos, 1.4, 6)
    mossm = nb.n('ShaderNodeMapRange', i_From_Min=0.52, i_From_Max=0.62)
    nb.l(moss.outputs['Fac'], mossm.inputs['Value'])
    c1 = nb.n('ShaderNodeMix', data_type='RGBA')
    nb.l(sc.outputs['Color'], c1.inputs[6]); c1.inputs[7].default_value = rgb('#4a5a1e'); nb.l(mossm.outputs['Result'], c1.inputs['Factor'])
    c2 = nb.n('ShaderNodeMix', data_type='RGBA')
    c2.inputs[6].default_value = rgb('#2a241c'); nb.l(c1.outputs[2], c2.inputs[7]); nb.l(mortar.outputs['Result'], c2.inputs['Factor'])
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.85)
    nb.l(c2.outputs[2], bs.inputs['Base Color'])
    bump = nb.n('ShaderNodeBump', i_Strength=1.0, i_Distance=0.04)
    nb.l(mortar.outputs['Result'], bump.inputs['Height']); nb.l(bump.outputs['Normal'], bs.inputs['Normal'])
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])

    m, nb = mat('brick')
    pos = tex_coord_obj(nb)
    br = nb.n('ShaderNodeTexBrick', i_Scale=9.0, i_Mortar_Size=0.015)
    br.inputs['Color1'].default_value = rgb('#6b3a26'); br.inputs['Color2'].default_value = rgb('#8a5236')
    br.inputs['Mortar'].default_value = rgb('#3a3128')
    nb.l(pos, br.inputs['Vector'])
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.9)
    nb.l(br.outputs['Color'], bs.inputs['Base Color'])
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])

    # ---- warm window glass
    m, nb = mat('window')
    em = nb.n('ShaderNodeEmission', i_Strength=9.0, i_Color=rgb('#ffb24a'))
    gl = nb.n('ShaderNodeBsdfGlossy', i_Roughness=0.05)
    fr = nb.n('ShaderNodeFresnel', i_IOR=1.5)
    mx = nb.n('ShaderNodeMixShader')
    nb.l(fr.outputs[0], mx.inputs['Fac']); nb.l(em.outputs[0], mx.inputs[1]); nb.l(gl.outputs[0], mx.inputs[2])
    nb.l(mx.outputs[0], nb.out.inputs['Surface'])

    m, nb = mat('window_far')
    em = nb.n('ShaderNodeEmission', i_Strength=1.2, i_Color=rgb('#ffb24a'))
    nb.l(em.outputs[0], nb.out.inputs['Surface'])

    m, nb = mat('lantern')
    em = nb.n('ShaderNodeEmission', i_Strength=25.0, i_Color=rgb('#ffbe5c'))
    nb.l(em.outputs[0], nb.out.inputs['Surface'])

    m, nb = mat('iron')
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Metallic=0.8, i_Roughness=0.6, i_Base_Color=rgb('#24221f'))
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])

    # ---- water
    m, nb = mat('water')
    geo = nb.n('ShaderNodeNewGeometry')
    nz = noise(nb, geo.outputs['Position'], 0.8, 4)
    bump = nb.n('ShaderNodeBump', i_Strength=0.08, i_Distance=0.1)
    nb.l(nz.outputs['Fac'], bump.inputs['Height'])
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.06, i_Base_Color=rgb('#1c2a26'))
    bs.inputs['Specular IOR Level'].default_value = 0.6
    nb.l(bump.outputs['Normal'], bs.inputs['Normal'])
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])

    # ---- flowers
    for nm, c in {'fl_pink': '#e07aa0', 'fl_white': '#f2efe6', 'fl_yellow': '#f0c430', 'fl_purple': '#8a5cc8',
                  'fl_red': '#c8322a'}.items():
        m, nb = mat(nm)
        bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.5, i_Base_Color=rgb(c))
        tr = nb.n('ShaderNodeBsdfTranslucent', i_Color=rgb(c))
        mx = nb.n('ShaderNodeMixShader', i_Fac=0.3)
        nb.l(bs.outputs[0], mx.inputs[1]); nb.l(tr.outputs[0], mx.inputs[2])
        nb.l(mx.outputs[0], nb.out.inputs['Surface'])

    # ---- clouds: transparent sheet, lit gold toward the sun, mauve away from it
    m, nb = mat('clouds')
    m.blend_method = 'BLEND'
    geo = nb.n('ShaderNodeNewGeometry')
    pos = geo.outputs['Position']
    mp = nb.n('ShaderNodeMapping', i_Scale=(0.0001, 0.00028, 0.001)); nb.l(pos, mp.inputs['Vector'])
    n1 = noise(nb, mp.outputs['Vector'], 1.0, 9, 0.62)
    cov = nb.n('ShaderNodeMapRange', i_From_Min=0.45, i_From_Max=0.66)
    nb.l(n1.outputs['Fac'], cov.inputs['Value'])
    inc = nb.n('ShaderNodeVectorMath', operation='NORMALIZE'); nb.l(geo.outputs['Incoming'], inc.inputs[0])
    dot = nb.n('ShaderNodeVectorMath', operation='DOT_PRODUCT')
    nb.l(inc.outputs[0], dot.inputs[0]); dot.inputs[1].default_value = tuple(-SUN_DIR)
    glow = nb.n('ShaderNodeMapRange', i_From_Min=0.75, i_From_Max=1.0)
    nb.l(dot.outputs['Value'], glow.inputs['Value'])
    gp = nb.n('ShaderNodeMath', operation='POWER'); gp.inputs[1].default_value = 3.0
    nb.l(glow.outputs['Result'], gp.inputs[0])
    col = ramp(nb, [(0.0, '#5e4a6a'), (0.35, '#c4746a'), (0.7, '#f2a04e'), (1.0, '#fff0c0')], gp.outputs[0])
    # thick cloud cores are darker underneath
    core = nb.n('ShaderNodeMapRange', i_From_Min=0.6, i_From_Max=0.85, i_To_Min=1.0, i_To_Max=0.45)
    nb.l(n1.outputs['Fac'], core.inputs['Value'])
    cm = nb.n('ShaderNodeVectorMath', operation='SCALE')
    nb.l(col.outputs['Color'], cm.inputs[0]); nb.l(core.outputs['Result'], cm.inputs['Scale'])
    em = nb.n('ShaderNodeEmission')
    nb.l(cm.outputs[0], em.inputs['Color'])
    st = nb.n('ShaderNodeMapRange', i_To_Min=1.2, i_To_Max=14.0)
    nb.l(gp.outputs[0], st.inputs['Value']); nb.l(st.outputs['Result'], em.inputs['Strength'])
    trn = nb.n('ShaderNodeBsdfTransparent')
    mx = nb.n('ShaderNodeMixShader')
    nb.l(cov.outputs['Result'], mx.inputs['Fac']); nb.l(trn.outputs[0], mx.inputs[1]); nb.l(em.outputs[0], mx.inputs[2])
    nb.l(mx.outputs[0], nb.out.inputs['Surface'])

def M(name):
    m = MATS[name]
    return m[0] if isinstance(m, tuple) else m

# --------------------------------------------------------------------------- terrain meshes
def frustum_grid(y0, y1, rows, cols, half_w, x_off=0.0, geo_k=None):
    i = np.arange(rows)
    if geo_k:
        a = math.log((y1 - y0) / geo_k + 1) / (rows - 1)
        ys = y0 + geo_k * (np.exp(a * i) - 1)
    else:
        ys = np.linspace(y0, y1, rows)
    u = np.linspace(-1, 1, cols)
    Y = np.repeat(ys[:, None], cols, 1)
    X = x_off + u[None, :] * half_w(ys)[:, None]
    return X, Y

def grid_faces(rows, cols):
    idx = np.arange(rows * cols).reshape(rows, cols)
    a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel(); c = idx[1:, 1:].ravel(); d = idx[1:, :-1].ravel()
    return np.stack([a, b, c, d], 1)

def build_terrain():
    rows, cols = int(1500 * min(1, DETAIL * 1.2)), int(1300 * min(1, DETAIL * 1.2))
    X, Y = frustum_grid(-6, 3200, rows, cols, lambda y: (y + 8) * 0.9 + 12, x_off=-4.0, geo_k=3.0)
    Z = height(X, Y)
    ob = new_mesh_obj('terrain', np.stack([X, Y, Z], -1).reshape(-1, 3), grid_faces(rows, cols))
    set_attr(ob, 'path', path_mask(X, Y).ravel())
    smooth(ob)
    ob.data.materials.append(M('terrain'))

    # mountains: a snowy range left of the sun, lower blue ridges elsewhere
    rows, cols = 420, 1400
    Xw, Yw = frustum_grid(3000, 26000, rows, cols, lambda y: y * 1.0)
    # the range is designed at its own angle and turned 6.6 deg left so the main peak lands between the oak and
    # the loading-screen info panel (screen x ~0.49-0.67 is covered by it)
    phi = math.radians(6.6)
    X = Xw * math.cos(phi) + Yw * math.sin(phi)
    Y = -Xw * math.sin(phi) + Yw * math.cos(phi)
    th = np.arctan2(X, Y)
    rng_mask = np.exp(-((th - math.radians(-9)) / math.radians(15)) ** 2) * 0.8 + \
        0.55 * np.exp(-((th - math.radians(-30)) / math.radians(14)) ** 2)
    rng2 = 0.45 * np.exp(-((th - math.radians(40)) / math.radians(10)) ** 2)
    rd = ridged(X / 3200.0, Y / 3200.0, 8, 77)
    env = smoothstep(7000, 13000, Y) * (1 - 0.5 * smoothstep(16000, 24000, Y))
    Z = 150 + 300 * fbm(X / 3000, Y / 3000, 4, 8) + (rng_mask + rng2) * env * (900 + 3900 * rd ** 1.2)
    ob = new_mesh_obj('mountains', np.stack([Xw, Yw, Z], -1).reshape(-1, 3), grid_faces(rows, cols))
    smooth(ob)
    ob.data.materials.append(M('mountain'))

    # river water surface
    xs = np.linspace(-220, 260, 1200)
    yc = river_y(xs)
    bank = np.minimum(height(xs, yc - 13, False), height(xs, yc + 13, False))
    bmin = np.lib.stride_tricks.sliding_window_view(np.pad(bank, 40, mode='edge'), 81).min(1)
    zc = np.convolve(np.pad(bmin, 40, mode='edge'), np.ones(81) / 81, mode='valid') - 0.5
    w = 10.0
    v = np.concatenate([np.stack([xs, yc - w, zc], 1), np.stack([xs, yc + w, zc], 1)])
    n = len(xs)
    f = np.stack([np.arange(n - 1), np.arange(1, n), np.arange(n + 1, 2 * n), np.arange(n, 2 * n - 1)], 1)
    ob = new_mesh_obj('river', v, f)
    ob.data.materials.append(M('water'))

    # cloud sheet
    ob = new_mesh_obj('clouds', [(-90000, -2000, 5600), (90000, -2000, 5600), (90000, 90000, 5600), (-90000, 90000, 5600)],
                      [(0, 1, 2, 3)])
    ob.data.materials.append(M('clouds'))
    ob.visible_shadow = False

# --------------------------------------------------------------------------- instancing via geometry nodes
def make_instancer(name, pts, rot, scale, index, collection):
    ob = new_mesh_obj(name, pts, None)
    set_attr(ob, 'rot', rot, typ='FLOAT_VECTOR')
    set_attr(ob, 'sc', scale)
    a = ob.data.attributes.new('vi', 'INT', 'POINT'); a.data.foreach_set('value', np.asarray(index, np.int32))
    ng = bpy.data.node_groups.new(name + '_gn', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N = ng.nodes; L = ng.links
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    iop = N.new('GeometryNodeInstanceOnPoints')
    ci = N.new('GeometryNodeCollectionInfo')
    ci.inputs['Collection'].default_value = collection
    ci.inputs['Separate Children'].default_value = True
    ci.inputs['Reset Children'].default_value = True
    na_r = N.new('GeometryNodeInputNamedAttribute'); na_r.data_type = 'FLOAT_VECTOR'; na_r.inputs['Name'].default_value = 'rot'
    na_s = N.new('GeometryNodeInputNamedAttribute'); na_s.data_type = 'FLOAT'; na_s.inputs['Name'].default_value = 'sc'
    na_i = N.new('GeometryNodeInputNamedAttribute'); na_i.data_type = 'INT'; na_i.inputs['Name'].default_value = 'vi'
    e2r = N.new('FunctionNodeEulerToRotation')
    L.new(gi.outputs[0], iop.inputs['Points'])
    L.new(ci.outputs[0], iop.inputs['Instance'])
    iop.inputs['Pick Instance'].default_value = True
    L.new(na_i.outputs['Attribute'], iop.inputs['Instance Index'])
    L.new(na_r.outputs['Attribute'], e2r.inputs[0])
    L.new(e2r.outputs[0], iop.inputs['Rotation'])
    L.new(na_s.outputs['Attribute'], iop.inputs['Scale'])
    L.new(iop.outputs[0], go.inputs[0])
    md = ob.modifiers.new('inst', 'NODES'); md.node_group = ng
    return ob

SRC_COLL = None
def src_collection(name):
    c = bpy.data.collections.new(name)
    SRC_COLL.children.link(c)
    return c

# --------------------------------------------------------------------------- grass & flowers
def grass_clump(name, rng, n_blades, hmin, hmax, radius, matname, coll):
    V, F, T = [], [], []
    for b in range(n_blades):
        r = radius * math.sqrt(rng.random()); a = rng.random() * 6.283
        bx, by = r * math.cos(a), r * math.sin(a)
        h = rng.uniform(hmin, hmax)
        w = rng.uniform(0.006, 0.011) * (h / 0.35) ** 0.4
        lean = rng.uniform(0.15, 0.6) * h
        la = rng.random() * 6.283
        face = la + math.pi / 2 + rng.uniform(-0.6, 0.6)
        fx, fy = math.cos(face), math.sin(face)
        segs = 5
        base = len(V)
        for s in range(segs + 1):
            t = s / segs
            off = lean * t ** 1.8
            cx, cy, cz = bx + off * math.cos(la), by + off * math.sin(la), h * t * (1 - 0.25 * t * (lean / h))
            ww = w * (1 - t ** 1.5) if s < segs else 0.0
            V.append((cx - fx * ww, cy - fy * ww, cz)); T.append(t)
            V.append((cx + fx * ww, cy + fy * ww, cz)); T.append(t)
        for s in range(segs):
            i = base + 2 * s
            F.append((i, i + 1, i + 3, i + 2))
    ob = new_mesh_obj(name, V, F, coll)
    set_attr(ob, 't', T)
    smooth(ob)
    ob.data.materials.append(M(matname))
    return ob

def flower(name, rng, color, coll, n=8, h=0.55):
    V, F = [], []
    stems = []
    for k in range(n):
        a = rng.random() * 6.283; r = 0.08 * rng.random()
        x, y, z = r * math.cos(a), r * math.sin(a), h * rng.uniform(0.7, 1.15)
        # head: small 6-petal star facing up-ish
        base = len(V)
        V.append((x, y, z + 0.005))
        pr = rng.uniform(0.035, 0.06)
        for p in range(12):
            ang = p / 12 * 6.283
            rr = pr if p % 2 == 0 else pr * 0.45
            V.append((x + rr * math.cos(ang), y + rr * math.sin(ang), z + (0.006 if p % 2 == 0 else 0)))
        for p in range(0, 12, 2):      # quad per petal: centre, tip, notch, next tip
            F.append((base, base + 1 + p, base + 1 + (p + 1) % 12, base + 1 + (p + 2) % 12))
        stems.append((x, y, z))
    ob = new_mesh_obj(name, V, F, coll)
    ob.data.materials.append(M(color))
    # stems as a second (green) part
    SV, SF = [], []
    for (x, y, z) in stems:
        i = len(SV)
        SV += [(x - 0.002, y, 0), (x + 0.002, y, 0), (x + 0.002, y, z), (x - 0.002, y, z)]
        SF.append((i, i + 1, i + 2, i + 3))
    st = new_mesh_obj(name + '_stem', SV, SF, coll)
    st.data.materials.append(M('grass'))
    a = st.data.attributes.new('t', 'FLOAT', 'POINT'); a.data.foreach_set('value', [0, 0, 1, 1] * len(stems))
    join([ob, st])
    return ob

def join(obs):
    ctx = bpy.context
    for o in ctx.view_layer.objects: o.select_set(False)
    for o in obs:
        # source collections may be excluded from the view layer: temporarily link to the scene
        if o.name not in ctx.view_layer.objects:
            ctx.scene.collection.objects.link(o); o['_tmp'] = 1
        o.select_set(True)
    ctx.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    o = obs[0]
    if o.get('_tmp'):
        ctx.scene.collection.objects.unlink(o); del o['_tmp']
    return o

def scatter_grass():
    rng = random.Random(7)
    coll = src_collection('src_grass')
    kinds = []
    for i in range(6):
        kinds.append(grass_clump('gc%d' % i, rng, 28, 0.18, 0.5, 0.09, 'grass', coll))
    for i in range(3):
        kinds.append(grass_clump('gd%d' % i, rng, 20, 0.3, 0.7, 0.1, 'grass_dry', coll))
    for i in range(3):
        kinds.append(grass_clump('gk%d' % i, rng, 30, 0.12, 0.35, 0.08, 'grass_dark', coll))
    nk = len(kinds)
    R = np.random.default_rng(11)
    pts = []
    bands = [(2.3, 4, 2200), (4, 6, 1300), (6, 9, 650), (9, 14, 280), (14, 22, 110), (22, 35, 40), (35, 55, 14), (55, 75, 5)]
    for y0, y1, dens in bands:
        area = (y1 - y0) * 2 * view_hw((y0 + y1) / 2)
        n = int(area * dens * DETAIL)
        y = R.uniform(y0, y1, n)
        x = view_cx(y) + R.uniform(-1, 1, n) * view_hw(y)
        pts.append(np.stack([x, y], 1))
    P = np.concatenate(pts)
    x, y = P[:, 0], P[:, 1]
    # cull: path, facade wall + yard, river, very far
    pm = path_mask(x, y)
    keep = R.random(len(x)) > pm * 1.3
    hp, r, ang, sector = hill_parts(x, y)
    wall_zone = (sector > 0.5) & (r > WALL_R - 0.12) & (r < WALL_R + 0.9)
    keep &= ~wall_zone
    keep &= np.abs(y - river_y(x)) > 7
    x, y = x[keep], y[keep]
    z = height(x, y)
    n = len(x)
    dist = np.hypot(x - CAM.x, y - CAM.y)
    sc = np.clip(dist / 10.0, 1.0, 2.0) * R.uniform(0.75, 1.3, n)
    # meadow variety: dry patches by noise
    dry = fbm(x / 6, y / 6, 3, 21)
    idx = R.integers(0, 6, n)
    idx = np.where(dry > 0.18, 6 + R.integers(0, 3, n), idx)
    idx = np.where((dry < -0.25) & (R.random(n) < 0.6), 9 + R.integers(0, 3, n), idx)
    # shorter, tidier grass around the hobbit hole yard
    _, r, _, sector = hill_parts(x, y)
    yard = (sector > 0.3) & (r < WALL_R + 7)
    sc = np.where(yard, sc * 0.38, sc)
    rot = np.stack([R.normal(0, 0.06, n), R.normal(0, 0.06, n), R.uniform(0, 6.283, n)], 1)
    make_instancer('grass', np.stack([x, y, z - 0.02], 1), rot, sc, idx, coll)
    print('grass clumps', n)

    # flowers
    fcoll = src_collection('src_flowers')
    frng = random.Random(3)
    fk = [flower('f%d' % i, frng, c, fcoll) for i, c in
          enumerate(['fl_pink', 'fl_white', 'fl_yellow', 'fl_purple', 'fl_pink', 'fl_white', 'fl_red'])]
    m = int(70000 * DETAIL)
    y = 2.3 + R.uniform(0, 1, m) ** 1.6 * 45
    x = view_cx(y) + R.uniform(-1, 1, m) * view_hw(y)
    patch = fbm(x / 3.5, y / 3.5, 3, 61)
    garden = np.exp(-((np.hypot(x - (HILL_C[0] + DOOR_DIR[0] * (WALL_R + 1.3)), y - (HILL_C[1] + DOOR_DIR[1] * (WALL_R + 1.3))) / 4.0) ** 2))
    keep = (R.random(m) < np.clip(patch * 2.2 - 0.1, 0, 1) * 0.5 + garden * 0.9)
    pm = path_mask(x, y)
    keep &= pm < 0.2
    keep &= np.hypot(x - CAM.x, y - CAM.y) > 7.5      # the nearest ones read as flat paper stars
    hp, r, ang, sector = hill_parts(x, y)
    keep &= ~((sector > 0.5) & (r > WALL_R - 0.6) & (r < WALL_R + 0.5))
    x, y = x[keep], y[keep]
    n = len(x)
    z = height(x, y)
    dist = np.hypot(x - CAM.x, y - CAM.y)
    sc = np.clip(dist / 25.0, 1, 1.5) * R.uniform(0.75, 1.15, n)
    col = (np.floor((fbm(x / 5, y / 5, 2, 71) + 1) * 3.5)).astype(int) % len(fk)
    rot = np.stack([np.zeros(n), np.zeros(n), R.uniform(0, 6.283, n)], 1)
    make_instancer('flowers', np.stack([x, y, z], 1), rot, sc, col, fcoll)
    print('flowers', n)

# --------------------------------------------------------------------------- trees
def tube_mesh(branches, ring=8):
    """branches: list of (points[N,3], radii[N]) -> verts, faces"""
    V, F = [], []
    for pts, rad in branches:
        pts = np.asarray(pts); n = len(pts)
        k = ring if rad[0] > 0.08 else (6 if rad[0] > 0.025 else 4)
        tang = np.gradient(pts, axis=0)
        tang /= np.linalg.norm(tang, axis=1)[:, None] + 1e-9
        up = np.array([0, 0, 1.0]) if abs(tang[0][2]) < 0.9 else np.array([1.0, 0, 0])
        nrm = np.cross(tang[0], up); nrm /= np.linalg.norm(nrm)
        base = len(V)
        for i in range(n):
            t = tang[i]
            nrm = nrm - t * np.dot(nrm, t); nrm /= np.linalg.norm(nrm) + 1e-9
            bn = np.cross(t, nrm)
            for j in range(k):
                a = j / k * 6.283
                V.append(pts[i] + rad[i] * (math.cos(a) * nrm + math.sin(a) * bn))
        for i in range(n - 1):
            for j in range(k):
                a = base + i * k + j; b = base + i * k + (j + 1) % k
                F.append((a, b, b + k, a + k))
    return np.array(V), np.array(F)

def make_tree(name, seed, height_, spread, levels, leaves_per_twig, leaf_size, leafmat, coll=None,
              trunk_h=0.3, lean=0.0, twig_cluster=0.5):
    rng = np.random.default_rng(seed)
    branches = []
    twigs = []

    def grow(p0, d, length, r0, level):
        n = max(4, int(length / (0.35 if level == 0 else 0.25)))
        pts = [np.array(p0, float)]; rads = [r0]
        d = np.array(d, float) / np.linalg.norm(d)
        step = length / n
        for i in range(1, n + 1):
            d = d + rng.normal(0, 0.12 + 0.06 * level, 3)
            if level == 0: d[2] += 0.25
            elif level == 1: d[2] += 0.05
            else: d[2] -= 0.04 * level * (i / n)
            d /= np.linalg.norm(d)
            pts.append(pts[-1] + d * step)
            rads.append(r0 * (1 - 0.72 * i / n))
        branches.append((np.array(pts), np.array(rads)))
        if level >= levels:
            twigs.append(np.array(pts))
            return
        if level == 0:
            nk = rng.integers(4, 6); t0 = trunk_h
        else:
            nk = rng.integers(4, 7) if level == 1 else rng.integers(3, 6); t0 = 0.25
        for c in range(nk):
            t = t0 + (1 - t0) * (c + rng.uniform(0.2, 0.9)) / nk if level else min(0.95, t0 + rng.uniform(0, 0.12))
            i = min(n - 1, int(t * n))
            pd = pts[min(i + 1, n)] - pts[i]; pd /= np.linalg.norm(pd)
            az = rng.uniform(0, 6.283) if level else (c / nk) * 6.283 + rng.uniform(-0.3, 0.3)
            side = np.array([math.cos(az), math.sin(az), 0.0])
            side -= pd * np.dot(side, pd); side /= np.linalg.norm(side) + 1e-9
            ang = rng.uniform(0.55, 1.0) if level == 0 else rng.uniform(0.5, 1.1)
            cd = pd * math.cos(ang) + side * math.sin(ang)
            if level == 0:
                cl = spread * rng.uniform(0.45, 0.6)
            else:
                cl = length * rng.uniform(0.45, 0.65) * (1 - 0.3 * t)
            grow(pts[i], cd, cl, rads[i] * (0.62 if level == 0 else 0.55), level + 1)

    tr = height_ * 0.028 + 0.08
    grow((0, 0, -0.3), (lean, 0, 1), height_ * trunk_h + 0.3 if levels else height_, tr, 0)
    bv, bf = tube_mesh(branches)
    # leaves: diamonds scattered around twig points
    L = []
    for tw in twigs:
        sel = tw[len(tw) // 3:]
        for _ in range(leaves_per_twig):
            p = sel[rng.integers(0, len(sel))] + rng.normal(0, twig_cluster, 3) * np.array([1, 1, 0.7])
            L.append(p)
    L = np.array(L)
    nl = len(L)
    # random orientation, mostly facing up/out
    nrm = rng.normal(0, 1, (nl, 3)); nrm[:, 2] += 0.8
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    tng = np.cross(nrm, rng.normal(0, 1, (nl, 3))); tng /= np.linalg.norm(tng, axis=1)[:, None]
    btg = np.cross(nrm, tng)
    s = leaf_size * rng.uniform(0.7, 1.3, nl)[:, None]
    v0 = L - tng * s; v2 = L + tng * s
    v1 = L + btg * s * 0.45 + tng * s * 0.1; v3 = L - btg * s * 0.45 + tng * s * 0.1
    lv = np.stack([v0, v1, v2, v3], 1).reshape(-1, 3)
    lf = np.arange(nl * 4).reshape(nl, 4)
    # colour variation: sunlit tops lighter, plus per-cluster noise
    zr = (L[:, 2] - L[:, 2].min()) / (np.ptp(L[:, 2]) + 1e-6)
    col = np.clip(0.25 + 0.5 * zr + rng.normal(0, 0.18, nl) + 0.3 * fbm(L[:, 0] / 2.0, L[:, 1] / 2.0 + L[:, 2] / 3, 2, seed), 0, 1)
    V = np.concatenate([bv, lv]); F = np.concatenate([bf, lf + len(bv)])
    ob = new_mesh_obj(name, V, F, coll)
    ob.data.materials.append(M('bark')); ob.data.materials.append(M(leafmat))
    mi = np.concatenate([np.zeros(len(bf), np.int32), np.ones(len(lf), np.int32)])
    ob.data.polygons.foreach_set('material_index', mi)
    smooth(ob)
    lvv = np.concatenate([np.full(len(bv), 0.5), np.repeat(col, 4)])
    set_attr(ob, 'lv', lvv)
    print(name, 'leaves', nl, 'branch verts', len(bv))
    return ob

def build_trees():
    # the great oak on top of Bag End hill
    oak = make_tree('oak', 5, 15.0, 17.0, 4, int(320 * max(DETAIL, 0.3)), 0.12, 'leaf_oak', trunk_h=0.24,
                    twig_cluster=0.42)
    oak.location = (HILL_C[0] - 3.0, HILL_C[1] + 2.5, float(height(HILL_C[0] - 3.0, HILL_C[1] + 2.5)))
    oak.rotation_euler = (0, 0, 0.6)
    # a couple of mid trees near the right edge for framing
    for i, (x, y, s) in enumerate([(16, 30, 1.0), (24, 46, 0.9), (-24, 40, 1.1)]):
        t = make_tree('mid%d' % i, 30 + i, 10 * s, 9 * s, 4, int(120 * max(DETAIL, 0.3)), 0.13, 'leaf_tree',
                      trunk_h=0.35, twig_cluster=0.4)
        t.location = (x, y, float(height(x, y)) - 0.1)
        t.rotation_euler = (0, 0, i * 1.7)

    # distant trees: a few variants instanced along hedgerows and copses
    coll = src_collection('src_trees')
    var = []
    for i in range(6):
        h = [9, 12, 7, 14, 10, 8][i]
        var.append(make_tree('ft%d' % i, 100 + i, h, h * 0.8, 3, 110, 0.3, 'leaf_tree' if i != 2 else 'leaf_autumn',
                             coll, trunk_h=0.35, twig_cluster=0.7))
    R = np.random.default_rng(5)
    P = []
    # hedgerows: polylines on the far slopes
    for k in range(70):
        y0 = R.uniform(110, 900); x0 = R.uniform(-1.0, 1.0) * (y0 * 0.9 + 30)
        ang = R.uniform(-0.6, 0.6) + (0 if R.random() < 0.6 else 1.5708)
        ln = R.uniform(40, 160)
        m = int(ln / R.uniform(4, 7))
        t = np.linspace(0, ln, m)
        P.append(np.stack([x0 + t * math.cos(ang) + R.normal(0, 1, m), y0 + t * math.sin(ang) * 0.6 + R.normal(0, 1, m)], 1))
    # copses
    for k in range(45):
        cy = R.uniform(70, 1400); cx = R.uniform(-1, 1) * (cy * 0.9 + 30)
        m = R.integers(5, 25)
        P.append(np.stack([cx + R.normal(0, 12, m), cy + R.normal(0, 9, m)], 1))
    # along the river
    xs = R.uniform(-160, 200, 30)
    P.append(np.stack([xs, river_y(xs) + R.choice([-1, 1], 30) * R.uniform(9, 14, 30)], 1))
    P = np.concatenate(P)
    x, y = P[:, 0], P[:, 1]
    keep = (np.abs(y - river_y(x)) > 7.5) & (y > 55)
    keep &= ~((x < -2) & (y < 120) & (x > -60))  # don't clutter behind the oak
    x, y = x[keep], y[keep]
    n = len(x)
    z = height(x, y) - 0.3
    rot = np.stack([np.zeros(n), np.zeros(n), R.uniform(0, 6.283, n)], 1)
    sc = R.uniform(0.75, 1.35, n)
    make_instancer('forest', np.stack([x, y, z], 1), rot, sc, R.integers(0, len(var), n), coll)
    print('far trees', n)

# --------------------------------------------------------------------------- the hobbit hole
def obj_from_bpy(op, name, matname, **kw):
    op(**kw)
    ob = bpy.context.active_object
    ob.name = name
    if matname: ob.data.materials.append(M(matname))
    return ob

def build_hobbit_hole():
    c = Vector((HILL_C[0], HILL_C[1], 0))
    d = Vector((DOOR_DIR[0], DOOR_DIR[1], 0))
    yaw = math.atan2(d.y, d.x)
    door_xy = c + d * (WALL_R + 0.02)
    gz = float(height(door_xy.x + d.x * 0.6, door_xy.y + d.y * 0.6))

    # curved dry-stone facade (part of a cylinder), slightly taller than the hill cut
    seg = 48
    V, F = [], []
    for i in range(seg + 1):
        a = yaw - WALL_SPAN - 0.08 + (2 * WALL_SPAN + 0.16) * i / seg
        for rr in (WALL_R, WALL_R - 0.5):
            x, y = HILL_C[0] + rr * math.cos(a), HILL_C[1] + rr * math.sin(a)
            g = float(height(x + math.cos(a) * 0.8, y + math.sin(a) * 0.8))
            top = float(hill_parts(np.array(x - math.cos(a) * 0.3), np.array(y - math.sin(a) * 0.3))[0]) + \
                float(height(x - math.cos(a) * 0.3, y - math.sin(a) * 0.3)) - \
                float(hill_parts(np.array(x - math.cos(a) * 0.3), np.array(y - math.sin(a) * 0.3))[0])
            top = max(top, g + 0.6)
            V.append((x, y, g - 0.4)); V.append((x, y, top - 0.12))
    for i in range(seg):
        for j in range(2):
            b = i * 4 + j * 2; nb_ = b + 4
            F.append((b, nb_, nb_ + 1, b + 1))
        F.append((i * 4 + 1, (i + 1) * 4 + 1, (i + 1) * 4 + 3, i * 4 + 3))
    wall = new_mesh_obj('facade', V, F)
    wall.data.materials.append(M('stone'))

    def place(ob, along, up, out=0.0, rot_extra=0.0):
        # along: metres along the wall arc from the door, up: height above yard ground
        a = yaw + along / WALL_R
        p = Vector((HILL_C[0] + (WALL_R + out) * math.cos(a), HILL_C[1] + (WALL_R + out) * math.sin(a), gz + up))
        ob.location = p
        ob.rotation_euler = Euler((math.pi / 2, 0, a + math.pi / 2 + rot_extra), 'XYZ')
        return ob

    # door, frame, stone ring, knob
    place(obj_from_bpy(bpy.ops.mesh.primitive_cylinder_add, 'door', 'door', vertices=64, radius=0.95, depth=0.1), 0, 1.0, 0.0)
    place(obj_from_bpy(bpy.ops.mesh.primitive_torus_add, 'doorframe', 'wood', major_segments=64, minor_segments=12,
                       major_radius=1.04, minor_radius=0.11), 0, 1.0, 0.06)
    for k in range(17):
        a = -math.pi * 0.12 + (math.pi * 1.24) * k / 16
        st = obj_from_bpy(bpy.ops.mesh.primitive_cube_add, 'ringstone%d' % k, 'stone', size=1)
        st.scale = (0.2, 0.2, 0.2)
        place(st, math.cos(a + math.pi / 2) * 1.28, 1.0 + math.sin(a + math.pi / 2) * 1.28, 0.07)
        st.rotation_euler.rotate_axis('Z', 0)
        st.rotation_mode = 'XYZ'
        st.rotation_euler = (st.rotation_euler[0], a, st.rotation_euler[2])
        st.scale = (0.17, 0.2, 0.16 + 0.02 * (k % 3))
    place(obj_from_bpy(bpy.ops.mesh.primitive_uv_sphere_add, 'knob', 'brass', radius=0.06, segments=24, ring_count=12),
          0, 1.0, 0.09)
    # threshold step
    stp = obj_from_bpy(bpy.ops.mesh.primitive_cube_add, 'step', 'stone', size=1)
    stp.scale = (1.6, 0.5, 0.16)
    place(stp, 0, 0.0, 0.3)
    stp.rotation_euler = (0, 0, yaw + math.pi / 2)

    # round windows with warm light
    for side in (-1, 1):
        al = side * 2.45
        place(obj_from_bpy(bpy.ops.mesh.primitive_cylinder_add, 'win%d' % side, 'window', vertices=48, radius=0.42,
                           depth=0.06), al, 1.15, 0.0)
        place(obj_from_bpy(bpy.ops.mesh.primitive_torus_add, 'winframe%d' % side, 'wood', major_segments=48,
                           minor_segments=10, major_radius=0.46, minor_radius=0.065), al, 1.15, 0.05)
        for k, (sx, sz) in enumerate([(0.03, 0.84), (0.84, 0.03)]):
            mb = obj_from_bpy(bpy.ops.mesh.primitive_cube_add, 'mull%d%d' % (side, k), 'wood', size=1)
            mb.scale = (sx, sz, 0.05)
            place(mb, al, 1.15, 0.05)
            mb.scale = (sx, sz, 0.05)
        # warm glow spilling out
        bpy.ops.object.light_add(type='POINT')
        L = bpy.context.active_object
        L.data.energy = 14; L.data.color = (1.0, 0.62, 0.28); L.data.shadow_soft_size = 0.3
        place(L, al, 1.15, 0.6)

    # lantern on a post beside the door
    post = obj_from_bpy(bpy.ops.mesh.primitive_cylinder_add, 'lpost', 'wood', vertices=10, radius=0.05, depth=1.6)
    a = yaw + 1.25 / WALL_R
    pp = Vector((HILL_C[0] + (WALL_R + 0.55) * math.cos(a), HILL_C[1] + (WALL_R + 0.55) * math.sin(a), gz + 0.8))
    post.location = pp
    lan = obj_from_bpy(bpy.ops.mesh.primitive_cube_add, 'lantern', 'lantern', size=0.16)
    lan.location = pp + Vector((0, 0, 0.88))
    cap = obj_from_bpy(bpy.ops.mesh.primitive_cone_add, 'lcap', 'iron', vertices=4, radius1=0.15, depth=0.1)
    cap.location = pp + Vector((0, 0, 1.01)); cap.rotation_euler = (0, 0, 0.785)
    bpy.ops.object.light_add(type='POINT')
    L = bpy.context.active_object
    L.data.energy = 45; L.data.color = (1.0, 0.65, 0.3); L.data.shadow_soft_size = 0.08
    L.location = pp + Vector((0, 0, 0.88))

    # soft warm fill (light bouncing off the sunlit meadow onto the facade)

    # chimney on the hill
    cx, cy = HILL_C[0] + 1.2, HILL_C[1] + 1.0
    cz = float(height(cx, cy))
    ch = obj_from_bpy(bpy.ops.mesh.primitive_cube_add, 'chimney', 'brick', size=1)
    ch.scale = (0.55, 0.55, 1.6); ch.location = (cx, cy, cz + 0.5)
    chc = obj_from_bpy(bpy.ops.mesh.primitive_cube_add, 'chimneycap', 'stone', size=1)
    chc.scale = (0.68, 0.68, 0.12); chc.location = (cx, cy, cz + 1.32)
    # chimney smoke: soft volume column
    sm = obj_from_bpy(bpy.ops.mesh.primitive_cube_add, 'smoke', None, size=1)
    sm.scale = (3.0, 3.0, 7.0); sm.location = (cx + 0.9, cy + 0.6, cz + 4.8)
    m, nb = mat('smoke')
    geo = nb.n('ShaderNodeNewGeometry')
    tc = nb.n('ShaderNodeTexCoord')
    sep = nb.n('ShaderNodeSeparateXYZ'); nb.l(tc.outputs['Generated'], sep.inputs[0])
    # plume: radial falloff around a line drifting with height
    cxm = nb.n('ShaderNodeMath', operation='MULTIPLY_ADD'); cxm.inputs[1].default_value = -0.25; cxm.inputs[2].default_value = 0.0
    nb.l(sep.outputs['Z'], cxm.inputs[0])
    dx = nb.n('ShaderNodeMath', operation='SUBTRACT'); nb.l(sep.outputs['X'], dx.inputs[0]); dx.inputs[1].default_value = 0.45
    dx2 = nb.n('ShaderNodeMath', operation='ADD'); nb.l(dx.outputs[0], dx2.inputs[0]); nb.l(cxm.outputs[0], dx2.inputs[1])
    dy = nb.n('ShaderNodeMath', operation='SUBTRACT'); nb.l(sep.outputs['Y'], dy.inputs[0]); dy.inputs[1].default_value = 0.45
    ln = nb.n('ShaderNodeCombineXYZ'); nb.l(dx2.outputs[0], ln.inputs[0]); nb.l(dy.outputs[0], ln.inputs[1])
    lnl = nb.n('ShaderNodeVectorMath', operation='LENGTH'); nb.l(ln.outputs[0], lnl.inputs[0])
    wid = nb.n('ShaderNodeMath', operation='MULTIPLY_ADD'); wid.inputs[1].default_value = 0.22; wid.inputs[2].default_value = 0.04
    nb.l(sep.outputs['Z'], wid.inputs[0])
    rr = nb.n('ShaderNodeMath', operation='DIVIDE'); nb.l(lnl.outputs['Value'], rr.inputs[0]); nb.l(wid.outputs[0], rr.inputs[1])
    fall = nb.n('ShaderNodeMapRange', i_From_Min=1.0, i_From_Max=0.0); nb.l(rr.outputs[0], fall.inputs['Value'])
    nz = noise(nb, geo.outputs['Position'], 0.9, 5)
    nzr = nb.n('ShaderNodeMapRange', i_From_Min=0.35, i_From_Max=0.75); nb.l(nz.outputs['Fac'], nzr.inputs['Value'])
    fade = nb.n('ShaderNodeMapRange', i_From_Min=0.0, i_From_Max=1.0, i_To_Min=1.0, i_To_Max=0.0)
    nb.l(sep.outputs['Z'], fade.inputs['Value'])
    d1 = nb.n('ShaderNodeMath', operation='MULTIPLY'); nb.l(fall.outputs['Result'], d1.inputs[0]); nb.l(nzr.outputs['Result'], d1.inputs[1])
    d2 = nb.n('ShaderNodeMath', operation='MULTIPLY'); nb.l(d1.outputs[0], d2.inputs[0]); nb.l(fade.outputs['Result'], d2.inputs[1])
    d3 = nb.n('ShaderNodeMath', operation='MULTIPLY'); nb.l(d2.outputs[0], d3.inputs[0]); d3.inputs[1].default_value = 1.6
    pv = nb.n('ShaderNodeVolumePrincipled', i_Color=rgb('#cfc6bd'), i_Anisotropy=0.5)
    nb.l(d3.outputs[0], pv.inputs['Density'])
    nb.l(pv.outputs[0], nb.out.inputs['Volume'])
    sm.data.materials.append(m)
    sm.visible_shadow = False

    # garden fence along the yard edge + low stone wall
    yard_r = WALL_R + 4.2
    posts = []
    for i in range(15):
        a = yaw - 0.62 + 1.24 * i / 14
        if abs(a - (yaw + 0.27)) < 0.05:  # gate gap where the path arrives
            continue
        x, y = HILL_C[0] + yard_r * math.cos(a), HILL_C[1] + yard_r * math.sin(a)
        z = float(height(x, y))
        p = obj_from_bpy(bpy.ops.mesh.primitive_cube_add, 'fpost%d' % i, 'wood', size=1)
        p.scale = (0.09, 0.09, 1.05); p.location = (x, y, z + 0.42); p.rotation_euler = (0, R_(i) * 0.06, a)
        posts.append((x, y, z, a))
    for (x0, y0, z0, a0), (x1, y1, z1, a1) in zip(posts[:-1], posts[1:]):
        if math.hypot(x1 - x0, y1 - y0) > 3.0:
            continue
        for hz in (0.38, 0.75):
            rl = obj_from_bpy(bpy.ops.mesh.primitive_cube_add, 'rail', 'wood', size=1)
            ln = math.hypot(x1 - x0, y1 - y0)
            rl.scale = (ln + 0.1, 0.05, 0.06)
            rl.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2 + hz)
            rl.rotation_euler = (0, math.atan2(z1 - z0, ln) * -1, math.atan2(y1 - y0, x1 - x0))

    # a few stepping stones on the path near the door
    R = np.random.default_rng(9)
    for k, t in enumerate(np.linspace(0.62, 0.98, 6)):
        q = PATH_MAIN[2] * (1 - t) + PATH_MAIN[-1] * t
        x, y = q[0] + R.normal(0, 0.1), q[1] + R.normal(0, 0.1)
        s = obj_from_bpy(bpy.ops.mesh.primitive_cylinder_add, 'pstone%d' % k, 'stone', vertices=9, radius=0.33, depth=0.12)
        s.scale = (1, R.uniform(0.7, 0.95), 1)
        s.location = (x, y, float(height(x, y)) + 0.01); s.rotation_euler = (0, 0, R.uniform(0, 3))

def R_(i):
    return math.sin(i * 12.9898) * 0.5

# --------------------------------------------------------------------------- distant hobbit holes (glowing windows on far slopes)
def build_far_holes():
    R = np.random.default_rng(21)
    for k in range(9):
        y = R.uniform(120, 260); x = R.uniform(-0.8, 0.9) * (y * 0.9)
        if abs(y - river_y(x)) < 12: continue
        z = float(height(x, y))
        to_cam = Vector((CAM.x - x, CAM.y - y, 0)).normalized()
        door = obj_from_bpy(bpy.ops.mesh.primitive_cylinder_add, 'fdoor%d' % k, ['door', 'brick', 'door'][k % 3],
                            vertices=24, radius=0.8, depth=0.1)
        door.location = Vector((x, y, z + 0.6)) + to_cam * 0.2
        door.rotation_euler = (math.pi / 2, 0, math.atan2(to_cam.y, to_cam.x) + math.pi / 2)
        for s in (R.choice([-1, 1]),):
            w = obj_from_bpy(bpy.ops.mesh.primitive_cylinder_add, 'fwin%d%d' % (k, s), 'window_far', vertices=16, radius=0.3, depth=0.1)
            side = Vector((-to_cam.y, to_cam.x, 0))
            w.location = Vector((x, y, z + 1.0)) + to_cam * 0.25 + side * s * 1.8
            w.rotation_euler = door.rotation_euler

# --------------------------------------------------------------------------- stone bridge over the river
def build_bridge():
    t = PATH_VALLEY
    # crossing point
    xs = np.linspace(8, 20, 400); ys = np.interp(xs, t[:, 0], t[:, 1])
    k = np.argmin(np.abs(ys - river_y(xs)))
    bx, by = float(xs[k]), float(ys[k])
    zb = float(height(bx, by - 9)) + 0.4
    br = obj_from_bpy(bpy.ops.mesh.primitive_cube_add, 'bridge', 'stone', size=1)
    br.scale = (3.4, 17.0, 2.6); br.location = (bx, by, zb - 0.6)
    cut = obj_from_bpy(bpy.ops.mesh.primitive_cylinder_add, 'arch', None, vertices=48, radius=4.8, depth=5)
    cut.rotation_euler = (0, math.pi / 2, 0); cut.location = (bx, by, zb - 6.0)
    md = br.modifiers.new('arch', 'BOOLEAN'); md.object = cut; md.operation = 'DIFFERENCE'
    cut.hide_render = True; cut.hide_viewport = True
    for s in (-1, 1):
        p = obj_from_bpy(bpy.ops.mesh.primitive_cube_add, 'parapet', 'stone', size=1)
        p.scale = (0.3, 17.0, 0.6); p.location = (bx + s * 1.55, by, zb + 0.95)
    rot = math.atan2(t[-3, 0] - t[-5, 0], t[-3, 1] - t[-5, 1])
    for o in (br, cut) + tuple(o for o in bpy.data.objects if o.name.startswith('parapet')):
        o.rotation_euler.z = -rot
        v = Vector(o.location) - Vector((bx, by, o.location.z))
        v.rotate(Euler((0, 0, -rot)))
        o.location = Vector((bx, by, o.location.z)) + v

# --------------------------------------------------------------------------- world, lights, camera, render
def build_world():
    w = bpy.data.worlds.new('sky'); bpy.context.scene.world = w
    w.use_nodes = True
    t = w.node_tree; t.nodes.clear()
    sky = t.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'NISHITA'
    sky.sun_disc = False
    sky.sun_elevation = SUN_EL
    sky.sun_rotation = -SUN_AZ  # blender: 0 = +Y, positive toward -X  (checked against the sun lamp)
    sky.altitude = 300
    sky.air_density = 1.3
    sky.dust_density = 1.6
    sky.ozone_density = 1.2
    bg = t.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 0.18
    out = t.nodes.new('ShaderNodeOutputWorld')
    t.links.new(sky.outputs[0], bg.inputs[0]); t.links.new(bg.outputs[0], out.inputs[0])

    bpy.ops.object.light_add(type='SUN')
    sun = bpy.context.active_object
    sun.data.energy = 4.2
    sun.data.color = (1.0, 0.68, 0.42)
    sun.data.angle = math.radians(0.6)
    sun.rotation_euler = (-SUN_DIR).to_track_quat('-Z', 'Y').to_euler()
    # a visible sun disc (emissive sphere far away), haze & bloom are added in post
    sd = obj_from_bpy(bpy.ops.mesh.primitive_uv_sphere_add, 'sundisc', None, radius=170, segments=32, ring_count=16)
    sd.location = CAM + SUN_DIR * 30000
    m, nb = mat('sundisc')
    em = nb.n('ShaderNodeEmission', i_Strength=120.0, i_Color=(1.0, 0.82, 0.55, 1))
    nb.l(em.outputs[0], nb.out.inputs['Surface'])
    sd.data.materials.append(m)
    sd.visible_shadow = False
    sd.visible_diffuse = False; sd.visible_glossy = True

    cam_d = bpy.data.cameras.new('cam'); cam_d.lens = 26; cam_d.sensor_width = 36
    cam_d.clip_start = 0.1; cam_d.clip_end = 80000
    cam = bpy.data.objects.new('cam', cam_d); bpy.context.scene.collection.objects.link(cam)
    cam.location = CAM
    cam.rotation_euler = Euler((math.pi / 2 + CAM_PITCH, 0, CAM_YAW), 'XYZ')
    bpy.context.scene.camera = cam

def write_meta():
    import json
    cam = bpy.context.scene.camera
    json.dump({'cam_matrix': [list(r) for r in cam.matrix_world], 'lens': cam.data.lens, 'sensor': cam.data.sensor_width,
               'sun_dir': list(SUN_DIR), 'res': [RES_X, RES_Y]}, open(OUT + '_meta.json', 'w'))

def render():
    write_meta()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = False          # this Blender build has no OpenImageDenoise: adaptive sampling instead
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.006
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 4; sc.cycles.transparent_max_bounces = 12; sc.cycles.volume_bounces = 1
    sc.cycles.light_sampling_threshold = 0.01
    sc.render.resolution_x = RES_X; sc.render.resolution_y = RES_Y; sc.render.resolution_percentage = 100
    sc.render.threads_mode = 'AUTO'
    sc.view_settings.view_transform = 'Standard'
    sc.render.film_transparent = False
    vl = sc.view_layers[0]
    vl.use_pass_z = True
    sc.use_nodes = True
    t = sc.node_tree; t.nodes.clear()
    rl = t.nodes.new('CompositorNodeRLayers')
    fo = t.nodes.new('CompositorNodeOutputFile')
    fo.base_path = os.path.dirname(OUT)
    fo.format.file_format = 'OPEN_EXR'; fo.format.color_depth = '32'; fo.format.exr_codec = 'ZIP'
    fo.file_slots.clear()
    fo.file_slots.new(os.path.basename(OUT) + '_rgb')
    fo.file_slots.new(os.path.basename(OUT) + '_z')
    t.links.new(rl.outputs['Image'], fo.inputs[0])
    t.links.new(rl.outputs['Depth'], fo.inputs[1])
    comp = t.nodes.new('CompositorNodeComposite'); t.links.new(rl.outputs['Image'], comp.inputs[0])
    sc.render.filepath = OUT + '_preview.png'
    sc.frame_set(1)
    bpy.ops.render.render(write_still=True)
    # the file-output node appends the frame number
    for s in ('_rgb', '_z'):
        src = OUT + s + '0001.exr'
        if os.path.exists(src):
            os.replace(src, OUT + s + '.exr')


def main():
    global SRC_COLL
    reset()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    SRC_COLL = bpy.data.collections.new('SOURCES')
    bpy.context.scene.collection.children.link(SRC_COLL)
    global YARD_Z
    dp = HILL_C + DOOR_DIR * (WALL_R + 1.5)
    YARD_Z = float(height(dp[0], dp[1], with_yard=False))
    print('yard level', YARD_Z)
    make_materials()
    build_world()
    build_terrain()
    build_hobbit_hole()
    build_trees()
    scatter_grass()
    bpy.context.view_layer.layer_collection.children['SOURCES'].exclude = True
    if '--save-blend' in ARGS:
        bpy.ops.wm.save_as_mainfile(filepath=OUT + '.blend')
    render()

main()
