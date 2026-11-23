"""Pure-Python Oodle1 decompressor for Granny2 (.gr2) sections.

Ported from opengr2's oodle1.c (MPL-2.0, https://github.com/arves100/opengr2),
itself derived from nwn2mdk's gr2_decompress.cpp. Used only to read stock
models for reference; the files we write are stored uncompressed.
"""
import struct


class Decoder:
    __slots__ = ('numer', 'denom', 'next_denom', 'buf', 'pos')

    def __init__(self, buf, pos):
        self.buf = buf
        self.pos = pos
        self.numer = buf[pos] >> 1
        self.denom = 0x80
        self.next_denom = 0

    def decode(self, mx):
        buf = self.buf
        while self.denom <= 0x800000:
            self.numer = ((self.numer << 8) | ((buf[self.pos] << 7) & 0x80) | ((buf[self.pos + 1] >> 1) & 0x7f)) & 0xffffffff
            self.pos += 1
            self.denom = (self.denom << 8) & 0xffffffff
        self.next_denom = self.denom // mx
        return min(self.numer // self.next_denom, mx - 1)

    def commit(self, mx, val, err):
        self.numer = (self.numer - self.next_denom * val) & 0xffffffff
        if val + err < mx:
            self.denom = (self.next_denom * err) & 0xffffffff
        else:
            self.denom = (self.denom - self.next_denom * val) & 0xffffffff
        return val

    def decode_commit(self, mx):
        return self.commit(mx, self.decode(mx), 1)


class WeighWindow:
    __slots__ = ('weight_total', 'count_cap', 'ranges', 'weights', 'values',
                 'thresh_increase', 'thresh_range_rebuild', 'thresh_weight_rebuild', 'thresh_increase_cap')

    def __init__(self, max_value, count_cap):
        self.weight_total = 4
        self.count_cap = (count_cap + 1) & 0xffff
        self.ranges = [0, 0x4000]
        self.weights = [4]
        self.values = [0]
        self.thresh_increase = 4
        self.thresh_range_rebuild = 8
        self.thresh_weight_rebuild = max(256, min(32 * max_value, 15160)) & 0xffff
        if max_value > 64:
            self.thresh_increase_cap = min(2 * max_value, self.thresh_weight_rebuild // 2 - 32) & 0xffff
        else:
            self.thresh_increase_cap = 128

    def rebuild_ranges(self):
        n = len(self.weights)
        range_weight = (8 * 0x4000 // self.weight_total) & 0xffff
        ranges = [0] * (n + 1)
        start = 0
        for i in range(n):
            ranges[i] = start
            start = (start + (self.weights[i] * range_weight) // 8) & 0xffff
        ranges[n] = 0x4000
        self.ranges = ranges
        if self.thresh_increase > self.thresh_increase_cap // 2:
            self.thresh_range_rebuild = (self.weight_total + self.thresh_increase_cap) & 0xffff
        else:
            self.thresh_increase = (self.thresh_increase * 2) & 0xffff
            self.thresh_range_rebuild = (self.weight_total + self.thresh_increase) & 0xffff

    def rebuild_weights(self):
        w = [x // 2 for x in self.weights]
        v = self.values
        self.weight_total = sum(w) & 0xffff
        i = 1
        while i < len(w):
            while i < len(w) and w[i] == 0:
                w[i] = w[-1]
                v[i] = v[-1]
                w.pop()
                v.pop()
            i += 1
        # max_element from index 1 (first maximum)
        best, idx = 0, 1
        for j in range(1, len(w)):
            if w[j] > best:
                best, idx = w[j], j
        if idx < len(w):
            w[idx], w[-1] = w[-1], w[idx]
            v[idx], v[-1] = v[-1], v[idx]
        if len(w) < self.count_cap and w[0] == 0:
            w[0] = 1
            self.weight_total = (self.weight_total + 1) & 0xffff
        self.weights = w
        self.values = v

    def try_decode(self, dec):
        """Returns (new_index or None, value)."""
        if self.weight_total >= self.thresh_range_rebuild:
            if self.thresh_range_rebuild >= self.thresh_weight_rebuild:
                self.rebuild_weights()
            self.rebuild_ranges()
        value = dec.decode(0x4000)
        ranges = self.ranges
        r = len(ranges) - 1
        for i, x in enumerate(ranges):
            if x > value:
                r = i
                break
        r -= 1
        dec.commit(0x4000, ranges[r], ranges[r + 1] - ranges[r])
        self.weights[r] += 1
        self.weight_total = (self.weight_total + 1) & 0xffff
        if r > 0:
            return None, self.values[r]
        if len(self.weights) >= len(ranges) and dec.decode_commit(2) == 1:
            idx = len(ranges) + dec.decode_commit(len(self.weights) - len(ranges) + 1) - 1
            self.weights[idx] += 2
            self.weight_total = (self.weight_total + 2) & 0xffff
            return None, self.values[idx]
        self.values.append(0)
        self.weights.append(2)
        self.weight_total = (self.weight_total + 2) & 0xffff
        if len(self.weights) == self.count_cap:
            self.weight_total = (self.weight_total - self.weights[0]) & 0xffff
            self.weights[0] = 0
        return len(self.values) - 1, 0


SIZES = (128, 192, 256, 512)


class Dictionary:
    def __init__(self, p):
        dvm, brm, dcount, hcount, sizes = p
        self.decoded_size = 0
        self.backref_size = 0
        self.decoded_value_max = dvm
        self.backref_value_max = brm
        self.lowbit_value_max = min(brm + 1, 4)
        self.midbit_value_max = min(brm // 4 + 1, 256)
        self.highbit_value_max = brm // 1024 + 1
        self.lowbit = WeighWindow(self.lowbit_value_max - 1, self.lowbit_value_max)
        self.highbit = WeighWindow(self.highbit_value_max - 1, hcount + 1)
        self.midbit = [WeighWindow(self.midbit_value_max - 1, self.midbit_value_max) for _ in range(self.highbit_value_max)]
        self.decoded = [WeighWindow(dvm - 1, dcount) for _ in range(4)]
        self.size_windows = []
        for i in range(4):
            for _ in range(16):
                self.size_windows.append(WeighWindow(64, sizes[3 - i]))
        self.size_windows.append(WeighWindow(64, sizes[0]))

    @staticmethod
    def _get(win, dec, mx):
        idx, val = win.try_decode(dec)
        if idx is not None:
            val = dec.decode_commit(mx)
            win.values[idx] = val
        return val

    def block(self, dec, out):
        self.backref_size = self._get(self.size_windows[self.backref_size], dec, 65)
        if self.backref_size > 0:
            bs = self.backref_size + 1 if self.backref_size < 61 else SIZES[self.backref_size - 61]
            brange = min(self.backref_value_max, self.decoded_size)
            d3 = self._get(self.lowbit, dec, self.lowbit_value_max)
            d4 = self._get(self.highbit, dec, brange // 1024 + 1)
            d5 = self._get(self.midbit[d4], dec, min(brange // 4 + 1, 256))
            off = (d4 << 10) + (d5 << 2) + d3 + 1
            self.decoded_size += bs
            start = len(out) - off
            for k in range(bs):
                out.append(out[start + k])
            return
        win = self.decoded[len(out) % 4]
        out.append(self._get(win, dec, self.decoded_value_max) & 0xff)
        self.decoded_size += 1


def decompress(comp, out_len, stop0, stop1):
    if not comp:
        return b''
    comp = bytes(comp) + b'\0' * 8
    params = []
    for i in range(3):
        w0, w1 = struct.unpack_from('<II', comp, i * 12)
        sizes = comp[i * 12 + 8:i * 12 + 12]
        params.append((w0 & 0x1ff, w0 >> 9, w1 & 0x1ff, w1 >> 19, sizes))
    dec = Decoder(comp, 36)
    out = bytearray()
    for i, stop in enumerate((stop0, stop1, out_len)):
        d = Dictionary(params[i])
        while len(out) < stop:
            d.block(dec, out)
    return bytes(out[:out_len])
