"""Granny animation curves exactly as Civ 5's stock animations store them.

Every animated orientation in the stock game uses the curve format D4nK16uC15u, degree 2:
  * KnotsControls = N uint16 knots followed by N * 3 uint16 controls;
  * knot time = knot / OneOverKnotScale (OneOverKnotScale = 65535 / duration);
  * the knots are [0, eps, h, 2h, ..., T - h, T]: a CLAMPED QUADRATIC B-SPLINE with uniform
    interior knots (the stock knot list omits the repeated end knots; eps marks the clamp);
  * a quaternion control drops its largest component: the high bits of b and c say which one
    (swizzle), the high bit of a is its sign; the other three are 15-bit values * scale + offset,
    with scale/offset chosen per component by a nibble of ScaleOffsetTableEntries
    (nibble 0: scale sqrt(2)/32767, offset -1/sqrt(2), which covers every non-largest component).
Verified by decoding the stock industrial-lighthouse beam (a steady 360-degree turn about Z in 20 s):
see self_test().

Positions that never change use D3Constant32f, everything else DaIdentity, like the stock files.
"""
import math

SQRT2 = math.sqrt(2.0)
# nibble -> (scale, offset); only the entries checked against stock data are listed
TABLE = {0: (SQRT2 / 32767.0, -1.0 / SQRT2), 7: (0.17677669 / 32767.0, 0.0)}


# --------------------------------------------------------------------------- quaternions
def quat_decode(a, b, c, scales, offsets):
    s1 = ((b & 0x8000) >> 14) | (c >> 15)
    s2, s3, s4 = (s1 + 1) & 3, (s1 + 2) & 3, (s1 + 3) & 3
    q = [0.0] * 4
    q[s2] = (a & 0x7fff) * scales[s2] + offsets[s2]
    q[s3] = (b & 0x7fff) * scales[s3] + offsets[s3]
    q[s4] = (c & 0x7fff) * scales[s4] + offsets[s4]
    d = math.sqrt(max(0.0, 1.0 - (q[s2] ** 2 + q[s3] ** 2 + q[s4] ** 2)))
    q[s1] = -d if a & 0x8000 else d
    return q


def quat_encode(q):
    """q = (x, y, z, w), unit length. Uses table entry 0 for every component."""
    n = math.sqrt(sum(v * v for v in q))
    q = [v / n for v in q]
    s1 = max(range(4), key=lambda i: abs(q[i]))
    sc, off = TABLE[0]
    vals = []
    for k in (1, 2, 3):
        i = (s1 + k) & 3
        v = int(round((q[i] - off) / sc))
        vals.append(min(0x7fff, max(0, v)))
    a, b, c = vals
    if q[s1] < 0:
        a |= 0x8000
    if s1 & 2:
        b |= 0x8000
    if s1 & 1:
        c |= 0x8000
    return a, b, c


def yaw_quat(deg):
    """Rotation about +Z (counter-clockwise seen from above)."""
    h = math.radians(deg) / 2
    return (0.0, 0.0, math.sin(h), math.cos(h))


# --------------------------------------------------------------------------- clamped quadratic B-spline
def full_knots(T, m):
    """Knot vector of a clamped quadratic B-spline with m uniform spans on [0, T] (m + 2 controls)."""
    h = T / m
    return [0.0, 0.0, 0.0] + [h * i for i in range(1, m)] + [T, T, T]


def basis(t, U, n):
    """Values of the n quadratic B-spline basis functions at t (Cox-de Boor)."""
    p = 2
    t = min(max(t, U[0]), U[-1] - 1e-9)
    N = [1.0 if U[i] <= t < U[i + 1] else 0.0 for i in range(len(U) - 1)]
    for k in range(1, p + 1):
        N = [((t - U[i]) / (U[i + k] - U[i]) * N[i] if U[i + k] > U[i] else 0.0) +
             ((U[i + k + 1] - t) / (U[i + k + 1] - U[i + 1]) * N[i + 1] if U[i + k + 1] > U[i + 1] else 0.0)
             for i in range(len(U) - k - 1)]
    return N[:n]


def fit(f, T, m, samples=None):
    """Least-squares controls of a clamped quadratic B-spline (m spans) for the scalar function f."""
    U = full_knots(T, m)
    n = m + 2
    ts = [T * i / (samples or 8 * m) for i in range((samples or 8 * m) + 1)]
    A = [basis(t, U, n) for t in ts]
    y = [f(t) for t in ts]
    # normal equations (n is small)
    M = [[sum(A[r][i] * A[r][j] for r in range(len(ts))) for j in range(n)] for i in range(n)]
    v = [sum(A[r][i] * y[r] for r in range(len(ts))) for i in range(n)]
    for i in range(n):                        # Gaussian elimination
        piv = max(range(i, n), key=lambda r: abs(M[r][i]))
        M[i], M[piv], v[i], v[piv] = M[piv], M[i], v[piv], v[i]
        for r in range(i + 1, n):
            f2 = M[r][i] / M[i][i]
            for c in range(i, n):
                M[r][c] -= f2 * M[i][c]
            v[r] -= f2 * v[i]
    x = [0.0] * n
    for i in reversed(range(n)):
        x[i] = (v[i] - sum(M[i][c] * x[c] for c in range(i + 1, n))) / M[i][i]
    return x


def evaluate(ctrl, T, t):
    m = len(ctrl) - 2
    U = full_knots(T, m)
    return sum(b * c for b, c in zip(basis(t, U, len(ctrl)), ctrl))


# --------------------------------------------------------------------------- the stock curve record
def yaw_curve_value(yaw_fn, T, m):
    """D4nK16uC15u curve dict (KnotsControls etc.) for a rotation about +Z given by yaw_fn(t) degrees."""
    ctrl = fit(yaw_fn, T, m)
    one_over = 65535.0 / T
    h = T / m
    knots = [0.0, 0.002] + [h * i for i in range(1, m)] + [T]      # stock layout (0, eps, interior, T)
    kq = [int(round(k * one_over)) for k in knots]
    cq = []
    for deg in ctrl:
        cq += list(quat_encode(yaw_quat(deg)))
    return dict(knots=kq, controls=cq, one_over=one_over, entries=0x0000, degrees=ctrl)


def decode_curve(kc, one_over, entries):
    n = len(kc) // 4
    scales = [TABLE[(entries >> (4 * i)) & 0xF][0] for i in range(4)]
    offsets = [TABLE[(entries >> (4 * i)) & 0xF][1] for i in range(4)]
    knots = [k / one_over for k in kc[:n]]
    quats = [quat_decode(*kc[n + 3 * i:n + 3 * i + 3], scales, offsets) for i in range(n)]
    return knots, quats


def quat_yaw_deg(q):
    return math.degrees(2 * math.atan2(q[2], q[3]))


def self_test(stock_idle_path):
    """Decode the stock lighthouse beam and check the codec + spline model against it."""
    import gr2
    r = gr2.read(stock_idle_path).root()
    tr = [t for t in r['TrackGroups'][0]['TransformTracks'] if t['Name'] == 'Point01'][0]
    v = tr['OrientationCurve']['CurveData'].value
    kc = [x['UInt16'] for x in v['KnotsControls']]
    knots, quats = decode_curve(kc, v['OneOverKnotScale'], v['ScaleOffsetTableEntries'])
    for q in quats:
        assert abs(sum(x * x for x in q) - 1.0) < 1e-3 and abs(q[0]) < 1e-3 and abs(q[1]) < 1e-3, q
    ang = []
    for q in quats:                                   # unwrap
        a = quat_yaw_deg(q)
        while ang and a < ang[-1] - 180:
            a += 360
        ang.append(a)
    T = knots[-1]
    for t in (0.0, 2.5, 5.0, 10.0, 15.0, 20.0):       # the beam turns 18 degrees per second
        assert abs(evaluate(ang, T, t) - 18.0 * t) < 0.6, (t, evaluate(ang, T, t))
    # our encoder round-trips
    for deg in (-170, -40, -3, 0, 12, 44, 90, 179):
        q = yaw_quat(deg)
        q2 = quat_decode(*quat_encode(q), [TABLE[0][0]] * 4, [TABLE[0][1]] * 4)
        assert abs(quat_yaw_deg(q2) - deg) < 0.05, (deg, q2)
    return True


# --------------------------------------------------------------------------- generic evaluation (any stored knots)
def evaluate_stored(ctrl, stored_knots, t):
    """Value of a clamped quadratic B-spline as Granny stores it: stored_knots = [0, eps, interior..., T]
    (one per control); the full knot vector is [0,0,0] + interior + [T,T,T]."""
    T = stored_knots[-1]
    U = [0.0, 0.0, 0.0] + list(stored_knots[2:-1]) + [T, T, T]
    return sum(b * c for b, c in zip(basis(t, U, len(ctrl)), ctrl))


def sample_quat_curve(value, t):
    """Orientation (x, y, z, w) of a D4nK16uC15u curve dict (as read by gr2) at time t."""
    kc = [x['UInt16'] for x in value['KnotsControls']]
    knots, quats = decode_curve(kc, value['OneOverKnotScale'], value['ScaleOffsetTableEntries'])
    for i in range(1, len(quats)):                 # one hemisphere, so components blend smoothly
        if sum(a * b for a, b in zip(quats[i - 1], quats[i])) < 0:
            quats[i] = [-x for x in quats[i]]
    if len(quats) == 1:
        return tuple(quats[0])
    q = [evaluate_stored([qq[c] for qq in quats], knots, t) for c in range(4)]
    n = math.sqrt(sum(x * x for x in q)) or 1.0
    return tuple(x / n for x in q)
