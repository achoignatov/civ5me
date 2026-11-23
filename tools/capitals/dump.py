"""Debug helper: pretty-print a .gr2 file's object tree (arrays truncated)."""
import sys, gr2

def show(v, ind=0, key=''):
    p = '  ' * ind
    if isinstance(v, dict):
        print(p + key + '{'); [show(x, ind + 1, k + ': ') for k, x in v.items()]; print(p + '}')
    elif isinstance(v, gr2.Variant):
        print(p + key + 'Variant<' + ', '.join(f'{m.name}:t{m.type}' + (f'[{m.array}]' if m.array else '') + (f'{m.extra}' if any(m.extra) else '') for m in v.members) + '>')
        if isinstance(v.value, list):
            print(p + f'  [{len(v.value)} items]'); [show(x, ind + 2) for x in v.value[:LIMIT]]
        else:
            show(v.value, ind + 1)
    elif isinstance(v, list):
        if v and not isinstance(v[0], (dict, list, gr2.Variant)):
            print(p + key + repr(v[:16]) + (f' ...({len(v)})' if len(v) > 16 else ''))
        else:
            print(p + key + f'[{len(v)} items]'); [show(x, ind + 1) for x in v[:LIMIT]]
    else:
        print(p + key + repr(v))

LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 3
f = gr2.read(sys.argv[1])
show(f.root())
