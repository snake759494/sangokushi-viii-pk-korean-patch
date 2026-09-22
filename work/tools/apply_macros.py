# -*- coding: utf-8 -*-
"""work/trans/ko/macros.tsv 를 그룹 0 항목에 적용해 units.tsv 의 ko 칸을 채운다."""
import csv, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s8text, units, macro_table

SRC = os.path.join(HERE, "..", "san8", "M_MSG.S8")
KO = os.path.join(HERE, "..", "trans", "ko", "macros.tsv")
UNITS = os.path.join(HERE, "..", "trans", "units.tsv")
TAG = macro_table.TAG


def rebuild(text, kolist):
    """slots() 와 같은 순서로 낱말만 한국어로 바꾼다."""
    out = []
    pos = 0
    it = iter(kolist)
    for m in TAG.finditer(text):
        seg = text[pos:m.start()]
        # ‖ 와 ⏎ 위치를 그대로 두고 낱말만 교체
        buf = []
        for part in re.split(r"([\u2016\u23ce])", seg):
            if part in ("\u2016", "\u23ce", ""):
                buf.append(part)
            else:
                buf.append(next(it))
        out.append("".join(buf))
        out.append(m.group(0))
        pos = m.end()
    seg = text[pos:]
    buf = []
    for part in re.split(r"([\u2016\u23ce])", seg):
        if part in ("\u2016", "\u23ce", ""):
            buf.append(part)
        else:
            buf.append(next(it))
    out.append("".join(buf))
    return "".join(out)


def main():
    args = units.load_args()
    c = s8text.parse_container(open(SRC, "rb").read())
    ko_rows = list(csv.DictReader(open(KO, encoding="utf-8"), delimiter="\t",
                                  quoting=csv.QUOTE_NONE))
    by_idx = {}
    for r in ko_rows:
        by_idx.setdefault(int(r["idx"]), []).append(r["ko"])

    result = {}
    for i, e in enumerate(c.groups[0]):
        t = units.to_text(e, args)
        result[(0, i)] = rebuild(t, by_idx.get(i, []))

    # units.tsv 갱신
    rows = list(csv.DictReader(open(UNITS, encoding="utf-8"), delimiter="\t",
                               quoting=csv.QUOTE_NONE))
    n = 0
    for r in rows:
        k = (int(r["group"]), int(r["entry"]))
        if k in result:
            r["ko"] = result[k]
            n += 1
    with open(UNITS, "w", encoding="utf-8", newline="\n") as f:
        f.write("group\tentry\tjp\tko\n")
        for r in rows:
            f.write("%s\t%s\t%s\t%s\n" % (r["group"], r["entry"], r["jp"], r["ko"]))
    print("그룹 0 항목 %d개 번역 채움" % n)


if __name__ == "__main__":
    main()
