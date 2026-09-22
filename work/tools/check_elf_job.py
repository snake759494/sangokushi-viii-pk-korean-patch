# -*- coding: utf-8 -*-
"""실행파일 문자열 작업 결과 검사.  사용: python work/tools/check_elf_job.py e001"""
import csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ko_enc, elf_strings

JOBS = os.path.join(HERE, "..", "trans", "jobs")


def main(name):
    name = os.path.basename(name).replace(".tsv", "")
    src = os.path.join(JOBS, name + ".tsv")
    out = os.path.join(JOBS, "out", name + ".tsv")
    need = {}
    for r in csv.DictReader(open(src, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE):
        need[r["key"]] = (r["jp"], int(r["cap"]))
    if not os.path.exists(out):
        print("결과 파일 없음:", out)
        return 1
    got = {}
    for line in open(out, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("key\t"):
            continue
        k, _, v = line.partition("\t")
        got[k.strip()] = v
    missing = [k for k in need if k not in got]
    bad = []
    for k, v in got.items():
        if k not in need:
            bad.append("%s: 작업 파일에 없는 키" % k)
            continue
        jp, cap = need[k]
        if not v.strip():
            missing.append(k)
            continue
        for ch in v:
            if ch == "\u30fb":      # \uac00\uc6b4\ub383\uc810\uc740 \uadf8\ub300\ub85c \uc4f8 \uc218 \uc788\ub2e4
                continue
            if "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff":
                bad.append("%s: 가나·한자 %r" % (k, ch))
                break
        else:
            try:
                b = ko_enc.encode(elf_strings.unesc(v))
            except ValueError as e:
                bad.append("%s: %s" % (k, e))
                continue
            if len(b) + 1 > cap:
                bad.append("%s: %d B > 용량 %d B (%s)" % (k, len(b) + 1, cap, v))
    print("%s  번역 %d/%d, 빠짐 %d, 오류 %d" % (name, len(got), len(need), len(missing), len(bad)))
    for m in missing[:15]:
        print("  빠짐 " + m)
    for m in bad[:40]:
        print("  오류 " + m)
    return 1 if (missing or bad) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
