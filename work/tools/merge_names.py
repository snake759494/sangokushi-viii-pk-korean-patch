# -*- coding: utf-8 -*-
"""n*/c*/x* 작업 결과를 이름표와 실행파일 문자열표에 합친다."""
import csv
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.join(HERE, "..", "trans")
OUTDIR = os.path.join(TR, "jobs", "out")


def read_out(prefix):
    got = {}
    for p in sorted(glob.glob(os.path.join(OUTDIR, prefix + "[0-9][0-9][0-9].tsv"))):
        for line in open(p, encoding="utf-8"):
            line = line.rstrip("\n")
            if not line or line.startswith(("no\t", "offset\t")):
                continue
            parts = line.split("\t")
            got[parts[0].strip()] = parts[1:]
    return got


def rows(path):
    return list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t",
                               quoting=csv.QUOTE_NONE))


def main():
    # 무장
    p = os.path.join(TR, "names_officer.tsv")
    got = read_out("n")
    rs = rows(p)
    n = 0
    for r in rs:
        v = got.get(r["no"])
        if not v:
            continue
        v = (v + ["", "", ""])[:3]
        r["ko_sei"], r["ko_mei"], r["ko_azana"] = [x.strip() for x in v]
        n += 1
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("no\tsei\tsei_yomi\tmei\tmei_yomi\tazana\tko_sei\tko_mei\tko_azana\n")
        for r in rs:
            f.write("\t".join(r[k] or "" for k in
                              ("no", "sei", "sei_yomi", "mei", "mei_yomi", "azana",
                               "ko_sei", "ko_mei", "ko_azana")) + "\n")
    print("무장 이름: %d/%d 채움" % (n, len(rs)))

    # 도시
    p = os.path.join(TR, "names_city.tsv")
    got = read_out("c")
    rs = rows(p)
    m = 0
    for r in rs:
        v = got.get(r["no"])
        if v and v[0].strip():
            r["ko"] = v[0].strip()
            m += 1
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("no\tjp\tyomi\tko\n")
        for r in rs:
            f.write("\t".join(r[k] or "" for k in ("no", "jp", "yomi", "ko")) + "\n")
    print("도시 이름: %d/%d 채움" % (m, len(rs)))

    # 실행파일 문자열: x·y 작업 결과를 오프셋으로 채운다
    p = os.path.join(TR, "elf_strings.tsv")
    got = read_out("x")
    got.update(read_out("y"))
    rs = rows(p)
    added = 0
    for r in rs:
        if (r["ko"] or "").strip():
            continue
        v = got.get(r["offset"])
        if v and v[0].strip():
            r["ko"] = v[0].strip()
            added += 1
    rs.sort(key=lambda r: int(r["offset"]))
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("offset\tcap\tjp\tko\n")
        for r in rs:
            f.write("\t".join(str(r[k] or "") for k in ("offset", "cap", "jp", "ko")) + "\n")
    print("실행파일 문자열: %d개 추가, 합계 %d개" % (added, len(rs)))


if __name__ == "__main__":
    main()
