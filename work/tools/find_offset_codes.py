# -*- coding: utf-8 -*-
"""인자 값이 '항목 안 바이트 위치'인 제어 코드를 찾는다.
각 코드의 각 인자(u32) 가 항목 길이 이하이고 토큰 경계에 떨어지는 비율을 잰다."""
import os, sys, struct, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s8text, units
args = units.load_args()
c = s8text.parse_container(open(os.path.join(HERE, "..", "san8", "M_MSG.S8"), "rb").read())
stat = collections.defaultdict(lambda: [0, 0, 0])   # (code, argidx) -> [총, 길이 이하, 경계]
for g, ents in enumerate(c.groups):
    if not ents:
        continue
    for e in ents:
        toks = s8text.lex(e, args)
        bounds = set(); pos = 0
        for t, b in toks:
            bounds.add(pos); pos += len(b)
        bounds.add(pos)
        pos = 0
        for t, b in toks:
            if t == "code" and len(b) > 3:
                cid = struct.unpack_from("<H", b, 1)[0]
                for k in range((len(b) - 3) // 4):
                    v = struct.unpack_from("<I", b, 3 + 4 * k)[0]
                    s = stat[(cid, k)]
                    s[0] += 1
                    if v <= len(e):
                        s[1] += 1
                        if v in bounds and v > 0:
                            s[2] += 1
            pos += len(b)
res = [(k, v) for k, v in stat.items() if v[0] >= 3]
res.sort(key=lambda kv: -kv[1][2] / kv[1][0])
print("코드 인자  총  길이이하  경계  경계비율")
for (cid, k), (n, le, bd) in res[:40]:
    print("%04X #%d  %5d %5d %5d  %.2f" % (cid, k, n, le, bd, bd / n))
