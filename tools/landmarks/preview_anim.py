"""Preview an animated landmark FROM THE WRITTEN GAME FILES (end-to-end check of the output).

Run:  blender -b --factory-startup -P tools/landmarks/preview_anim.py -- [model] [--frames 0.6,1.6,3.4,4.4]
Output: build/landmarks/preview/<model>_anim.png (frames side by side, in the game camera's direction)

Reads <model>.gr2 (tower + skinned Eye), <model>_Idle.gr2 (the gaze curve, decoded with granim exactly
as stored), MEC_EyeBeam.gr2/_IdleA.gr2 and the effect scales, then poses everything the way the engine
does: Eye vertices about the 'eyepivot' bone, the beam about its Point01 at the 'fxbeam' bone, both sizes
times the building fScale. Fire particles are drawn as glowing markers at their bones.
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
from mathutils import Matrix, Vector  # noqa: E402

import dds  # noqa: E402
import gr2  # noqa: E402
import granim  # noqa: E402
from landmarks import EFFECTS, LANDMARKS, OUT, PREVIEW  # noqa: E402


def mesh_arrays(m):
    v = m['PrimaryVertexData']['Vertices']
    if isinstance(v.value, (bytes, bytearray)):
        size = gr2.struct_size(v.members)
        names = [x.name for x in v.members]
        pos, uv, bidx = [], [], []
        for i in range(len(v.value) // size):
            o = i * size
            p = struct.unpack_from('<3f', v.value, o)
            if 'BoneWeights' in names:
                bi = v.value[o + 16]
                o2 = o + 20
            else:
                bi, o2 = 0, o + 12
            t = struct.unpack_from('<3f', v.value, o2 + 36)
            pos.append(p); uv.append((t[0], t[1])); bidx.append(bi)
    else:
        pos = [tuple(x['Position']) for x in v.value]
        uv = [tuple(x['TextureCoordinates0'][:2]) for x in v.value]
        bidx = [x.get('BoneIndices', [0])[0] for x in v.value]
    ib = m['PrimaryTopology']['Indices16']
    idx = struct.unpack('<%dH' % (len(ib) // 2), ib) if isinstance(ib, (bytes, bytearray)) else [x['Int16'] for x in ib]
    return pos, uv, bidx, [tuple(idx[i:i + 3]) for i in range(0, len(idx), 3)]


def yaw_of(anim_path, group, track):
    r = gr2.read(anim_path).root()
    tg = [g for g in r['TrackGroups'] if g['Name'] == group][0]
    t = [x for x in tg['TransformTracks'] if x['Name'] == track][0]
    v = t['OrientationCurve']['CurveData'].value
    kc = [x['UInt16'] for x in v['KnotsControls']]
    knots, quats = granim.decode_curve(kc, v['OneOverKnotScale'], v['ScaleOffsetTableEntries'])
    degs = [granim.quat_yaw_deg(q) for q in quats]
    T = r['Animations'][0]['Duration']
    return lambda tt: granim.evaluate(degs, T, tt % T)


def image_material(name, path, emission=0.0, alpha=False):
    img = dds.decode_dxt3(path)
    h, w = img.shape[:2]
    im = bpy.data.images.new(name, w, h, alpha=True)
    px = np.flipud(img).astype(np.float32) / 255.0
    im.pixels.foreach_set(px.ravel())
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = im
    nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.85
    if emission:
        nt.links.new(tn.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = emission
    if alpha:
        nt.links.new(tn.outputs['Alpha'], bsdf.inputs['Alpha'])
        m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    return m


def add_mesh(name, pos, uv, tris, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata(pos, [], tris)
    lay = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            u, v = uv[me.loops[li].vertex_index]
            lay.data[li].uv = (u, 1.0 - v)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    frames = [0.6, 1.6, 3.4, 4.4]
    if '--frames' in argv:
        frames = [float(x) for x in argv[argv.index('--frames') + 1].split(',')]
    names = [a for a in argv if not a.startswith('--') and ',' not in a]
    lm = [x for x in LANDMARKS if x.get('animated') and (not names or x['model'] in names or x['module'] in names)][0]
    name, s = lm['model'], lm['scale']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    r = gr2.read(os.path.join(OUT, name + '.gr2')).root()
    meshes = {m['Name']: m for m in r['Meshes']}
    eye_skel = [sk for sk in r['Skeletons'] if sk['Name'] == name + '_Eye'][0]
    bones, world = {}, {}
    for b in eye_skel['Bones']:
        p = b['Transform']['Position']
        par = eye_skel['Bones'][b['ParentIndex']]['Name'] if b['ParentIndex'] >= 0 else None
        world[b['Name']] = [p[i] * s + (world[par][i] if par else 0.0) for i in range(3)]
    pivot = Vector(world['eyepivot'])
    yaw = yaw_of(os.path.join(OUT, name + '_Idle.gr2'), name + '_Eye', 'eyepivot')
    beam_yaw = yaw_of(os.path.join(OUT, 'MEC_EyeBeam_IdleA.gr2'), 'World', 'Point01')

    tmat = image_material('tower', os.path.join(OUT, name + '_DIFF.dds'))
    emat = image_material('eye', os.path.join(OUT, name + '_Eye_DIFF.dds'), emission=1.5)
    bmat = image_material('beam', os.path.join(OUT, 'MEC_EyeBeam_DIFF.dds'), emission=6.0, alpha=True)
    pos, uv, _, tris = mesh_arrays(meshes[name])
    add_mesh('tower', [tuple(c * s for c in p) for p in pos], uv, tris, tmat)
    epos, euv, _, etris = mesh_arrays(meshes[name + '_Eye'])
    eye_ob = add_mesh('eye', [tuple(c * s for c in p) for p in epos], euv, etris, emat)
    eye_ob.data.transform(Matrix.Translation(-pivot))
    eye_ob.location = pivot
    br = gr2.read(os.path.join(OUT, 'MEC_EyeBeam.gr2')).root()
    bpos, buv, _, btris = mesh_arrays(br['Meshes'][0])
    bs = EFFECTS['EYE_BEAM']['scale'] * s
    beam_ob = add_mesh('beam', [tuple(c * bs for c in p) for p in bpos], buv, btris, bmat)
    beam_ob.location = Vector(world['fxbeam'])
    fire = []
    em = bpy.data.materials.new('fire')
    em.use_nodes = True
    em.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (1.0, 0.45, 0.08, 1)
    em.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 8.0
    for bn in world:
        if bn.startswith('fxfire') or bn == 'fxcore':
            bpy.ops.mesh.primitive_ico_sphere_add(radius=0.7 if bn != 'fxcore' else 1.4, subdivisions=2)
            o = bpy.context.active_object
            o.data.materials.append(em)
            fire.append((o, Vector(world[bn]) - pivot))
    # ground, light, camera from the game's direction (south, looking down ~50 degrees)
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.05))
    g = bpy.context.active_object
    gm = bpy.data.materials.new('g'); gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.16, 0.14, 0.12, 1)
    g.data.materials.append(gm)
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-30))
    bpy.context.scene.collection.objects.link(sun)
    sc = bpy.context.scene
    world_ = bpy.data.worlds.new('w'); world_.use_nodes = True
    world_.node_tree.nodes['Background'].inputs['Color'].default_value = (0.35, 0.3, 0.3, 1)
    sc.world = world_
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    cam.data.lens = 32
    cam.location = (0, -105, 88)
    cam.rotation_euler = (Vector((0, -22, 22)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in
                                                                       bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'CYCLES'
    if sc.render.engine == 'CYCLES':
        sc.cycles.samples = 24
    sc.render.resolution_x, sc.render.resolution_y = 720, 560
    sc.view_settings.view_transform = 'Standard'
    shots = []
    os.makedirs(PREVIEW, exist_ok=True)
    for i, t in enumerate(frames):
        a = math.radians(yaw(t))
        eye_ob.rotation_euler = (0, 0, a)
        beam_ob.rotation_euler = (0, 0, math.radians(beam_yaw(t)))
        R = Matrix.Rotation(a, 3, 'Z')
        for o, off in fire:
            o.location = pivot + R @ off
        p = os.path.join(PREVIEW, '%s_anim_%d.png' % (name, i))
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        shots.append((p, t, yaw(t), beam_yaw(t)))
        print('frame t=%.2fs  eye yaw %.1f  beam yaw %.1f' % (t, yaw(t), beam_yaw(t)))
    W, H = 720, 560
    out = np.zeros((H, W * len(shots), 4), np.float32)
    for i, (p, *_rest) in enumerate(shots):
        im = bpy.data.images.load(p)
        out[:, i * W:(i + 1) * W] = np.array(im.pixels[:], np.float32).reshape(H, W, 4)
    res = bpy.data.images.new('sheet', W * len(shots), H)
    res.pixels.foreach_set(out.ravel())
    res.filepath_raw = os.path.join(PREVIEW, name + '_anim.png')
    res.file_format = 'PNG'
    res.save()


if __name__ == '__main__':
    main()
