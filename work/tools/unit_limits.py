# -*- coding: utf-8 -*-
"""단위마다 번역 줄 폭 한계를 정한다 -> work/trans/unit_limits.tsv

원문은 화면 상자에 맞춰 줄이 나뉘어 있으므로, **그 단위 안 가장 긴 원문 줄**이
상자 폭에 가장 가까운 추정값이다. 그룹 전체의 최대치를 쓰면 한 줄짜리 예외 때문에
한계가 너무 느슨해져 글자가 상자 밖으로 나간다(시나리오 개요·연표에서 확인).

  여러 줄 단위 : limit = max(단위 원문 최대, min(그룹 90퍼센타일, 28))
  한 줄 단위   : limit = 그룹 90퍼센타일 (그 화면의 흔한 폭)
어느 쪽이든 그룹 최대를 넘지 않는다.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s8text
import units
import validate

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "work", "san8", "M_MSG.S8")
OUT = os.path.join(ROOT, "work", "trans", "unit_limits.tsv")
TAG = re.compile(r"\{[0-9A-F]{4}(?::[0-9,]+)?\}")
NL, NUL = "⏎", "‖"
FLOOR = 28


def plain_lines(text):
    for ln in text.split(NL):
        p = TAG.sub("", ln).replace(NUL, "")
        if p.strip():
            yield p


def percentile(xs, q):
    if not xs:
        return 0
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))]


def compute():
    args = units.load_args()
    c = s8text.parse_container(open(SRC, "rb").read())
    per_group = {}
    per_unit = {}
    for g, i, e in units.iter_entries(c, args):
        t = units.to_text(e, args)
        ws = [validate.width(p) for p in plain_lines(t)]
        if not ws:
            continue
        per_group.setdefault(g, []).extend(ws)
        per_unit[(g, i)] = (max(ws), len(ws))
    gp90 = {g: percentile(ws, 0.90) for g, ws in per_group.items()}
    gmax = {g: max(ws) for g, ws in per_group.items()}
    out = {}
    for (g, i), (umax, n) in per_unit.items():
        if g == 0:
            continue                    # 그룹 0 은 말투 매크로 조각이라 줄 폭 개념이 없다
        if n >= 2:
            lim = max(umax, min(gp90[g], FLOOR))
        else:
            lim = max(gp90[g], umax)
        out[(g, i)] = min(lim, gmax[g])
    return out


def main():
    out = compute()
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("group\tentry\tlimit\n")
        for (g, i), lim in sorted(out.items()):
            f.write("%d\t%d\t%d\n" % (g, i, lim))
    import collections
    h = collections.Counter(out.values())
    print("단위 %d개, 폭 한계 분포 %s" % (len(out), sorted(h.items())[:12]))


if __name__ == "__main__":
    main()
