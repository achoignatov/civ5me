"""Pose an animated landmark FROM THE WRITTEN GAME FILES at several moments of its idle loop and render them side by
side (end-to-end check of blended skinning: lmodel skins=, e.g. Treebeard's lean).

Run:  blender -b --factory-startup -P tools/landmarks/preview_lean.py -- MEC_LM_Treebeard [--times 0,3,6,9]
                [--view side|game|both] [--scale 0.25]
Output: build/landmarks/preview/<model>_lean_<view>.png

Reads <model>.gr2 (every model and mesh; skinned vertices with their 4 weights and BoneIndices into the mesh's
BoneBindings) and <model>_Idle.gr2 (curves decoded with granim as stored), poses the bones like the engine
(world = parent world x local(t); vertex = sum w * world(t) x InverseWorldTransform x rest) and renders with the
baked textures. Positions are shown in in-game units (file units x the improvement Scale).
Also prints how far the highest vertex travels over the loop.
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'capitals')]
sys.path.append(os.path.join(HERE, '..', '..', 'build', 'venv', 'lib', 'python%d.%d' % sys.version_info[:2],
                             'site-packages'))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import dds  # noqa: E402
import gr2  # noqa: E402
from landmarks import OUT, PREVIEW  # noqa: E402
from render_gif import Animation, gmat, local_matrix  # noqa: E402


def read_meshes(path):
    """[(model name, bones [(name, parent, rest local, inverse world)], mesh dict)] of every mesh in the file."""
    r = gr2.read(path).root()
    out = []
    for m in r['Models']:
        if m['Name'] == 'Tree cut':
            continue
        bones = [(b['Name'], b['ParentIndex'], local_matrix(b['Transform']['Position'], b['Transform']['Orientation']),
                  gmat(b['InverseWorldTransform'])) for b in m['Skeleton']['Bones']]
        for mb in m['MeshBindings']:
            me = mb['Mesh']
            v = me['PrimaryVertexData']['Vertices']
            names = [x.name for x in v.members]
            size = gr2.struct_size(v.members)
            skinned = 'BoneWeights' in names
            pos, uv, wts = [], [], []
            if not isinstance(v.value, (bytes, bytearray)):          # already decoded records
                for x in v.value:
                    pos.append(tuple(x['Position']))
                    uv.append(tuple(x['TextureCoordinates0'][:2]))
                    wts.append([(x['BoneIndices'][k], x['BoneWeights'][k] / 255.0) for k in range(4)
                                if x['BoneWeights'][k]] if skinned else [(0, 1.0)])
            for i in range(len(v.value) // size if isinstance(v.value, (bytes, bytearray)) else 0):
                o = i * size
                if skinned:
                    vals = struct.unpack_from('<3f4B4B12f', v.value, o)
                    pos.append(vals[0:3])
                    wts.append([(vals[7 + k], vals[3 + k] / 255.0) for k in range(4) if vals[3 + k]])
                    uv.append(vals[20:22])
                else:
                    vals = struct.unpack_from('<15f', v.value, o)
                    pos.append(vals[0:3])
                    wts.append([(0, 1.0)])
                    uv.append(vals[12:14])
            ib = me['PrimaryTopology']['Indices16']
            idx = (struct.unpack('<%dH' % (len(ib) // 2), ib) if isinstance(ib, (bytes, bytearray))
                   else [x['Int16'] if 'Int16' in x else x['UInt16'] for x in ib])
            mat = me['MaterialBindings'][0]['Material']
            tex = mat['Maps'][0]['Map']['Texture']['FromFileName']
            out.append((m['Name'], bones, dict(name=me['Name'], pos=pos, uv=uv, w=wts,
                                               binds=[b['BoneName'] for b in me['BoneBindings']],
                                               tris=[idx[i:i + 3] for i in range(0, len(idx), 3)], tex=tex)))
    return out


def pose(model, bones, mesh, anim, t, scale):
    world = {}
    for name, parent, rest, _inv in bones:
        loc = anim.local(model, name, t) if anim else None
        loc = rest if loc is None else loc
        world[name] = (world[bones[parent][0]] @ loc) if parent >= 0 else loc
    inv = {n: i for n, _, _, i in bones}
    mats = [world[b] @ inv[b] if b in world else None for b in mesh['binds']]
    P = np.array(mesh['pos'], np.float64)
    out = np.zeros_like(P)
    for i, (p, ws) in enumerate(zip(mesh['pos'], mesh['w'])):
        if not mats or mats[0] is None:
            out[i] = p
            continue
        acc = Vector((0.0, 0.0, 0.0))
        for bi, w in ws:
            acc += w * (mats[bi] @ Vector(p))
        out[i] = acc
    return out * scale


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []

    def opt(k, d):
        return argv[argv.index(k) + 1] if k in argv else d
    name = [a for a in argv if not a.startswith('--') and a not in
            (opt('--times', None), opt('--view', None), opt('--scale', None))][0]
    scale = float(opt('--scale', 0.25))
    anim = Animation(os.path.join(OUT, name + '_Idle.gr2'))
    T = anim.duration
    times = [float(x) for x in opt('--times', ','.join('%g' % (T * i / 8) for i in range(8))).split(',')]
    views = {'side': ((150.0, -6.0, 58.0), (0.0, 0.0, 54.0), 40), 'game': ((0.0, -150.0, 130.0), (0.0, 0.0, 52.0), 42)}
    which = ['side', 'game'] if opt('--view', 'both') == 'both' else [opt('--view', 'both')]
    meshes = read_meshes(os.path.join(OUT, name + '.gr2'))
    # scene: one object per mesh, its baked texture
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    objs = []
    for model, bones, me in meshes:
        bm = bpy.data.meshes.new(me['name'])
        bm.from_pydata([tuple(p) for p in pose(model, bones, me, anim, 0.0, scale)], [], me['tris'])
        bm.update()
        uvl = bm.uv_layers.new()
        for poly in bm.polygons:
            for li in poly.loop_indices:
                u, v = me['uv'][bm.loops[li].vertex_index]
                uvl.data[li].uv = (u, 1.0 - v)
        img = dds.decode_dxt3(os.path.join(OUT, me['tex']))
        h, w = img.shape[:2]
        im = bpy.data.images.new(me['name'], w, h, alpha=True)
        px = np.concatenate([np.flipud(img[..., :3]).astype(np.float32) / 255.0,
                             np.flipud(img[..., 3:4]).astype(np.float32) / 255.0], -1)
        im.pixels.foreach_set(px.ravel())
        mat = bpy.data.materials.new(me['name'])
        mat.use_nodes = True
        nt = mat.node_tree
        tn = nt.nodes.new('ShaderNodeTexImage')
        tn.image = im
        bsdf = nt.nodes['Principled BSDF']
        nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
        gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.5
        nt.links.new(tn.outputs['Alpha'], gt.inputs[0])
        nt.links.new(gt.outputs[0], bsdf.inputs['Alpha'])
        bsdf.inputs['Roughness'].default_value = 0.9
        bm.materials.append(mat)
        ob = bpy.data.objects.new(me['name'], bm)
        sc.collection.objects.link(ob)
        objs.append((ob, model, bones, me))
    bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, -0.05))
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-30))
    sc.collection.objects.link(sun)
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.65, 0.8, 1)
    sc.world = world
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 16
    sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = 420, 560
    sc.view_settings.view_transform = 'Standard'
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    top = []
    for t in times:
        hi = None
        for ob, model, bones, me in objs:
            P = pose(model, bones, me, anim, t, scale)
            ob.data.vertices.foreach_set('co', P.astype(np.float32).ravel())
            ob.data.update()
            k = int(np.argmax(P[:, 2]))
            if hi is None or P[k, 2] > hi[2]:
                hi = tuple(P[k])
        top.append(hi)
        for view in which:
            loc, tgt, lens = views[view]
            cam.location = loc
            cam.data.lens = lens
            d = Vector(tgt) - Vector(loc)
            cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = os.path.join(PREVIEW, 'work_lean_%s_%s_%05.2f.png' % (name, view, t))
            bpy.ops.render.render(write_still=True)
    tops = np.array(top)
    print('LEAN %s: top vertex over the loop: y %.2f .. %.2f, x %.2f .. %.2f (in-game units)' % (
        name, tops[:, 1].min(), tops[:, 1].max(), tops[:, 0].min(), tops[:, 0].max()))
    for view in which:
        ims = [bpy.data.images.load(os.path.join(PREVIEW, 'work_lean_%s_%s_%05.2f.png' % (name, view, t))) for t in times]
        w, h = ims[0].size
        strip = np.zeros((h, w * len(ims), 4), np.float32)
        for i, im in enumerate(ims):
            a = np.empty(w * h * 4, np.float32)
            im.pixels.foreach_get(a)
            strip[:, i * w:(i + 1) * w] = a.reshape(h, w, 4)
        out = bpy.data.images.new('strip', w * len(ims), h, alpha=True)
        out.pixels.foreach_set(strip.ravel())
        out.filepath_raw = os.path.join(PREVIEW, '%s_lean_%s.png' % (name, view))
        out.file_format = 'PNG'
        out.save()
        print('wrote', out.filepath_raw)


main()
