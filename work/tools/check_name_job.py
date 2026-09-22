# -*- coding: utf-8 -*-
"""이름·잔여 문자열 작업 결과 검사.

사용: python work/tools/check_name_job.py n001   (무장)
      python work/tools/check_name_job.py c001   (도시)
      python work/tools/check_name_job.py x001   (실행파일 잔여 문자열)
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ko_enc
import elf_strings

JOBS = os.path.join(HERE, "..", "trans", "jobs")
NAME_CAP = 5          # 姓·名·字 칸: 4바이트 + NUL
CITY_CAP = 0x11


def enc(v):
    return ko_enc.encode(elf_strings.unesc(v))


def bad_chars(v):
    for ch in v:
        if ch == "・":
            continue
        if "぀" <= ch <= "ヿ" or "一" <= ch <= "鿿":
            return "가나·한자 %r" % ch
    return None


def read_out(path):
    got = {}
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith(("no\t", "offset\t")):
            continue
        parts = line.split("\t")
        got[parts[0].strip()] = parts[1:]
    return got


def main(name):
    name = os.path.basename(name).replace(".tsv", "")
    src = os.path.join(JOBS, name + ".tsv")
    out = os.path.join(JOBS, "out", name + ".tsv")
    need = list(csv.DictReader(open(src, encoding="utf-8"), delimiter="\t",
                               quoting=csv.QUOTE_NONE))
    if not os.path.exists(out):
        print("결과 파일 없음:", out)
        return 1
    got = read_out(out)
    kind = name[0]
    missing, bad = [], []
    for r in need:
        key = r["no"] if kind in "nc" else r["offset"]
        v = got.get(key)
        if v is None:
            missing.append(key)
            continue
        if kind == "n":
            vals = (v + ["", "", ""])[:3]
            src_has = (r["sei"], r["mei"], r["azana"])
            for k, (val, orig) in enumerate(zip(vals, src_has)):
                val = val.strip()
                if not orig:
                    continue
                if not val:
                    missing.append("%s[%d]" % (key, k))
                    continue
                e = bad_chars(val)
                if e:
                    bad.append("%s[%d]: %s" % (key, k, e))
                    continue
                try:
                    b = enc(val)
                except ValueError as ex:
                    bad.append("%s[%d]: %s" % (key, k, ex))
                    continue
                if len(b) + 1 > NAME_CAP:
                    bad.append("%s[%d]: %d B > %d B (%s) — 두 글자까지"
                               % (key, k, len(b) + 1, NAME_CAP, val))
        elif kind == "c":
            val = (v[0] if v else "").strip()
            if not val:
                missing.append(key)
                continue
            e = bad_chars(val)
            if e:
                bad.append("%s: %s" % (key, e))
                continue
            try:
                b = enc(val)
            except ValueError as ex:
                bad.append("%s: %s" % (key, ex))
                continue
            if len(b) + 2 > CITY_CAP:
                bad.append("%s: %d B > %d B (%s)" % (key, len(b) + 2, CITY_CAP, val))
        else:
            val = (v[0] if v else "").strip()
            if not val:
                missing.append(key)
                continue
            e = bad_chars(val)
            if e:
                bad.append("%s: %s" % (key, e))
                continue
            try:
                b = enc(val)
            except ValueError as ex:
                bad.append("%s: %s" % (key, ex))
                continue
            cap = int(r["cap"])
            if len(b) + 1 > cap:
                bad.append("%s: %d B > 용량 %d B (%s)" % (key, len(b) + 1, cap, val))
    print("%s  결과 %d/%d, 빠짐 %d, 오류 %d" % (name, len(got), len(need), len(missing), len(bad)))
    for m in missing[:15]:
        print("  빠짐 " + str(m))
    for m in bad[:40]:
        print("  오류 " + m)
    return 1 if (missing or bad) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
