import sys, os, sqlite3, hashlib
import simulate

dbp = sys.argv[1]; out = open(sys.argv[2], 'w')
db = sqlite3.connect(dbp)
civs = [r[0] for r in db.execute("select Type from Civilizations where Type like 'CIVILIZATION_MEC_%' order by ID")]
mins = [r[0] for r in db.execute("select Type from MinorCivilizations order by ID")]
ref = {}
for key in ['TaHugeRndWw', 'TaLrgRndNww', 'TaStdRndNww']:
    lua, _, W, H, dump, starts = simulate.run(dbp, key, 11, [], civs, mins[:22])
    nres = sum(1 for d in dump if d[3] != -1)
    out.write('%s %dx%d starts=%d resources=%d hash=%s\n' % (key, W, H, len(starts), nres, hashlib.md5(repr((dump, starts)).encode()).hexdigest()[:10]))
