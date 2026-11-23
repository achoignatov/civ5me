"""Build the capital models: Blender modelling -> UV -> texture bake -> .gr2/.dds/.fxsxml + previews.

Run:  blender --background --factory-startup --python tools/capitals/pipeline.py -- [names...] [--tex 1024] [--no-preview]
Output: build/capitals/out/<Name>.{gr2,fxsxml}, <Name>_DIFF.dds, <Name>_SREF.dds
        build/capitals/preview/<Name>.png
Nothing is written outside the repository.
"""
import importlib
import math
import os
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'models'))
VENV = os.path.join(ROOT, 'build', 'venv', 'lib', 'python%d.%d' % sys.version_info[:2], 'site-packages')
sys.path.append(VENV)

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import atlas  # noqa: E402
import blib  # noqa: E402
import civ5model  # noqa: E402
import dds  # noqa: E402

OUT = os.path.join(ROOT, 'build', 'capitals', 'out')
PREVIEW = os.path.join(ROOT, 'build', 'capitals', 'preview')
WORK = os.path.join(ROOT, 'build', 'capitals', 'work')

from capitals import CAPITALS, PARTICLES  # noqa: E402
from citystates import CITYSTATES  # noqa: E402


def common_materials():
    M, h = blib.material, blib.hexcol
    M('grass', h('5f7f35'), h('7d9a45'), noise=0.35)
    M('dirt', h('7a6447'), h('8f7756'), noise=0.6)
    M('rock', h('77756f'), h('5d5b56'), noise=0.25)
    M('darkrock', h('3b3836'), h('2a2726'), noise=0.3)
    M('snow', h('e9edf0'), h('d5dde3'), noise=0.3)
    M('bark', h('4a3627'))
    M('leaves', h('3f6b2a'), h('557f33'), noise=1.2)
    M('pine', h('2c4a2c'), h('365a33'), noise=1.2)
    M('window', h('1d1a18'))
    M('water', h('3d6c8a'), h('4f84a3'), noise=0.15, ao=False)
    M('wood', h('6b4a2f'), h('5a3c25'), noise=1.5)
    M('gold', h('d1a43a'), h('b8862a'), noise=2.0)
    M('iron', h('2e2f33'))
    blib.SKIRT_MAT[0] = 'rock'


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    blib.PALETTE.clear()
    blib.SKIRT_MAT[0] = None
    common_materials()


def finalize(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.004, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')


def bake(ob, tex):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.render.bake.margin = 6
    if sc.world is None:
        sc.world = bpy.data.worlds.new('w')
    sc.world.light_settings.distance = 1.6
    imgs = {}
    for kind in ('diff', 'ao'):
        img = bpy.data.images.new(kind, tex, tex, alpha=False)
        if kind == 'ao':
            img.colorspace_settings.name = 'Non-Color'
        imgs[kind] = img
    for kind in ('diff', 'ao'):
        for m in ob.data.materials:
            nt = m.node_tree
            n = nt.nodes.get('bake_target') or nt.nodes.new('ShaderNodeTexImage')
            n.name = 'bake_target'
            n.image = imgs[kind]
            nt.nodes.active = n
        if kind == 'diff':
            sc.cycles.samples = 4
            bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_clear=True)
        else:
            sc.cycles.samples = 48
            bpy.ops.object.bake(type='AO', use_clear=True)
    d = np.array(imgs['diff'].pixels[:], np.float32).reshape(tex, tex, 4)
    a = np.array(imgs['ao'].pixels[:], np.float32).reshape(tex, tex, 4)[..., :1]
    col = d[..., :3] * (0.42 + 0.58 * a)
    return np.flipud(np.clip(col, 0, 1))  # top row first (DirectX / DDS order)


def export_arrays(ob):
    me = ob.data
    name = me.uv_layers.active.name
    me.calc_tangents(uvmap=name)
    nl = len(me.loops)
    vi = np.zeros(nl, np.int32); me.loops.foreach_get('vertex_index', vi)
    nrm = np.zeros(nl * 3, np.float32); me.loops.foreach_get('normal', nrm)
    tan = np.zeros(nl * 3, np.float32); me.loops.foreach_get('tangent', tan)
    sgn = np.zeros(nl, np.float32); me.loops.foreach_get('bitangent_sign', sgn)
    uv = np.zeros(nl * 2, np.float32); me.uv_layers[name].data.foreach_get('uv', uv)
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co)
    nrm, tan, uv, co = nrm.reshape(-1, 3), tan.reshape(-1, 3), uv.reshape(-1, 2), co.reshape(-1, 3)
    pos = co[vi]
    uv[:, 1] = 1.0 - uv[:, 1]                       # DirectX: v=0 at the top of the texture
    bn = -np.cross(nrm, tan) * sgn[:, None]         # V is flipped, so the binormal flips too
    key = np.concatenate([np.round(pos, 4), np.round(nrm, 3), np.round(uv, 5)], 1)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    verts = [(tuple(pos[i]), tuple(nrm[i]), tuple(tan[i]), tuple(bn[i]), tuple(uv[i])) for i in first]
    ls = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('loop_start', ls)
    inv = inv.reshape(-1)
    tris = [(int(inv[s]), int(inv[s + 1]), int(inv[s + 2])) for s in ls]
    return verts, tris


def look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def preview(name, verts, tris, img_top_first, size=(900, 640), extra=(), fx=()):
    """Rebuild the model from the exported arrays + decoded DDS and render it (validates the export)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new('pv')
    me.from_pydata([v[0] for v in verts], [], tris)
    me.update()
    uvl = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            u, v = verts[me.loops[li].vertex_index][4]
            uvl.data[li].uv = (u, 1.0 - v)
    me.normals_split_custom_set_from_vertices([v[1] for v in verts]) if hasattr(me, 'normals_split_custom_set_from_vertices') else None
    ob = bpy.data.objects.new('pv', me)
    bpy.context.scene.collection.objects.link(ob)
    h, w = img_top_first.shape[:2]
    im = bpy.data.images.new('tex', w, h)
    px = np.concatenate([np.flipud(img_top_first[..., :3]).astype(np.float32) / 255.0, np.ones((h, w, 1), np.float32)], -1)
    im.pixels.foreach_set(px.ravel())
    m = bpy.data.materials.new('m')
    m.use_nodes = True
    nt = m.node_tree
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = im
    # back faces (wrong winding; the game culls them) render bright red so they can be spotted
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    nt.links.new(geo.outputs['Backfacing'], mix.inputs['Factor'])
    nt.links.new(tn.outputs['Color'], mix.inputs['A'])
    mix.inputs['B'].default_value = (1, 0, 0, 1)
    nt.links.new(mix.outputs['Result'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    nt.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
    me.materials.append(m)
    # ground
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.02))
    g = bpy.context.active_object
    gm = bpy.data.materials.new('g')
    gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.13, 0.2, 0.07, 1)
    g.data.materials.append(gm)
    # the city hexagon and its six neighbours, as thin yellow lines on the ground (fit check)
    lm = bpy.data.materials.new('hexline')
    lm.use_nodes = True
    lm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.9, 0.8, 0.1, 1)
    lv, lf = [], []
    centres = [(0.0, 0.0)] + [(2 * blib.HEX_IN * math.cos(math.radians(60 * k)),
                                2 * blib.HEX_IN * math.sin(math.radians(60 * k))) for k in range(6)]
    for cx, cy in centres:
        corners = [(cx + blib.HEX_OUT * math.cos(math.radians(30 + 60 * k)),
                    cy + blib.HEX_OUT * math.sin(math.radians(30 + 60 * k))) for k in range(7)]
        for (x0, y0), (x1, y1) in zip(corners, corners[1:]):
            dx, dy = x1 - x0, y1 - y0
            L = math.hypot(dx, dy)
            nx, ny = -dy / L * 0.25, dx / L * 0.25
            n0 = len(lv)
            lv += [(x0 - nx, y0 - ny, 0.0), (x1 - nx, y1 - ny, 0.0), (x1 + nx, y1 + ny, 0.0), (x0 + nx, y0 + ny, 0.0)]
            lf.append((n0, n0 + 1, n0 + 2, n0 + 3))
    lme = bpy.data.meshes.new('hexlines')
    lme.from_pydata(lv, [], lf)
    lme.materials.append(lm)
    lob = bpy.data.objects.new('hexlines', lme)
    bpy.context.scene.collection.objects.link(lob)
    # effect positions: emissive markers approximating the in-game particles (glow, fire, candles)
    FXCOL = {'EYE': (1.0, 0.45, 0.05), 'CANDLE': (1.0, 0.75, 0.3), 'ITHILDIN': (0.45, 0.78, 1.0),
             'GOLD': (1.0, 0.85, 0.4), 'SMOKE': (0.6, 0.6, 0.6), 'TORCH': (1.0, 0.55, 0.1),
             'BRAZIER': (1.0, 0.5, 0.1), 'CAMPFIRE': (1.0, 0.5, 0.1), 'BLUE': (0.3, 0.5, 1.0),
             'WHITE': (1.0, 1.0, 0.95), 'FIREWORKS': (1.0, 0.9, 0.3), 'GHOST': (0.3, 1.0, 0.5),
             'RED_EYES': (1.0, 0.1, 0.05), 'MIST': (0.85, 0.9, 1.0)}
    for bname, pos, effect in fx:
        col = next((c for k, c in FXCOL.items() if k in effect.replace('RED_EYES', 'RED_EYE_S')), (1, 1, 1)) if 'RED_EYES' not in effect else FXCOL['RED_EYES']
        rad = 0.5 if 'CANDLE' in effect else 0.35 if ('GOLD' in effect or 'RED_EYES' in effect) else 0.9 if 'MEC_EYE' in effect else 0.6
        bpy.ops.mesh.primitive_ico_sphere_add(radius=rad, subdivisions=2, location=pos)
        mk = bpy.context.active_object
        em = bpy.data.materials.new('fx')
        em.use_nodes = True
        nt2 = em.node_tree
        nt2.nodes.remove(nt2.nodes['Principled BSDF'])
        e = nt2.nodes.new('ShaderNodeEmission')
        e.inputs['Color'].default_value = col + (1,)
        e.inputs['Strength'].default_value = 6.0
        nt2.links.new(e.outputs[0], nt2.nodes['Material Output'].inputs[0])
        mk.data.materials.append(em)
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-30))
    bpy.context.scene.collection.objects.link(sun)
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.65, 0.8, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
    sc = bpy.context.scene
    sc.world = world
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 32
    sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.view_settings.view_transform = 'Standard'
    zmax = max(v[0][2] for v in verts)
    shots = []
    k = max(1.0, zmax / 42.0)
    views = [((0, -105 * k, 95 * k), (0, 0, zmax * 0.28), 50), ((48 * k, -62 * k, 34 * k), (0, 0, zmax * 0.4), 42)] + list(extra)
    for i, (loc, tgt, lens) in enumerate(views):
        cam = bpy.data.objects.new('cam%d' % i, bpy.data.cameras.new('cam%d' % i))
        cam.data.lens = lens
        cam.location = loc
        look_at(cam, tgt)
        sc.collection.objects.link(cam)
        sc.camera = cam
        p = os.path.join(WORK, '%s_%d.png' % (name, i))
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        shots.append(p)
    # side by side
    a = [bpy.data.images.load(p) for p in shots]
    W, H = size
    cols = 2
    rows = (len(a) + 1) // 2
    out = np.zeros((H * rows, W * cols, 4), np.float32)
    for i, im2 in enumerate(a):
        r = rows - 1 - i // 2
        out[r * H:(r + 1) * H, (i % 2) * W:(i % 2 + 1) * W] = np.array(im2.pixels[:], np.float32).reshape(H, W, 4)
    res = bpy.data.images.new('side', W * cols, H * rows)
    res.pixels.foreach_set(out.ravel())
    res.filepath_raw = os.path.join(PREVIEW, name + '.png')
    res.file_format = 'PNG'
    res.save()


# Texture sizes written for the game. The atlas is baked at atlas.ATLAS (1024) and box-filtered
# down: stock wonders use 256x256 (at most 512x512) textures, and with 1024x1024 ones only about a
# dozen of our landmarks were drawn per game (hypothesis: the game's building texture space fills up).
GAME_DIFF = 512
GAME_SREF = 256


# Geometry budget, from the stock wonders: the biggest (Colossus, Great Lighthouse) have about
# 16k triangles and 22k vertices. Vertices are what costs memory (60 bytes each, an index triangle
# 6 bytes). A landmark over the budget is rebuilt with fewer segments on its curved primitives
# (blib.SEG); the log names the level used.
MAX_VERTS = 24000
MAX_TRIS = 20000


def clip_to_hex(b):
    """Drop the pieces (connected primitives) whose centre lies outside the city hexagon, e.g.
    edge trees pushed out by FILL. The base itself is centred on the tile and always stays."""
    parent = list(range(len(b.verts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for f in b.faces:
        r0 = find(f[0])
        for v in f[1:]:
            r = find(v)
            if r != r0:
                parent[r] = r0
    acc = {}
    for i, (x, y, z) in enumerate(b.verts):
        k = find(i)
        a = acc.setdefault(k, [0.0, 0.0, 0])
        a[0] += x
        a[1] += y
        a[2] += 1
    design_fill, blib.FILL[0] = blib.FILL[0], 1.0      # the model is already at tile scale here
    try:
        out = {k for k, (sx, sy, n) in acc.items() if not blib.in_hex(sx / n, sy / n, margin=0.3)}
        b.fx[:] = [(n, p, e) for n, p, e in b.fx if blib.in_hex(p[0], p[1])]
    finally:
        blib.FILL[0] = design_fill
    if out:
        keep = [i for i, f in enumerate(b.faces) if find(f[0]) not in out]
        b.faces = [b.faces[i] for i in keep]
        b.fmat = [b.fmat[i] for i in keep]
        b.fsmooth = [b.fsmooth[i] for i in keep]
    # long pieces that stay (rivers, roads, walls) end on the tile's edge
    for i, (x, y, z) in enumerate(b.verts):
        r = math.hypot(x, y)
        if r > 0:
            design_fill, blib.FILL[0] = blib.FILL[0], 1.0
            lim = blib.hex_radius(math.atan2(y, x))
            blib.FILL[0] = design_fill
            if r > lim:
                b.verts[i] = (x * lim / r, y * lim / r, z)


def _shrink(a, size):
    f = a.shape[0] // size
    if f <= 1:
        return a
    return a.reshape(size, f, size, f, a.shape[2]).mean((1, 3)).astype(np.uint8)


def build_one(module, name, tex, do_preview=True):
    t0 = time.time()
    reset()
    mod = importlib.import_module(module)
    importlib.reload(mod)
    fill = getattr(mod, 'FILL', 1.0)

    def make(seg):
        reset()
        blib.SEG[0] = seg
        blib.FILL[0] = fill
        b = blib.Builder(seed=zlib.crc32(name.encode()) & 0xffff)
        mod.build(b)
        if fill != 1.0:
            # a design laid out small: scale it to fill the tile (its base was built at
            # tile / FILL, so it now lands exactly on the hexagon)
            b.verts = [(x * fill, y * fill, z * fill) for (x, y, z) in b.verts]
            b.fx[:] = [(n, (p[0] * fill, p[1] * fill, p[2] * fill), e) for n, p, e in b.fx]
            clip_to_hex(b)
        return b
    # full detail, unless the model is over the budget: then the highest detail level that fits
    # (or the lowest one tried)
    for seg in (1.0, 0.8, 0.65, 0.5):
        b = make(seg)
        if b.tri_count() > MAX_TRIS * 1.15 and seg > 0.5:
            continue
        res = atlas.process(b)
        if (len(res.verts) <= MAX_VERTS and len(res.tris) <= MAX_TRIS) or seg <= 0.5:
            break
    if seg < 1.0:
        print('  %s: detail level %.2f' % (name, seg))
    blib.SEG[0] = 1.0
    blib.FILL[0] = 1.0
    img = res.image
    alpha = np.full(img.shape[:2] + (1,), 255, np.uint8)
    diff = np.concatenate([img, alpha], -1)
    sref = res.sref
    dn, sn = name + '_DIFF.dds', name + '_SREF.dds'
    dds.write_dxt3(os.path.join(OUT, dn), _shrink(diff, GAME_DIFF))
    dds.write_dxt3(os.path.join(OUT, sn), _shrink(sref, GAME_SREF))
    size = civ5model.write_model(OUT, name, res.verts, res.tris, dn, sn, fx=b.fx)
    zs = [v[0] for v in res.verts]
    bb = [(round(min(p[i] for p in zs), 1), round(max(p[i] for p in zs), 1)) for i in range(3)]
    print('%-22s tris %6d  verts %6d  cells %3d x %dpx  gr2 %7d bytes  bbox %s  (%.1fs)' % (
        name, len(res.tris), len(res.verts), res.cells, res.cell_px, size, bb, time.time() - t0))
    if do_preview:
        decoded = dds.decode_dxt3(os.path.join(OUT, dn))
        extra = [(tuple(c * fill for c in loc), tuple(c * fill for c in tgt), lens)
                 for loc, tgt, lens in getattr(mod, 'PREVIEW', ())]
        preview(name, res.verts, res.tris, decoded, extra=extra, fx=b.fx)
    return len(res.tris)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    tex = 1024
    if '--tex' in argv:
        tex = int(argv[argv.index('--tex') + 1])
    names = [a for a in argv if not a.startswith('--') and not a.isdigit()]
    for d in (OUT, PREVIEW, WORK):
        os.makedirs(d, exist_ok=True)
    import particles
    try:
        particles.make(OUT)
    except Exception as e:  # the game files are not needed for the models themselves
        need = [fn for (_, _, fn) in PARTICLES.values()]
        if not all(os.path.exists(os.path.join(OUT, fn)) for fn in need):
            raise
        print('particles: game files unavailable (%s); keeping existing outputs' % e)
    rows = CAPITALS + CITYSTATES
    if '--capitals-only' in argv:
        rows = CAPITALS
    if '--citystates-only' in argv:
        rows = CITYSTATES
    for civ, module, name, prefix, old in rows:
        if names and module not in names:
            continue
        build_one(module, name, tex, '--no-preview' not in argv)


if __name__ == '__main__':
    main()
