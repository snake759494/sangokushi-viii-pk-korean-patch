# -*- coding: utf-8 -*-
"""작업 파일 하나의 번역 결과를 검사한다.  사용: python work/tools/check_job.py j001"""
import csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import validate

JOBS = os.path.join(HERE, "..", "trans", "jobs")


def main(name):
    name = os.path.basename(name).replace(".tsv", "")
    src = os.path.join(JOBS, name + ".tsv")
    out = os.path.join(JOBS, "out", name + ".tsv")
    jp = {}
    for r in csv.DictReader(open(src, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE):
        jp[r["key"]] = (r["jp"], int(r["limit"]))
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
    missing = [k for k in jp if k not in got or not got[k].strip()]
    bad = []
    for k, v in got.items():
        if k not in jp:
            bad.append("%s: 작업 파일에 없는 키" % k)
            continue
        j, lim = jp[k]
        validate.LIMITS = None
        errs = validate.check_with_limit(j, v, lim)
        if errs:
            bad.append("%s: %s" % (k, " / ".join(errs[:3])))
    print("%s  번역 %d/%d, 빠짐 %d, 오류 %d" % (name, len(got), len(jp), len(missing), len(bad)))
    for m in missing[:20]:
        print("  빠짐 " + m)
    for m in bad[:40]:
        print("  오류 " + m)
    return 1 if (missing or bad) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
