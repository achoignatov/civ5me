import sys, itertools, collections
from civ5map import read_map
m = read_map(sys.argv[1]); W, H = m['w'], m['h']
def corners(x, y):
    cx = 2*x + (y & 1); cy = 3*y
    return dict(N=(cx,cy+2), NE=(cx+1,cy+1), SE=(cx+1,cy-1), S=(cx,cy-2), SW=(cx-1,cy-1), NW=(cx-1,cy+1))
EDGES = {'E': ('NE','SE'), 'SE': ('SE','S'), 'SW': ('S','SW')}
def score(bitmap):  # bitmap: bit -> edge name
    deg = collections.Counter(); n = 0
    for i, pl in enumerate(m['plots']):
        x, y = i % W, i // W
        c = corners(x, y)
        es = set(e for b, e in bitmap.items() if pl[3] & (1 << b))
        for e in es:
            a, b = EDGES[e]; deg[c[a]] += 1; deg[c[b]] += 1; n += 1
    dang = sum(1 for v in deg.values() if v == 1)
    return n, dang
res = []
for perm in itertools.permutations(['E','SE','SW']):
    res.append(('H1 bits012', perm, score({0:perm[0],1:perm[1],2:perm[2]})))
    res.append(('H2 pairs (0,1)(2,3)(4,5)', perm, score({0:perm[0],1:perm[0],2:perm[1],3:perm[1],4:perm[2],5:perm[2]})))
    res.append(('H3 pairs (0,3)(1,4)(2,5)', perm, score({0:perm[0],3:perm[0],1:perm[1],4:perm[1],2:perm[2],5:perm[2]})))
for r in sorted(res, key=lambda r: r[2][1]/max(1,r[2][0])): print(r)
