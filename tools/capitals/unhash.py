"""Debug helper: replace '#xxxxxxxx' string hashes in a dump with known strings."""
import sys,re,pickle
h=pickle.load(open(sys.argv[1],'rb'))
t=open(sys.argv[2]).read()
miss=set()
def r(m):
    v=int(m.group(1),16)
    if v in h: return h[v]
    miss.add(m.group(0)); return m.group(0)
print(re.sub(r'#([0-9a-f]{8})',r,t))
print('MISSING',sorted(miss),file=sys.stderr)
