"""DXT3 .dds encode/decode with numpy (run under Blender's bundled Python).

Civ 5 building textures are DXT3 with a full mip chain, so that's what we emit.
"""
import struct
import numpy as np


def _565_to_rgb(c):
    r = ((c >> 11) & 31) * 255 // 31
    g = ((c >> 5) & 63) * 255 // 63
    b = (c & 31) * 255 // 31
    return np.stack([r, g, b], -1).astype(np.float32)


def decode_dxt3(path):
    d = open(path, 'rb').read()
    h, w = struct.unpack_from('<II', d, 12)
    assert d[84:88] == b'DXT3'
    bw, bh = max(1, w // 4), max(1, h // 4)
    n = bw * bh
    blk = np.frombuffer(d, np.uint8, n * 16, 128).reshape(n, 16)
    alpha = blk[:, :8].copy().view('<u8')[:, 0]
    c0 = blk[:, 8:10].copy().view('<u2')[:, 0].astype(np.int32)
    c1 = blk[:, 10:12].copy().view('<u2')[:, 0].astype(np.int32)
    idx = blk[:, 12:16].copy().view('<u4')[:, 0]
    p0, p1 = _565_to_rgb(c0), _565_to_rgb(c1)
    pal = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3], 1)  # n,4,3
    out = np.zeros((n, 16, 4), np.float32)
    for i in range(16):
        sel = (idx >> (2 * i)) & 3
        out[:, i, :3] = pal[np.arange(n), sel]
        out[:, i, 3] = ((alpha >> (4 * i)) & 15) * 17
    img = out.reshape(bh, bw, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, 4)
    return img.astype(np.uint8)  # rows top-to-bottom


def _rgb_to_565(c):
    c = np.clip(np.rint(c), 0, 255).astype(np.int32)
    return ((c[..., 0] * 31 + 127) // 255 << 11) | ((c[..., 1] * 63 + 127) // 255 << 5) | ((c[..., 2] * 31 + 127) // 255)


def _encode_level(img):
    """img: HxWx4 uint8 (top row first). Returns DXT3 bytes."""
    h, w = img.shape[:2]
    ph, pw = max(4, (h + 3) // 4 * 4), max(4, (w + 3) // 4 * 4)
    if (ph, pw) != (h, w):
        img = np.pad(img, ((0, ph - h), (0, pw - w), (0, 0)), mode='edge')
    bh, bw = ph // 4, pw // 4
    blocks = img.reshape(bh, 4, bw, 4, 4).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 4).astype(np.float32)
    rgb = blocks[..., :3]
    # endpoints: project on principal axis (cheap PCA via max-variance channel span)
    mean = rgb.mean(1, keepdims=True)
    cen = rgb - mean
    cov = np.einsum('nki,nkj->nij', cen, cen)
    axis = np.ones((len(rgb), 3), np.float32)
    for _ in range(4):
        axis = np.einsum('nij,nj->ni', cov, axis)
        axis /= np.linalg.norm(axis, axis=1, keepdims=True) + 1e-6
    t = np.einsum('nki,ni->nk', cen, axis)
    lo = mean[:, 0] + axis * t.min(1, keepdims=True)
    hi = mean[:, 0] + axis * t.max(1, keepdims=True)
    c0, c1 = _rgb_to_565(hi), _rgb_to_565(lo)
    swap = c0 < c1
    c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    p0, p1 = _565_to_rgb(c0), _565_to_rgb(c1)
    pal = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3], 1)
    dist = ((rgb[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(-1)
    sel = dist.argmin(-1).astype(np.uint32)
    sel = np.where((c0 == c1)[:, None], 0, sel)
    idx = np.zeros(len(rgb), np.uint32)
    for i in range(16):
        idx |= sel[:, i] << (2 * i)
    a4 = np.clip(np.rint(blocks[..., 3] / 17), 0, 15).astype(np.uint64)
    alpha = np.zeros(len(rgb), np.uint64)
    for i in range(16):
        alpha |= a4[:, i] << np.uint64(4 * i)
    out = np.zeros((len(rgb), 16), np.uint8)
    out[:, :8] = alpha.astype('<u8').view(np.uint8).reshape(-1, 8)
    out[:, 8:10] = c0.astype('<u2').view(np.uint8).reshape(-1, 2)
    out[:, 10:12] = c1.astype('<u2').view(np.uint8).reshape(-1, 2)
    out[:, 12:16] = idx.astype('<u4').view(np.uint8).reshape(-1, 4)
    return out.tobytes()


def write_dxt3(path, img):
    """img: HxWx4 uint8, top row first, power-of-two size."""
    h, w = img.shape[:2]
    levels = []
    cur = img.astype(np.float32)
    while True:
        levels.append(_encode_level(np.clip(np.rint(cur), 0, 255).astype(np.uint8)))
        if cur.shape[0] == 1 and cur.shape[1] == 1:
            break
        hh, ww = max(1, cur.shape[0] // 2), max(1, cur.shape[1] // 2)
        cur = cur[:hh * 2 if cur.shape[0] > 1 else 1, :ww * 2 if cur.shape[1] > 1 else 1]
        cur = cur.reshape(hh, cur.shape[0] // hh, ww, cur.shape[1] // ww, 4).mean((1, 3))
    hdr = struct.pack('<4sIIIIIII44x', b'DDS ', 124, 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000,
                      h, w, len(levels[0]), 0, len(levels))
    pf = struct.pack('<II4sIIIII', 32, 0x4, b'DXT3', 0, 0, 0, 0, 0)
    caps = struct.pack('<IIIII', 0x1000 | 0x400000 | 0x8, 0, 0, 0, 0)
    blob = hdr + pf + caps
    assert len(blob) == 128
    open(path, 'wb').write(blob + b''.join(levels))
