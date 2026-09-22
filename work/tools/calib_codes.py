# -*- coding: utf-8 -*-
"""$코드별 인자 바이트 수(0/4/8/...)를 판정해 work/trans/code_args.txt 에 쓴다.

인자는 리틀엔디언 u32 이고 값이 65536 미만이라 항상 `xx xx 00 00` 꼴이다.
코드마다 인자 칸을 하나씩 늘려 가며, 그 칸이 전체 출현의 90% 이상에서
이 꼴이면 인자로 인정한다. 그 뒤 CP932 로 디코드되지 않는 텍스트 토큰이
남으면 그 앞 코드의 인자 칸을 하나 더 늘려 다시 검사한다.
"""
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s8text

SRC = os.path.join(HERE, "..", "san8", "M_MSG.S8")
OUT = os.path.join(HERE, "..", "trans", "code_args.txt")
MAX_SLOTS = 4
THRESH = 0.90


def occurrences(entries):
    """코드별 출현 위치(각 항목 안 바이트 오프셋)."""
    pos = collections.defaultdict(list)
    for e in entries:
        i = 0
        while True:
            i = e.find(b"\x24", i)
            if i < 0 or i + 3 > len(e):
                break
            pos[struct.unpack_from("<H", e, i + 1)[0]].append((e, i))
            i += 1
    return pos


def slot_ok(e, o):
    return o + 4 <= len(e) and e[o + 2] == 0 and e[o + 3] == 0 and e[o] != 0x24


def main():
    data = open(SRC, "rb").read()
    c = s8text.parse_container(data)
    entries = [x for g in c.groups if g for x in g]
    pos = occurrences(entries)

    args = {}
    for cid, lst in pos.items():
        slots = 0
        while slots < MAX_SLOTS:
            o = 3 + slots * 4
            good = sum(1 for e, i in lst if slot_ok(e, i + o))
            if good < THRESH * len(lst):
                break
            slots += 1
        if slots:
            args[cid] = slots * 4

    for it in range(1, 30):
        bump = set()
        for e in entries:
            toks = s8text.lex(e, args)
            for j, (k, v) in enumerate(toks):
                if k != "txt":
                    continue
                try:
                    v.decode("cp932")
                except UnicodeDecodeError:
                    if j and toks[j - 1][0] == "code":
                        cid = struct.unpack_from("<H", toks[j - 1][1], 1)[0]
                        if args.get(cid, 0) < MAX_SLOTS * 4:
                            bump.add(cid)
        if not bump:
            print("%d회 반복 후 수렴" % (it - 1))
            break
        for cid in bump:
            args[cid] = args.get(cid, 0) + 4
        print("  반복 %d: 코드 %d개 인자 칸 증가" % (it, len(bump)))

    left = []
    for gi, e in enumerate(entries):
        for k, v in s8text.lex(e, args):
            if k == "txt":
                try:
                    v.decode("cp932")
                except UnicodeDecodeError:
                    left.append((gi, v[:8].hex()))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("# $코드\t인자 바이트 수\t출현 횟수\n")
        for cid in sorted(pos):
            f.write("%d\t%d\t%d\n" % (cid, args.get(cid, 0), len(pos[cid])))
    print("코드 %d종, 인자 있는 코드 %d종, 남은 디코드 실패 %d" %
          (len(pos), sum(1 for v in args.values() if v), len(left)))
    for x in left[:10]:
        print("  남음", x)


if __name__ == "__main__":
    main()
