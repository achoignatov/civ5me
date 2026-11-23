import sys, itertools, collections
from civ5map import read_map
m = read_map(sys.argv[1]); W, H = m['w'], m['h']
def corners(x, y):
    cx = 2*x + (y & 1); cy = 3*y
    return dict(N=(cx,cy+2), NE=(cx+1,cy+1), SE=(cx+1,cy-1), S=(cx,cy-2), SW=(cx-1,cy-1), NW=(cx-1,cy+1))
# edge: (presence bit, flow bit, (from,to) if flow bit set, (from,to) if not set)
for combo in itertools.product([0,1], repeat=3):
    defs = [
        (0, 3, ('NE','SE'), ('SE','NE')),   # E edge: set=SOUTH (NE->SE), unset=NORTH
        (1, 4, ('SE','S'), ('S','SE')),     # SE edge: set=SW, unset=NE
        (2, 5, ('S','SW'), ('SW','S')),     # SW edge: set=NW, unset=SE
    ]
    ins = collections.Counter(); outs = collections.Counter()
    for i, pl in enumerate(m['plots']):
        c = corners(i % W, i // W)
        for k,(pb, fb, a, b) in enumerate(defs):
            if pl[3] & (1<<pb):
                s = bool(pl[3] & (1<<fb)) ^ bool(combo[k])
                f, t = a if s else b
                outs[c[f]] += 1; ins[c[t]] += 1
    good = sum(1 for v in set(ins)|set(outs) if ins[v]==1 and outs[v]==1)
    bad = sum(1 for v in set(ins)|set(outs) if (ins[v]==2 and outs[v]==0) or (outs[v]==2 and ins[v]==0))
    print(combo, good, bad)
# water-adjacency of sinks vs sources for combo (0,1,0)
combo=(0,1,0)
defs = [(0,3,('NE','SE'),('SE','NE')),(1,4,('SE','S'),('S','SE')),(2,5,('S','SW'),('SW','S'))]
ins = collections.Counter(); outs = collections.Counter(); vplots=collections.defaultdict(set)
for i, pl in enumerate(m['plots']):
    c = corners(i % W, i // W)
    for v in c.values(): vplots[v].add(i)
    for k,(pb,fb,a,b) in enumerate(defs):
        if pl[3] & (1<<pb):
            s = bool(pl[3] & (1<<fb)) ^ bool(combo[k]); f,t = a if s else b
            outs[c[f]]+=1; ins[c[t]]+=1
water = lambda i: m['plots'][i][0] in (5,6)
sinks=[v for v in ins if outs[v]==0]; srcs=[v for v in outs if ins[v]==0]
print('sinks', len(sinks), 'water-adj', sum(any(water(i) for i in vplots[v]) for v in sinks))
print('sources', len(srcs), 'water-adj', sum(any(water(i) for i in vplots[v]) for v in srcs))
