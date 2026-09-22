# -*- coding: utf-8 -*-
"""번역을 넣어 M_MSG.S8 과 SLPM_623.19 를 만든다.

입력  work/san8/M_MSG.S8, work/iso/SLPM_623.19
      work/trans/units.tsv        (group, entry, jp, ko)
      work/trans/elf_strings.tsv  (offset, cap, jp, ko)
출력  work/patched/M_MSG.S8, work/patched/SLPM_623.19
      work/trans/build_report.txt
"""
import csv
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s8text, units, ko_enc, elf_strings

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
MSG_SRC = os.path.join(ROOT, "work", "san8", "M_MSG.S8")
ELF_SRC = os.path.join(ROOT, "work", "iso", "SLPM_623.19")
UNITS = os.path.join(ROOT, "work", "trans", "units.tsv")
ELFTSV = os.path.join(ROOT, "work", "trans", "elf_strings.tsv")
OUT = os.path.join(ROOT, "work", "patched")
REPORT = os.path.join(ROOT, "work", "trans", "build_report.txt")

SECTOR = 2048
ELF_TABLE = 0x4EB2A0          # 파일 테이블 (파일 오프셋)
FREE_LBA = 46030              # 원본에서 비어 있는 구간 시작
FREE_END = 100000             # LOGO.PSS 시작


def read_tsv(path):
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        r = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        head = next(r)
        for row in r:
            if len(row) < len(head):
                row += [""] * (len(head) - len(row))
            rows.append(dict(zip(head, row)))
    return rows


def find_entry(elf, name):
    i = 0
    while True:
        namep, _, s, _, e, _, n, _ = struct.unpack_from("<8I", elf, ELF_TABLE + i * 32)
        if not (0x600000 <= namep < 0x610000):
            raise KeyError(name)
        o = namep - 0x100000 + 0x80
        if elf[o:elf.index(b"\0", o)].decode("ascii").lstrip("\\").split(";")[0] == name:
            return i, s, e, n
        i += 1


# 인자가 '그룹 안 바이트 위치'인 제어 코드: {코드: 위치 인자 번호들}
# (그룹 첫 항목 시작부터 센 위치. 원문에서 전부 명령 경계에 떨어짐 - find_offset_codes.py)
OFFSET_CODES = {0x0011: (0,), 0x0013: (0, 1), 0x0015: (0, 1, 2, 3), 0x0019: (0, 1), 0x053B: (1,)}


def _skeleton(e, args):
    """항목의 (뼈대 토큰 시작, 끝) 위치 목록과 코드 토큰 목록."""
    pos, sk = 0, []
    for t, b in s8text.lex(e, args):
        if t != "txt":
            sk.append((pos, pos + len(b), t, b))
        pos += len(b)
    return sk, pos


def fix_offsets(orig, new, args, log, g):
    """번역으로 길이가 바뀐 그룹에서 위치 인자를 새 위치로 옮긴다."""
    m, ob, nb = {}, 0, 0
    for i, (eo, en) in enumerate(zip(orig, new)):
        so, lo = _skeleton(eo, args)
        sn, ln = _skeleton(en, args)
        if len(so) != len(sn):
            log.append("위치 보정: g%d e%d 뼈대 수 다름 (%d/%d)" % (g, i, len(so), len(sn)))
        m[ob] = nb
        for (a0, a1, _, _), (b0, b1, _, _) in zip(so, sn):
            m[ob + a0] = nb + b0
            m[ob + a1] = nb + b1
        m[ob + lo] = nb + ln
        ob += lo
        nb += ln
    out, fixed, miss = [], 0, 0
    for i, en in enumerate(new):
        buf = bytearray(en)
        pos = 0
        for t, b in s8text.lex(en, args):
            if t == "code":
                cid = struct.unpack_from("<H", b, 1)[0]
                for k in OFFSET_CODES.get(cid, ()):
                    at = pos + 3 + 4 * k
                    if at + 4 > pos + len(b):
                        continue
                    v = struct.unpack_from("<I", buf, at)[0]
                    if v in m:
                        if m[v] != v:
                            struct.pack_into("<I", buf, at, m[v])
                            fixed += 1
                    else:
                        miss += 1
                        log.append("위치 보정 실패: g%d e%d 코드 %04X 값 %d" % (g, i, cid, v))
            pos += len(b)
        out.append(bytes(buf))
    return out, fixed, miss


def main():
    args = units.load_args()
    msg = open(MSG_SRC, "rb").read()
    c = s8text.parse_container(msg)
    orig_groups = [list(e) if e else e for e in s8text.parse_container(msg).groups]
    elf = bytearray(open(ELF_SRC, "rb").read())

    log = []
    n_unit = n_ko = n_err = 0
    for row in read_tsv(UNITS):
        n_unit += 1
        ko = row["ko"].strip()
        if not ko:
            continue
        g, i = int(row["group"]), int(row["entry"])
        try:
            c.groups[g][i] = units.from_text(ko, ko_enc.encode)
            n_ko += 1
        except Exception as ex:
            n_err += 1
            log.append("단위 g%d e%d: %s" % (g, i, ex))

    # 점프·호출 위치 보정
    n_fix = n_miss = 0
    for g, ents in enumerate(c.groups):
        if not ents or ents == orig_groups[g]:
            continue
        c.groups[g], f, ms = fix_offsets(orig_groups[g], ents, args, log, g)
        n_fix += f
        n_miss += ms
    log.append("위치 인자 보정 %d개, 실패 %d개" % (n_fix, n_miss))
    print("위치 인자 보정 %d개, 실패 %d개" % (n_fix, n_miss))

    e_all = e_ko = e_err = 0
    for row in read_tsv(ELFTSV):
        e_all += 1
        ko = row["ko"].strip()
        if not ko:
            continue
        off, cap = int(row["offset"]), int(row["cap"])
        try:
            b = ko_enc.encode(elf_strings.unesc(ko))
        except Exception as ex:
            e_err += 1
            log.append("실행파일 0x%X: %s" % (off, ex))
            continue
        if len(b) + 1 > cap:
            e_err += 1
            log.append("실행파일 0x%X: %d B > 용량 %d B (%s)" % (off, len(b) + 1, cap, ko))
            continue
        elf[off:off + cap] = b + b"\0" * (cap - len(b))
        e_ko += 1

    os.makedirs(OUT, exist_ok=True)
    new_msg = c.build()
    secs = (len(new_msg) + SECTOR - 1) // SECTOR
    new_msg += b"\0" * (secs * SECTOR - len(new_msg))

    idx, s0, e0, n0 = find_entry(elf, "M_MSG.S8")
    if secs <= n0:
        place = s0                                   # 제자리
        secs = n0
        new_msg += b"\0" * ((n0 - (len(new_msg) // SECTOR)) * SECTOR)
    else:
        place = FREE_LBA                             # 빈 영역으로 이동
        if place + secs > FREE_END:
            raise SystemExit("빈 영역이 모자랍니다: %d 섹터 필요" % secs)
    struct.pack_into("<I", elf, ELF_TABLE + idx * 32 + 8, place)
    struct.pack_into("<I", elf, ELF_TABLE + idx * 32 + 16, place + secs - 1)
    struct.pack_into("<I", elf, ELF_TABLE + idx * 32 + 24, secs)

    open(os.path.join(OUT, "M_MSG.S8"), "wb").write(new_msg)
    open(os.path.join(OUT, "SLPM_623.19"), "wb").write(bytes(elf))

    with open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("번역 단위 %d/%d, 오류 %d\n" % (n_ko, n_unit, n_err))
        f.write("실행파일 문자열 %d/%d, 오류 %d\n" % (e_ko, e_all, e_err))
        f.write("M_MSG.S8 %d B (%d 섹터) LBA %d..%d %s\n" %
                (len(new_msg), secs, place, place + secs - 1,
                 "제자리" if place == s0 else "재배치"))
        for l in log[:400]:
            f.write("  " + l + "\n")
    print(open(REPORT, encoding="utf-8").read()[:2000])


if __name__ == "__main__":
    main()
