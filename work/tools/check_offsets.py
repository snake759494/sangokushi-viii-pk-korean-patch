# -*- coding: utf-8 -*-
"""원본·패치 M_MSG 에서 위치 인자가 같은 뼈대 토큰을 가리키는지 검사."""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s8text, units
from build_text import OFFSET_CODES
args = units.load_args()
W = os.path.join(HERE, "..")
A = s8text.parse_container(open(os.path.join(W, "san8", "M_MSG.S8"), "rb").read())
B = s8text.parse_container(open(os.path.join(W, "patched", "M_MSG.S8"), "rb").read())


def targets(ents):
    """그룹 위치 -> (항목, 뼈대 번호 또는 '끝'), 그리고 위치 인자 목록"""
    tmap, refs, base = {}, [], 0
    for i, e in enumerate(ents):
        pos, j = 0, 0
        tmap[base] = (i, 0, "시작")
        for t, b in s8text.lex(e, args):
            if t != "txt":
                tmap.setdefault(base + pos, (i, j, "앞"))
                if t == "code":
                    cid = struct.unpack_from("<H", b, 1)[0]
                    for k in OFFSET_CODES.get(cid, ()):
                        if 3 + 4 * k + 4 <= len(b):
                            refs.append((i, j, cid, k, struct.unpack_from("<I", b, 3 + 4 * k)[0]))
                j += 1
                tmap.setdefault(base + pos + len(b), (i, j, "앞"))
            pos += len(b)
        tmap.setdefault(base + pos, (i, j, "끝"))
        base += len(e)
    return tmap, refs


bad = n = 0
for g in range(len(A.groups)):
    if not A.groups[g]:
        continue
    ta, ra = targets(A.groups[g])
    tb, rb = targets(B.groups[g])
    for x, y in zip(ra, rb):
        n += 1
        if ta.get(x[4], "?")[:2] != tb.get(y[4], "!")[:2]:
            bad += 1
            if bad <= 10:
                print("g%d: 원문 %s -> %s / 번역 %s -> %s" % (g, x, ta.get(x[4]), y, tb.get(y[4])))
print("위치 인자 %d개 중 불일치 %d개" % (n, bad))
