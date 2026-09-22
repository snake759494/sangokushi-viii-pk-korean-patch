# -*- coding: utf-8 -*-
"""번역이 비어 있는 단위를 작업 파일로 나눈다 -> work/trans/jobs/jNNN.tsv

같은 원문은 한 번만 번역하도록 묶는다(대표 단위에만 싣는다).
각 줄: key <TAB> 폭한계 <TAB> 원문
"""
import csv, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
UNITS = os.path.join(HERE, "..", "trans", "units.tsv")
LIMS = os.path.join(HERE, "..", "trans", "group_limits.tsv")
JOBS = os.path.join(HERE, "..", "trans", "jobs")
PER_JOB = 110


def main():
    lim = {}
    for line in open(LIMS, encoding="utf-8"):
        if not line.startswith("group"):
            g, l, _ = line.split("\t")
            lim[int(g)] = int(l)
    rows = list(csv.DictReader(open(UNITS, encoding="utf-8"), delimiter="\t",
                               quoting=csv.QUOTE_NONE))
    todo = [r for r in rows if not r["ko"].strip()]
    seen = {}
    reps = []
    for r in todo:
        k = (r["jp"], lim.get(int(r["group"]), 40))
        if k in seen:
            continue
        seen[k] = True
        reps.append(r)
    os.makedirs(JOBS, exist_ok=True)
    for old in os.listdir(JOBS):
        if old.endswith(".tsv"):
            os.remove(os.path.join(JOBS, old))
    n = 0
    for i in range(0, len(reps), PER_JOB):
        chunk = reps[i:i + PER_JOB]
        n += 1
        with open(os.path.join(JOBS, "j%03d.tsv" % n), "w", encoding="utf-8", newline="\n") as f:
            f.write("key\tlimit\tjp\tko\n")
            for r in chunk:
                f.write("%s:%s\t%d\t%s\t\n" % (r["group"], r["entry"],
                                               lim.get(int(r["group"]), 40), r["jp"]))
    print("번역 대기 단위 %d개 -> 중복 제거 %d개 -> 작업 파일 %d개" % (len(todo), len(reps), n))


if __name__ == "__main__":
    main()
