# -*- coding: utf-8 -*-
"""D_SCE.S8 에서 무장 레코드 밖의 이름 표(도시·시설·아이템·관작)를 찾아 뽑는다.

이 파일의 이름 표는 **고정 길이 레코드**가 줄지어 있고, 레코드 앞에 1바이트
번호가 붙는 경우가 많다. 그 번호 값이 Shift-JIS 선두 바이트 범위(0x81~0x9F)라
단순히 '전각 글자에서 시작' 하는 식으로 훑으면 한 칸 밀린 가짜 문자열이 잡히고,
그대로 써 넣으면 번호 바이트를 덮어 레코드가 깨진다.

그래서 **스트라이드와 위상(phase)을 먼저 찾는다**: 어떤 간격으로 같은 자리에
Shift-JIS 이름 + NUL 이 이어지면 그 구간을 표로 본다.

-> work/trans/dsce_strings.tsv  (offset / cap / kind / jp / ko)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import d_sce
import elf_strings

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "work", "san8", "D_SCE.S8")
OUT = os.path.join(ROOT, "work", "trans", "dsce_strings.tsv")

STRIDES = (9, 11, 13, 17, 21, 12, 16, 10, 0x11)
MIN_RUN = 4                     # 이만큼 이어져야 표로 본다


def name_at(d, o, limit):
    """o 에서 시작하는 '전각/반각가나 + NUL' 이름. (바이트, 이름길이) 또는 None."""
    j = o
    n = min(len(d), o + limit)
    while j < n:
        c = d[j]
        if d_sce.is_lead(c) and j + 1 < n and 0x40 <= d[j + 1] <= 0xFC and d[j + 1] != 0x7F:
            j += 2
        elif 0xA1 <= c <= 0xDF or c == 0x20:
            j += 1
        else:
            break
    body = d[o:j].rstrip(b"\x20")
    if not body or j >= n or d[j] != 0x00:
        return None
    try:
        s = body.decode("cp932")
    except UnicodeDecodeError:
        return None
    if elf_strings.quality(s) < 0.6:
        return None
    return body, j - o


def find_tables(d, stop):
    """[(시작, 스트라이드, 개수, 이름칸 크기)]"""
    tables = []
    covered = bytearray(stop)
    for stride in STRIDES:
        o = 0
        while o < stop - stride * MIN_RUN:
            if covered[o]:
                o += 1
                continue
            r = name_at(d, o, stride)
            if not r:
                o += 1
                continue
            k = 1
            while o + k * stride < stop and name_at(d, o + k * stride, stride):
                k += 1
            if k >= MIN_RUN:
                # 앞쪽으로도 이어지는지 본다
                s = o
                while s - stride >= 0 and name_at(d, s - stride, stride):
                    s -= stride
                    k += 1
                tables.append((s, stride, k))
                for p in range(s, min(stop, s + k * stride)):
                    covered[p] = 1
                o = s + k * stride
            else:
                o += 1
    tables.sort()
    return tables


def main():
    d = open(SRC, "rb").read()
    base = d_sce.find_first_record(d)
    rows = []
    seen = set()
    for start, stride, count in find_tables(d, base):
        for k in range(count):
            o = start + k * stride
            r = name_at(d, o, stride)
            if not r or o in seen:
                continue
            body, ln = r
            seen.add(o)
            # 용량: 이름 뒤 NUL·공백까지
            e = o + ln
            while e < base and d[e] in (0x00, 0x20):
                e += 1
            cap = min(e - o, stride)
            s = body.decode("cp932")
            kana = all(0xFF61 <= ord(ch) <= 0xFF9F or ch == " " for ch in s)
            rows.append((o, cap, "yomi" if kana else "text", s))
    # 앞 항목 범위 안에서 다시 잡힌 것(한 칸 밀린 가짜)은 버린다
    rows.sort()
    clean, end = [], -1
    for o, cap, kind, s in rows:
        if o < end:
            continue
        clean.append((o, cap, kind, s))
        end = o + cap
    rows = clean
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("offset\tcap\tkind\tjp\tko\n")
        for o, cap, kind, s in rows:
            f.write("%d\t%d\t%s\t%s\t%s\n" % (o, cap, kind, elf_strings.esc(s),
                                              "<빈칸>" if kind == "yomi" else ""))
    ntext = sum(1 for r in rows if r[2] == "text")
    print("이름 표 문자열 %d개 (번역 대상 %d, 읽기 %d) -> %s"
          % (len(rows), ntext, len(rows) - ntext, OUT))


if __name__ == "__main__":
    main()
