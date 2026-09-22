# -*- coding: utf-8 -*-
"""무장·도시·아이템·관작 이름 번역을 D_SCE.S8 에 넣는다 -> work/patched/D_SCE.S8

  work/trans/names_officer.tsv   무장 레코드(성·이름·자)
  work/trans/dsce_strings.tsv    그 밖의 이름 칸 (도시·시설·아이템·관작·읽기)

가나 읽기는 한글을 그릴 수 없는 작은 가나 전용 글꼴로 나오므로 비운다(9PK 와 같은 방식).
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import d_sce
import elf_strings
import ko_enc

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "work", "san8", "D_SCE.S8")
OUT = os.path.join(ROOT, "work", "patched", "D_SCE.S8")
T_OFF = os.path.join(ROOT, "work", "trans", "names_officer.tsv")
T_STR = os.path.join(ROOT, "work", "trans", "dsce_strings.tsv")
REPORT = os.path.join(ROOT, "work", "trans", "names_report.txt")
BLANK = "<빈칸>"


def rows(path):
    return list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t",
                               quoting=csv.QUOTE_NONE))


def put(data, off, cap, body_len, new):
    """원래 채움 바이트를 되도록 살리며 문자열 칸을 바꾼다."""
    if len(new) + 1 > cap:
        raise ValueError("%d B > 용량 %d B" % (len(new) + 1, cap))
    tail = bytes(data[off + body_len:off + cap])
    need = cap - len(new) - 1
    filler = tail[1:][:need]
    filler += b"\x00" * (need - len(filler))
    data[off:off + cap] = new + b"\x00" + filler


CITY_BASE = 0x7F0
CITIES = ("요동 북평 계 발해 평원 업 진양 상당 제남 북해 복양 진류 하비 소패 초 허창 여남 낙양 "
          "홍농 장안 천수 서평 서량 광릉 수춘 여강 말릉 오 회계 파양 시상 완 신야 양양 상용 강하 "
          "강릉 장사 무릉 계양 영릉 한중 무도 영안 부 파 성도 건녕 영창 삼강").split()


def main():
    data = bytearray(open(SRC, "rb").read())
    log, done, err = [], 0, 0

    base, offs = d_sce.officers(data)
    ko = {int(r["no"]): r for r in rows(T_OFF)}
    for n, o, rec in offs:
        r = ko.get(n)
        if not r:
            continue
        new = dict(rec)
        try:
            for fld, col in (("sei", "ko_sei"), ("mei", "ko_mei"), ("azana", "ko_azana")):
                v = (r.get(col) or "").strip()
                if not rec[fld]:
                    new[fld] = b""
                    continue
                if not v:
                    raise ValueError("%s 번역 없음" % col)
                new[fld] = ko_enc.encode(v)
            new["sei_yomi"] = b""
            new["mei_yomi"] = b""
            d_sce.write_officer(data, o, new)
            done += 1
        except ValueError as ex:
            err += 1
            log.append("무장 %d: %s" % (n, ex))

    sdone = serr = 0
    for r in rows(T_STR):
        off, cap = int(r["offset"]), int(r["cap"])
        body_len = len(elf_strings.unesc(r["jp"]).encode("cp932", "replace"))
        v = (r.get("ko") or "").strip()
        if not v:
            continue
        try:
            new = b"" if v == BLANK else ko_enc.encode(elf_strings.unesc(v))
            put(data, off, cap, body_len, new)
            sdone += 1
        except ValueError as ex:
            serr += 1
            log.append("0x%X %s: %s" % (off, r["jp"], ex))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # 주(州) 표: 0x24 부터 17바이트 레코드 16개 = [이름 5][읽기 7][기타 5]. 읽기(반각 가나)만 비운다
    for k in range(16):
        o = 0x24 + 0x11 * k + 5
        e = data.index(0, o)
        assert e - o <= 7 and all(0xA1 <= x <= 0xDF for x in data[o:e]), (k, bytes(data[o:e]))
        data[o:e] = bytes(e - o)
    # 도시 표: 0x7F0 부터 16바이트 레코드 50개 = [속성 3][번호][이름 5][읽기 7]
    for k, ko in enumerate(CITIES):
        o = CITY_BASE + 16 * k
        assert data[o + 3] == k
        b = ko_enc.encode(ko)
        assert len(b) <= 4, ko
        data[o + 4:o + 16] = b + bytes(12 - len(b))
    open(OUT, "wb").write(bytes(data))
    all_str = rows(T_STR)
    with open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("무장 이름 %d/%d, 오류 %d\n" % (done, len(offs), err))
        f.write("그 밖의 이름 칸 %d/%d, 오류 %d\n" % (sdone, len(all_str), serr))
        for l in log[:200]:
            f.write("  " + l + "\n")
    print(open(REPORT, encoding="utf-8").read()[:1200])
    print("출력:", OUT, os.path.getsize(OUT), "B")


if __name__ == "__main__":
    main()
