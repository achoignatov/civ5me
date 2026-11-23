import sys, sqlite3, io, contextlib, hashlib, os
import simulate
dbp = sys.argv[1]
db = sqlite3.connect(dbp)
allciv = [r[0] for r in db.execute("select Type from Civilizations where Type like 'CIVILIZATION_MEC_%' order by ID")]
allmin = [r[0] for r in db.execute("select Type from MinorCivilizations order by ID")]
out = open(sys.argv[2], 'w')
for key in ['TaHugeRndWw', 'TaLrgRndNww', 'TaHugeRndNww', 'TaLrgRndWw', 'TaStdRndWw', 'TaStdRndNww']:
    hs = []
    for seed in (11, 11, 99):
        lua, _, W, H, dump, starts = simulate.run(dbp, key, seed, [], allciv, allmin[:22])
        hs.append(hashlib.md5(repr((dump, starts)).encode()).hexdigest()[:10])
    nres = sum(1 for d in dump if d[3] != -1)
    dup = len(set((s[2], s[3]) for s in starts)) != len(starts)
    out.write('%-12s %dx%d starts=%d res=%d same-seed-identical=%s other-seed-differs=%s duplicate-starts=%s\n' % (key, W, H, len(starts), nres, hs[0] == hs[1], hs[0] != hs[2], dup))
    out.flush()
