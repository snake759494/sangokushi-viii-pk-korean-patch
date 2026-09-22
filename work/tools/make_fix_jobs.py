# -*- coding: utf-8 -*-
"""검사에 걸린 단위만 모아 수정용 작업 파일을 만든다 -> work/trans/jobs/fNNN.tsv"""
import csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import validate

TR = os.path.join(HERE, "..", "trans")
UNITS = os.path.join(TR, "units.tsv")
JOBS = os.path.join(TR, "jobs")
PER = 40


def main():
    lim = {}
    for line in open(os.path.join(TR, "group_limits.tsv"), encoding="utf-8"):
        if not line.startswith("group"):
            g, l, _ = line.split("\t")
            lim[int(g)] = int(l)
    rows = list(csv.DictReader(open(UNITS, encoding="utf-8"), delimiter="\t",
                               quoting=csv.QUOTE_NONE))
    bad = []
    for r in rows:
        if not r["ko"].strip():
            continue
        e = validate.check(int(r["group"]), r["jp"], r["ko"])
        if e:
            bad.append((r, e))
    for old in os.listdir(JOBS):
        if old.startswith("f") and old.endswith(".tsv"):
            os.remove(os.path.join(JOBS, old))
    n = 0
    for i in range(0, len(bad), PER):
        n += 1
        with open(os.path.join(JOBS, "f%03d.tsv" % n), "w", encoding="utf-8", newline="\n") as f:
            f.write("key\tlimit\terrors\tjp\tko\n")
            for r, e in bad[i:i + PER]:
                f.write("%s:%s\t%d\t%s\t%s\t%s\n" % (
                    r["group"], r["entry"], lim.get(int(r["group"]), 40),
                    " | ".join(x[:60] for x in e[:3]), r["jp"], r["ko"]))
    print("수정 대상 %d단위 -> 작업 파일 %d개" % (len(bad), n))


if __name__ == "__main__":
    main()
