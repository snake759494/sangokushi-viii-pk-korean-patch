# -*- coding: utf-8 -*-
"""그룹 0(말투 매크로 표)의 분기 낱말을 뽑아 번역용 TSV 를 만든다.

매크로 코드 $05XX 는 그룹 0 의 항목 (0x05XX - 0x055A) 을 편다.
각 항목은 {0026:조건}낱말‖⏎{0036}낱말‖⏎... {003B} 구조이고,
조건 번호가 화자 유형(여성·군주 평어·거친 말투·정중 등)을 고른다.
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s8text, units

SRC = os.path.join(HERE, "..", "san8", "M_MSG.S8")
OUT = os.path.join(HERE, "..", "trans", "macros.tsv")
BASE = 0x055A
TAG = re.compile(r"\{([0-9A-F]{4})(?::([0-9,]+))?\}")


def slots(text):
    """태그 사이의 낱말 조각을 (앞태그들, 낱말) 목록으로 돌려준다."""
    out = []
    pos = 0
    pre = []
    for m in TAG.finditer(text):
        seg = text[pos:m.start()]
        for part in re.split(r"[\u2016\u23ce]", seg):
            if part:
                out.append(("".join(pre), part))
                pre = []
        pre.append(m.group(0))
        pos = m.end()
    for part in re.split(r"[\u2016\u23ce]", text[pos:]):
        if part:
            out.append(("".join(pre), part))
            pre = []
    return out


def main():
    args = units.load_args()
    c = s8text.parse_container(open(SRC, "rb").read())
    rows = []
    for i, e in enumerate(c.groups[0]):
        t = units.to_text(e, args)
        for k, (pre, w) in enumerate(slots(t)):
            rows.append((i, BASE + i, k, pre, w))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("idx\tcode\tslot\tcond\tjp\tko\n")
        for i, code, k, pre, w in rows:
            f.write("%d\t%04X\t%d\t%s\t%s\t\n" % (i, code, k, pre, w))
    print("매크로 항목 %d개, 낱말 칸 %d개" % (len(c.groups[0]), len(rows)))


if __name__ == "__main__":
    main()
