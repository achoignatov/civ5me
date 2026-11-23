"""Replay Civ5 mod UpdateDatabase actions (XML + SQL) against a copy of the game DB to find errors.
Usage: dbreplay.py <base.db> <out.db> <modinfo>"""
import sqlite3, sys, os, re, shutil, xml.etree.ElementTree as ET

def conv(v):
    if v is None: return None
    lv = v.strip().lower()
    if lv == 'true': return 1
    if lv == 'false': return 0
    return v

def load_xml(db, path, errs):
    txt = open(path, 'rb').read().decode('utf-8-sig', errors='replace')
    try:
        root = ET.fromstring(txt.encode('utf-8'))
    except ET.ParseError as e:
        errs.append((path, 'XML parse error: %s' % e)); return
    cur = db.cursor()
    for tbl in root:
        if not isinstance(tbl.tag, str): continue
        name = tbl.tag
        if name == 'Table':
            cols = []
            for c in tbl:
                if c.tag != 'Column': continue
                a = c.attrib; s = '"%s" %s' % (a['name'], a.get('type', 'text'))
                if a.get('primarykey') == 'true': s += ' PRIMARY KEY'
                if a.get('autoincrement') == 'true': s += ' AUTOINCREMENT'
                if a.get('unique') == 'true': s += ' UNIQUE'
                if a.get('notnull') == 'true': s += ' NOT NULL'
                if 'default' in a:
                    d = a['default']; s += ' DEFAULT %s' % (d if d.upper() == 'NULL' or re.fullmatch(r'-?\d+(\.\d+)?', d) else "'%s'" % d.replace("'", "''"))
                cols.append(s)
            try: cur.execute('CREATE TABLE IF NOT EXISTS "%s" (%s)' % (tbl.attrib['name'], ', '.join(cols)))
            except Exception as e: errs.append((path, 'CREATE %s: %s' % (tbl.attrib['name'], e)))
            continue
        if name.startswith('Language_'):
            continue  # localization DB, not validated here
        for op in tbl:
            if not isinstance(op.tag, str): continue
            try:
                if op.tag in ('Row', 'Replace'):
                    vals = dict(op.attrib)
                    for ch in op: vals[ch.tag] = ch.text if ch.text is not None else ''
                    keys = list(vals)
                    sql = '%s INTO "%s" (%s) VALUES (%s)' % ('INSERT OR REPLACE' if op.tag == 'Replace' else 'INSERT', name,
                        ','.join('"%s"' % k for k in keys), ','.join('?' * len(keys)))
                    cur.execute(sql, [conv(vals[k]) for k in keys])
                elif op.tag == 'Update':
                    w = op.find('Where'); s = op.find('Set')
                    wv = dict(w.attrib) if w is not None else {}
                    sv = dict(s.attrib) if s is not None else {}
                    if s is not None:
                        for ch in s: sv[ch.tag] = ch.text
                    sql = 'UPDATE "%s" SET %s' % (name, ','.join('"%s"=?' % k for k in sv))
                    if wv: sql += ' WHERE ' + ' AND '.join('"%s"=?' % k for k in wv)
                    cur.execute(sql, [conv(v) for v in sv.values()] + [conv(v) for v in wv.values()])
                elif op.tag == 'Delete':
                    wv = dict(op.attrib)
                    sql = 'DELETE FROM "%s"' % name
                    if wv: sql += ' WHERE ' + ' AND '.join('"%s"=?' % k for k in wv)
                    cur.execute(sql, [conv(v) for v in wv.values()])
                else:
                    errs.append((path, 'unknown op %s in %s' % (op.tag, name)))
            except Exception as e:
                errs.append((path, '%s %s: %s %s' % (op.tag, name, e, dict(op.attrib) or [c.tag for c in op][:4])))

def load_sql(db, path, errs):
    txt = open(path, 'rb').read().decode('utf-8-sig', errors='replace')
    # execute statement by statement so one failure doesn't hide others
    buf = ''
    for line in txt.splitlines(True):
        buf += line
        if sqlite3.complete_statement(buf):
            try: db.execute(buf)
            except Exception as e: errs.append((path, '%s :: %s' % (e, buf.strip()[:150])))
            buf = ''

def replay(base, out, modinfo):
    shutil.copy(base, out)
    db = sqlite3.connect(out)
    root = os.path.dirname(modinfo)
    t = open(modinfo, 'rb').read().decode('utf-8-sig')
    m = re.search(r'<OnModActivated>(.*?)</OnModActivated>', t, re.S)
    errs = []
    for f in re.findall(r'<UpdateDatabase>([^<]+)</UpdateDatabase>', m.group(1)):
        p = os.path.join(root, f.replace('\\', '/'))
        if not os.path.exists(p): errs.append((f, 'MISSING FILE')); continue
        (load_sql if p.lower().endswith('.sql') else load_xml)(db, p, errs)
    db.commit()
    return db, errs

if __name__ == '__main__':
    db, errs = replay(*sys.argv[1:4])
    for e in errs: print('ERR', e)
    print('errors:', len(errs))
