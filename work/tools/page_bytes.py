# -*- coding: utf-8 -*-
"""페이지(= {0021}/{001F} 로 나뉜 구간)별 바이트 수를 원문과 비교한다."""
import csv, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ko_enc
TAG = re.compile(r"\{([0-9A-F]{4})(?::([0-9,]+))?\}")
BRK = ("0021", "001F")


def pages(text):
    """[(페이지 글, [줄들])] - 태그는 빼고 글자만."""
    out, cur = [], ""
    pos = 0
    for m in TAG.finditer(text):
        cur += text[pos:m.start()]
        pos = m.end()
        if m.group(1) in BRK:
            out.append(cur); cur = ""
    cur += text[pos:]
    out.append(cur)
    return out


def nbytes(s, ko):
    s = s.replace("‖", "").replace("⏎", "\n")
    n = 0
    for ch in s:
        if ch == "\n":
            n += 2
        elif ko and "\uac00" <= ch <= "\ud7a3":
            n += 2
        else:
            try:
                n += len(ch.encode("cp932"))
            except UnicodeEncodeError:
                n += 2
    return n


def lines(s):
    return [l for l in s.replace("‖", "").split("⏎")]


if __name__ == "__main__":
    rows = list(csv.DictReader(open(os.path.join(HERE, "..", "trans", "units.tsv"), encoding="utf-8"),
                               delimiter="\t", quoting=csv.QUOTE_NONE))
    for pat in sys.argv[1:]:
        for r in rows:
            if pat in r["ko"]:
                pj, pk = pages(r["jp"]), pages(r["ko"])
                for a, b in zip(pj, pk):
                    if pat in b:
                        print("g%s e%s  원문 %d바이트 / 번역 %d바이트" % (r["group"], r["entry"], nbytes(a, 0), nbytes(b, 1)))
                        print("   JP:", [l for l in lines(a)])
                        print("   KO:", [l for l in lines(b)])
