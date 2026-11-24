"""High-fidelity texturing for landmarks: a real UV unwrap + textures baked in Blender (runs inside Blender).

The older path (tools/capitals/atlas.py) gives every face one small pre-made swatch of a shared atlas and shades it
flat, which reads as a blocky, "pixelated" patchwork in game. This path instead:
  * keeps the model's smooth-shading flags (terrain, foliage, tentacles smooth; walls and lines sharp);
  * unwraps the whole model (Smart UV Project, one texture, uniform texel density);
  * gives every palette material a procedural Blender material (multi-octave noise, colour by height and slope,
    fine cracks/strata), and bakes:
        1. base colour (albedo)      -> DIFF rgb, darkened by
        2. ambient occlusion          (Cycles AO bake)
        3. specular strength / reflection per material -> SREF (rgb = albedo * spec, a = reflection)
  * an optional painted GLOW (b.glow: line segments on a vertical plane) adds a soft halo to the materials that ask
    for it (palette entry glow=True), e.g. the ithildin light around the Doors of Durin;
  * returns the same Result as atlas.process (verts (pos, nrm, tan, bin, uv), tris, image, sref), uv in DirectX
    convention (v = 0 at the top row), image rows top first.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Vector

import blib


class Result:
    pass


def _lin(c):
    return tuple(blib._srgb_to_lin(c)) + (1.0,)


# --------------------------------------------------------------------------- glow image
def glow_image(b, px=1024):
    """Rasterise b.glow = dict(lines=[(x0, z0, x1, z1, width)], box=(X0, X1, Z0, Z1), sigma=(core, wide)) into an
    RGBA float image (halo strength in every channel). Returns (bpy image, box)."""
    g = b.glow
    X0, X1, Z0, Z1 = g['box']
    W = px
    H = max(16, int(round(px * (Z1 - Z0) / (X1 - X0))))
    xs = X0 + (np.arange(W) + 0.5) / W * (X1 - X0)
    zs = Z0 + (np.arange(H) + 0.5) / H * (Z1 - Z0)
    X, Z = np.meshgrid(xs, zs)                    # row 0 = Z0 (bottom), like Blender image pixels
    d = np.full(X.shape, 1e9)
    for (x0, z0, x1, z1, w) in g['lines']:
        vx, vz = x1 - x0, z1 - z0
        L2 = vx * vx + vz * vz or 1e-9
        t = np.clip(((X - x0) * vx + (Z - z0) * vz) / L2, 0, 1)
        dist = np.hypot(X - (x0 + t * vx), Z - (z0 + t * vz)) - w / 2
        d = np.minimum(d, dist)
    d = np.maximum(d, 0)
    s1, s2 = g['sigma']
    halo = np.clip(1.0 * np.exp(-(d / s1) ** 2) + 0.3 * np.exp(-(d / s2) ** 2), 0, 1)
    img = bpy.data.images.new('MEC_Glow', W, H, alpha=True, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    rgba = np.repeat(halo[..., None], 4, axis=2).astype(np.float32)
    rgba[..., 3] = 1.0
    img.pixels.foreach_set(rgba.ravel())
    return img, (X0, X1, Z0, Z1)


# --------------------------------------------------------------------------- procedural materials
def _material(name, glow=None):
    p = blib.PALETTE[name]
    mat = bpy.data.materials.new('BK_' + name)
    mat.use_nodes = True
    nt = mat.node_tree
    N, Lk = nt.nodes, nt.links
    bsdf = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ')
    Lk.new(tc.outputs['Object'], sep.inputs[0])

    def noise(scale, detail=8.0, rough=0.6):
        n = N.new('ShaderNodeTexNoise')
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        Lk.new(tc.outputs['Object'], n.inputs['Vector'])
        return n.outputs['Fac']

    def mix(a, b_, fac, blend='MIX'):
        m = N.new('ShaderNodeMix')
        m.data_type = 'RGBA'
        m.blend_type = blend
        for sock, v in ((m.inputs[6], a), (m.inputs[7], b_)):
            if isinstance(v, tuple):
                sock.default_value = v
            else:
                Lk.new(v, sock)
        if isinstance(fac, float):
            m.inputs[0].default_value = fac
        else:
            Lk.new(fac, m.inputs[0])
        return m.outputs[2]

    def maprange(src, a, b_, c=0.0, d=1.0):
        m = N.new('ShaderNodeMapRange')
        m.clamp = True
        m.inputs[1].default_value, m.inputs[2].default_value = a, b_
        m.inputs[3].default_value, m.inputs[4].default_value = c, d
        Lk.new(src, m.inputs[0])
        return m.outputs[0]

    # mottled base: two colours by large noise, broken up by fine detail
    big = noise(p.get('scale', 0.18), 6.0, 0.55)
    fine = noise(p.get('scale', 0.18) * 7.0, 10.0, 0.7)
    c1, c2 = _lin(p['color']), _lin(p['color2'] if p.get('color2') else tuple(x * 0.85 for x in p['color']))
    col = mix(c1, c2, maprange(big, 0.35, 0.65))
    if p.get('zramp'):
        zs = sorted(p['zramp'])
        ramp = N.new('ShaderNodeValToRGB')
        cr = ramp.color_ramp
        z0, z1 = zs[0][0], zs[-1][0]
        while len(cr.elements) < len(zs):
            cr.elements.new(0.5)
        for el, (z, c) in zip(cr.elements, zs):
            el.position = (z - z0) / (z1 - z0)
            el.color = _lin(c)
        # jitter the height a little with noise so bands (snow line) are ragged, not straight
        add = N.new('ShaderNodeMath')
        add.operation = 'MULTIPLY_ADD'
        Lk.new(big, add.inputs[0])
        add.inputs[1].default_value = (z1 - z0) * p.get('zjitter', 0.04)
        Lk.new(sep.outputs['Z'], add.inputs[2])
        Lk.new(maprange(add.outputs[0], z0, z1), ramp.inputs[0])
        col = mix(ramp.outputs[0], col, 0.25, 'OVERLAY')
    if p.get('slope_color') is not None:
        geo = N.new('ShaderNodeNewGeometry')
        nz = N.new('ShaderNodeSeparateXYZ')
        Lk.new(geo.outputs['Normal'], nz.inputs[0])
        s = p.get('slope_start', 0.55)
        steep = maprange(nz.outputs['Z'], s - 0.2, s + 0.15, 1.0, 0.0)
        sc = _lin(p['slope_color'])
        rock = mix(sc, tuple(x * 0.7 for x in sc[:3]) + (1.0,), maprange(fine, 0.3, 0.7))
        col = mix(col, rock, steep)
    if p.get('cracks'):
        # dark cracks and crevices: the edges of large Voronoi cells, distorted by noise
        vor = N.new('ShaderNodeTexVoronoi')
        vor.feature = 'DISTANCE_TO_EDGE'
        vor.inputs['Scale'].default_value = p['cracks']
        warp = N.new('ShaderNodeTexNoise')            # distort the cells so cracks wander like real fractures
        warp.inputs['Scale'].default_value = p['cracks'] * 1.5
        warp.inputs['Detail'].default_value = 4.0
        Lk.new(tc.outputs['Object'], warp.inputs['Vector'])
        wv = N.new('ShaderNodeMix')
        wv.data_type = 'VECTOR'
        wv.inputs[0].default_value = 0.35
        Lk.new(tc.outputs['Object'], wv.inputs[4])
        Lk.new(warp.outputs['Color'], wv.inputs[5])
        sc_ = N.new('ShaderNodeVectorMath')
        sc_.operation = 'SCALE'
        Lk.new(wv.outputs[1], sc_.inputs[0])
        sc_.inputs['Scale'].default_value = 1.0
        Lk.new(sc_.outputs[0], vor.inputs['Vector'])
        crack = maprange(vor.outputs['Distance'], 0.0, 0.025, 0.72, 1.0)
        cm = N.new('ShaderNodeCombineColor')
        for i in range(3):
            Lk.new(crack, cm.inputs[i])
        col = mix(col, cm.outputs[0], 1.0, 'MULTIPLY')
    if p.get('moss'):
        # moss and grass on gentle, low, upward-facing ground: blends the model into the game's terrain
        mcol, mtop = p['moss']
        geo2 = N.new('ShaderNodeNewGeometry')
        nz2 = N.new('ShaderNodeSeparateXYZ')
        Lk.new(geo2.outputs['Normal'], nz2.inputs[0])
        up = maprange(nz2.outputs['Z'], 0.72, 0.9)
        low = maprange(sep.outputs['Z'], mtop, mtop * 0.4, 0.0, 1.0)
        mul = N.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        Lk.new(up, mul.inputs[0])
        Lk.new(low, mul.inputs[1])
        mossc = mix(_lin(mcol), tuple(x * 0.75 for x in _lin(mcol)[:3]) + (1.0,), maprange(fine, 0.3, 0.7))
        col = mix(col, mossc, mul.outputs[0])
    # fine grain everywhere (multiply around 1)
    col = mix(col, mix((0.78, 0.78, 0.78, 1), (1.12, 1.12, 1.12, 1), maprange(fine, 0.3, 0.7)), 1.0, 'MULTIPLY')
    if p.get('strata'):
        wave = N.new('ShaderNodeTexWave')
        wave.wave_type = 'BANDS'
        wave.bands_direction = 'Z'
        wave.inputs['Scale'].default_value = p['strata']
        wave.inputs['Distortion'].default_value = 6.0
        wave.inputs['Detail'].default_value = 4.0
        Lk.new(tc.outputs['Object'], wave.inputs['Vector'])
        lo = 1.0 - p.get('strata_amp', 0.12)
        col = mix(col, mix((lo, lo, lo, 1), (1.03, 1.03, 1.03, 1), wave.outputs['Fac']), 1.0, 'MULTIPLY')
    if p.get('glow') and glow is not None:
        img, (X0, X1, Z0, Z1) = glow
        comb = N.new('ShaderNodeCombineXYZ')
        for i, (axis, lo, hi) in enumerate((('X', X0, X1), ('Z', Z0, Z1))):
            m = N.new('ShaderNodeMapRange')
            m.clamp = False
            m.inputs[1].default_value, m.inputs[2].default_value = lo, hi
            Lk.new(sep.outputs[axis], m.inputs[0])
            Lk.new(m.outputs[0], comb.inputs[i])
        tex = N.new('ShaderNodeTexImage')
        tex.image = img
        tex.extension = 'CLIP'
        tex.interpolation = 'Cubic'
        Lk.new(comb.outputs[0], tex.inputs[0])
        gc = _lin(p.get('glow_color', blib.hexcol('9fd8ff')))
        col = mix(col, gc, tex.outputs['Color'], 'SCREEN')
    Lk.new(col, bsdf.inputs['Base Color'])
    # SREF source and AO weight: emission colour = (specular strength, reflection, AO weight), read by an EMIT bake
    spec = p.get('spec') if p.get('spec') is not None else 0.3
    refl = p.get('refl') if p.get('refl') is not None else 6
    bsdf.inputs['Emission Color'].default_value = (spec, refl / 255.0, 1.0 if p.get('ao', True) else 0.0, 1.0)
    bsdf.inputs['Emission Strength'].default_value = 1.0
    target = N.new('ShaderNodeTexImage')
    target.name = 'BAKE_TARGET'
    N.active = target
    return mat


# --------------------------------------------------------------------------- object
def _object(b, glow):
    faces, fmat, fsm = [], [], []
    for f, m, s in zip(b.faces, b.fmat, b.fsmooth):
        if len(set(f)) < 3:
            continue
        faces.append(f)
        fmat.append(m)
        fsm.append(s)
    me = bpy.data.meshes.new('landmark')
    me.from_pydata([tuple(v) for v in b.verts], [], faces)
    me.update()
    for n in b.mat_names:
        me.materials.append(_material(n, glow))
    assert len(me.polygons) == len(faces), (len(me.polygons), len(faces))
    me.polygons.foreach_set('material_index', fmat)
    me.polygons.foreach_set('use_smooth', fsm)
    me.update()
    ob = bpy.data.objects.new('landmark', me)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    # merge coincident vertices of smooth parts (helpers emit separate vertices per primitive) and unwrap
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=1e-4)
    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    # palette uv_boost: those materials' islands get more texture (sharper), then everything is packed again
    boost = {i: blib.PALETTE[n].get('uv_boost', 1.0) for i, n in enumerate(b.mat_names)}
    if any(v != 1.0 for v in boost.values()):
        me = ob.data
        uvd = me.uv_layers.active.data
        for poly in me.polygons:
            k = boost.get(poly.material_index, 1.0)
            if k != 1.0:
                for li in poly.loop_indices:
                    uvd[li].uv = uvd[li].uv * k
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
        bpy.ops.object.mode_set(mode='OBJECT')
    # the top strip of the texture is kept free for SWATCHES (see process): shrink the layout below it
    me = ob.data
    for d in me.uv_layers.active.data:
        d.uv = (d.uv[0], d.uv[1] * (1.0 - SWATCH_V))
    return ob


SWATCH_V = 1.0 / 32        # top 1/32 of the texture: solid colour swatches for uniform materials (palette solid=True)


def _bake(ob, kind, px, colorspace, samples=1):
    img = bpy.data.images.new('BK_' + kind, px, px, alpha=True, float_buffer=True)
    img.colorspace_settings.name = colorspace
    for slot in ob.material_slots:
        node = slot.material.node_tree.nodes['BAKE_TARGET']
        node.image = img
        slot.material.node_tree.nodes.active = node
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.render.bake.margin = 16
    sc.render.bake.margin_type = 'EXTEND'
    if kind == 'DIFFUSE':
        sc.render.bake.use_pass_direct = False
        sc.render.bake.use_pass_indirect = False
        sc.render.bake.use_pass_color = True
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
    elif kind == 'AO':
        sc.world = sc.world or bpy.data.worlds.new('W')
        bpy.ops.object.bake(type='AO')
    else:
        bpy.ops.object.bake(type='EMIT')
    a = np.empty(px * px * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(px, px, 4)[::-1]               # top row first


def process(b, px=1024, ao_samples=48, ao_strength=0.65):
    glow = glow_image(b) if getattr(b, 'glow', None) else None
    ob = _object(b, glow)
    me = ob.data
    bpy.context.scene.world = bpy.data.worlds.new('W')
    bpy.context.scene.world.light_settings.distance = 3.0
    diff = _bake(ob, 'DIFFUSE', px, 'Linear Rec.709')       # linear albedo
    ao = _bake(ob, 'AO', px, 'Non-Color', samples=ao_samples)[..., 0:1]
    emit = _bake(ob, 'EMIT', px, 'Non-Color')
    # solid materials (palette solid=True, e.g. ithildin): one swatch of colour in the top strip; their faces' UVs
    # all point at its centre, so tiny faces never depend on tiny islands (mip-map bleeding) and stay crisp
    strip = max(4, int(round(px * SWATCH_V)))
    solids = [i for i, n in enumerate(b.mat_names) if blib.PALETTE[n].get('solid')]
    swatch_uv = {}
    for k, i in enumerate(solids):
        p = blib.PALETTE[b.mat_names[i]]
        w = px // max(1, len(solids))
        x0 = k * w
        c = np.array(blib._srgb_to_lin(p['color']), np.float32)
        rows = slice(0, strip)                     # top rows (arrays are top row first after _bake)
        diff[rows, x0:x0 + w, :3] = c
        emit[rows, x0:x0 + w, 0] = p.get('spec') if p.get('spec') is not None else 0.3
        emit[rows, x0:x0 + w, 1] = (p.get('refl') if p.get('refl') is not None else 6) / 255.0
        emit[rows, x0:x0 + w, 2] = 0.0
        swatch_uv[i] = ((x0 + w / 2) / px, 1.0 - strip / 2 / px)     # Blender uv (v up)
    if swatch_uv:
        uvd = me.uv_layers.active.data
        for poly in me.polygons:
            if poly.material_index in swatch_uv:
                for li in poly.loop_indices:
                    uvd[li].uv = swatch_uv[poly.material_index]
    spec, refl, aow = emit[..., 0:1], emit[..., 1:2], emit[..., 2:3]
    if os.environ.get('MEC_BAKE_DEBUG'):        # per material: faces whose baked colour is dark, by facing
        uvd = me.uv_layers.active.data
        stats = {}
        for poly in me.polygons:
            u = sum(uvd[li].uv[0] for li in poly.loop_indices) / poly.loop_total
            v = sum(uvd[li].uv[1] for li in poly.loop_indices) / poly.loop_total
            c = diff[px - 1 - min(px - 1, int(v * px)), min(px - 1, int(u * px)), :3].mean()
            m = ob.material_slots[poly.material_index].material.name
            facing = max(('x', 'y', 'z'), key=lambda k: abs(getattr(poly.normal, k)))
            facing = ('-' if getattr(poly.normal, facing) < 0 else '+') + facing
            st = stats.setdefault((m, facing), [0, 0, 0.0])
            st[0] += 1; st[1] += c < 0.05; st[2] += poly.area
        for k, (n, dark, area) in sorted(stats.items()):
            print('BAKE_DEBUG %-14s %s faces %5d dark %5d area %.2f' % (k[0], k[1], n, dark, area))
    lin = diff[..., :3] * (1.0 - ao_strength * aow * (1.0 - ao))     # materials with ao=False are not darkened
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)
    srgb = np.clip(srgb, 0, 1)

    # ---- export: one game vertex per (position, corner normal, uv)
    me.calc_loop_triangles()
    cn = me.corner_normals
    uvl = me.uv_layers.active.data
    out, index, tris = [], {}, []
    for lt in me.loop_triangles:
        ids = []
        for li in lt.loops:
            vi = me.loops[li].vertex_index
            n = cn[li].vector
            u, v = uvl[li].uv
            key = (vi, round(n.x, 4), round(n.y, 4), round(n.z, 4), round(u, 6), round(v, 6))
            if key not in index:
                index[key] = len(out)
                out.append([tuple(me.vertices[vi].co), tuple(n), None, None, (u, 1.0 - v)])
            ids.append(index[key])
        tris.append(tuple(ids))
    _tangents(out, tris)
    res = Result()
    res.verts = [tuple(v) for v in out]
    res.tris = tris
    res.image = np.rint(srgb * 255).astype(np.uint8)
    res.sref = np.concatenate([np.rint(np.clip(srgb * spec, 0, 1) * 255),
                               np.rint(np.clip(refl, 0, 1) * 255)], -1).astype(np.uint8)
    return res


def _tangents(verts, tris):
    """Tangents / binormals from UV derivatives (v is DirectX: 0 = top row), as in atlas.process."""
    acc_t = [Vector((0, 0, 0)) for _ in verts]
    acc_b = [Vector((0, 0, 0)) for _ in verts]
    for (i0, i1, i2) in tris:
        p0, p1, p2 = (Vector(verts[i][0]) for i in (i0, i1, i2))
        (u0, v0), (u1, v1), (u2, v2) = (verts[i][4] for i in (i0, i1, i2))
        d1, d2 = p1 - p0, p2 - p0
        du1, dv1, du2, dv2 = u1 - u0, v1 - v0, u2 - u0, v2 - v0
        det = du1 * dv2 - du2 * dv1
        if abs(det) < 1e-14:
            continue
        r = 1.0 / det
        T = (d1 * dv2 - d2 * dv1) * r
        B = (d2 * du1 - d1 * du2) * r
        for i in (i0, i1, i2):
            acc_t[i] += T
            acc_b[i] += B
    for i, v in enumerate(verts):
        n = Vector(v[1])
        t = acc_t[i] - n * n.dot(acc_t[i])
        if t.length < 1e-9:
            t = n.orthogonal()
        t.normalize()
        bb = n.cross(t)
        if bb.dot(acc_b[i]) < 0:
            bb = -bb
        v[2], v[3] = tuple(t), tuple(bb)
