# -*- coding: utf-8 -*-
"""work/trans/jobs/out/*.tsv 를 units.tsv / elf_strings.tsv 에 합친다.

같은 원문(같은 폭 한계)을 쓰는 다른 단위에도 같은 번역을 넣는다.
"""
import csv, os, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.join(HERE, "..", "trans")
UNITS = os.path.join(TR, "units.tsv")
ELF = os.path.join(TR, "elf_strings.tsv")
OUTDIR = os.path.join(TR, "jobs", "out")


def read_out(prefix):
    got = {}
    for p in sorted(glob.glob(os.path.join(OUTDIR, prefix + "*.tsv"))):
        for line in open(p, encoding="utf-8"):
            line = line.rstrip("\n")
            if not line or line.startswith("key\t"):
                continue
            k, _, v = line.partition("\t")
            if v.strip():
                got[k.strip()] = v
    return got


def merge_units():
    lim = {}
    for line in open(os.path.join(TR, "group_limits.tsv"), encoding="utf-8"):
        if not line.startswith("group"):
            g, l, _ = line.split("\t")
            lim[int(g)] = int(l)
    got = read_out("j")
    rows = list(csv.DictReader(open(UNITS, encoding="utf-8"), delimiter="\t",
                               quoting=csv.QUOTE_NONE))
    # key -> 번역, 그리고 (jp, limit) -> 번역 으로 퍼뜨린다
    by_text = {}
    for r in rows:
        k = "%s:%s" % (r["group"], r["entry"])
        if k in got:
            by_text[(r["jp"], lim.get(int(r["group"]), 40))] = got[k]
    n = 0
    for r in rows:
        if r["ko"].strip():
            continue
        k = "%s:%s" % (r["group"], r["entry"])
        v = got.get(k) or by_text.get((r["jp"], lim.get(int(r["group"]), 40)))
        if v:
            r["ko"] = v
            n += 1

    # 수정(fNNN)·재번역(gNNN) 작업은 기존 번역을 덮어쓴다. g 가 f 보다 나중 판이다.
    fix = read_out("f")
    fix.update(read_out("g"))
    fix.update(read_out("h"))
    fix.update(read_out("w"))
    fix.update(read_out("v"))
    nf = 0
    for r in rows:
        k = "%s:%s" % (r["group"], r["entry"])
        if k in fix and r["ko"] != fix[k]:
            r["ko"] = fix[k]
            nf += 1
    if nf:
        print("단위: 수정본 %d개 적용" % nf)
    with open(UNITS, "w", encoding="utf-8", newline="\n") as f:
        f.write("group\tentry\tjp\tko\n")
        for r in rows:
            f.write("%s\t%s\t%s\t%s\n" % (r["group"], r["entry"], r["jp"], r["ko"]))
    done = sum(1 for r in rows if r["ko"].strip())
    print("단위: 이번에 %d개 채움, 누적 %d/%d" % (n, done, len(rows)))


def merge_elf():
    got = read_out("e")
    rows = list(csv.DictReader(open(ELF, encoding="utf-8"), delimiter="\t",
                               quoting=csv.QUOTE_NONE))
    by_text = {}
    for r in rows:
        if r["offset"] in got:
            by_text[r["jp"]] = got[r["offset"]]
    n = 0
    for r in rows:
        if r["ko"].strip():
            continue
        v = got.get(r["offset"]) or by_text.get(r["jp"])
        if v:
            r["ko"] = v
            n += 1
    with open(ELF, "w", encoding="utf-8", newline="\n") as f:
        f.write("offset\tcap\tjp\tko\n")
        for r in rows:
            f.write("%s\t%s\t%s\t%s\n" % (r["offset"], r["cap"], r["jp"], r["ko"]))
    done = sum(1 for r in rows if r["ko"].strip())
    print("실행파일: 이번에 %d개 채움, 누적 %d/%d" % (n, done, len(rows)))


if __name__ == "__main__":
    merge_units()
    merge_elf()
