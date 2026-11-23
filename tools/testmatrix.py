import sys, sqlite3, collections, io, contextlib, hashlib
import simulate
dbp = sys.argv[1]
db = sqlite3.connect(dbp)
allciv = [r[0] for r in db.execute("select Type from Civilizations where Type like 'CIVILIZATION_MEC_%' order by ID")]
allmin = [r[0] for r in db.execute("select Type from MinorCivilizations order by ID")]
resname = {r[0]: r[1] for r in db.execute('select ID, Type from Resources')}

def go(key, seed, opts, nmaj, nmin):
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        lua, _, W, H, dump, starts = simulate.run(dbp, key, seed, opts, allciv[:nmaj], allmin[:nmin])
    h = hashlib.md5(repr(dump).encode()).hexdigest()[:10]
    return W, H, dump, starts, h

def geo_violations(key, W, dump, requested_plots=set()):
    pos = list(db.execute('select Type,X,Y,Width,Height from Resource_%sRegionPosition' % key))
    exc = collections.defaultdict(set)
    for t, r in db.execute('select Type, Resource from Resource_%sRegionExclude' % key): exc[t].add(r)
    bad = 0
    for i, d in enumerate(dump):
        if d[3] == -1: continue
        x, y = i % W, i // W
        for t, rx, ry, rw, rh in pos:
            if rx <= x <= rx + rw and ry <= y <= ry + rh and resname[d[3]] in exc[t]:
                bad += 1; break
    return bad

def nres(dump): return sum(1 for d in dump if d[3] != -1)

results = []
for key in ['TaHugeRndWw', 'TaLrgRndNww', 'TaHugeRndNww', 'TaLrgRndWw', 'TaStdRndWw', 'TaStdRndNww']:
    W, H, d1, s1, h1 = go(key, 11, [], 14, 22)
    _, _, d2, s2, h2 = go(key, 11, [], 14, 22)
    _, _, d3, s3, h3 = go(key, 99, [], 14, 22)
    print('%-12s %dx%d starts=%d res=%d  same-seed-identical=%s  diff-seed-differs=%s' % (key, W, H, len(s1), nres(d1), h1 == h2, h1 != h3))
    tsl = [s for s in s1]
    dup = len(set((s[2], s[3]) for s in s1)) != len(s1)
    print('   duplicate start plots: %s' % dup)
for key in ['TaHugeRndWw', 'TaLrgRndNww']:
    for opts, label in [([1,3,1,1,1,1,2,2], 'defaults'), ([2,3,1,1,1,1,2,2], 'CS tsl+random'), ([3,3,1,1,1,1,2,2], 'CS all random'),
                        ([1,1,1,1,1,1,2,2], 'resources poor'), ([1,5,1,1,1,1,2,2], 'resources rich'),
                        ([1,3,2,2,2,2,2,2], 'NW/geo/requested off')]:
        W, H, d, s, h = go(key, 5, opts, 14, 22)
        nw = sum(1 for x in d if x[2] >= 8)
        print('%-12s %-22s starts=%d res=%d NWtiles=%d geoViolations=%d' % (key, label, len(s), nres(d), nw, geo_violations(key, W, d)))
    W, H, d, s, h = go(key, 3, [], 4, 6)
    print('%-12s small game 4 civs 6 CS: starts=%d res=%d' % (key, len(s), nres(d)))
