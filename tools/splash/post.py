"""Post-process the Shire render: aerial perspective, sun glow, god rays, bloom, filmic tonemap, grade.

  blender -b --factory-startup -P tools/splash/post.py -- build/splash/<name> [--dds out.dds]

Reads <name>_rgb.exr, <name>_z.exr, <name>_meta.json; writes <name>_final.png (and a DDS when asked).
Runs inside Blender only because Blender can read EXR; the maths is plain numpy.
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.append(os.path.join(ROOT, 'build', 'venv', 'lib', 'python%d.%d' % sys.version_info[:2], 'site-packages'))
import numpy as np
import bpy

ARGS = sys.argv[sys.argv.index('--') + 1:]
BASE = os.path.join(ROOT, ARGS[0]) if not os.path.isabs(ARGS[0]) else ARGS[0]
HAZE_GAIN = 0.55
RAY_THRESH = 1.2
RAY_GAIN = 0.6
EXPOSURE = 1.0
for _k in ('HAZE_GAIN', 'RAY_THRESH', 'RAY_GAIN', 'EXPOSURE'):
    if '--' + _k.lower() in ARGS:
        globals()[_k] = float(ARGS[ARGS.index('--' + _k.lower()) + 1])
DDS = ARGS[ARGS.index('--dds') + 1] if '--dds' in ARGS else None


def load(path, ch):
    im = bpy.data.images.load(path)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[::-1]           # blender stores bottom-up
    return a[..., :ch].copy()


def box(a, r, axis):
    if r < 1:
        return a
    c = np.cumsum(np.pad(a, [(r + 1, r) if i == axis else (0, 0) for i in range(a.ndim)], mode='edge'), axis=axis)
    hi = np.take(c, np.arange(2 * r + 1, c.shape[axis]), axis=axis)
    lo = np.take(c, np.arange(0, c.shape[axis] - 2 * r - 1), axis=axis)
    return (hi - lo) / (2 * r + 1)


def blur(a, sigma):
    r = max(1, int(sigma * 0.85))
    for _ in range(3):
        a = box(box(a, r, 0), r, 1)
    return a


def down(a, f):
    h, w = a.shape[0] // f * f, a.shape[1] // f * f
    return a[:h, :w].reshape(h // f, f, w // f, f, -1).mean((1, 3))


def up(a, shape):
    h, w = shape[:2]
    ys = (np.arange(h) + 0.5) * a.shape[0] / h - 0.5
    xs = (np.arange(w) + 0.5) * a.shape[1] / w - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, a.shape[0] - 1); y1 = np.clip(y0 + 1, 0, a.shape[0] - 1)
    x0 = np.clip(np.floor(xs).astype(int), 0, a.shape[1] - 1); x1 = np.clip(x0 + 1, 0, a.shape[1] - 1)
    fy = np.clip(ys - y0, 0, 1)[:, None, None]; fx = np.clip(xs - x0, 0, 1)[None, :, None]
    t = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    b = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return t * (1 - fy) + b * fy


def aces(x):
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)


def srgb(x):
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def main():
    meta = json.load(open(BASE + '_meta.json'))
    img = load(BASE + '_rgb.exr', 3)
    z = load(BASE + '_z.exr', 1)[..., 0]
    H, W = z.shape
    M = np.array(meta['cam_matrix'])
    t = meta['sensor'] / 2 / meta['lens']
    xs = ((np.arange(W) + 0.5) / W * 2 - 1) * t
    ys = (1 - (np.arange(H) + 0.5) / H * 2) * t * H / W
    d = np.stack(np.broadcast_arrays(xs[None, :], ys[:, None], -np.ones((H, 1))), -1)
    d = d @ M[:3, :3].T
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    sun = np.array(meta['sun_dir'])
    cosang = np.clip(d @ sun, -1, 1)
    # sun position on screen
    sc = np.linalg.inv(M[:3, :3]) @ sun
    sx = (sc[0] / -sc[2] / t + 1) / 2 * W
    sy = (1 - sc[1] / -sc[2] / (t * H / W)) / 2 * H
    print('sun on screen', sx / W, sy / H)

    sky = z > 1.0e6
    dist = np.where(sky, 1e6, z)
    # --- aerial perspective: warm toward the sun, cool lavender away from it
    phase = np.clip((cosang + 1) / 2, 0, 1) ** 6
    warm = np.array([1.35, 0.86, 0.50]); cool = np.array([0.42, 0.44, 0.58])
    haze_col = cool + (warm - cool) * phase[..., None]
    up_amount = np.clip(d[..., 2], 0, 1)
    f = 1 - np.exp(-(dist / 3500.0) ** 0.9)
    f = f * (0.58 - 0.3 * up_amount)
    f = np.where(sky, 0.0, f)
    # ground mist in the valley: denser where the view ray dips (low z)
    img = img * (1 - f[..., None]) + haze_col * f[..., None] * HAZE_GAIN

    # --- sun glow (wide + tight), stronger near the horizon
    g1 = np.exp(-(1 - cosang) * 9000)[..., None] * np.array([8.0, 6.5, 4.5])
    g2 = np.exp(-(1 - cosang) * 600)[..., None] * np.array([0.7, 0.45, 0.22])
    g3 = np.exp(-(1 - cosang) * 40)[..., None] * np.array([0.10, 0.055, 0.025])
    vis = blur(sky.astype(np.float32)[..., None], 2.0)
    img = img + g1 * vis + g2 * (0.35 + 0.65 * vis) + g3

    # --- god rays: radial blur of the bright, unoccluded sky toward the sun
    F = 4
    small = down(np.concatenate([img, sky[..., None].astype(np.float32)], -1), F)
    lum = small[..., :3].mean(-1, keepdims=True)
    src = small[..., :3] * small[..., 3:4] * np.clip(lum - RAY_THRESH, 0, None)
    h, w = src.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = sx / F, sy / F
    acc = np.zeros_like(src)
    N = 96
    for i in range(N):
        s = 1 - 0.55 * i / N
        px = np.clip((cx + (xx - cx) * s).astype(int), 0, w - 1)
        py = np.clip((cy + (yy - cy) * s).astype(int), 0, h - 1)
        acc += src[py, px] * (1 - i / N)
    acc /= N
    near = np.exp(-(1 - cosang) * 25)[..., None]
    rays = up(blur(acc, 1.5), img.shape) * np.array([1.0, 0.8, 0.55]) * near
    img = img + rays * RAY_GAIN

    # --- bloom
    bright = np.clip(img - 1.2, 0, None)
    bl = np.zeros_like(img)
    for s, wgt in ((4, 0.5), (16, 0.35), (48, 0.25)):
        sm = down(bright, 4)
        bl += up(blur(sm, s / 4), img.shape) * wgt
    img = img + bl * 0.3

    # --- graduated filter: deepen and cool the upper sky
    gy = np.clip(1 - (np.arange(H) / H) / 0.42, 0, 1)[:, None, None] ** 1.6
    img = img * (1 - gy * (1 - np.array([0.62, 0.66, 0.84])))

    # --- grade + tonemap
    exposure = EXPOSURE
    img = aces(img * exposure)
    lum = (img * np.array([0.2126, 0.7152, 0.0722])).sum(-1, keepdims=True)
    img = lum + (img - lum) * 1.12                      # a touch more saturation
    img = img * np.array([1.02, 1.0, 0.96])            # warm
    # vignette
    vx = (np.arange(W) / W - 0.5)[None, :]; vy = (np.arange(H) / H - 0.5)[:, None]
    v = 1 - 0.42 * np.clip((vx ** 2 * 1.0 + vy ** 2 * 1.4) * 2.2, 0, 1) ** 1.5
    img = np.clip(img * v[..., None], 0, 1)
    out = srgb(img)
    # dither, 8-bit
    out = np.clip(out * 255 + np.random.default_rng(0).uniform(-0.5, 0.5, out.shape), 0, 255).astype(np.uint8)
    save_png(BASE + '_final.png', out)
    if DDS:
        save_dds(DDS, out)
    print('wrote', BASE + '_final.png', out.shape)


def save_png(path, rgb8):
    H, W, _ = rgb8.shape
    im = bpy.data.images.new('out', W, H, alpha=True)
    px = np.ones((H, W, 4), np.float32)
    px[..., :3] = rgb8[::-1] / 255.0
    im.pixels.foreach_set(px.ravel())
    im.filepath_raw = path; im.file_format = 'PNG'
    bpy.context.scene.render.image_settings.color_depth = '8'
    im.save()


def save_dds(path, rgb8):
    """uncompressed 32-bit A8R8G8B8 DDS, no mipmaps (UI textures don't need them)"""
    import struct
    H, W, _ = rgb8.shape
    hdr = struct.pack('<4sIIIIIII44x', b'DDS ', 124, 0x1 | 0x2 | 0x4 | 0x8 | 0x1000, H, W, W * 4, 0, 1)
    pf = struct.pack('<IIIIIIII', 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    caps = struct.pack('<IIII4x', 0x1000, 0, 0, 0)
    bgra = np.empty((H, W, 4), np.uint8)
    bgra[..., 0] = rgb8[..., 2]; bgra[..., 1] = rgb8[..., 1]; bgra[..., 2] = rgb8[..., 0]; bgra[..., 3] = 255
    with open(path, 'wb') as f:
        f.write(hdr + pf + caps)
        f.write(bgra.tobytes())
    assert os.path.getsize(path) == 128 + W * H * 4


main()
