"""Mordor loading-screen wallpaper: Sauron on a lava-cracked crag of Gorgoroth, Mount Doom erupting on the right,
Barad-dur and its Eye far off on the left, under a burning overcast. Rendered with Cycles (CPU).

  blender -b --factory-startup -P tools/splash/mordor.py -- [--res 960] [--samples 32] [--out build/splash/mprev]
          [--studio]   (Sauron alone, close camera, for checking the figure)

Writes <out>_rgb.exr (linear), <out>_z.exr and <out>_meta.json; tools/splash/post_mordor.py makes the PNG + DDS.
Reference: screenshots/sauron-splash-1.webp, -2.webp. Everything comes from fixed seeds: reproducible.
The info panel of the loading screen covers x 0.49-0.67, y 0.28-0.70 of the screen: nothing important goes there.
"""
import os, sys, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import splashlib  # noqa: E402  (adds the venv's numpy to sys.path)
import numpy as np
import bpy
from mathutils import Vector, Matrix, Euler
from splashlib import (ROOT, Geo, geo_obj, mesh_obj, set_attr, grid_faces, sweep, tube, spike, slab, sphere_grid,
                       new_material, NB, rgb, ramp, noise, attr, fbm, ridged, vnoise, fbm3, smoothstep, nrm, render)
import sauron

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    return type(default)(ARGS[ARGS.index(name) + 1]) if name in ARGS else default
RES_X = arg('--res', 960)
RES_Y = RES_X * 9 // 16
SAMPLES = arg('--samples', 32)
OUT = os.path.join(ROOT, arg('--out', 'build/splash/mprev'))
STUDIO = '--studio' in ARGS

# --------------------------------------------------------------------------- layout (world: z up, camera looks +y)
CAM = np.array([1.9, -9.2, 1.15])
CAM_YAW = math.radians(0.5)             # + turns left (toward -x)
CAM_PITCH = math.radians(3.0)
LENS = 40.0
SENSOR = 36.0
TAN_H = SENSOR / 2 / LENS
TAN_V = TAN_H * 9 / 16
SAURON_FWD = nrm(np.array([0.50, -0.87, 0.0]))      # he faces just right of the camera
PLAIN_Z = -95.0

def cam_basis():
    f = np.array([-math.sin(CAM_YAW) * math.cos(CAM_PITCH), math.cos(CAM_YAW) * math.cos(CAM_PITCH), math.sin(CAM_PITCH)])
    r = np.array([math.cos(CAM_YAW), math.sin(CAM_YAW), 0.0])
    u = np.cross(r, f)
    return f, r, u

def screen_dir(xf, yf):
    """unit view ray through screen fraction (xf, yf), y from the top"""
    f, r, u = cam_basis()
    return nrm(f + (xf * 2 - 1) * TAN_H * r + (1 - yf * 2) * TAN_V * u)

def ground_at(xf, dist, z=PLAIN_Z):
    d = screen_dir(xf, 0.5); d[2] = 0; d = nrm(d)
    p = CAM + d * dist; p[2] = z
    return p

DOOM = ground_at(0.84, 3600)
BARAD = ground_at(0.07, 5200)
DOOM_H = 520.0
DOOM_R = 900.0

def sauron_matrix():
    f = SAURON_FWD; r = np.array([f[1], -f[0], 0.0])        # his right = forward x up
    M = np.eye(4)
    M[:3, 0] = r; M[:3, 1] = f; M[:3, 2] = [0, 0, 1]
    return M

def to_world(p):
    M = sauron_matrix()
    return M[:3, :3] @ np.asarray(p) + M[:3, 3]

# --------------------------------------------------------------------------- materials
MATS = {}
def M(name):
    return MATS[name]

def lava_color(nb, fac, strength):
    """black-body ramp: dull red -> orange -> yellow-white, times strength (fac 0..1)"""
    c = ramp(nb, [(0.0, (0, 0, 0, 1)), (0.25, (0.35, 0.02, 0.0, 1)), (0.55, (1.0, 0.18, 0.01, 1)),
                  (0.85, (1.0, 0.45, 0.06, 1)), (1.0, (1.0, 0.8, 0.4, 1))], fac)
    e = nb.n('ShaderNodeEmission', i_Strength=strength)
    nb.l(c.outputs['Color'], e.inputs['Color'])
    return e

def make_materials():
    # ---- blackened steel: dark, fairly glossy, hammered, worn brighter on edges
    for name, base, rough in (('iron', '#1b1918', 0.34), ('iron_dark', '#0d0c0c', 0.5)):
        m, nb = new_material(name); MATS[name] = m
        geo = nb.n('ShaderNodeNewGeometry')
        pos = nb.n('ShaderNodeTexCoord').outputs['Object']
        n1 = noise(nb, pos, 9.0, 6, 0.6)
        n2 = noise(nb, pos, 55.0, 4, 0.5)
        edge = nb.maprange(geo.outputs['Pointiness'], 0.5, 0.62)
        col = ramp(nb, [(0.0, base), (1.0, '#3a3532')], edge)
        col2 = nb.mix(nb.maprange(n1.outputs['Fac'], 0.45, 0.75, 0.0, 0.5), col.outputs['Color'], rgb('#2a1c14'))
        bs = nb.n('ShaderNodeBsdfPrincipled', i_Metallic=1.0)
        nb.l(col2, bs.inputs['Base Color'])
        nb.l(nb.maprange(n1.outputs['Fac'], 0.3, 0.7, rough - 0.12, rough + 0.2), bs.inputs['Roughness'])
        bump = nb.n('ShaderNodeBump', i_Strength=0.25, i_Distance=0.004)
        nb.l(n2.outputs['Fac'], bump.inputs['Height']); nb.l(bump.outputs['Normal'], bs.inputs['Normal'])
        nb.l(bs.outputs[0], nb.out.inputs['Surface'])
    # ---- mail: small rings (voronoi bump), dull
    m, nb = new_material('mail'); MATS['mail'] = m
    pos = nb.n('ShaderNodeTexCoord').outputs['Object']
    vor = nb.n('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE', i_Scale=140.0); nb.l(pos, vor.inputs['Vector'])
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Metallic=1.0, i_Roughness=0.45, i_Base_Color=rgb('#22201e'))
    bump = nb.n('ShaderNodeBump', i_Strength=0.8, i_Distance=0.003)
    nb.l(vor.outputs['Distance'], bump.inputs['Height']); nb.l(bump.outputs['Normal'], bs.inputs['Normal'])
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])
    # ---- cloth: black, heavy, a little sheen
    m, nb = new_material('cloth'); MATS['cloth'] = m
    pos = nb.n('ShaderNodeTexCoord').outputs['Object']
    n1 = noise(nb, pos, 30.0, 5)
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.9, i_Base_Color=rgb('#070606'), i_Sheen_Weight=0.05, i_Specular_IOR_Level=0.12,
              i_Sheen_Roughness=0.4)
    bump = nb.n('ShaderNodeBump', i_Strength=0.15, i_Distance=0.003)
    nb.l(n1.outputs['Fac'], bump.inputs['Height']); nb.l(bump.outputs['Normal'], bs.inputs['Normal'])
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])
    # ---- void (eye slits) and the Ring (gold, glowing)
    m, nb = new_material('void'); MATS['void'] = m
    nb.l(nb.n('ShaderNodeBsdfDiffuse', i_Color=(0.0, 0.0, 0.0, 1)).outputs[0], nb.out.inputs['Surface'])
    m, nb = new_material('ring'); MATS['ring'] = m
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Metallic=1.0, i_Roughness=0.15, i_Base_Color=rgb('#ffc35a'),
              i_Emission_Color=(1.0, 0.55, 0.12, 1), i_Emission_Strength=6.0)
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])

    # ---- basalt with glowing lava cracks (crag & boulders). Object coords, so it works at any scale via `sc`.
    for name, sc, glow, ashk in (('rock', 1.0, 30.0, 0.0), ('plain', 0.025, 14.0, 0.0)):
        m, nb = new_material(name); MATS[name] = m
        pos = nb.n('ShaderNodeTexCoord').outputs['Object']
        geo = nb.n('ShaderNodeNewGeometry')
        warp = noise(nb, pos, 0.9 * sc, 3)
        wm = nb.n('ShaderNodeMix', data_type='VECTOR', i_Factor=0.35 / sc)
        nb.l(pos, wm.inputs[4]); nb.l(warp.outputs['Color'], wm.inputs[5])
        cr1 = nb.n('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE', i_Scale=0.9 * sc, i_Randomness=1.0)
        nb.l(wm.outputs[1], cr1.inputs['Vector'])
        cr2 = nb.n('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE', i_Scale=3.2 * sc, i_Randomness=1.0)
        nb.l(wm.outputs[1], cr2.inputs['Vector'])
        gate = nb.maprange(noise(nb, pos, 0.35 * sc, 3).outputs['Fac'], 0.52, 0.62)
        c1 = nb.maprange(cr1.outputs['Distance'], 0.022, 0.0)
        c2 = nb.maprange(cr2.outputs['Distance'], 0.012, 0.0)
        c2g = nb.math('MULTIPLY', c2, nb.maprange(noise(nb, pos, 0.5 * sc, 2).outputs['Fac'], 0.5, 0.62))
        crack = nb.math('MAXIMUM', nb.math('MULTIPLY', c1, gate), nb.math('MULTIPLY', c2g, 0.7))
        # flat tops hold more lava than walls
        sep = nb.n('ShaderNodeSeparateXYZ'); nb.l(geo.outputs['Normal'], sep.inputs[0])
        flat = nb.maprange(sep.outputs['Z'], 0.55, 0.85)
        crack = nb.math('MULTIPLY', crack, flat)
        if name == 'rock':
            crack = nb.math('MULTIPLY', crack, attr(nb, 'lava').outputs['Fac'])
        heat = nb.math('POWER', crack, 1.4)
        em = lava_color(nb, heat, glow)
        n1 = noise(nb, pos, 2.5 * sc, 8, 0.62)
        n2 = noise(nb, pos, 14.0 * sc, 5, 0.6)
        col = ramp(nb, [(0.3, '#050404'), (0.55, '#0c0b0a'), (0.75, '#161312')], n1.outputs['Fac'])
        # ash: lighter grey dust on up-facing surfaces
        ash = nb.maprange(nb.math('ADD', sep.outputs['Z'], nb.math('MULTIPLY', n2.outputs['Fac'], 0.5)), 1.05, 1.35)
        col2 = nb.mix(nb.math('MULTIPLY', ash, ashk), col.outputs['Color'], rgb('#34302c'))
        # scorched red-brown near the cracks
        near = nb.maprange(cr1.outputs['Distance'], 0.16, 0.04)
        col3 = nb.mix(nb.math('MULTIPLY', near, nb.math('MULTIPLY', gate, 0.6)), col2, rgb('#2a120a'))
        bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.93, i_Specular_IOR_Level=0.15)
        nb.l(col3, bs.inputs['Base Color'])
        hb = nb.math('ADD', nb.math('MULTIPLY', n1.outputs['Fac'], 0.6), nb.math('MULTIPLY', n2.outputs['Fac'], 0.08))
        hb = nb.math('SUBTRACT', hb, nb.math('MULTIPLY', nb.math('MAXIMUM', c1, c2), 0.5))
        bump = nb.n('ShaderNodeBump', i_Strength=0.6, i_Distance=0.06 / sc)
        nb.l(hb, bump.inputs['Height']); nb.l(bump.outputs['Normal'], bs.inputs['Normal'])
        add = nb.n('ShaderNodeAddShader')
        nb.l(bs.outputs[0], add.inputs[0]); nb.l(em.outputs[0], add.inputs[1])
        nb.l(add.outputs[0], nb.out.inputs['Surface'])

    # ---- Mount Doom: ash and slag, lava rivers from a vertex attribute
    m, nb = new_material('doom'); MATS['doom'] = m
    pos = nb.n('ShaderNodeTexCoord').outputs['Object']
    lv = attr(nb, 'lava').outputs['Fac']
    n1 = noise(nb, pos, 0.02, 8, 0.6)
    lvn = nb.math('MULTIPLY', lv, nb.maprange(noise(nb, pos, 0.03, 6).outputs['Fac'], 0.42, 0.62, 0.0, 1.1))
    em = lava_color(nb, nb.math('MINIMUM', lvn, 1.0), 11.0)
    col = ramp(nb, [(0.35, '#0c0b0b'), (0.65, '#221e1b')], n1.outputs['Fac'])
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.9)
    nb.l(col.outputs['Color'], bs.inputs['Base Color'])
    add = nb.n('ShaderNodeAddShader'); nb.l(bs.outputs[0], add.inputs[0]); nb.l(em.outputs[0], add.inputs[1])
    nb.l(add.outputs[0], nb.out.inputs['Surface'])
    # ---- tower stone: black, a faint sheen
    m, nb = new_material('tower'); MATS['tower'] = m
    bs = nb.n('ShaderNodeBsdfPrincipled', i_Roughness=0.55, i_Metallic=0.4, i_Base_Color=rgb('#0c0b0b'))
    nb.l(bs.outputs[0], nb.out.inputs['Surface'])
    # ---- emissive fire / the Eye
    for name, col, s in (('fire', (1.0, 0.35, 0.05, 1), 60.0), ('window', (1.0, 0.3, 0.05, 1), 25.0)):
        m, nb = new_material(name); MATS[name] = m
        nb.l(nb.n('ShaderNodeEmission', i_Color=col, i_Strength=s).outputs[0], nb.out.inputs['Surface'])
    m, nb = new_material('eye'); MATS['eye'] = m
    tc = nb.n('ShaderNodeTexCoord').outputs['Generated']
    sep = nb.n('ShaderNodeSeparateXYZ'); nb.l(tc, sep.inputs[0])
    dx = nb.math('ABSOLUTE', nb.math('SUBTRACT', sep.outputs['X'], 0.5))
    slit = nb.maprange(dx, 0.03, 0.08)
    fl = noise(nb, tc, 6.0, 6)
    heat = nb.math('MULTIPLY', slit, nb.maprange(fl.outputs['Fac'], 0.3, 0.7, 0.7, 1.0))
    em = lava_color(nb, heat, 45.0)
    nb.l(em.outputs[0], nb.out.inputs['Surface'])
    # ---- ember sparks
    m, nb = new_material('ember'); MATS['ember'] = m
    info = nb.n('ShaderNodeObjectInfo')
    a = attr(nb, 'ember_t').outputs['Fac']     # not 'heat': Cycles reserves it (smoke)
    em = lava_color(nb, a, 1.0)
    st = nb.math('MULTIPLY', nb.math('POWER', a, 3.0), 14.0)
    nb.l(st, em.inputs['Strength'])
    nb.l(em.outputs[0], nb.out.inputs['Surface'])
    # ---- Doom's plume (volume): dark smoke lit from beneath
    m, nb = new_material('plume'); MATS['plume'] = m
    tc = nb.n('ShaderNodeTexCoord').outputs['Object']
    sep = nb.n('ShaderNodeSeparateXYZ'); nb.l(tc, sep.inputs[0])
    hz = sep.outputs['Z']
    # column axis leans downwind (-x) as it rises and spreads: r(h) = 70 + 0.42 h
    dx = nb.math('ADD', sep.outputs['X'], nb.math('MULTIPLY', nb.math('POWER', nb.math('MAXIMUM', hz, 0.0), 1.2), 0.07))
    dy = nb.math('SUBTRACT', sep.outputs['Y'], nb.math('MULTIPLY', hz, 0.06))
    dist = nb.math('SQRT', nb.math('ADD', nb.math('MULTIPLY', dx, dx), nb.math('MULTIPLY', dy, dy)))
    rad = nb.math('ADD', nb.math('MULTIPLY', hz, 0.33), 60.0)
    warp = noise(nb, tc, 0.004, 3)
    wv = nb.n('ShaderNodeMix', data_type='VECTOR', i_Factor=260.0)
    nb.l(tc, wv.inputs[4]); nb.l(warp.outputs['Color'], wv.inputs[5])
    n1 = noise(nb, wv.outputs[1], 0.006, 8, 0.6)
    q = nb.math('DIVIDE', dist, rad)
    q = nb.math('SUBTRACT', q, nb.math('MULTIPLY', nb.math('SUBTRACT', n1.outputs['Fac'], 0.5), 2.2))
    fall = nb.maprange(q, 1.0, 0.45)
    dens = nb.math('MULTIPLY', fall, nb.maprange(n1.outputs['Fac'], 0.35, 0.65, 0.3, 1.0))
    dens = nb.math('MULTIPLY', dens, nb.maprange(hz, 1950, 900))
    dens = nb.math('MULTIPLY', dens, nb.maprange(hz, -20, 30))
    dens = nb.math('MULTIPLY', dens, 0.03)
    vol = nb.n('ShaderNodeVolumePrincipled', i_Color=rgb('#2c2826'), i_Anisotropy=0.3)
    nb.l(dens, vol.inputs['Density'])
    ems = nb.math('MULTIPLY', nb.math('POWER', nb.maprange(hz, 500, 0), 2.0), 90.0)
    ems = nb.math('MULTIPLY', ems, nb.math('MULTIPLY', dens, 0.02))                    # principled volume emission is not scaled by density
    nb.l(ems, vol.inputs['Emission Strength'])
    vol.inputs['Emission Color'].default_value = (1.0, 0.22, 0.03, 1)
    nb.l(vol.outputs[0], nb.out.inputs['Volume'])

# --------------------------------------------------------------------------- terrain
def crag_height(x, y):
    """the rock Sauron stands on: a rough flat-topped crag at the origin falling away to the plain"""
    rx, ry = x - 0.2, y - 0.6
    d = np.sqrt(rx * rx * 0.8 + ry * ry * 1.1)
    top = 0.10 * fbm(x * 0.9, y * 0.9, 5, 3) + 0.05 * ridged(x * 2.5, y * 2.5, 4, 4) - 0.08
    drop = smoothstep(2.2, 9.0, d + 1.2 * fbm(x * 0.3, y * 0.3, 3, 5)) ** 1.1 * 26.0
    jag = 1.6 * ridged(x * 0.45, y * 0.45, 6, 6) * smoothstep(2.0, 5.0, d)
    jag = jag + (0.45 * ridged(x * 1.7, y * 1.7, 5, 8) ** 2 - 0.25 * np.abs(fbm(x * 3.5, y * 3.5, 4, 9))) * smoothstep(1.2, 3.0, d)
    jag = jag + 0.03 * fbm(x * 9, y * 9, 3, 10)
    h = top - drop + jag
    # the feet: flatten under them
    for (fx, fy), r in (((0.0, 0.0), 0.9),):
        h = h * (1 - (1 - smoothstep(0.3, r, np.hypot(x - fx, y - fy))) * 0.7)
    return h

def build_crag():
    n = 360
    xs = np.linspace(-11, 13, n); ys = np.linspace(-8.5, 16, n)
    X, Y = np.meshgrid(xs, ys, indexing='xy')
    Z = crag_height(X, Y)
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    ob = mesh_obj('crag', V, grid_faces(n, n).tolist())
    ob.data.materials.append(M('rock'))
    ob.data.polygons.foreach_set('use_smooth', np.ones(len(ob.data.polygons), bool))
    # lava only away from his feet (no glowing cracks under the boots)
    d = np.hypot(X, Y).ravel()
    set_attr(ob, 'lava', smoothstep(0.7, 1.4, d))
    # boulders: the one under his left foot, and a jumble on the crag edges
    g = Geo()
    lf = to_world(sauron.J['l_an'])
    g.add_vf(sphere_grid(np.array([lf[0], lf[1], sauron.LEFT_ROCK_TOP - 0.30]), 0.36, 14, 20, 0.3, seed=3,
                         nscale=2.2, squash=(1.3, 1.1, 0.8), sharp=0.25))
    rng = np.random.default_rng(12)
    for i in range(70):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(1.6, 7.0)
        x, y = 0.2 + math.cos(a) * r * 1.1, 0.6 + math.sin(a) * r
        if y < -2.0 and abs(x - CAM[0]) < 4: continue
        s = rng.uniform(0.15, 0.6) * (0.6 + r / 7)
        z = float(crag_height(np.array(x), np.array(y)))
        g.add_vf(sphere_grid(np.array([x, y, z + s * 0.1]), s, 14, 18, 0.7, seed=int(i + 20), nscale=1.1, sharp=0.5,
                             squash=(1.0, rng.uniform(0.7, 1.2), rng.uniform(0.45, 0.85))))
    ob2 = geo_obj('boulders', g, M('rock'), smooth=False)
    set_attr(ob2, 'lava', np.zeros(len(ob2.data.vertices)))

def frustum_grid(y0, y1, rows, cols, half_w, geo_k):
    i = np.arange(rows)
    a = math.log((y1 - y0) / geo_k + 1) / (rows - 1)
    ys = y0 + geo_k * (np.exp(a * i) - 1)
    u = np.linspace(-1, 1, cols)
    Y = np.repeat(ys[:, None], cols, 1)
    X = CAM[0] + u[None, :] * half_w(ys)[:, None]
    return X, Y

def build_plain():
    X, Y = frustum_grid(4.0, 16000, 420, 700, lambda y: (y - CAM[1]) * 0.95 + 30, 25.0)
    Z = PLAIN_Z + 6 * fbm(X * 0.004, Y * 0.004, 6, 21) + 3 * ridged(X * 0.02, Y * 0.02, 5, 22)
    # cinder cones and slag ridges
    rng = np.random.default_rng(5)
    for i in range(26):
        cx, cy = rng.uniform(-5000, 5000), rng.uniform(300, 9000)
        r = rng.uniform(60, 260); h = r * rng.uniform(0.25, 0.5)
        d = np.hypot(X - cx, Y - cy)
        Z += h * np.clip(1 - d / r, 0, 1) ** 1.3
    # Mount Doom's apron
    d = np.hypot(X - DOOM[0], Y - DOOM[1])
    Z += 60 * np.clip(1 - d / (DOOM_R * 2.2), 0, 1) ** 2
    # the far ranges: Ephel Duath behind Barad-dur, Ered Lithui on the right
    Z += smoothstep(7000, 12000, Y) * (700 * ridged(X * 0.0006, Y * 0.0006, 7, 31) ** 1.3 + 200)
    # keep the crag's foot below the crag (camera rows nearest)
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    ob = mesh_obj('plain', V, grid_faces(*X.shape).tolist())
    ob.data.materials.append(M('plain'))
    ob.data.polygons.foreach_set('use_smooth', np.ones(len(ob.data.polygons), bool))

def build_doom():
    nr, na = 140, 360
    r = np.linspace(0, 1, nr)[:, None] ** 1.3 * DOOM_R
    a = np.linspace(0, 2 * math.pi, na, endpoint=False)[None, :]
    x = np.cos(a) * r; y = np.sin(a) * r
    u = r / DOOM_R
    u = u * (1 + 0.28 * fbm(np.cos(a) * 1.3 + 4, np.sin(a) * 1.3, 3, 44) + 0.08 * fbm(np.cos(a) * 5, np.sin(a) * 5, 3, 45))
    # shoulder + steep cone ("like a vast oast"), jagged crater
    prof = 0.40 * np.clip(1 - u, 0, 1) ** 2.2 + 0.60 * smoothstep(0.34, 0.07, u) ** 1.2
    gul = ridged(np.cos(a) * 9 + u * 2, np.sin(a) * 9 + u * 2, 6, 41)
    z = DOOM_H * prof * (1 + 0.10 * fbm(x * 0.006, y * 0.006, 5, 42)) - 80 * gul * u * (1 - u)
    z = z - 40 * np.cos(a - 0.7) * smoothstep(0.25, 0.0, u)          # a breached, slanting summit
    crater = smoothstep(0.075, 0.0, u)
    z = z - crater * 70 + 18 * ridged(np.cos(a) * 3, np.sin(a) * 3, 3, 43) * smoothstep(0.02, 0.09, u) * (u < 0.1)
    V = np.stack(np.broadcast_arrays(x, y, z), -1).reshape(-1, 3) + np.array([DOOM[0], DOOM[1], PLAIN_Z])
    F = []
    idx = np.arange(nr * na).reshape(nr, na)
    a0 = idx[:-1]; a1 = np.roll(idx[:-1], -1, 1); b1 = np.roll(idx[1:], -1, 1); b0 = idx[1:]
    F = np.stack([a0, a1, b1, b0], -1).reshape(-1, 4).tolist()
    ob = mesh_obj('doom', V, F)
    ob.data.materials.append(M('doom'))
    ob.data.polygons.foreach_set('use_smooth', np.ones(len(ob.data.polygons), bool))
    # lava: rivers down gullies on the near side + the crater + a breach toward the camera
    to_cam = math.atan2(CAM[1] - DOOM[1], CAM[0] - DOOM[0])
    lava = np.zeros_like(np.broadcast_to(x, (nr, na)))
    for k, (off, w, reach) in enumerate(((-0.12, 0.016, 0.62), (0.34, 0.011, 0.40), (-0.58, 0.010, 0.33),
                                         (0.70, 0.008, 0.25))):
        wig = off + 0.22 * np.sin(u * 4 + k * 2) + 0.30 * fbm(u * 3, k * 3.1, 4, 50 + k) + 0.06 * fbm(u * 14, k, 3, 60 + k)
        w = w * (0.6 + 0.8 * vnoise(u * 12, k * 5.0, 70 + k))
        da = np.angle(np.exp(1j * (a - to_cam - wig)))
        lava = np.maximum(lava, smoothstep(w, 0.0, np.abs(da)) * smoothstep(reach, reach * 0.6, u)
                          * smoothstep(0.03, 0.07, u))
    lava = np.maximum(lava, smoothstep(0.06, 0.02, u) * 1.0)
    set_attr(ob, 'lava', lava.ravel())
    # fire in the crater (a light) and the plume
    top = np.array([DOOM[0], DOOM[1], PLAIN_Z + DOOM_H * 0.98])
    L = bpy.data.lights.new('crater', 'POINT'); L.energy = 4.0e6; L.color = (1.0, 0.35, 0.08); L.shadow_soft_size = 60
    lo = bpy.data.objects.new('crater', L); lo.location = Vector(top + np.array([0, 0, 90]))
    bpy.context.scene.collection.objects.link(lo)
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.active_object; ob.name = 'plume'
    ob.data.transform(Matrix.Translation((-0.25, 0.0, 0.5)))
    ob.data.transform(Matrix.Diagonal((2600, 1400, 2000, 1)))
    ob.location = Vector(top)
    ob.data.materials.append(M('plume'))

def build_barad_dur():
    """far off: black crag, the tower of stepped ribbed stages, the two prongs and the Eye between them"""
    g, gw = Geo(), Geo()
    base = BARAD.copy()
    # crag
    g.add_vf(sphere_grid(base + np.array([0, 0, -40]), 380, 16, 28, 0.35, seed=71, squash=(1, 1, 0.45)))
    stages = [(62, 50, 120, 360, 18), (44, 37, 360, 580, 16), (33, 27, 580, 760, 14), (24, 19, 760, 900, 12),
              (17, 13, 900, 1010, 10)]
    for r0, r1, z0, z1, ribs in stages:
        P = np.stack([base + [0, 0, z0], base + [0, 0, z1]])
        g.add_vf(tube(P, [r0, r1], ref=(1, 0, 0), K=ribs * 2))
        for k in range(ribs):
            a = 2 * math.pi * (k + 0.5) / ribs
            o = np.array([math.cos(a), math.sin(a), 0])
            Q = np.stack([base + [0, 0, z0] + o * (r0 + 6), base + [0, 0, z1 - 10] + o * (r1 + 4)])
            g.add_vf(tube(Q, 5, 3, ref=o, K=4))
            g.add_vf(spike(base + [0, 0, z1 - 5] + o * (r1 + 6), o - np.array([0, 0, 0.6]), 30, 4, K=4))
            if k % 3 == 0:
                w = base + [0, 0, z0 + (z1 - z0) * 0.5] + o * (0.5 * (r0 + r1) + 1)
                gw.add_vf(tube(np.stack([w, w + [0, 0, 9]]), 1.6, ref=o, K=4))
        # ledge
        g.add_vf(tube(np.stack([base + [0, 0, z1 - 12], base + [0, 0, z1]]), [r1 + 12, r1 + 9], ref=(1, 0, 0),
                      K=ribs * 2))
    top = base + [0, 0, 1010]
    for sx in (1, -1):
        s = np.linspace(0, 1, 14)
        P = top[None] + np.stack([sx * (12 + 46 * np.sin(s * 2.2)), 0 * s, s * 250], -1)
        g.add_vf(tube(P, 15 * (1 - s) + 2, 9 * (1 - s) + 1.5, ref=(1, 0, 0), K=6))
    ob = geo_obj('baraddur', g, M('tower'))
    geo_obj('baraddur_windows', gw, M('window'), smooth=False)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=24, ring_count=12)
    e = bpy.context.active_object; e.name = 'eye'
    e.scale = (16, 7, 38); e.location = Vector(top + [0, 0, 130])
    # face the camera
    d = CAM - (top + [0, 0, 130]); e.rotation_euler = (0, 0, math.atan2(d[1], d[0]) + math.pi / 2)
    e.data.materials.append(M('eye'))
    # a fire halo round the Eye
    bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.18)
    h = bpy.context.active_object; h.scale = (22, 22, 42); h.location = e.location
    h.rotation_euler = (math.pi / 2, 0, e.rotation_euler[2])
    h.data.materials.append(M('fire'))

# --------------------------------------------------------------------------- debris, embers
def build_debris():
    """broken spears and a few helms of the slain at his feet"""
    rng = np.random.default_rng(31)
    g = Geo()
    for i in range(14):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0.9, 2.8)
        x, y = 0.2 + math.cos(a) * r, 0.3 + math.sin(a) * r
        z = float(crag_height(np.array(x), np.array(y)))
        d = nrm(np.array([rng.normal(), rng.normal(), rng.uniform(-0.1, 0.5)]))
        L = rng.uniform(0.6, 1.8)
        p0 = np.array([x, y, z + 0.03])
        if rng.random() < 0.4:          # stuck in the ground, leaning
            d = nrm(np.array([rng.normal() * 0.5, rng.normal() * 0.5, 1.0])); p0[2] -= 0.15
        g.add_vf(tube(np.stack([p0, p0 + d * L]), 0.016, ref=(0, 0, 1), K=6))
        if rng.random() < 0.5:
            g.add_vf(spike(p0 + d * L, d, 0.22, 0.03, K=4, flat=0.3))
    for i in range(6):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0.9, 2.2)
        x, y = 0.2 + math.cos(a) * r, 0.3 + math.sin(a) * r
        z = float(crag_height(np.array(x), np.array(y)))
        g.add_vf(sphere_grid(np.array([x, y, z]), 0.13, 8, 12, 0.05, seed=i, squash=(1, 1.15, 0.9), flat_bottom=0.0))
    ob = geo_obj('debris', g, M('iron_dark'), bevel=0.003)

def build_embers(n=750):
    rng = np.random.default_rng(77)
    f, r, u = cam_basis()
    depth = np.exp(rng.uniform(math.log(3.5), math.log(90), n))
    xf = rng.uniform(-0.1, 1.1, n); yf = rng.uniform(0, 1, n) ** 0.8 * 1.2 - 0.1
    V, F, H = [], [], []
    for i in range(n):
        d = screen_dir(xf[i], yf[i])
        p = CAM + d * depth[i] / max(np.dot(d, f), 0.3)
        s = 0.0011 * depth[i] * rng.uniform(0.5, 1.3)
        streak = nrm(np.array([0.5, 0.2, 1.0]) + rng.normal(0, 0.4, 3)) * s * rng.uniform(2, 5)
        k = len(V)
        side = nrm(np.cross(streak, d)) * s * 0.5
        V += [p - streak, p + side, p + streak, p - side, p + nrm(np.cross(side, streak)) * s * 0.4]
        F += [[k, k + 1, k + 2, k + 3], [k, k + 1, k + 4], [k + 1, k + 2, k + 4], [k + 2, k + 3, k + 4], [k + 3, k, k + 4]]
        H += [rng.uniform(0.4, 1.0) ** 2] * 5
    ob = mesh_obj('embers', np.array(V), F)
    ob.data.materials.append(M('ember'))
    set_attr(ob, 'ember_t', np.array(H))
    ob.visible_shadow = False; ob.visible_diffuse = False; ob.visible_glossy = False

# --------------------------------------------------------------------------- sky, lights, camera
def build_world():
    w = bpy.data.worlds.new('sky'); bpy.context.scene.world = w
    w.use_nodes = True
    nb = NB(w.node_tree)
    out = nb.n('ShaderNodeOutputWorld')
    D = nb.n('ShaderNodeTexCoord').outputs['Generated']
    sep = nb.n('ShaderNodeSeparateXYZ'); nb.l(D, sep.inputs[0])
    el = sep.outputs['Z']
    # cloud layers: stretched noise on the direction (squashed vertically -> sheets of smoke)
    mp = nb.n('ShaderNodeMapping', i_Scale=(1.0, 1.0, 3.2)); nb.l(D, mp.inputs['Vector'])
    c1 = noise(nb, mp.outputs['Vector'], 4.0, 12, 0.64)
    c2 = noise(nb, mp.outputs['Vector'], 13.0, 10, 0.58)
    dens = nb.math('ADD', c1.outputs['Fac'], nb.math('MULTIPLY', c2.outputs['Fac'], 0.35))
    dens = nb.maprange(dens, 0.6, 1.0)
    # glow from Doom on the cloud undersides and a burning horizon behind it
    dd = nrm(np.array([DOOM[0] - CAM[0], DOOM[1] - CAM[1], DOOM_H * 1.1 + PLAIN_Z - CAM[2]]))
    dot = nb.n('ShaderNodeVectorMath', operation='DOT_PRODUCT'); nb.l(D, dot.inputs[0])
    dot.inputs[1].default_value = tuple(dd)
    g_wide = nb.math('POWER', nb.maprange(dot.outputs['Value'], 0.3, 1.0), 3.0)
    g_tight = nb.math('POWER', nb.maprange(dot.outputs['Value'], 0.85, 1.0), 6.0)
    horizon = nb.math('POWER', nb.maprange(el, 0.35, 0.0), 2.0)
    # a pale rift low in the west (left), behind the tower: the last daylight
    bd = nrm(np.array([BARAD[0] - CAM[0] + 900, BARAD[1] - CAM[1], 0.0]))
    dot2 = nb.n('ShaderNodeVectorMath', operation='DOT_PRODUCT'); nb.l(D, dot2.inputs[0])
    dot2.inputs[1].default_value = tuple(bd)
    rift = nb.math('MULTIPLY', nb.math('POWER', nb.maprange(dot2.outputs['Value'], 0.75, 1.0), 2.0),
                   nb.math('POWER', nb.maprange(el, 0.12, 0.0), 1.5))
    rift = nb.math('MULTIPLY', rift, nb.maprange(c2.outputs['Fac'], 0.65, 0.35))
    base = ramp(nb, [(0.0, (0.003, 0.0027, 0.0027, 1)), (1.0, (0.012, 0.009, 0.008, 1))], horizon)
    warm = nb.math('ADD', nb.math('MULTIPLY', g_wide, 0.22), nb.math('MULTIPLY', g_tight, 2.2))
    warm = nb.math('MULTIPLY', warm, nb.math('ADD', nb.math('MULTIPLY', horizon, 1.2), 0.25))
    lit = nb.math('MULTIPLY', warm, nb.math('ADD', nb.math('MULTIPLY', dens, 1.6), 0.15))
    col = nb.mix(dens, base.outputs['Color'], (0.007, 0.0065, 0.0065, 1))
    emb = nb.n('ShaderNodeMix', data_type='RGBA', blend_type='ADD', i_Factor=1.0)
    nb.l(col, emb.inputs[6]); emb.inputs[7].default_value = (0.0, 0.0, 0.0, 1)
    warmcol = nb.n('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY', i_Factor=1.0)
    warmcol.inputs[7].default_value = (0.5, 0.11, 0.02, 1)
    fac_rgb = nb.n('ShaderNodeCombineXYZ'); nb.l(lit, fac_rgb.inputs[0]); nb.l(lit, fac_rgb.inputs[1]); nb.l(lit, fac_rgb.inputs[2])
    nb.l(fac_rgb.outputs[0], warmcol.inputs[6])
    nb.l(warmcol.outputs[2], emb.inputs[7])
    riftc = nb.n('ShaderNodeMix', data_type='RGBA', blend_type='ADD', i_Factor=1.0)
    nb.l(emb.outputs[2], riftc.inputs[6])
    rr = nb.n('ShaderNodeCombineXYZ')
    nb.l(nb.math('MULTIPLY', rift, 0.9), rr.inputs[0]); nb.l(nb.math('MULTIPLY', rift, 0.75), rr.inputs[1])
    nb.l(nb.math('MULTIPLY', rift, 0.62), rr.inputs[2])
    nb.l(rr.outputs[0], riftc.inputs[7])
    bg = nb.n('ShaderNodeBackground', i_Strength=1.0)
    nb.l(riftc.outputs[2], bg.inputs['Color'])
    nb.l(bg.outputs[0], out.inputs['Surface'])

def area(name, loc, target, size, energy, color, spot=None):
    L = bpy.data.lights.new(name, 'AREA'); L.energy = energy; L.color = color
    L.shape = 'DISK'; L.size = size
    ob = bpy.data.objects.new(name, L); bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(loc)
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if spot: L.spread = math.radians(spot)
    return ob

def build_lights(ring_pos):
    S = to_world((0, 0, 1.7))
    # rim/back light: the glow of Doom behind his right shoulder (screen right), hot orange
    area('rim', S + nrm(np.array([3.0, 4.5, 1.6])) * 6, S, 3.0, 2600, (1.0, 0.42, 0.12))
    area('rim2', S + nrm(np.array([-3.5, 3.5, 2.5])) * 6, S + [0, 0, 0.6], 2.5, 900, (1.0, 0.5, 0.22))
    # cold, dim key from the overcast (camera left, high)
    area('key', S + nrm(np.array([-4.0, -5.0, 5.0])) * 9, S, 6.0, 2200, (0.70, 0.72, 0.80))
    # the lava's under-glow
    area('under', S + np.array([0.4, -1.8, -1.55]), S + [0, 0, 0.5], 2.4, 140, (1.0, 0.32, 0.07))
    # the Ring
    L = bpy.data.lights.new('ring', 'POINT'); L.energy = 6.0; L.color = (1.0, 0.55, 0.15); L.shadow_soft_size = 0.02
    ob = bpy.data.objects.new('ringlight', L); bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(ring_pos)

def build_camera(studio=False):
    cam_d = bpy.data.cameras.new('cam'); cam_d.lens = LENS; cam_d.sensor_width = SENSOR
    cam_d.clip_start = 0.05; cam_d.clip_end = 60000
    cam = bpy.data.objects.new('cam', cam_d); bpy.context.scene.collection.objects.link(cam)
    if studio:
        S = to_world((0, 0, 1.85))
        p = S + SAURON_FWD * float(arg('--sdist', 7.0)) + np.array([0.9, 0, 0.1]) * float(arg('--sdist', 7.0)) / 7
        S = S + np.array([0, 0, float(arg('--sz', 0.0))])
        cam.location = Vector(p)
        cam.rotation_euler = (Vector(S) - Vector(p)).to_track_quat('-Z', 'Y').to_euler()
        cam_d.lens = 32
    else:
        cam.location = Vector(CAM)
        cam.rotation_euler = Euler((math.pi / 2 + CAM_PITCH, 0, CAM_YAW), 'XYZ')
    bpy.context.scene.camera = cam

def build_sauron():
    G = sauron.build()
    ring_pos = to_world(G.pop('ring_light'))
    Mw = sauron_matrix()
    for name, g in G.items():
        g.transform(Mw)
        geo_obj('sauron_' + name, g, M(name), bevel=0.004 if name.startswith('iron') else None)
    return ring_pos

def write_meta():
    cam = bpy.context.scene.camera
    json.dump({'cam_matrix': [list(r) for r in cam.matrix_world], 'lens': cam.data.lens, 'sensor': cam.data.sensor_width,
               'res': [RES_X, RES_Y], 'doom': list(DOOM), 'doom_h': DOOM_H, 'barad': list(BARAD), 'plain_z': PLAIN_Z},
              open(OUT + '_meta.json', 'w'))

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    make_materials()
    # big meshes with sparse glowing cracks: don't treat them as lights (thousands of fireflies); the lava's light
    # on Sauron and the rock comes from the area lamps instead
    for n in ('rock', 'plain', 'doom', 'ember'):
        M(n).cycles.emission_sampling = 'NONE'
    ring = build_sauron()
    build_world()
    build_lights(ring)
    build_camera(STUDIO)
    if STUDIO:
        g = Geo(); g.add_vf(sphere_grid(np.zeros(3) - [0, 0, 3.0], 3.0, 10, 20))
        geo_obj('floor', g, M('rock'))
    else:
        build_crag()
        build_plain()
        build_doom()
        build_barad_dur()
        build_debris()
        build_embers()
    if '--save-blend' in ARGS:
        bpy.ops.wm.save_as_mainfile(filepath=OUT + '.blend')
    write_meta()
    render(OUT, RES_X, RES_Y, SAMPLES)

main()
