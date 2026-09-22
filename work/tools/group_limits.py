# -*- coding: utf-8 -*-
"""그룹마다 원문 줄의 최대 폭을 재어 번역 줄 폭 한계로 삼는다.

같은 그룹은 같은 화면에 그려지므로, 그 화면은 적어도 원문의 가장 긴 줄만큼
넓다. 그 폭을 넘지 않으면 잘릴 일이 없다. -> work/trans/group_limits.tsv
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s8text, units

SRC = os.path.join(HERE, "..", "san8", "M_MSG.S8")
OUT = os.path.join(HERE, "..", "trans", "group_limits.tsv")
TAG = re.compile(r"\{[0-9A-F]{4}(?::[0-9,]+)?\}")
MIN_LIMIT = 24          # 대사·메시지 화면의 최소 보장 폭


def width(s):
    t = 0
    for ch in s:
        if "\uac00" <= ch <= "\ud7a3":
            t += 2
        else:
            try:
                t += 2 if len(ch.encode("cp932")) == 2 else 1
            except UnicodeEncodeError:
                t += 2
    return t


def plain_lines(text):
    for line in text.split("\u23ce"):
        yield TAG.sub("", line).replace("\u2016", "")


def main():
    args = units.load_args()
    c = s8text.parse_container(open(SRC, "rb").read())
    mx = {}
    for g, i, e in units.iter_entries(c, args):
        t = units.to_text(e, args)
        for p in plain_lines(t):
            if p.strip():
                mx[g] = max(mx.get(g, 0), width(p))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("group\tlimit\traw_max\n")
        for g in sorted(mx):
            f.write("%d\t%d\t%d\n" % (g, max(mx[g], MIN_LIMIT), mx[g]))
    import collections
    h = collections.Counter(max(v, MIN_LIMIT) for v in mx.values())
    print("그룹 %d개, 폭 한계 분포: %s" % (len(mx), sorted(h.items())[:14]))


if __name__ == "__main__":
    main()
