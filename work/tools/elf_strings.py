# -*- coding: utf-8 -*-
"""SLPM_623.19 안의 일본어 UI 문자열을 뽑아 work/trans/elf_strings.tsv 로 낸다.

걸러내는 기준
  1) 문자열 데이터 구간 안 (코드 영역의 우연한 일치 배제)
  2) 앞 4바이트가 적재 구간을 가리키는 포인터 값이 아닐 것 (포인터 표 배제)
  3) CP932 로 디코드될 것
  4) 일본어(한자·히라가나·가타카나·반각 가나) 비율이 기준 이상일 것
     - 반각 가나도 일본어로 센다 (ｱｲﾃﾑ情報 같은 문자열을 놓치지 않으려고)
     - 버튼 아이콘 등 사설 영역과 공백·숫자·서식(%d)·문장부호는 셈에서 뺀다
     - 반각 가나 한 글자뿐인 것은 데이터 조각으로 보고 버린다
  5) 코드에서 주소가 참조될 것 (실제로 쓰이는 문자열만)
`cap` 은 다음 비영(非零) 바이트까지의 여유로, 번역문 바이트 수 한계다.
여러 줄 문자열이 있으므로 TSV 에는 줄바꿈·탭을 역슬래시로 이스케이프해 적는다.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SRC = os.path.join(HERE, "..", "iso", "SLPM_623.19")
OUT = os.path.join(HERE, "..", "trans", "elf_strings.tsv")

SEG = (0x100000, 0x628900)
REGION = (0x4D0000, 0x520000)
PUA_LO, PUA_HI = 0xE000, 0xF8FF
HALF_KANA_LO, HALF_KANA_HI = 0xFF61, 0xFF9F
JP_PUNCT = set(map(ord, "　、。・！？「」"
                        "（）：％／±→←"))
NEUTRAL_ASCII = set(" \t\n\r\x1b[]()<>/:.,-+*#%_=|")

ESCAPES = {"\\": "\\\\", "\t": "\\t", "\n": "\\n", "\r": "\\r"}
UNESCAPES = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\"}
FMT = re.compile(r"%[-+ #0]*[0-9]*(?:\.[0-9]+)?[diouxXeEfgGcs%]")


def esc(s):
    return "".join(ESCAPES.get(ch, ch) for ch in s)


def unesc(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append(UNESCAPES.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def is_lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xFC


def scan(d):
    out, n, i = [], len(d), 0
    while i < n:
        if d[i] == 0:
            i += 1
            continue
        j, jp, ok = i, False, True
        while j < n and d[j] != 0:
            b = d[j]
            if is_lead(b) and j + 1 < n and 0x40 <= d[j + 1] <= 0xFC and d[j + 1] != 0x7F:
                jp = True
                j += 2
            elif 0x20 <= b <= 0x7E or b in (0x1B, 0x0A):
                j += 1
            elif 0xA1 <= b <= 0xDF:
                jp = True
                j += 1
            else:
                ok = False
                break
        if ok and jp and j > i:
            k = j
            while k < n and d[k] == 0:
                k += 1
            out.append((i, d[i:j], k - i))
            i = k
        else:
            i = j + 1 if j > i else i + 1
    return out


def is_jp(ch):
    c = ord(ch)
    return (0x3040 <= c <= 0x30FF            # 히라가나·가타카나
            or 0x4E00 <= c <= 0x9FFF         # 한자
            or HALF_KANA_LO <= c <= HALF_KANA_HI
            or 0xFF01 <= c <= 0xFF60         # 전각 영숫자·기호
            or c in JP_PUNCT)


def is_neutral(ch):
    c = ord(ch)
    return ch in NEUTRAL_ASCII or ch.isdigit() or PUA_LO <= c <= PUA_HI


def quality(s):
    s = FMT.sub("", s)
    body = [ch for ch in s if not is_neutral(ch)]
    if not body:
        return 0.0
    # 반각 가나 한 글자뿐이면 데이터 조각으로 본다
    wide = [ch for ch in body if not (HALF_KANA_LO <= ord(ch) <= HALF_KANA_HI)]
    if len(body) < 2 and not any(is_jp(ch) for ch in wide):
        return 0.0
    return sum(1 for ch in body if is_jp(ch)) / len(body)


def ui_strings(d, refs=None, min_quality=0.5):
    rows = []
    for off, b, cap in scan(d):
        if not (REGION[0] <= off < REGION[1]):
            continue
        if off + 4 <= len(d):
            v = struct.unpack_from("<I", d, off)[0]
            if SEG[0] <= v < SEG[1]:
                continue
        try:
            s = b.decode("cp932")
        except UnicodeDecodeError:
            continue
        if quality(s) < min_quality:
            continue
        if refs is not None and (off - 0x80 + 0x100000) not in refs:
            continue
        rows.append((off, s, cap))
    return rows


def main():
    import elf_refs
    d = open(SRC, "rb").read()
    refs = elf_refs.refs(d)
    rows = ui_strings(d, refs)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("offset\tcap\tjp\tko\n")
        for off, s, cap in rows:
            f.write("%d\t%d\t%s\t\n" % (off, cap, esc(s)))
    print("실행파일 일본어 문자열 %d개" % len(rows))


if __name__ == "__main__":
    main()
