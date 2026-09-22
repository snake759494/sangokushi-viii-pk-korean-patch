# -*- coding: utf-8 -*-
"""M_MSG.S8 의 항목을 번역 단위 TSV 로 내보낸다. (work/trans/units.tsv)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s8text, units

SRC = os.path.join(HERE, "..", "san8", "M_MSG.S8")
OUT = os.path.join(HERE, "..", "trans", "units.tsv")

def main():
    args = units.load_args()
    c = s8text.parse_container(open(SRC, "rb").read())
    rows = []
    for g, i, e in units.iter_entries(c, args):
        if not units.has_jp(e):
            continue
        t = units.to_text(e, args)
        rows.append((g, i, t))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("group\tentry\tjp\tko\n")
        for g, i, t in rows:
            f.write("%d\t%d\t%s\t\n" % (g, i, t.replace("\t", " ")))
    jp = sum(len(t) for _, _, t in rows)
    print("번역 단위 %d개, 태그 포함 %d자" % (len(rows), jp))

if __name__ == "__main__":
    main()
