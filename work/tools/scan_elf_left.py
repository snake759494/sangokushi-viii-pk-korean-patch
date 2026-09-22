# -*- coding: utf-8 -*-
"""패치된 실행파일에 '아직 일본어인' 문자열을 찾는다.

한글은 한자 슬롯 코드로 적히므로 패치본만 봐서는 한자와 구분되지 않는다.
그래서 **원본과 견주어** 바뀌지 않은 자리 가운데 한자가 든 것을 고른다.

거르는 조건
  1) 문자열 데이터 구간 안
  2) 앞 4바이트가 적재 구간 포인터가 아닐 것
  3) 패치본이 원본과 같을 것 (= 손대지 않은 문자열)
  4) 한글로 덮인 슬롯(0x889F~0x94FC)의 한자를 품을 것 (= 화면에서 깨진다)
  5) 코드에서 주소가 참조될 것
-> work/trans/elf_left.tsv
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import elf_refs
import elf_strings

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
ORIG = os.path.join(ROOT, "work", "iso", "SLPM_623.19")
PATCHED = os.path.join(ROOT, "work", "patched", "SLPM_623.19")
OUT = os.path.join(ROOT, "work", "trans", "elf_left.tsv")

KO_LO, KO_HI = 0x889F, 0x94FC          # 한글로 덮인 슬롯


def overwritten_kanji(b):
    n, i = 0, 0
    while i < len(b) - 1:
        if elf_strings.is_lead(b[i]):
            if KO_LO <= (b[i] << 8 | b[i + 1]) <= KO_HI:
                n += 1
            i += 2
        else:
            i += 1
    return n


def main():
    o = open(ORIG, "rb").read()
    p = open(PATCHED, "rb").read()
    refs = elf_refs.refs(o)
    rows = []
    for off, b, cap in elf_strings.scan(o):
        if not (elf_strings.REGION[0] <= off < elf_strings.REGION[1]):
            continue
        if off + 4 <= len(o):
            v = struct.unpack_from("<I", o, off)[0]
            if elf_strings.SEG[0] <= v < elf_strings.SEG[1]:
                continue
        if p[off:off + cap] != o[off:off + cap]:
            continue                       # 이미 번역한 자리
        if not overwritten_kanji(b):
            continue
        try:
            s = b.decode("cp932")
        except UnicodeDecodeError:
            continue
        if elf_strings.quality(s) < 0.4:
            continue
        rows.append((off, cap, s, elf_refs.o2v(off) in refs))
    rows.sort()
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("offset\tcap\tref\tjp\tko\n")
        for off, cap, s, r in rows:
            f.write("%d\t%d\t%d\t%s\t\n" % (off, cap, int(r), elf_strings.esc(s)))
    ref = sum(1 for r in rows if r[3])
    print("손대지 않은 채 남은 일본어 문자열 %d개 (코드 참조 %d개) -> %s" % (len(rows), ref, OUT))


if __name__ == "__main__":
    main()
