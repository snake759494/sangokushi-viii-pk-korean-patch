# -*- coding: utf-8 -*-
"""D_SCE.S8 의 무장·도시 이름을 번역용 TSV 로 내보낸다.

  work/trans/names_officer.tsv  no / 姓 / 姓읽기 / 名 / 名읽기 / 字 / ko_sei / ko_mei / ko_azana
  work/trans/names_city.tsv     no / 이름 / 읽기 / ko

코에이 외자(사용자 정의 영역 0xF040~)는 유니코드로 못 읽으므로 `〓{코드}` 로 적는다.
가나 읽기는 한글을 그릴 수 없어 비운다(9PK 와 같은 방식).
칸 크기가 전각 2자(4바이트)라 한국어도 두 글자까지만 쓸 수 있다.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import d_sce

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "work", "san8", "D_SCE.S8")
OUT_O = os.path.join(ROOT, "work", "trans", "names_officer.tsv")
OUT_C = os.path.join(ROOT, "work", "trans", "names_city.tsv")


def dec(b):
    """외자는 〓{코드} 로 표시한다."""
    out, i = [], 0
    while i < len(b):
        if d_sce.is_lead(b[i]) and i + 1 < len(b):
            code = (b[i] << 8) | b[i + 1]
            ch = b[i:i + 2]
            if 0xF040 <= code <= 0xF9FC:
                out.append("〓{%04X}" % code)
            else:
                try:
                    out.append(ch.decode("cp932"))
                except UnicodeDecodeError:
                    out.append("〓{%04X}" % code)
            i += 2
        else:
            out.append(chr(b[i]))
            i += 1
    return "".join(out)


def main():
    d = open(SRC, "rb").read()
    base, offs = d_sce.officers(d)
    with open(OUT_O, "w", encoding="utf-8", newline="\n") as f:
        f.write("no\tsei\tsei_yomi\tmei\tmei_yomi\tazana\tko_sei\tko_mei\tko_azana\n")
        for n, o, r in offs:
            f.write("%d\t%s\t%s\t%s\t%s\t%s\t\t\t\n" % (
                n, dec(r["sei"]), dec(r["sei_yomi"]), dec(r["mei"]),
                dec(r["mei_yomi"]), dec(r["azana"])))
    cs = d_sce.cities(d)
    with open(OUT_C, "w", encoding="utf-8", newline="\n") as f:
        f.write("no\tjp\tyomi\tko\n")
        for n, o, nm, ym in cs:
            f.write("%d\t%s\t%s\t\n" % (n, dec(nm), dec(ym)))
    gaiji = sum(1 for n, o, r in offs
                if any("〓" in dec(r[k]) for k in ("sei", "mei", "azana")))
    print("무장 %d명 (외자 포함 %d명) -> %s" % (len(offs), gaiji, OUT_O))
    print("도시/지역 %d개 -> %s" % (len(cs), OUT_C))


if __name__ == "__main__":
    main()
