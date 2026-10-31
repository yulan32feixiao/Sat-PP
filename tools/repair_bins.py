#!/usr/bin/env python3
"""重放公式修复到 mock2026.bin/mock2025.bin（importer重跑后执行）。读 tools/repairs.json。"""
import gzip, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
SAT = os.path.dirname(HERE)
REPAIRS = json.load(open(os.path.join(HERE, 'repairs.json')))
for fname in ('mock2026.bin', 'mock2025.bin'):
    p = os.path.join(SAT, fname)
    if not os.path.exists(p): continue
    d = json.loads(gzip.decompress(open(p,'rb').read()))
    n = 0
    for q in d['questions']:
        r = REPAIRS.get(q['id'])
        if not r: continue
        if 'op' in r: q['op'] = r['op']
        for k, v in r.items():
            if k.startswith('op') and k != 'op':
                q['op']['ABCD'.index(k[2])] = v
        if 'note' in r:
            q['ra'] = ('<p><b>修复说明：</b>' + r['note'] + '</p>') + (q['ra'] or '')
        n += 1
    js = json.dumps(d, ensure_ascii=False, separators=(',',':')).encode()
    open(p,'wb').write(gzip.compress(js, 9))
    print(fname, 'replayed', n)
