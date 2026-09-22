# -*- coding: utf-8 -*-
"""문단형 단위(태그 없이 `글‖⏎` 가 이어지는 줄들)를 줄 수는 그대로 두고
어절 단위로 다시 나눠 폭 한계에 맞춘다. 검사에 걸린 단위에만 쓴다.

사용: python work/tools/rewrap.py        (units.tsv 를 고쳐 쓴다)
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import validate

UNITS = os.path.join(HERE, "..", "trans", "units.tsv")
NL, NUL = "⏎", "‖"
TAG = re.compile(r"\{[0-9A-F]{4}(?::[0-9,]+)?\}")


def wrap(words, n, lim):
    """words 를 n 줄 이하, 줄마다 lim 폭 이하로 나눈다. 안 되면 None."""
    lines, cur = [], ""
    for w in words:
        cand = w if not cur else cur + " " + w
        if validate.width(cand) <= lim:
            cur = cand
        else:
            if not cur:
                return None
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > n:
        return None
    return lines + [""] * (n - len(lines))


def fix(ko, lim):
    parts = ko.split(NL)
    # 앞쪽 연속된 '태그 없는 글‖' 줄을 문단으로 본다
    k = 0
    while k < len(parts) and parts[k].endswith(NUL) and not TAG.search(parts[k]) \
            and parts[k][:-1].strip() and not parts[k].startswith("　"):
        k += 1
    if k < 2:
        return None
    text = " ".join(p[:-1].strip() for p in parts[:k])
    lines = wrap(text.split(), k, lim)
    if lines is None or any(not x for x in lines):
        # 빈 줄이 생기면 원래 줄 수와 어긋나 보이므로 쓰지 않는다
        if lines is None:
            return None
    return NL.join([l + NUL for l in lines] + parts[k:])


def main():
    rows = list(csv.DictReader(open(UNITS, encoding="utf-8"), delimiter="\t",
                               quoting=csv.QUOTE_NONE))
    ul = validate.unit_limits()
    fixed = 0
    for r in rows:
        g, e = int(r["group"]), int(r["entry"])
        if not validate.check(g, r["jp"], r["ko"], e):
            continue
        new = fix(r["ko"], ul.get((g, e), 40))
        if new and not validate.check(g, r["jp"], new, e):
            r["ko"] = new
            fixed += 1
    with open(UNITS, "w", encoding="utf-8", newline="\n") as f:
        f.write("group\tentry\tjp\tko\n")
        for r in rows:
            f.write("%s\t%s\t%s\t%s\n" % (r["group"], r["entry"], r["jp"], r["ko"]))
    print("다시 나눠 고친 단위 %d개" % fixed)


if __name__ == "__main__":
    main()
